"""Changing a handful of cells in an .xlsx without rewriting the workbook.

openpyxl reads a workbook and writes a new one from what it understood. Formulas keep their text but lose the
result Excel stored with them, so every formula cell reads as blank until someone opens the file in Excel and
saves it; anything openpyxl doesn't model (the conditional-formatting extension, for one) is dropped as well.
`pull` only ever changes a few cells, so it edits those cells in the sheet's XML and copies every other part of
the zip across untouched: formulas, their stored results, formatting and validation all survive.

Excel is told to recalculate on load, since a number written over a cell other formulas depend on leaves their
stored results out of date.
"""
from __future__ import annotations

import re
import shutil
import tempfile
import zipfile
from pathlib import Path


class Unsupported(Exception):
    """Something in this workbook (or this value) isn't safe to edit in place: use openpyxl instead."""


def column_index(ref):
    """'AB12' -> 28."""
    n = 0
    for ch in re.match(r"[A-Z]+", ref).group(0):
        n = n * 26 + ord(ch) - 64
    return n


def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _cell(ref, value, style):
    s = f' s="{style}"' if style else ""
    if value is None or value == "":
        return f'<c r="{ref}"{s}/>'
    if isinstance(value, bool):
        raise Unsupported(f"{ref}: true/false isn't written in place")
    if isinstance(value, (int, float)):
        return f'<c r="{ref}"{s}><v>{value:g}</v></c>'
    if isinstance(value, str):
        return f'<c r="{ref}"{s} t="inlineStr"><is><t xml:space="preserve">{_esc(value)}</t></is></c>'
    raise Unsupported(f"{ref}: values of type {type(value).__name__} aren't written in place")


def _find(xml, ref):
    """(start, end, attributes) of the <c r="REF"> element, or None."""
    for m in re.finditer(r'<c\s+r="%s"(\s[^>]*?)?(/>|>)' % re.escape(ref), xml):
        attrs = m.group(1) or ""
        if m.group(2) == "/>":
            return m.start(), m.end(), attrs
        close = xml.index("</c>", m.end())
        return m.start(), close + 4, attrs
    return None


def _row_span(xml, row):
    """(start of the row's content, end) for inserting a cell, creating the row if it isn't there."""
    m = re.search(r'<row\s+r="%d"(\s[^>]*?)?(/>|>)' % row, xml)
    if m and m.group(2) == ">":
        return m.end(), xml.index("</row>", m.end()), xml
    if m:  # an empty self-closing row: open it up
        xml = xml[:m.start()] + f'<row r="{row}"{m.group(1) or ""}></row>' + xml[m.end():]
        return _row_span(xml, row)
    raise Unsupported(f"row {row} isn't in the sheet")


def _put(xml, ref, value):
    """The sheet XML with this cell set, and the formula it replaced (None if it held none)."""
    row = int(re.search(r"\d+", ref).group(0))
    found = _find(xml, ref)
    was = None
    if found:
        start, end, attrs = found
        old = xml[start:end]
        if 't="shared"' in old:
            raise Unsupported(f"{ref}: holds a shared formula, which other cells refer to")
        f = re.search(r"<f[^>]*>(.*?)</f>", old, re.S)
        was = "=" + f.group(1) if f else None
        style = (re.search(r'\ss="(\d+)"', attrs) or [None, None])[1]
        return xml[:start] + _cell(ref, value, style) + xml[end:], was
    start, end, xml = _row_span(xml, row)
    at, mine = end, column_index(ref)
    for m in re.finditer(r'<c\s+r="([A-Z]+\d+)"', xml[start:end]):
        if column_index(m.group(1)) > mine:
            at = start + m.start()
            break
    return xml[:at] + _cell(ref, value, None) + xml[at:], None


def _parts(z):
    """{sheet name: the zip entry holding it}."""
    book = z.read("xl/workbook.xml").decode("utf-8")
    rels = z.read("xl/_rels/workbook.xml.rels").decode("utf-8")
    target = {}
    for rel in re.finditer(r"<Relationship\b[^>]*>", rels):  # the attributes come in no particular order
        rid, dest = re.search(r'Id="([^"]+)"', rel.group(0)), re.search(r'Target="([^"]+)"', rel.group(0))
        if rid and dest:
            target[rid.group(1)] = dest.group(1)
    out = {}
    for m in re.finditer(r"<sheet\b[^>]*>", book):
        name = re.search(r'name="([^"]*)"', m.group(0))
        rid = re.search(r'r:id="([^"]*)"', m.group(0))
        if name and rid and rid.group(1) in target:
            part = target[rid.group(1)].lstrip("/")
            out[name.group(1)] = part if part.startswith("xl/") else "xl/" + part
    return out


def _recalculate(book):
    """Tell Excel to recalculate everything next time it opens the file."""
    if "fullCalcOnLoad" in book:
        return book
    if "<calcPr" in book:
        return re.sub(r"<calcPr\b([^>]*?)/>", r'<calcPr\1 fullCalcOnLoad="1"/>', book, count=1)
    return book.replace("</workbook>", '<calcPr calcId="191029" fullCalcOnLoad="1"/></workbook>')


def write_cells(path, changes):
    """Set {sheet name: {cell ref: value}} in place. Returns ({(sheet, ref): the formula it replaced}, how many
    formulas the workbook still holds).

    Raises Unsupported if this workbook or value isn't safe to edit this way; the file is left alone. Anything
    the caller didn't name is copied across byte for byte.
    """
    path = Path(path)
    edited, replaced = {}, {}
    with zipfile.ZipFile(path) as z:
        parts = _parts(z)
        for sheet, cells in changes.items():
            if not cells:
                continue
            if sheet not in parts:
                raise Unsupported(f"no sheet called {sheet}")
            xml = z.read(parts[sheet]).decode("utf-8")
            for ref, value in cells.items():
                xml, was = _put(xml, ref, value)
                if was:
                    replaced[(sheet, ref)] = was
            edited[parts[sheet]] = xml.encode("utf-8")
        formulas = 0
        if edited:  # a number written over a cell other formulas read leaves their stored results out of date
            edited["xl/workbook.xml"] = _recalculate(z.read("xl/workbook.xml").decode("utf-8")).encode("utf-8")
            formulas = sum(z.read(p).count(b"<f>") + z.read(p).count(b"<f ")  # not <formula1>, from validation
                           for p in parts.values())
        raw = {n: z.read(n) for n in z.namelist()}
    work = Path(tempfile.mkdtemp())
    try:
        tmp = work / path.name
        with zipfile.ZipFile(path) as z, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
            for info in z.infolist():
                out.writestr(info, edited.get(info.filename, raw[info.filename]))
        shutil.move(str(tmp), str(path))  # not os.replace: the temp folder is often on another drive
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return replaced, formulas
