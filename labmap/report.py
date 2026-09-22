"""The check report: one self-contained HTML page (works offline), readable on screen and on paper."""
from __future__ import annotations

import datetime as dt
import html
from collections import defaultdict
from pathlib import Path

from . import metrics
from .checks import RULES, describe, spare_state
from .model import order_links

CSS = """.done { width: 36px; text-align: center; }
.banner { background: #fffaeb; border: 1px solid #fedf89; color: #93370d; padding: 10px 14px; border-radius: 6px; font-weight: 600; }

:root { --ink:#1f2328; --muted:#59636e; --line:#d1d9e0; --soft:#f6f8fa; --bad:#b42318; --badbg:#fef3f2;
        --ok:#067647; --okbg:#ecfdf3; --accent:#1f4e79; }
body { font: 14px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; color: var(--ink); background: #fff; margin: 0; }
main { max-width: 1120px; margin: 0 auto; padding: 24px 20px 64px; }
h1 { font-size: 26px; margin: 0 0 2px; }
h2 { font-size: 19px; margin: 40px 0 8px; padding-bottom: 4px; border-bottom: 1px solid var(--line); }
h3 { font-size: 15px; margin: 22px 0 2px; }
p { margin: 4px 0 8px; }
.sub, .note { color: var(--muted); }
nav { margin: 14px 0 0; display: flex; flex-wrap: wrap; gap: 4px 14px; }
nav a { color: var(--accent); text-decoration: none; }
table { border-collapse: collapse; width: 100%; margin: 6px 0 14px; font-size: 13px; }
th, td { text-align: left; padding: 5px 8px; border-bottom: 1px solid var(--line); vertical-align: top; }
th { background: var(--soft); font-weight: 600; }
.n { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
.chips { display: flex; gap: 8px; flex-wrap: wrap; margin: 14px 0 0; }
.chip { border: 1px solid var(--line); border-radius: 999px; padding: 2px 11px; background: var(--soft); }
.chip.bad { border-color: #fda29b; background: var(--badbg); color: var(--bad); }
.chip.ok { border-color: #abefc6; background: var(--okbg); color: var(--ok); }
.chip.warn { border-color: #fedf89; background: #fffaeb; color: #93370d; }
.bar { height: 8px; background: #eaeef2; border-radius: 4px; overflow: hidden; min-width: 90px; }
.bar > span { display: block; height: 100%; background: var(--accent); }
.bar.bad > span { background: var(--bad); }
table.problems td:first-child, table.problems th:first-child { width: 110px; white-space: nowrap; }
.bad { color: var(--bad); font-weight: 600; }
.ok { color: var(--ok); }
@media print { nav { display: none; } h2, h3 { break-after: avoid; } tr { break-inside: avoid; } }
"""


def esc(v):
    return html.escape("" if v is None else str(v))


def cell(v, cls=""):
    if isinstance(v, tuple) and len(v) == 2 and v[0] == "html":
        body = v[1]
    elif isinstance(v, float):
        body, cls = f"{v:,.1f}", cls or "n"
    elif isinstance(v, int):
        body, cls = f"{v:,}", cls or "n"
    else:
        body = esc(v)
    return f'<td class="{cls}">{body}</td>' if cls else f"<td>{body}</td>"


def table(head, rows, cls=""):
    """Headers starting with # are numeric columns: right-aligned, whatever the cell holds."""
    if not rows:
        return '<p class="note">Nothing to show yet.</p>'
    num = [h.startswith("#") for h in head]
    th = "".join(f'<th class="n">{esc(h[1:])}</th>' if n else f"<th>{esc(h)}</th>" for h, n in zip(head, num))
    body = "".join("<tr>" + "".join(cell(v, "n" if n else "") for v, n in zip(r, num)) + "</tr>" for r in rows)
    return f"<table{f' class={cls}' if cls else ''}><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>"


def bar(share, bad=False):
    w = max(0.0, min(1.0, share or 0.0))
    return ("html", f'<div class="bar{" bad" if bad else ""}"><span style="width:{w:.0%}"></span></div>')


def pct(x):
    return "" if x is None else f"{x:.0%}"


