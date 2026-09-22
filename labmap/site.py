"""The lab directory: static HTML pages that work offline and straight from a shared drive.

No server and no internet needed: every link is relative, the search index is a script file (browsers block
fetch() on file:// pages), and photos are shrunk copies. Your originals in photos/ are never touched.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import shutil
import unicodedata
from collections import defaultdict
from pathlib import Path

from . import checks, layout, md, report
from .model import order_links

PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp"}
BIG, THUMB = 1200, 360
PAGE_DIRS = ("o", "s", "rooms", "sops")

CSS = """
:root { --ink:#1f2328; --muted:#59636e; --line:#d1d9e0; --soft:#f6f8fa; --accent:#1f4e79; --hi:#fff4c2; }
* { box-sizing: border-box; }
body { font: 15px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; color: var(--ink); background: #fff; margin: 0; }
header { display: flex; gap: 16px; align-items: center; flex-wrap: wrap; padding: 10px 20px; background: var(--accent); }
header a.home { color: #fff; font-weight: 700; text-decoration: none; font-size: 17px; }
header form { flex: 1; min-width: 200px; max-width: 520px; }
header input { width: 100%; padding: 7px 10px; border: 0; border-radius: 6px; font: inherit; }
main { max-width: 1040px; margin: 0 auto; padding: 20px 20px 48px; }
footer { max-width: 1040px; margin: 0 auto; padding: 16px 20px 32px; color: var(--muted); font-size: 13px; border-top: 1px solid var(--line); }
a { color: var(--accent); }
h1 { font-size: 26px; margin: 4px 0; } h1 .sub { font-weight: 400; color: var(--muted); }
h2 { font-size: 18px; margin: 30px 0 8px; padding-bottom: 4px; border-bottom: 1px solid var(--line); }
.where { color: var(--muted); font-size: 14px; }
code { font: 13px ui-monospace, Consolas, monospace; background: var(--soft); padding: 1px 5px; border-radius: 4px; }
table { border-collapse: collapse; width: 100%; font-size: 14px; margin: 6px 0 10px; }
th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--line); vertical-align: top; }
th { background: var(--soft); font-weight: 600; }
table.facts th { width: 190px; background: none; color: var(--muted); font-weight: 500; }
tr:target { background: var(--hi); }
.scroll { overflow-x: auto; }
.cols { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 0 28px; }
img.ref { max-width: 100%; border-radius: 6px; border: 1px solid var(--line); }
.gallery { display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0; }
.gallery img, img.thumb { height: 120px; border-radius: 6px; border: 1px solid var(--line); }
img.thumb { height: 48px; vertical-align: middle; margin-right: 8px; }
.map { border: 1px solid var(--line); border-radius: 6px; padding: 8px; background: #fff; }
.map svg { display: block; }
.map g[id^="obj-"] { cursor: pointer; }
.mini svg { display: block; margin-top: 8px; max-height: 260px; }
.big-search { width: 100%; padding: 12px 14px; font: inherit; font-size: 18px; border: 2px solid var(--accent); border-radius: 8px; }
#results { list-style: none; padding: 0; margin: 14px 0; }
#results li { padding: 9px 2px; border-bottom: 1px solid var(--line); }
#results li a { font-weight: 600; }
.badge { font-size: 12px; padding: 1px 8px; border-radius: 999px; background: var(--soft); border: 1px solid var(--line); color: var(--muted); }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }
.card { border: 1px solid var(--line); border-radius: 8px; padding: 12px; text-decoration: none; color: inherit; }
.card:hover { border-color: var(--accent); }
.unknown { color: #b42318; }
.note { color: var(--muted); font-size: 14px; }
.sop blockquote { margin: 10px 0; padding: 6px 14px; border-left: 4px solid var(--line); background: var(--soft); }
.sop li.task { list-style: none; margin-left: -20px; }
.top { display: flex; gap: 24px; align-items: flex-start; justify-content: space-between; flex-wrap: wrap; }
img.hero { width: 320px; max-width: 100%; border-radius: 8px; border: 1px solid var(--line); }
.status { font-size: 12px; padding: 1px 8px; border-radius: 999px; border: 1px solid; white-space: nowrap; }
.status.ok { color: #067647; background: #ecfdf3; border-color: #abefc6; }
.status.warn { color: #93370d; background: #fffaeb; border-color: #fedf89; }
.status.bad { color: #b42318; background: #fef3f2; border-color: #fda29b; }
@media print { header, footer { display: none; } }
"""

DOC_TYPES = {"coshh": "COSHH", "risk-assessment": "Risk assessment", "calibration": "Calibration",
             "electrical-test": "Electrical test", "service": "Service record", "other": "Other"}

SEARCH_JS = """(function () {
  var box = document.getElementById('q'), out = document.getElementById('results'), browse = document.getElementById('browse');
  function fold(s) { return (s || '').toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g, ''); }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
    return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]; }); }
  var BONUS = {item: 3, object: 2, socket: 1, procedure: 0};
  function run(q) {
    var toks = fold(q).split(/\\s+/).filter(Boolean);
    browse.hidden = toks.length > 0;
    if (!toks.length) { out.innerHTML = ''; return; }
    var hits = [];
    window.LABMAP.forEach(function (e) {
      if (!toks.every(function (t) { return e.h.indexOf(t) >= 0; })) return;
      var s = BONUS[e.t] || 0;
      toks.forEach(function (t) {
        if (e.k === t) s += 100;
        if (e.n.indexOf(t) === 0) s += 20; else if (e.n.indexOf(t) >= 0) s += 10;
        if (e.s.indexOf(t) >= 0) s += 6;
      });
      hits.push([s, e]);
    });
    hits.sort(function (a, b) { return b[0] - a[0]; });
    out.innerHTML = hits.length ? hits.slice(0, 80).map(function (h) {
      var e = h[1];
      return '<li><a href="' + e.u + '">' + esc(e.name) + '</a> <span class="badge">' + e.t + '</span> ' +
        (e.id ? '<code>' + esc(e.id) + '</code>' : '') + '<div class="where">' + esc(e.w) + '</div></li>';
    }).join('') : '<li>Nothing found. Once you find it, add the word you tried as a synonym.</li>';
  }
  var q = new URLSearchParams(location.search).get('q') || '';
  box.value = q; run(q); box.focus();
  box.addEventListener('input', function () { run(box.value); });
})();
"""


def esc(v):
    return html.escape("" if v is None else str(v))


def doc_href(link):
    """A link a browser can open: web addresses as they are, full Windows or network paths as file: links."""
    s = str(link or "").strip()
    if re.match(r"https?://", s):
        return s
    if s.startswith("\\\\"):
        return "file:" + s.replace("\\", "/")
    if re.match(r"[A-Za-z]:[\\/]", s):
        return "file:///" + s.replace("\\", "/")
    return None


def fname(i):
    return re.sub(r"[^A-Za-z0-9.\-_]", "_", str(i))


def fold(s):
    s = unicodedata.normalize("NFD", str(s or "").lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def facts(rows):
    rows = [(k, v) for k, v in rows if v not in (None, "", [])]
    if not rows:
        return ""
    return "<table class='facts'>" + "".join(f"<tr><th>{esc(k)}</th><td>{v}</td></tr>" for k, v in rows) + "</table>"


class Site:
    def __init__(self, lab, res, out):
        self.lab, self.res, self.out = lab, res, Path(out)
        self.P, self.E, self.S = lab.placeables, lab.equipment, lab.services
        self.items_in, self.photos, self.links_of, self.sops_for = (defaultdict(list) for _ in range(4))
        self.spares_for = defaultdict(list)
        for it in lab.items.values():
            if it.get("container"):
                self.items_in[it["container"]].append(it)
            for i in it.get("spare_for") or []:
                self.spares_for[i].append(it)
        for link in lab.links:
            self.links_of[link["from"]].append((link, link["to"], "to"))
            self.links_of[link["to"]].append((link, link["from"], "from"))
        self.sops = []
        self.drawings = {}
        self.docs_for = defaultdict(list)
        for d in lab.documents.values():
            for i in d.get("applies_to") or []:
                self.docs_for[i].append(d)

    # --- links and page frame -----------------------------------------------------------------------------

    def href(self, i, root):
        if i in self.P:
            return f"{root}o/{fname(i)}.html"
        if i in self.S:
            return f"{root}s/{fname(i)}.html"
        if i in self.lab.items:
            it = self.lab.items[i]
            if it.get("container"):
                return f"{root}o/{fname(it['container'])}.html#{fname(i)}"
            return f"{root}o/{fname(it['spare_for'][0])}.html#spare-{fname(i)}" if it.get("spare_for") else None
        if i in self.lab.rooms:
            return f"{root}rooms/{fname(i)}.html"
        return None

    def a(self, i, root, text=None):
        h = self.href(i, root)
        label = esc(i if text is None else text)
        return f'<a href="{h}">{label}</a>' if h else f'<span class="unknown" title="not in lab-data.xlsx">{label}</span>'

    def crumbs(self, i, root):
        chain, j = [], i
        while j in self.P and j not in chain:
            chain.append(j)
            j = self.P[j].get("parent")
        room = (self.P.get(i) or self.S.get(i) or {}).get("room")
        return " › ".join(([self.a(room, root)] if room else []) + [self.a(c, root) for c in reversed(chain)])

    def page(self, path, title, body, root, head="", search=True, scripts=()):
        form = (f"<form action='{root}index.html'><input name='q' type='search' aria-label='Search' "
                f"placeholder='Search tools, drawers, instruments, procedures…'></form>") if search else ""
        js = "".join(f"<script src='{root}{s}'></script>" for s in (*scripts, "map.js"))
        text = (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' "
                f"content='width=device-width, initial-scale=1'><title>{esc(title)} · Lab directory</title>"
                f"<link rel='stylesheet' href='{root}style.css'>{head}</head><body data-root='{root}'>"
                f"<header><a class='home' href='{root}index.html'>Lab directory</a>{form}</header><main>{body}</main>"
                f"<footer>Generated {dt.date.today()} from lab-data.xlsx · <a href='{root}report.html'>Check report</a>"
                f"</footer>{js}</body></html>")
        target = self.out / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def map(self, rid, mark=None, view=None, svc=None):
        room = self.lab.rooms.get(rid) or {}
        if not room.get("poly"):
            return "", ""
        style = (f"<style>.map [id='obj-{esc(mark)}'] > .fp {{ stroke: #1f4e79; stroke-width: 5; fill: #ffd84d; fill-opacity: 1; }}</style>"
                 if mark else "")
        if svc:
            style += (f"<style>.map [id='svc-{esc(svc)}'] > .mk {{ stroke: #1f4e79; stroke-width: 5; }}"
                      f".map .plug[data-s='{esc(svc)}'] {{ opacity: 1; stroke: #1f4e79; stroke-width: 3; }}</style>")
        attr = (f" data-view='{view}'" if view else "") + (" data-svc='on'" if svc else "")
        if rid not in self.drawings:  # the same for every page in the room: draw it once
            self.drawings[rid] = layout.drawing(self.lab, self.res, rid, flag=False)
        return f"<div class='map'{attr}>{self.drawings[rid]}</div>", style

    def placed_ancestor(self, i):
        j, seen = i, set()
        while j in self.P and j not in seen:
            seen.add(j)
            g = self.res.geo.get(j)
            if g and g.poly:
                return j
            j = self.P[j].get("parent")
        return None

    # --- content ------------------------------------------------------------------------------------------

    def load_photos(self):
        src = self.lab.folder / "photos"
        if not src.is_dir():
            return
        try:
            from PIL import Image, ImageOps
        except ImportError:
            Image = None
        for p in sorted(src.iterdir()):
            if p.suffix.lower() not in PHOTO_EXT:
                continue
            key, ref = p.stem.split("--")[0].upper(), p.stem.lower().endswith("--reference")
            name = f"{p.stem}.jpg" if Image else p.name
            big, small = self.out / "photos" / name, self.out / "photos" / "t" / name
            if not (big.exists() and small.exists() and big.stat().st_mtime >= p.stat().st_mtime):
                small.parent.mkdir(parents=True, exist_ok=True)
                try:
                    if Image is None:
                        raise OSError
                    with Image.open(p) as im:
                        im = ImageOps.exif_transpose(im).convert("RGB")
                        for size, target in ((BIG, big), (THUMB, small)):
                            copy = im.copy()
                            copy.thumbnail((size, size))
                            copy.save(target, "JPEG", quality=82, optimize=True)
                except OSError:
                    shutil.copy2(p, big)
                    shutil.copy2(p, small)
            self.photos[key].append((f"photos/{name}", f"photos/t/{name}", ref))

    def load_sops(self):
        for p in sorted((self.lab.folder / "sops").glob("*.md")):
            if p.name.startswith("_"):
                continue
            meta, body = md.front_matter(p.read_text(encoding="utf-8"))
            eq = meta.get("equipment") or []
            eq = [str(x).strip().upper() for x in (eq if isinstance(eq, list) else [eq])]
            sop = dict(stem=p.stem, title=meta.get("title") or p.stem, meta=meta, body=body, equipment=eq)
            self.sops.append(sop)
            for i in eq:
                self.sops_for[i].append(sop)

    def sop_links(self, i, root):
        return ", ".join(f"<a href='{root}sops/{fname(s['stem'])}.html'>{esc(s['title'])}</a>"
                         for s in self.sops_for.get(i, [])) or None

    def docs(self, i, root):
        """The 'Forms and certificates' table for anything the documents sheet applies to."""
        if not self.docs_for.get(i):
            return ""
        today, warn, rows = dt.date.today(), self.lab.settings["expiry_warning_days"], []
        for d in self.docs_for[i]:
            state, left = checks.doc_state(d, today, warn)
            status = d.get("status") or ""
            badge = f"<span class='status {'ok' if status == 'approved' else 'warn'}'>{esc(status)}</span>"
            exp = esc(d.get("expires") or "")
            if state == "expired":
                exp += " <span class='status bad'>expired</span>"
            elif state == "expiring":
                exp += f" <span class='status warn'>in {left} days</span>"
            href, title = doc_href(d.get("link")), esc(d.get("title") or d["id"])
            name = f"<a href='{esc(href)}'>{title}</a>" if href else title
            who = f"<div class='note'>approved by {esc(d['approved_by'])}</div>" if d.get("approved_by") else ""
            rows.append(f"<tr><td>{esc(DOC_TYPES.get(d.get('type'), d.get('type')))}</td><td>{name} "
                        f"<code>{esc(d['id'])}</code></td><td>{badge}{who}</td><td>{esc(d.get('filled') or '')}</td>"
                        f"<td>{exp}</td></tr>")
        return ("<h2 id='docs'>Forms and certificates</h2><div class='scroll'><table><thead><tr><th>Type</th>"
                "<th>Document</th><th>Status</th><th>Filled</th><th>Expires</th></tr></thead><tbody>"
                + "".join(rows) + "</tbody></table></div>")

    @staticmethod
    def order(it):
        return ", ".join(f"<a href='{esc(u)}'>{esc(t)}</a>" for t, u in order_links(it))

    def thumb(self, it, root):
        pics = self.photos.get(it["id"], [])
        return f"<a href='{root}{pics[0][0]}'><img class='thumb' src='{root}{pics[0][1]}' alt=''></a>" if pics else ""

    def item_rows(self, items, root):
        rows = []
        for it in sorted(items, key=lambda t: str(t.get("name") or "")):
            spare = ("Spare for " + ", ".join(self.a(e, root) for e in it["spare_for"]) + ". ") if it.get("spare_for") else ""
            rows.append(f"<tr id='{fname(it['id'])}'><td>{self.thumb(it, root)}{esc(it.get('name'))}</td>"
                        f"<td>{esc(it.get('qty'))}</td><td>{esc(it.get('synonyms'))}</td><td>{self.order(it)}</td>"
                        f"<td>{spare}{esc(it.get('notes'))}</td></tr>")
        return ("<div class='scroll'><table><thead><tr><th>Item</th><th>How many</th><th>Also called</th><th>Order</th>"
                "<th>Notes</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")

    def spares(self, i, root):
        """The 'Spare parts' table: items whose spare_for names this object, with stock and where to order."""
        if not self.spares_for.get(i):
            return ""
        rows = []
        for it in sorted(self.spares_for[i], key=lambda t: str(t.get("name") or "")):
            state, _ = checks.spare_state(it)
            badge = {"out": "<span class='status bad'>none left</span>", "low": "<span class='status warn'>low</span>",
                     "ok": "<span class='status ok'>ok</span>"}.get(state, "")
            where = (self.crumbs(it["container"], root) if it.get("container") else
                     f"{esc(it.get('elsewhere'))} <span class='note'>(outside these labs)</span>")
            name = self.a(it["id"], root, it.get("name")) if it.get("container") else esc(it.get("name"))
            rows.append(f"<tr id='spare-{fname(it['id'])}'><td>{self.thumb(it, root)}{name}</td><td>{esc(it.get('qty'))}</td>"
                        f"<td>{esc(it.get('min_qty'))}</td><td>{badge}</td><td>{where}</td><td>{self.order(it)}</td>"
                        f"<td>{esc(it.get('notes'))}</td></tr>")
        return ("<h2 id='spares'>Spare parts</h2><div class='scroll'><table><thead><tr><th>Part</th><th>In stock</th>"
                "<th>Keep at least</th><th>Stock</th><th>Where</th><th>Order</th><th>Notes</th></tr></thead><tbody>"
                + "".join(rows) + "</tbody></table></div>")

    def object_page(self, i):
        r, e, root = self.P[i], self.E.get(i), "../"
        pics = self.photos.get(i, [])
        main = next((p for p in pics if not p[2]), None)
        hero = (f"<a href='{root}{main[0]}'><img class='hero' src='{root}{main[0]}' alt='Photo of {esc(i)}'></a>"
                if main else "")
        body = [f"<div class='top'><div><h1>{esc(i)} <span class='sub'>{esc(r.get('name'))}</span></h1>"
                f"<p class='where'>{self.crumbs(i, root)}</p></div>{hero}</div>"]
        body += [f"<h2>How it should look</h2><a href='{root}{p[0]}'><img class='ref' src='{root}{p[0]}' "
                 f"alt='How {esc(i)} should look'></a>" for p in pics if p[2]]
        rest = [p for p in pics if not p[2] and p is not main]
        if rest:
            body.append("<div class='gallery'>" + "".join(f"<a href='{root}{p[0]}'><img src='{root}{p[1]}' alt='{esc(i)}'></a>"
                                                         for p in rest) + "</div>")
        w, d, h = r.get("w"), r.get("d"), r.get("h")
        size = (f"⌀ {w} cm, {h} cm tall" if r.get("shape") == "circle" and w else
                f"{w} × {d} × {h} cm (w × d × h)" if w and d and h else "")
        mount = {"on": "on", "under": "under", "in": "inside", "part": "part of"}.get(r.get("mount"))
        details = facts([("Category", esc(r.get("category"))), ("Size", esc(size)),
                         ("Free underneath", f"{r['free_under']} cm" if r.get("free_under") is not None else None),
                         ("Sits", f"{mount} {self.a(r['parent'], root)}" if mount and r.get("parent") else None),
                         ("Fixed", "yes" if r.get("fixed") == "yes" else None),
                         ("On wheels", "yes" if r.get("mobile") == "yes" else None),
                         ("Full", f"{r['fill']}%" if r.get("fill") is not None else None),
                         ("Contents checked", esc(r.get("checked"))), ("Procedures", self.sop_links(i, root)),
                         ("Notes", esc(r.get("notes")))])
        cols = [f"<div><h2>Details</h2>{details}</div>"]
        if e:
            sid = self.res.assign.get(i)
            plug = None
            if sid:
                plug = self.a(sid, root) + (f" (circuit {esc(self.res.circuit_of.get(sid))})" if self.res.circuit_of.get(sid) else "")
                plug += " <span class='note'>(assumed: nearest socket)</span>" if i in self.res.nearest else ""
            power = ", ".join(x for x in (f"{e['plugs']} plug{'s' if e['plugs'] != 1 else ''}" if e.get("plugs") else "",
                                          esc(e.get("plug_type")),
                                          f"{e['watts_typ']} W running" if e.get("watts_typ") is not None else "",
                                          f"{e['watts_max']} W peak" if e.get("watts_max") is not None else "") if x)
            manual = e.get("manual")
            manual = f"<a href='{esc(manual)}'>{esc(manual)}</a>" if manual and re.match(r"https?://", manual) else esc(manual)
            cols.append("<div><h2>Equipment</h2>" + facts([
                ("Make and model", esc(" ".join(x for x in (e.get("maker"), e.get("model")) if x))),
                ("Serial", esc(e.get("serial"))), ("Asset tag", esc(e.get("asset_tag"))), ("Owner", esc(e.get("owner"))),
                ("Condition", esc(e.get("condition"))), ("Plan", esc(e.get("plan"))),
                ("Used", esc(" ".join(x for x in (e.get("usage"), f"({e['usage_source']})" if e.get("usage_source") else "") if x))),
                ("Workflow", esc(e.get("workflow"))), ("Power", power),
                ("Must never lose power", "yes" if e.get("critical") == "yes" else None),
                ("Plugged into", plug), ("Manual", manual), ("Notes", esc(e.get("notes")))]) + "</div>")
        body.append(f"<div class='cols'>{''.join(cols)}</div>")
        kids = self.lab.children.get(i, [])
        for title, mnt in (("Parts", "part"), ("On it", "on"), ("Under it", "under"), ("Inside", "in")):
            ks = [k for k in kids if self.P[k].get("mount") == mnt]
            if ks:
                lis = []
                for k in ks:
                    inside = self.items_in.get(k, [])
                    extra = (": " + ", ".join(self.a(t["id"], root, t.get("name")) for t in inside[:12]) +
                             (" …" if len(inside) > 12 else "")) if inside else ""
                    lis.append(f"<li>{self.a(k, root)} {esc(self.P[k].get('name'))}{extra}</li>")
                body.append(f"<h2>{title}</h2><ul>{''.join(lis)}</ul>")
        if self.items_in.get(i):
            body.append(f"<h2>Items kept here</h2>{self.item_rows(self.items_in[i], root)}")
        body.append(self.spares(i, root))
        if self.links_of.get(i):
            body.append("<h2>Connected to</h2><ul>" + "".join(
                f"<li>{self.a(other, root)} {esc(self.P.get(other, {}).get('name'))} "
                f"<span class='note'>({esc(link.get('type'))}{', ' + esc(link['notes']) if link.get('notes') else ''})</span></li>"
                for link, other, _ in self.links_of[i]) + "</ul>")
        body.append(self.docs(i, root))
        anchor = self.placed_ancestor(i)
        svg_, style = self.map(r.get("room"), anchor, layout.level_of(self.lab, self.res, i))
        if svg_:
            where = "" if anchor == i else f" <span class='note'>(shown: {self.a(anchor, root)})</span>" if anchor else \
                " <span class='note'>(not placed yet)</span>"
            body.append(f"<h2>Where</h2><p class='where'>{self.crumbs(i, root)}{where}</p>{svg_}")
        self.page(f"o/{fname(i)}.html", f"{i} {r.get('name') or ''}", "".join(body), root, style)

    def service_page(self, i):
        s, root = self.S[i], "../"
        users = [e for e, t in self.res.assign.items() if t == i] + [k for k, t in self.S.items() if t.get("fed_by") == i]
        body = [f"<h1>{esc(i)} <span class='sub'>{esc(s.get('type'))}</span></h1><p class='where'>{self.crumbs(i, root)}"
                + (f" › on {self.a(s['parent'], root)}" if s.get("parent") else "") + "</p>",
                facts([("Circuit", esc(self.res.circuit_of.get(i))), ("Plugged into", self.a(s["fed_by"], root) if s.get("fed_by") else None),
                       ("Sockets", f"{self.res.used.get(i, 0)} of {s['sockets']} in use" if s.get("sockets") is not None else None),
                       ("Socket type", esc(s.get("socket_type"))), ("Supplies", esc(s.get("medium"))),
                       ("Height", f"{s['z']} cm" if s.get("z") is not None else None), ("Notes", esc(s.get("notes")))])]
        if users:
            body.append("<h2>Plugged in</h2><ul>" + "".join(f"<li>{self.a(u, root)} {esc((self.P.get(u) or self.S.get(u) or {}).get('name'))}</li>"
                                                           for u in users) + "</ul>")
        svg_, style = self.map(s.get("room"), self.placed_ancestor(s["parent"]) if s.get("parent") else None,
                               layout.level_of(self.lab, self.res, s["parent"]) if s.get("parent") else None, i)
        body.append(self.docs(i, root))
        body.append(svg_)
        self.page(f"s/{fname(i)}.html", i, "".join(body), root, style)

    def room_page(self, rid):
        room, root = self.lab.rooms[rid], "../"
        svg_, _ = self.map(rid)
        top = [i for i, r in self.P.items() if r.get("room") == rid and not r.get("parent")]
        lis = "".join(f"<li>{self.a(i, root)} {esc(self.P[i].get('name'))} <span class='note'>{esc(self.P[i].get('category'))}"
                      f"{' · ' + str(len(self.lab.children.get(i, []))) + ' inside/on it' if self.lab.children.get(i) else ''}</span></li>"
                      for i in sorted(top))
        socks = [i for i, s in self.S.items() if s.get("room") == rid]
        body = (f"<h1>{esc(rid)} <span class='sub'>{esc(room.get('name'))}</span></h1>"
                f"<p class='note'>Click anything on the plan to open it.</p>{svg_}<h2>In this room</h2><ul>{lis}</ul>")
        if socks:
            body += "<h2>Sockets, strips and taps</h2><ul>" + "".join(
                f"<li>{self.a(i, root)} <span class='note'>{esc(self.S[i].get('type'))}</span></li>" for i in sorted(socks)) + "</ul>"
        body += self.docs(rid, root)
        self.page(f"rooms/{fname(rid)}.html", f"{rid} {room.get('name') or ''}", body, root)

    def sop_page(self, sop):
        root, meta = "../", sop["meta"]

        def link(i):
            key = i.upper()
            return self.a(key, root) if self.href(key, root) else f"<span class='unknown' title='not in lab-data.xlsx'>{esc(i)}</span>"

        head = facts([("Applies to", ", ".join(self.a(i, root) for i in sop["equipment"])), ("Owner", esc(meta.get("owner"))),
                      ("Version", esc(meta.get("version"))), ("Last reviewed", esc(meta.get("reviewed")))])
        text = md.render(sop["body"], link)
        text = text.replace("</h1>", "</h1>" + head, 1) if "</h1>" in text else head + text
        body = f"<div class='sop'>{text}</div>"
        self.page(f"sops/{fname(sop['stem'])}.html", sop["title"], body, root)

    def search_index(self):
        entries = []

        def add(t, i, name, where, url, syn="", extra=""):
            entries.append(dict(t=t, id=i, name=name or i, w=where, u=url, k=fold(i), n=fold(name), s=fold(syn),
                                h=fold(" ".join(str(x) for x in (i, name, syn, extra, where) if x))))

        loc = lambda i: re.sub(r"<[^>]+>", "", self.crumbs(i, ""))  # noqa: E731
        for i, r in self.P.items():
            e = self.E.get(i, {})
            add("object", i, r.get("name"), loc(i), f"o/{fname(i)}.html",
                extra=" ".join(str(x) for x in (r.get("category"), e.get("maker"), e.get("model"), e.get("owner"),
                                                e.get("workflow"), r.get("notes")) if x))
        for i, it in self.lab.items.items():
            c = it.get("container")
            add("item", i, it.get("name"), loc(c) if c else it.get("elsewhere") or "", self.href(i, "") or "",
                it.get("synonyms") or "",
                " ".join(str(x) for x in (it.get("category"), it.get("notes"), it.get("owner"), it.get("rs_part"),
                                          "RS" if it.get("rs_part") else "", "spare for",
                                          " ".join(it.get("spare_for") or [])) if x and (x != "spare for" or it.get("spare_for"))))
        for i, s in self.S.items():
            add("socket", i, f"{s.get('type')} {i}", loc(i), f"s/{fname(i)}.html",
                extra=" ".join(str(x) for x in (s.get("medium"), self.res.circuit_of.get(i), s.get("notes")) if x))
        for i, d in self.lab.documents.items():
            first = (d.get("applies_to") or [None])[0]
            url = self.href(first, "") + "#docs" if self.href(first, "") else "index.html"
            add("document", i, f"{DOC_TYPES.get(d.get('type'), d.get('type'))}: {d.get('title') or i}",
                "for " + ", ".join(d.get("applies_to") or []), url, extra=f"{d.get('status')} {d.get('notes') or ''}")
        for sop in self.sops:
            add("procedure", "", sop["title"], "applies to " + ", ".join(sop["equipment"]), f"sops/{fname(sop['stem'])}.html",
                extra=md.plain(sop["body"])[:4000])
        return entries

    def index_page(self):
        cards = []
        for rid, room in self.lab.rooms.items():
            svg_, _ = self.map(rid)
            cards.append(f"<a class='card' href='rooms/{fname(rid)}.html'><strong>{esc(rid)}</strong> {esc(room.get('name'))}"
                         f"{svg_.replace('class=' + chr(39) + 'map' + chr(39), 'class=' + chr(39) + 'mini' + chr(39), 1)}</a>")
        sops = "".join(f"<li><a href='sops/{fname(s['stem'])}.html'>{esc(s['title'])}</a> <span class='note'>"
                       f"{esc(', '.join(s['equipment']))}</span></li>" for s in self.sops)
        body = ("<input id='q' class='big-search' type='search' aria-label='Search' "
                "placeholder='What are you looking for? Try “allen key”, “freezer” or a drawer like PED-01.D2'>"
                "<ul id='results'></ul><div id='browse'>"
                f"<h2>Rooms</h2><div class='cards'>{''.join(cards)}</div>"
                + (f"<h2>Procedures</h2><ul>{sops}</ul>" if sops else "") +
                f"<p class='note'>{len(self.P)} objects, {len(self.lab.items)} items, {len(self.S)} sockets and taps, "
                f"{len(self.sops)} procedures.</p></div>")
        self.page("index.html", "Search", body, "", search=False, scripts=("search.js",))

    def build(self):
        for d in PAGE_DIRS:
            shutil.rmtree(self.out / d, ignore_errors=True)
        self.out.mkdir(parents=True, exist_ok=True)
        self.load_photos()
        self.load_sops()
        (self.out / "style.css").write_text(CSS + layout.MAP_CSS, encoding="utf-8")
        (self.out / "map.js").write_text(layout.MAP_JS, encoding="utf-8")
        data = json.dumps(self.search_index(), ensure_ascii=False, separators=(",", ":"))
        (self.out / "search.js").write_text(f"window.LABMAP={data};\n{SEARCH_JS}", encoding="utf-8")
        for i in self.P:
            self.object_page(i)
        for i in self.S:
            self.service_page(i)
        for rid in self.lab.rooms:
            self.room_page(rid)
        for sop in self.sops:
            self.sop_page(sop)
        self.index_page()
        report.write(self.res, self.out / "report.html")
        return self.out / "index.html"


def build(lab, res, out=None):
    return Site(lab, res, out or Path(lab.folder) / "build" / "site").build()
