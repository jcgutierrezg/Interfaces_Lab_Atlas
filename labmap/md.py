"""Just enough Markdown for the SOPs: front matter, headings, paragraphs, lists (with checkboxes), tables,
block quotes, bold, italic, code, links, and [[ID]] links into the directory."""
from __future__ import annotations

import html
import re

LIST = re.compile(r"\s*([-*+]|\d+[.)])\s+")
BLOCK_START = re.compile(r"(#{1,6}\s|>|\s*\||\s*([-*+]|\d+[.)])\s+)")


def front_matter(text):
    """({key: value or [values]}, body) from a document starting with a --- block."""
    meta, body = {}, text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            block, body = text[3:end], text[end + 4:].lstrip("\n")
            for line in block.splitlines():
                line = re.split(r"\s+#", line, maxsplit=1)[0].rstrip()
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                value = value.strip()
                if value.startswith("[") and value.endswith("]"):
                    value = [v.strip() for v in value[1:-1].split(",") if v.strip()]
                meta[key.strip()] = value
    return meta, body


def plain(text):
    """Searchable text: the words without the Markdown."""
    return re.sub(r"\s+", " ", re.sub(r"[#>*`|_\[\]]|-{3,}", " ", text)).strip()


def inline(s, link):
    s = html.escape(s, quote=False)
    s = re.sub(r"\[\[([^\]]+)\]\]", lambda m: link(m.group(1).strip()), s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    return re.sub(r"(?<![*\w])\*([^*\s][^*]*?)\*(?![*\w])", r"<em>\1</em>", s)


def _table(rows, link):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    head = None
    if len(cells) > 1 and all(re.fullmatch(r":?-{2,}:?", c) for c in cells[1] if c):
        head, cells = cells[0], cells[2:]
    out = ["<table>"]
    if head:
        out.append("<thead><tr>" + "".join(f"<th>{inline(c, link)}</th>" for c in head) + "</tr></thead>")
    out.append("<tbody>" + "".join("<tr>" + "".join(f"<td>{inline(c, link)}</td>" for c in r) + "</tr>" for r in cells))
    return "".join(out) + "</tbody></table>"


def render(text, link):
    """HTML for a Markdown body. link(id) returns the HTML for a [[id]] reference."""
    lines, out, i = text.splitlines(), [], 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
        elif m := re.match(r"(#{1,6})\s+(.*)", line):
            n = len(m.group(1))
            out.append(f"<h{n}>{inline(m.group(2), link)}</h{n}>")
            i += 1
        elif line.startswith(">"):
            block = []
            while i < len(lines) and lines[i].startswith(">"):
                block.append(lines[i][1:].lstrip())
                i += 1
            out.append(f"<blockquote>{render(chr(10).join(block), link)}</blockquote>")
        elif re.match(r"\s*\|", line):
            rows = []
            while i < len(lines) and re.match(r"\s*\|", lines[i]):
                rows.append(lines[i])
                i += 1
            out.append(_table(rows, link))
        elif LIST.match(line):
            ordered, items = bool(re.match(r"\s*\d", line)), []
            while i < len(lines) and LIST.match(lines[i]):
                items.append(LIST.sub("", lines[i], count=1))
                i += 1
                while i < len(lines) and lines[i].startswith("  ") and lines[i].strip() and not LIST.match(lines[i]):
                    items[-1] += " " + lines[i].strip()
                    i += 1
            lis = []
            for item in items:
                box = re.match(r"\[( |x|X)\]\s*(.*)", item)
                if box:
                    tick = " checked" if box.group(1) != " " else ""
                    lis.append(f'<li class="task"><input type="checkbox" disabled{tick}> {inline(box.group(2), link)}</li>')
                else:
                    lis.append(f"<li>{inline(item, link)}</li>")
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>{''.join(lis)}</{tag}>")
        else:
            para = []
            while i < len(lines) and lines[i].strip() and not BLOCK_START.match(lines[i]):
                para.append(lines[i].strip())
                i += 1
            if not para:  # a line the block rules didn't take: keep it as text
                para, i = [line.strip()], i + 1
            out.append(f"<p>{inline(' '.join(para), link)}</p>")
    return "\n".join(out)