def summary(res):
    """The numbers two arrangements are compared on."""
    groups, warned = res.by_rule("problem"), res.by_rule("warning")
    free = defaultdict(float)
    for s in metrics.surfaces(res):
        free[s["room"]] += s["area"] * s["free"]
    return dict(problems=sum(len(v) for k, v in groups.items() if k != "data"),
                warnings=sum(len(v) for v in warned.values()),
                rules={k: len(v) for k, v in {**groups, **warned}.items() if k != "data"},
                free=dict(free), flows={w["tag"]: w for w in metrics.workflows(res)})


def _verdict(better):
    return ("html", f"<span class='{'ok' if better else 'bad'}'>{'better' if better else 'worse'}</span>")


def _spread(w):
    if not w:
        return ""
    if w["split"]:
        return "split: " + " + ".join(w["rooms"])
    return f"{w['spread']:.1f} m" if w["spread"] is not None else ""


def comparison(before, after):
    """Table: the arrangement now (lab-data.xlsx) against the one tried. Only what changes, plus the totals."""
    b, a, s = summary(before), summary(after), after.lab.settings
    rows = []

    def row(what, x, y, lower_is_better=True, always=False):
        if x != y or always:
            rows.append((what, x, y, "" if x == y else _verdict((y < x) == lower_is_better)))

    row("Problems", b["problems"], a["problems"], always=True)
    row("Warnings", b["warnings"], a["warnings"], always=True)
    for rule in RULES:
        if rule != "data":
            row(f"· {describe(rule, s)[0]}", b["rules"].get(rule, 0), a["rules"].get(rule, 0))
    for rid in sorted(set(b["free"]) | set(a["free"])):
        row(f"Free bench space in {rid}, m²", round(b["free"].get(rid, 0), 2), round(a["free"].get(rid, 0), 2),
            lower_is_better=False)
    for tag in sorted(set(b["flows"]) | set(a["flows"])):
        wb, wa = b["flows"].get(tag), a["flows"].get(tag)
        if wb and wa and _spread(wb) != _spread(wa):
            worse = (wa["split"] and not wb["split"]) or (
                wa["split"] == wb["split"] and (wa["spread"] or 0) > (wb["spread"] or 0))
            rows.append((f"Workflow '{tag}': how spread out", _spread(wb), _spread(wa), _verdict(not worse)))
    return table(["", "Now (lab-data.xlsx)", "As drawn", ""], rows)


def _where(P, i):
    r = P[i]
    if r.get("mount") == "in":
        return f"{r.get('room')} · in {r.get('parent')}"
    host = f"{r['mount']} {r['parent']}" if r.get("parent") else "on the floor" if r.get("mount") == "floor" else "on the wall"
    spot = "not placed" if r.get("x") is None else f"at {r['x']}, {r['y']}" + (f", facing {r['faces']}" if r.get("faces") else "")
    return f"{r.get('room')} · {host}, {spot}"


def move_rows(before, after, moves):
    """(what, from, to, re-plug, notes) for each thing that moves: the list to hand out on moving day."""
    Pb, Pa = before.lab.placeables, after.lab.placeables
    changes = moves.get("placeables", {})
    out = []
    for i, change in sorted(changes.items(), key=lambda kv: (Pb[kv[0]].get("room") or "", kv[0])):
        if set(change) == {"room"}:
            continue  # drawers and the like: they go with their parent
        pb, pa = before.assign.get(i), after.assign.get(i)
        plug = "" if pb == pa else f"{pb or 'none'} → {pa or 'none'}" + (" (nearest)" if i in after.nearest else "")
        notes = []
        along = [k for k, c in changes.items() if set(c) == {"room"} and Pb[k].get("parent") == i]
        if along:
            notes.append("take along " + ", ".join(along))
        if i in moves.get("equipment", {}):
            notes.append(f"outlet {before.lab.equipment[i].get('outlet')} cleared: fill in the new one")
        out.append((f"{i} {Pb[i].get('name') or ''}".strip(), _where(Pb, i), _where(Pa, i), plug, "; ".join(notes)))
    for sid, change in sorted(moves.get("services", {}).items()):
        s = before.lab.services[sid]
        out.append((f"{sid} ({s.get('type')})", s.get("room"), change["room"], "",
                    f"goes with {s.get('parent')}: check its circuit in the new room"))
    return out


def move_list(before, after, moves):
    rows = move_rows(before, after, moves)
    return table(["What", "From", "To", "Re-plug", "Notes"], rows) if rows else "<p class='note'>Nothing moves.</p>"


def write_move_list(path, before, after, moves, note=""):
    """A printable page: every move, with a box to tick."""
    rows = move_rows(before, after, moves)
    body = "".join("<tr><td class='done'>&#9744;</td>" + "".join(f"<td>{esc(v)}</td>" for v in r) + "</tr>" for r in rows)
    text = (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><title>Move list</title><style>{CSS}</style>"
            f"</head><body><main><h1>Move list</h1><div class='sub'>{esc(note)}</div>"
            f"<table><thead><tr><th class='done'>Done</th><th>What</th><th>From</th><th>To</th><th>Re-plug</th>"
            f"<th>Notes</th></tr></thead><tbody>{body}</tbody></table></main></body></html>")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write(res, path, banner=None, before=None, moves=None):
    """The report. With before (the checks on lab-data.xlsx as it is) and moves, it's for an arrangement being
    tried: a comparison with the current one and the move list come first."""
    lab = res.lab
    derate = lab.settings["circuit_limit"] / 100
    groups, warned = res.by_rule("problem"), res.by_rule("warning")
    problems = [f for k, v in groups.items() if k != "data" for f in v]
    warnings = [f for v in warned.values() for f in v]
    data = groups.get("data", [])
    per_room = {}
    for f in problems:
        per_room[f.room or "several rooms"] = per_room.get(f.room or "several rooms", 0) + 1
    title = f"Lab check · {lab.folder.resolve().name}"
    out = [f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' "
           f"content='width=device-width, initial-scale=1'><title>{esc(title)}</title><style>{CSS}</style></head><body><main>",
           f"<h1>{esc(title)}</h1><div class='sub'>Generated {dt.datetime.now():%Y-%m-%d %H:%M} from "
           f"<code>{esc(lab.folder.resolve())}</code></div>"]
    if banner:
        out.append(f"<p class='banner'>{esc(banner)}</p>")
    chips = [f"<span class='chip {'bad' if problems else 'ok'}'>{len(problems)} problem{'' if len(problems) == 1 else 's'}</span>"]
    chips += [f"<span class='chip'>{esc(r)}: {n}</span>" for r, n in sorted(per_room.items())]
    if warnings:
        chips.append(f"<span class='chip warn'>{len(warnings)} warning{'' if len(warnings) == 1 else 's'}</span>")
    if data:
        chips.append(f"<span class='chip bad'>{len(data)} data problem{'' if len(data) == 1 else 's'}</span>")
    out.append("<div class='chips'>" + "".join(chips) + "</div>")
    sections = ["Problems", "Warnings", "Progress", "Rooms", "Bench space", "Power", "Connections", "Documents",
                "Spare parts", "Triage", "Workflow groups", "Containers", "Not placed yet"]
    if before is not None:
        sections = ["Compared", "Move list"] + sections
    out.append("<nav>" + "".join(f"<a href='#{s.lower().replace(' ', '-')}'>{s}</a>" for s in sections) + "</nav>")
    if before is not None:
        out.append("<h2 id='compared'>Compared with lab-data.xlsx</h2><p class='note'>The arrangement in the "
                   "spreadsheet against the one drawn in the layout: the totals, and whatever changes.</p>")
        out.append(comparison(before, res))
        out.append("<h2 id='move-list'>Move list</h2><p class='note'>What moves where, and which socket it plugs into "
                   "before and after. pull saves it as a printable page too.</p>")
        out.append(move_list(before, res, moves or {}))

    for heading, found_by_rule, empty in (("Problems", groups, "No problems found."),
                                          ("Warnings", warned, "No warnings.")):
        out.append(f"<h2 id='{heading.lower()}'>{heading}</h2>")
        if not found_by_rule:
            out.append(f"<p class='ok'>{empty}</p>")
        for rule, found in found_by_rule.items():
            name, what, _ = describe(rule, lab.settings)
            out.append(f"<h3>{esc(name)} ({len(found)})</h3><p class='note'>{esc(what)}</p>")
            out.append(table(["Room", heading[:-1]], [(f.room or "", f.message) for f in found], "problems"))

    out.append("<h2 id='progress'>Progress</h2><p class='note'>How much of the data is filled in. "
               "Missing data isn't a problem, but the checks can only see what's there.</p>")
    out.append(table(["What", "#Done", "#Of", "#Share", ""],
                     [(what, done, total, pct(done / total) if total else "", bar(done / total if total else 0))
                      for what, done, total in metrics.completeness(res)]))

    out.append("<h2 id='rooms'>Rooms</h2>")
    out.append(table(["Room", "Name", "#Floor m²", "#Floor covered", "#Heat W", "#Cooling W", "Walkways"],
                     [(r["id"], r["name"], r["area"], pct(r["covered"]), int(r["heat"]),
                       r["cooling"] if r["cooling"] is not None else "",
                       r["walk"] or "checked") for r in metrics.rooms(res)]))
    from . import layout
    for rid, room in lab.rooms.items():
        if room.get("poly"):
            out.append(f"<h3>{esc(rid)} · {esc(room.get('name'))}</h3><p class='note'>Red outline = involved in a "
                       "problem; dashed = under a bench or table; pink = clear zones. Hover for names.</p>")
            out.append(f"<div class='map'>{layout.drawing(lab, res, rid)}</div>")

    out.append("<h2 id='bench-space'>Bench space</h2><p class='note'>Used = things standing on it; reserved = "
               "working areas and the clear zones of things on it. The largest free rectangle is what a new instrument "
               "would have to fit in.</p>")
    out.append(table(["Surface", "Room", "#Area m²", "#Used", "#Reserved", "#Free", "", "#Largest free (cm)", "#Things"],
                     [(s["id"], s["room"], s["area"], pct(s["used"]), pct(s["kept"]), pct(s["free"]), bar(s["used"] + s["kept"]),
                       f"{s['largest'][0]} × {s['largest'][1]}", s["items"]) for s in metrics.surfaces(res)]))

    out.append("<h2 id='power'>Power</h2><h3>Circuits</h3>")
    rows = []
    for c, ci in sorted(lab.circuits.items()):
        w = res.load.get(c, 0)
        limit = derate * ci["rating_a"] * ci["volts"] if ci.get("rating_a") and ci.get("volts") else None
        rows.append((c, ci.get("panel"), f"{ci.get('rating_a') or '?'} A", int(w), int(limit) if limit else "",
                     bar(w / limit if limit else 0, bool(limit and w > limit)), ", ".join(res.members.get(c, []))))
    out.append(table(["Circuit", "Board", "Breaker", "#Running W", f"#Limit W ({derate:.0%})", "", "Plugged in"], rows))
    out.append("<h3>Sockets and strips</h3>")
    rows = []
    for sid, s in sorted(lab.services.items()):
        if s.get("type") not in ("outlet", "strip"):
            continue
        n, cap = res.used.get(sid, 0), s.get("sockets")
        users = [e for e, t in res.assign.items() if t == sid] + [k for k, t in lab.services.items() if t.get("fed_by") == sid]
        rows.append((sid, s.get("room"), res.circuit_of.get(sid) or "?", f"{n} / {cap if cap is not None else '?'}",
                     bar(n / cap if cap else 0, bool(cap is not None and n > cap)), ", ".join(users)))
    out.append(table(["Socket", "Room", "Circuit", "#In use", "", "Plugged in"], rows))
    if res.nearest:
        out.append("<h3>Assumed sockets</h3><p class='note'>These have no <code>outlet</code>, so the checks assumed the "
                   "nearest socket or strip. Worth confirming in the lab.</p>")
        out.append(table(["Device", "Assumed socket", "#Distance cm"],
                         [(e, s, round(d)) for e, (s, d) in sorted(res.nearest.items())]))

    out.append("<h2 id='connections'>Connections</h2>")
    out.append(table(["From", "To", "Type", "#Run m", "#Limit m", ""],
                     [(l["from"], l["to"], l.get("type"), round(run / 100, 1) if run is not None else "not placed",
                       round(limit / 100, 1) if limit else "", ("html", "<span class='bad'>too far</span>")
                       if run is not None and limit and run > limit else "") for l, run, limit in res.runs]))

    out.append("<h2 id='documents'>Documents</h2><p class='note'>Forms and certificates from the documents sheet.</p>")
    from .checks import doc_state
    rows = []
    for i, d in sorted(lab.documents.items()):
        state, left = doc_state(d, dt.date.today(), lab.settings["expiry_warning_days"])
        flag = {"expired": ("html", "<span class='bad'>expired</span>"),
                "expiring": ("html", f"<span class='bad'>in {left} days</span>")}.get(state, "")
        rows.append((i, d.get("type"), d.get("title"), ", ".join(d.get("applies_to") or []), d.get("status"),
                     d.get("filled") or "", d.get("expires") or "", flag))
    out.append(table(["Document", "Type", "Title", "For", "Status", "Filled", "Expires", ""], rows))

    out.append("<h2 id='spare-parts'>Spare parts</h2><p class='note'>Items with spare_for or min_qty on the items "
               "sheet. Stock is the first number in qty; a required spare with a blank qty counts as none.</p>")
    rows = []
    for i, it in sorted(lab.items.items()):
        if not it.get("spare_for") and not it.get("min_qty"):
            continue
        state, _ = spare_state(it)
        flag = {"out": ("html", "<span class='bad'>none left</span>"),
                "low": ("html", "<span class='bad'>low</span>")}.get(state, "")
        order = ", ".join(f"<a href='{esc(u)}'>{esc(t)}</a>" for t, u in order_links(it))
        rows.append((f"{i} {it.get('name') or ''}", ", ".join(it.get("spare_for") or []), it.get("qty") or "",
                     it.get("min_qty") or "", it.get("container") or it.get("elsewhere") or "", ("html", order), flag))
    out.append(table(["Part", "For", "In stock", "#Keep", "Where", "Order", ""], rows))

    out.append("<h2 id='triage'>Triage</h2><p class='note'>Equipment with a plan other than keep, or used a few times "
               "a year or less. Removing things usually frees more space than rearranging them.</p>")
    out.append(table(["Equipment", "Name", "Room", "Plan", "Usage", "Condition", "#Frees m²"],
                     [(t["id"], t["name"], t["room"], t["plan"], t["usage"], t["condition"],
                       f"{t['area']:.2f} ({t['where']})" if t["area"] else "") for t in metrics.triage(res)]))

    out.append("<h2 id='workflow-groups'>Workflow groups</h2><p class='note'>Equipment tagged with the same workflow "
               "should stay close together. Spread is the largest distance between two members.</p>")
    out.append(table(["Group", "Rooms", "#Spread m", "Members"],
                     [(w["tag"], ", ".join(w["rooms"]), "split across rooms" if w["split"] else
                       round(w["spread"], 1) if w["spread"] is not None else "", ", ".join(w["ids"]))
                      for w in metrics.workflows(res)]))

    out.append("<h2 id='containers'>Containers</h2>")
    out.append(table(["Container", "Name", "Where", "#Fill", "#Items", "Checked"],
                     [(c["id"], c["name"], c["where"], f"{c['fill']}%" if c["fill"] is not None else "", c["items"],
                       c["checked"] or "") for c in metrics.containers(res)]))

    out.append("<h2 id='not-placed-yet'>Not placed yet</h2><p class='note'>No x and y yet. The layout step puts these "
               "in a staging area beside the room, ready to drag in.</p>")
    out.append(table(["Object", "Name", "Room"], metrics.unplaced(res)))
    from . import layout as _layout
    out.append(f"</main><style>{_layout.MAP_CSS}</style><script>{_layout.MAP_JS}</script></body></html>")

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out), encoding="utf-8")
    return path
