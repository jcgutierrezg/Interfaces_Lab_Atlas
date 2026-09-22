"""Room layouts: editable SVGs for Inkscape (`layout`), reading the moves back (`pull`), and drawings for the report.

Every object is a group with id "obj-<ID>" whose transform is its own frame: translate to its back-left corner,
then rotate to its facing. Things on, under or part of an object are nested inside it, so they move with it.
Reading back works from each group's transform relative to its parent's, so it doesn't matter how Inkscape
chooses to write the transforms.
"""
from __future__ import annotations

import copy
import html
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from . import geometry as G
from . import svg

NS_SVG = "http://www.w3.org/2000/svg"
NS_INK = "http://www.inkscape.org/namespaces/inkscape"
NS_SOD = "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
for _p, _u in (("", NS_SVG), ("inkscape", NS_INK), ("sodipodi", NS_SOD)):
    ET.register_namespace(_p, _u)

PREFIX = "obj-"
OVERHEAD = 120   # cm: wall-mounted things this high are drawn see-through so what's below stays visible
STAGE_GAP = 60   # cm between the room and the staging area
FACES = {v: k for k, v in G.ANG.items()}
CHAR_W = 0.62  # width of an upper-case/digit character, as a share of the font size
MAP_CSS = """.map g.hover > .fp { fill: #ffe58f; fill-opacity: 1; stroke: #1f4e79; stroke-width: 3px; }
.levels { display: flex; gap: 6px; flex-wrap: wrap; margin: 8px 0 6px; }
.levels button { font: inherit; font-size: 13px; padding: 3px 11px; border: 1px solid #d1d9e0; background: #fff;
                 color: #1f2328; border-radius: 999px; cursor: pointer; }
.levels button.on { background: #1f4e79; border-color: #1f4e79; color: #fff; }
.map[data-view="floor"] g[id^="obj-"]:not(.lv-floor) > :not(g),
.map[data-view="bench"] g[id^="obj-"]:not(.lv-bench) > :not(g),
.map[data-view="wall"] g[id^="obj-"]:not(.lv-wall) > :not(g) { opacity: 0.15; pointer-events: none; }
.map[data-view="floor"] g[id^="obj-"]:not(.lv-floor) > text, .map[data-view="bench"] g[id^="obj-"]:not(.lv-bench) > text,
.map[data-view="wall"] g[id^="obj-"]:not(.lv-wall) > text { display: none; }
.map[data-view="floor"] g.lv-floor > .fp[fill="none"] { fill: #e8eef5; }  /* under a bench: solid when in focus */
.map:not([data-view]) .lb-level, .map[data-view="all"] .lb-level,
.map[data-view="floor"] .lb-all, .map[data-view="bench"] .lb-all, .map[data-view="wall"] .lb-all { display: none; }
.levels .sep { width: 1px; background: #d1d9e0; margin: 0 4px; }
.levels .legend { font-size: 12px; color: #59636e; align-self: center; display: none; }
.levels .legend i { display: inline-block; width: 10px; height: 10px; border: 1px solid #333; margin: 0 3px 0 8px;
                    vertical-align: -1px; }
.levels.svc-on .legend { display: inline; }
.map .svc-layer { display: none; }
.map[data-svc="on"] .svc-layer { display: inline; }
.map[data-svc="on"] g[id^="obj-"] > .fp { fill-opacity: 0.55; }
.map .plug { stroke: #475467; stroke-width: 1.5; stroke-dasharray: 5 4; opacity: 0.5; pointer-events: none; fill: none; }
.map .plug.hot { opacity: 1; stroke: #1f4e79; stroke-width: 3.5; stroke-dasharray: none; }
.map g.svc { cursor: pointer; }
.map g.svc.hover > .mk { stroke: #1f4e79; stroke-width: 4; }
.maptip { position: absolute; z-index: 10; background: #1f2328; color: #fff; font: 13px/1.35 system-ui, sans-serif;
          padding: 4px 8px; border-radius: 4px; pointer-events: none; max-width: 380px; }"""
MAP_JS = """(function () {
  // Highlight the object under the mouse (the innermost one only) and name it next to the cursor.
  // Level switch above each map: everything, or only what's on the floor, on bench tops, or on walls and shelves.
  var VIEWS = [['all', 'Everything'], ['floor', 'Floor'], ['bench', 'Bench tops'], ['wall', 'Walls and shelves']];
  document.querySelectorAll('.map').forEach(function (m) {
    if (!m.querySelector('g.lv-floor, g.lv-bench, g.lv-wall, .svc-layer g.svc')) return;
    var bar = document.createElement('div'), saved = null;
    bar.className = 'levels';
    try { saved = localStorage.getItem('labmap-view'); } catch (e) {}
    function set(v, remember) {
      m.dataset.view = v;
      bar.querySelectorAll('button[data-v]').forEach(function (b) { b.classList.toggle('on', b.dataset.v === v); });
      if (remember) { try { localStorage.setItem('labmap-view', v); } catch (e) {} }
    }
    VIEWS.forEach(function (v) {
      var b = document.createElement('button');
      b.type = 'button'; b.textContent = v[1]; b.dataset.v = v[0];
      b.addEventListener('click', function () { set(v[0], true); });
      bar.appendChild(b);
    });
    var sbtn = null;
    if (m.querySelector('.svc-layer g.svc')) {
      var sep = document.createElement('span'), legend = document.createElement('span'), svc = null;
      sep.className = 'sep';
      sbtn = document.createElement('button');
      sbtn.type = 'button'; sbtn.textContent = 'Sockets and taps';
      legend.className = 'legend';
      legend.innerHTML = 'number = free sockets<i style="background:#7fd6a4"></i>free<i style="background:#fdd67a"></i>full' +
        '<i style="background:#f97066"></i>too many plugs<i style="background:#fff;border-radius:50%"></i>taps and ports';
      try { svc = localStorage.getItem('labmap-svc'); } catch (e) {}
      var setSvc = function (on, remember) {
        m.dataset.svc = on ? 'on' : 'off'; sbtn.classList.toggle('on', on); bar.classList.toggle('svc-on', on);
        if (remember) { try { localStorage.setItem('labmap-svc', on ? 'on' : 'off'); } catch (e) {} }
      };
      sbtn.addEventListener('click', function () { setSvc(m.dataset.svc !== 'on', true); });
      bar.appendChild(sep); bar.appendChild(sbtn); bar.appendChild(legend);
      setSvc((m.dataset.svc || svc) === 'on', false);
    }
    m.parentNode.insertBefore(bar, m);
    set(m.dataset.view || saved || 'all', false);
  });
  var tip = document.createElement('div'), current = null, links = document.body.dataset.root !== undefined;
  tip.className = 'maptip'; tip.hidden = true; document.body.appendChild(tip);
  document.querySelectorAll('.map g[id^="obj-"], .map g[id^="svc-"]').forEach(function (g) {
    var svc = g.id.indexOf('svc-') === 0, map = g.closest('.map');
    var lines = function () { return map.querySelectorAll('.plug[data-' + (svc ? 's' : 'e') + '="' + g.id.slice(4) + '"]'); };
    var first = g.firstElementChild;
    if (first && first.tagName.toLowerCase() === 'title') { g.dataset.tip = first.textContent; first.remove(); }
    g.addEventListener('mouseover', function (e) {
      e.stopPropagation();
      if (current) current.classList.remove('hover');
      current = g; g.classList.add('hover');
      lines().forEach(function (l) { l.classList.add('hot'); });
      tip.textContent = g.dataset.tip || g.id.slice(4); tip.hidden = false;
    });
    g.addEventListener('mousemove', function (e) { tip.style.left = (e.pageX + 14) + 'px'; tip.style.top = (e.pageY + 16) + 'px'; });
    g.addEventListener('mouseout', function (e) {
      e.stopPropagation(); g.classList.remove('hover'); if (current === g) current = null; tip.hidden = true;
      lines().forEach(function (l) { l.classList.remove('hot'); });
    });
    if (links) g.addEventListener('click', function (e) {
      e.stopPropagation(); location.href = document.body.dataset.root + (svc ? 's/' : 'o/') + g.id.slice(4) + '.html';
    });
  });
})();
"""
FILL = {"bench": "#e9dcc3", "table": "#e9dcc3", "desk": "#e9dcc3", "instrument": "#bcd7f0", "computer": "#d9c9ef",
        "monitor": "#d9c9ef", "freezer": "#bfe8ec", "fridge": "#bfe8ec", "structure": "#9e9e9e", "safety": "#bfe3bf",
        "cabinet": "#d6d6d6", "shelf": "#d6d6d6", "pedestal": "#cfc3ad", "container": "#f0e0a0", "cart": "#f5c68f",
        "gas-cylinder": "#f3e37c", "sink": "#a9c9e0", "fume-hood": "#c9d3db", "door": "#ffffff", "window": "#ffffff",
        "workspace": "none"}


def esc(v):
    return html.escape("" if v is None else str(v))


def _n(v):
    return f"{v:.2f}".rstrip("0").rstrip(".") if v != int(v) else str(int(v))


def _pts(pts):
    return " ".join(f"{_n(x)},{_n(y)}" for x, y in pts)


def _inv(m):
    a, b, c, d, e, f = m
    det = a * d - b * c
    return (d / det, -b / det, -c / det, a / det, (c * f - d * e) / det, (b * e - a * f) / det)


# --- where things sit in their parent's frame, straight from the data -------------------------------------

def outline(lab, i, override=None):
    """Footprint in the object's own frame; for a group, the union of its parts. None if it can't be drawn."""
    P, override = lab.placeables, override or {}
    r = P[i]
    if r.get("shape") != "group":
        shp = G.shape_local(lab, i, r, [])
        return shp[0] if shp else None
    pts = []
    for c in lab.children.get(i, []):
        rc = dict(P[c])
        if c in override:
            rc["x"], rc["y"], rc["faces"] = override[c]
        if rc.get("mount") == "part" and rc.get("x") is not None and rc.get("y") is not None:
            got = G.in_frame(lab, c, rc, (0.0, 0.0), 0, [])
            if got:
                pts += [got[2](u, v) for u, v in got[0]]
    return pts or None


def local_transform(lab, i):
    """(origin, angle) of an object in its parent's frame, from its x, y and faces."""
    r = lab.placeables[i]
    rel = G.ANG.get(r.get("faces") or "S", 0)
    pts = outline(lab, i)
    if pts is None or r.get("x") is None or r.get("y") is None:
        return None
    rp = [G.rot(rel, u, v) for u, v in pts]
    return (r["x"] - min(p[0] for p in rp), r["y"] - min(p[1] for p in rp)), rel


# --- drawing ----------------------------------------------------------------------------------------------

def _flagged(lab, res):
    """{id: (messages, True if any of them is a problem rather than a warning)}"""
    from .checks import RULES

    out = {}
    for f in res.findings if res else []:
        if f.rule != "data":
            for i in f.ids:
                if i in lab.placeables:
                    msgs, bad = out.get(i, ([], False))
                    out[i] = (msgs + [f.message], bad or RULES[f.rule][2] == "problem")
    return out


LEVELS = ("floor", "bench", "wall")
SURFACES = {"bench", "desk", "table"}


def level_of(lab, res, i):
    """floor, bench or wall: the level a person would say something is at.

    Work surfaces (bench, desk, table) and what stands on them are "bench"; things on a wall or starting above
    OVERHEAD are "wall"; everything else standing on the floor, including what's tucked under a bench, is "floor".
    """
    P = lab.placeables
    r, g = P.get(i, {}), (res.geo.get(i) if res else None)
    kids = [c for c in lab.children.get(i, ()) if P[c].get("mount") == "part"]
    if r.get("mount") == "wall" or (g and g.poly and g.z[0] >= OVERHEAD):
        return "wall"
    if r.get("category") in SURFACES or (kids and all(level_of(lab, res, c) == "bench" for c in kids)):
        return "bench"
    if g and g.poly:
        return "bench" if g.z[0] > 0 else "floor"
    parent = r.get("parent")
    return level_of(lab, res, parent) if parent in P and r.get("mount") in ("in", "part") else "floor"


STACK_FILL = 0.2  # stack members above the bottom one: faint enough to read the labels below, filled enough to click
FURNITURE = {"bench", "desk", "table", "shelf", "cabinet", "cart", "pedestal"}


def stack_pos(lab, i):
    """(place from the bottom, height) of i in a stack of things standing on each other (SMUs, a monitor on a
    PC), or None. Furniture isn't part of a stack: the stack starts with what stands on the bench."""
    P = lab.placeables

    def up(j):
        ups = [c for c in lab.children.get(j, []) if P[c].get("mount") == "on"]
        return ups[0] if len(ups) == 1 and P[j].get("category") not in FURNITURE else None

    root, seen = i, {i}
    while P[root].get("mount") == "on" and P.get(P[root].get("parent"), {}).get("category") not in FURNITURE \
            and P[root].get("parent") in P and P[root]["parent"] not in seen:
        root = P[root]["parent"]
        seen.add(root)
    chain = [root]
    while up(chain[-1]) and up(chain[-1]) not in chain:
        chain.append(up(chain[-1]))
    return (chain.index(i), len(chain)) if len(chain) > 1 and i in chain else None


LABEL_MIN = {"map": 4.5, "layout": 4.0}  # smallest label worth drawing: read-only maps, Inkscape layouts
GRID = (0.5, 0.35, 0.65, 0.2, 0.8, 0.08, 0.92)  # where to try a label, as shares of width and depth


LAYER_ORDER = ("floor", "under", "on", "wall")  # Inkscape layers, bottom to top


def layout_layer(lab, res, i):
    """Which layer of the Inkscape layout an object goes on."""
    r = lab.placeables[i]
    if r.get("mount") == "wall" or level_of(lab, res, i) == "wall":
        return "wall"
    return r.get("mount") if r.get("mount") in ("on", "under") else "floor"


def label_want(lab, i, w, d):
    """(size a label would like, carries things, stack slot or None)."""
    P = lab.placeables
    st = stack_pos(lab, i)
    nxt = [c for c in lab.children.get(i, []) if P[c].get("mount") == "on"] if st and st[0] < st[1] - 1 else []
    carries = any(P[c].get("mount") in ("on", "under") and c not in nxt for c in lab.children.get(i, []))
    if carries:
        return 6.5, True, None
    if st:
        k, n = st
        return max(4.0, min(11.0, min(w, d / n) * 0.4)), False, (w / 2, d * (n - k - 0.5) / n)
    return max(4.0, min(11.0, min(w, d) * 0.3)), False, None


def _spots(w, d, carries, slot):
    """Label positions to try, in the object's own frame, best first."""
    if slot:
        return [slot]
    pts = [(fu, fv) for fu in GRID for fv in GRID]
    if carries:  # a bench: its label goes where people look for it, the front-left, and moves right from there
        pts.sort(key=lambda f: (-f[1], f[0]))
    else:
        pts.sort(key=lambda f: (f[0] - 0.5) ** 2 + (f[1] - 0.5) ** 2)
    return [(fu * w, fv * d) for fu, fv in pts]


def _hits(box, boxes):
    return any(box[0] < b[2] and b[0] < box[2] and box[1] < b[3] and b[1] < box[3] for b in boxes)


def _fits(box, margin, poly):
    x0, y0, x1, y1 = box[0] - margin, box[1] - margin, box[2] + margin, box[3] + margin
    xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
    return all(G.inside(p, poly) for p in ((x0, y0), (x1, y0), (x1, y1), (x0, y1), (xm, y0), (xm, y1), (x0, ym), (x1, ym)))


def label_box(i, size, x, y):
    """The room-frame box an upright label of this size takes, centred on (x, y)."""
    tw = CHAR_W * size * len(i)
    return x - tw / 2, y - 0.55 * size, x + tw / 2, y + 0.55 * size


def label_plan(lab, res, rid, min_size, only=None, covered=False):
    """{id: (font size, box in room coordinates, (u, v) centre in the object's own frame)}. Size 0 = hidden (the
    name still shows on hover). Every label is upright, fully inside its own object with a margin, clear of other
    labels and of things drawn above it, and at least min_size; its position is searched over the object before
    it's made smaller. Higher things are labelled first (what's on a bench before what's under it), benches last.
    covered: plan for the Inkscape layouts, where what covers what follows the layers, and where a label with no
    uncovered spot goes under a higher layer rather than being hidden (that layer can be hidden to read it)."""
    if res is None:
        return {}
    P, geo = lab.placeables, res.geo
    ids = [i for i, g in geo.items() if g and g.poly and g.room == rid and P[i].get("shape") != "group"
           and (only is None or i in only)]
    box_of = {i: G.bbox(geo[i].poly) for i in ids}
    stack_of = {i: stack_pos(lab, i) for i in ids}

    def mates(i):
        """i's own stack: labels there are meant to show through each other."""
        out, j = {i}, i
        while stack_of.get(j) and stack_of[j][0] > 0:
            j = P[j]["parent"]
            out.add(j)
        todo = [i]
        while todo:
            for c in lab.children.get(todo.pop(), []):
                if stack_of.get(c) and c not in out:
                    out.add(c)
                    todo.append(c)
        return out

    cands = []
    for i in ids:
        g = geo[i]
        w, d = g.size
        want, carries, slot = label_want(lab, i, w, d)
        own = mates(i)
        if covered:  # Inkscape: a higher layer, or deeper in the same one, is drawn over it
            mine = (LAYER_ORDER.index(layout_layer(lab, res, i)), _depth(lab, i))
            over = [j for j in ids if (LAYER_ORDER.index(layout_layer(lab, res, j)), _depth(lab, j)) > mine
                    and not (P[j].get("category") == "workspace" and P[j].get("mount") != "under")]
        else:  # read-only maps: what stands higher is drawn over it; under a bench is only an outline there
            over = [j for j in ids if P[j].get("mount") == "on" and P[j].get("category") != "workspace"
                    and geo[j].z[0] >= g.z[1] - 0.5]
        above = [box_of[j] for j in over if j not in own and _hits(box_of[j], [box_of[i]])]
        under = P[i].get("mount") == "under"
        cands.append(((carries, under, -round(g.z[0]), -abs(G.area(g.poly)), i), i, g, want, carries, slot, above))
    placed, out = [], {}
    for _, i, g, want, carries, slot, above in sorted(cands):
        out[i] = (0, None, None)
        w, d = g.size
        spots = [(u, v, g.T(u, v)) for u, v in _spots(w, d, carries, slot)]
        # uncovered first, at any legible size. Only something itself hidden under others (not a bench, whose label
        # would be cut off by what's on it) falls back to a covered spot, readable once the upper layer is hidden
        for avoid in ([above, []] if covered and above and not carries else [above]):
            s = want
            while s >= min_size and not out[i][0]:
                margin = max(1.0, 0.3 * s)
                for u, v, (x, y) in spots:
                    box = label_box(i, s, x, y)
                    if _fits(box, margin, g.poly) and not _hits(box, placed) and not _hits(box, avoid):
                        placed.append(box)
                        out[i] = (round(s, 1), box, (round(u, 2), round(v, 2)))
                        break
                s = round(s - 0.5, 1)
    return out


def _object(lab, i, origin, angle, abs_angle, flagged, unplaced=False, sizes=None, lsizes=None, levels=None,
            nest=True):
    """One object as an obj-<ID> group. nest: draw what stands on and under it inside it (read-only maps);
    without, only a group's parts are inside it (the Inkscape layouts, where everything moves on its own)."""
    P = lab.placeables
    r = P[i]
    tip = f"{i} · {r.get('name') or ''}"
    if unplaced:
        tip += " · not placed yet: drag it into place"
    if i in flagged:
        tip += " · " + " · ".join(flagged[i][0])
    tf = f"translate({_n(origin[0])},{_n(origin[1])})" + (f" rotate({_n(angle)})" if angle % 360 else "")
    cls = f' class="lv-{levels[i]}"' if levels and i in levels else ""
    ink = "" if nest else f' inkscape:label="{esc(i)}"'
    out = [f'<g id="{PREFIX}{esc(i)}"{cls}{ink} transform="{tf}"><title>{esc(tip)}</title>']
    kids = lab.children.get(i, [])
    if r.get("shape") == "group":
        for c in kids:
            lt = local_transform(lab, c) if P[c].get("mount") == "part" else None
            if lt:
                out.append(_object(lab, c, lt[0], lt[1], abs_angle + lt[1], flagged, sizes=sizes, lsizes=lsizes,
                                   levels=levels, nest=nest))
        out.append("</g>")
        return "".join(out)
    shp = G.shape_local(lab, i, r, [])
    if shp is None:
        return ""
    local, lzone = shp
    w, d = r["w"], r.get("d") or r["w"]
    zone_style = 'fill="#d64545" fill-opacity="0.07" stroke="#d64545" stroke-opacity="0.45" stroke-width="0.6" ' \
                 'stroke-dasharray="3 2"'
    if lzone:
        out.append(f'<polygon points="{_pts(lzone)}" {zone_style}/>')
    else:
        for u0, v0, u1, v1 in G.clear_boxes(r, w, d).values():
            out.append(f'<rect x="{_n(min(u0, u1))}" y="{_n(min(v0, v1))}" width="{_n(abs(u1 - u0))}" '
                       f'height="{_n(abs(v1 - v0))}" {zone_style}/>')
    under = r.get("mount") == "under"
    overhead = r.get("mount") == "wall" and (r.get("z") or 0) >= OVERHEAD
    fill = ("#e8eef5" if not nest else "none") if under else FILL.get(r.get("category"), "#dddddd")
    alert = "#c00000" if flagged.get(i, ((), False))[1] else "#d97706"
    stroke, width = (alert, 1.6) if i in flagged else ("#e07b00", 1.2) if unplaced else ("#555555", 0.6)
    dash = ' stroke-dasharray="2 1.5"' if under or unplaced or r.get("category") == "workspace" else ""
    st = stack_pos(lab, i)
    op = ' fill-opacity="0.35"' if overhead else f' fill-opacity="{STACK_FILL}"' if st and st[0] > 0 else ""
    out.append(f'<polygon class="fp" points="{_pts(local)}" fill="{fill}"{op} stroke="{stroke}" '
               f'stroke-width="{width}"{dash}/>')
    color = alert if i in flagged else "#6b6b6b" if under else "#222222"
    want, carries, slot = label_want(lab, i, w, d)
    late = carries or st is not None  # drawn after what stands on it, so that doesn't cover it

    def text(plan, kind):
        """A label from the planner's (size, box, (u, v)); unplanned (staging area): centred, sized to fit."""
        if plan is None:
            cu, cv = slot or G.centroid(local)
            plan = (min(want, (w - 2) / (CHAR_W * len(i))), None, (cu, cv))
        sz, _, uv = plan
        if not sz or sz <= 0:
            return ""
        cu, cv = uv
        turn = f' transform="rotate({_n(-abs_angle % 360)} {_n(cu)} {_n(cv)})"' if abs_angle % 360 else ""
        return (f'<text class="{kind}" x="{_n(cu)}" y="{_n(cv)}" dy="0.35em" font-family="sans-serif" '
                f'font-size="{_n(round(sz, 1))}" text-anchor="middle" fill="{color}"{turn}>{esc(i)}</text>')

    plan = sizes.get(i, (0, None, None)) if sizes is not None else None
    label = text(plan, "lb-all") + (text(lsizes.get(i, (0, None, None)), "lb-level") if lsizes else "")
    if not late:
        out.append(label)
    for mount in ("under", "on") if nest else ():
        for c in kids:
            if P[c].get("mount") != mount:
                continue
            lt = local_transform(lab, c)
            if lt:
                out.append(_object(lab, c, lt[0], lt[1], abs_angle + lt[1], flagged, sizes=sizes, lsizes=lsizes, levels=levels))
            elif outline(lab, c):  # not placed yet: wait beside the parent, in its frame
                out.append(_object(lab, c, (w + 10, 0), 0, abs_angle, flagged, unplaced=True, sizes=sizes, lsizes=lsizes, levels=levels))
    if late:
        out.append(label)
    out.append("</g>")
    return "".join(out)


def _room_objects(lab, rid, flagged, sizes=None, lsizes=None, levels=None):
    """(svg of the placed objects, svg of the staging area, extent of everything)."""
    P, room = lab.placeables, lab.rooms[rid]
    poly = room.get("poly") or [(0, 0), (room.get("width") or 500, 0),
                                (room.get("width") or 500, room.get("depth") or 400), (0, room.get("depth") or 400)]
    x0, y0, x1, y1 = G.bbox(poly)
    top = [i for i, r in P.items() if r.get("room") == rid and not r.get("parent") and r.get("mount") in ("floor", "wall")]

    def order(i):
        r, pts = P[i], outline(lab, i) or [(0, 0)]
        z = r.get("z") or 0 if r.get("mount") == "wall" else 0
        return (z >= OVERHEAD, z, -abs(G.area(pts)) if len(pts) > 2 else 0)

    placed, staged, stage = [], [], []
    for i in sorted(top, key=order):
        lt = local_transform(lab, i)
        (placed if lt else staged).append((i, lt))
    body = [_object(lab, i, lt[0], lt[1], lt[1], flagged, sizes=sizes, lsizes=lsizes, levels=levels) for i, lt in placed]
    sx, sy, sw = x1 + STAGE_GAP, y0 + 25, 0
    for i, _ in staged:
        pts = outline(lab, i)
        if not pts:
            continue
        bx0, by0, bx1, by1 = G.bbox(pts)
        stage.append(_object(lab, i, (sx - bx0, sy - by0), 0, 0, flagged, unplaced=True))
        sy += by1 - by0 + 20
        sw = max(sw, bx1 - bx0)
    if stage:
        stage.insert(0, f'<text x="{_n(sx)}" y="{_n(y0 + 12)}" font-family="sans-serif" font-size="12" '
                        f'fill="#e07b00">Not placed yet: drag into the room</text>')
    extent = (min(x0, 0) - 50, min(y0, 0) - 60, max(x1 + 50, sx + sw + 50 if stage else 0), max(y1 + 80, sy + 20))
    return "".join(body), "".join(stage), extent, poly


SVC_LETTER = {"gas": "G", "vacuum": "V", "air": "A", "water": "W", "drain": "D", "network": "N", "exhaust": "X"}
SVC_FILL = {"gas": "#f3e37c", "vacuum": "#d0d5dd", "air": "#c7e3f5", "water": "#8ec5ea", "drain": "#b9c3cf",
            "network": "#d9c9ef", "exhaust": "#e4e7ec"}


def services_layer(lab, res, rid):
    """Sockets, strips, taps and ports as markers, plus a line from every plugged-in device to its socket.

    A power marker shows how many sockets are still free, coloured free / full / too many plugs.
    Hidden until the map's 'Sockets and taps' button is on.
    """
    S, geo = lab.services, res.geo
    pos = {i: G.service_position(lab, geo, s) for i, s in S.items() if s.get("room") == rid}
    pos = {i: p for i, p in pos.items() if p is not None}
    if not pos:
        return ""
    plugged = {}
    for eid, sid in res.assign.items():
        plugged.setdefault(sid, []).append(eid)
    lines, marks = [], []
    for eid, sid in sorted(res.assign.items()):
        p, d = pos.get(sid), G.position(lab, geo, eid)
        if p and d:
            lines.append(f'<line class="plug" data-s="{esc(sid)}" data-e="{esc(eid)}" x1="{_n(round(d[0], 1))}" '
                         f'y1="{_n(round(d[1], 1))}" x2="{_n(round(p[0], 1))}" y2="{_n(round(p[1], 1))}"/>')
    for sid, s in sorted(S.items()):
        if s.get("type") == "strip" and sid in pos and s.get("fed_by") in pos:
            (x1, y1), (x2, y2) = pos[sid], pos[s["fed_by"]]
            lines.append(f'<line class="plug" data-s="{esc(s["fed_by"])}" data-e="{esc(sid)}" x1="{_n(round(x1, 1))}" '
                         f'y1="{_n(round(y1, 1))}" x2="{_n(round(x2, 1))}" y2="{_n(round(y2, 1))}"/>')
    for sid, (x, y) in sorted(pos.items(), key=lambda kv: (S[kv[0]].get("type") == "strip", kv[0])):
        s, kind = S[sid], S[sid].get("type")
        tip = [sid, kind or ""]
        if kind in ("outlet", "strip"):
            total, used = s.get("sockets"), res.used.get(sid, 0)
            free = None if total is None else total - used
            fill = "#d0d5dd" if free is None else "#7fd6a4" if free > 0 else "#fdd67a" if free == 0 else "#f97066"
            text = "?" if free is None else str(free) if free >= 0 else f"+{-free}"
            tip.append(f"{used} plug{'s' if used != 1 else ''} in use" +
                       (f" of {total} socket{'s' if total != 1 else ''}" if total is not None else " (sockets not counted)") +
                       (f", {-free} too many" if free is not None and free < 0 else ""))
            if res.circuit_of.get(sid):
                tip.append(f"circuit {res.circuit_of[sid]}")
            elif kind == "strip" and s.get("fed_by"):
                tip.append(f"plugged into {s['fed_by']}")
            users = plugged.get(sid, []) + [k for k, t in S.items() if t.get("fed_by") == sid]
            if users:
                tip.append("feeds " + ", ".join(u + (" (nearest)" if u in res.nearest else "") for u in users))
            w, h = (30, 14) if kind == "strip" else (20, 20)
            shape = (f'<rect class="mk" x="{_n(-w / 2)}" y="{_n(-h / 2)}" width="{w}" height="{h}" rx="{3 if kind == "strip" else 1}" '
                     f'fill="{fill}" stroke="#333" stroke-width="1.5"/>')
        else:
            text, fill = SVC_LETTER.get(kind, "?"), SVC_FILL.get(kind, "#ffffff")
            tip += [x for x in (s.get("medium"), f"{s['sockets']} ports" if kind == "network" and s.get("sockets") else "") if x]
            shape = f'<circle class="mk" r="10" fill="{fill}" stroke="#333" stroke-width="1.5"/>'
        if s.get("notes"):
            tip.append(str(s["notes"]))
        marks.append(f'<g id="svc-{esc(sid)}" class="svc" transform="translate({_n(round(x, 1))} {_n(round(y, 1))})">'
                     f'<title>{esc(" · ".join(t for t in tip if t))}</title>{shape}'
                     f'<text dy="0.35em" text-anchor="middle" font-family="sans-serif" font-size="11" font-weight="bold" '
                     f'fill="#1f2328" pointer-events="none">{esc(text)}</text></g>')
    return f'<g class="svc-layer">{"".join(lines)}{"".join(marks)}</g>'


def drawing(lab, res, rid, flag=True):
    """A read-only drawing of one room: problems outlined for the report (flag), plain for the directory."""
    flagged = _flagged(lab, res) if flag else {}
    levels = {i: level_of(lab, res, i) for i, r in lab.placeables.items() if r.get("room") == rid}
    lsizes = {}
    for lv in LEVELS:
        lsizes.update(label_plan(lab, res, rid, LABEL_MIN["map"], only={i for i, v in levels.items() if v == lv}))
    body, _, _, poly = _room_objects(lab, rid, flagged, label_plan(lab, res, rid, LABEL_MIN["map"]), lsizes, levels)
    x0, y0, x1, y1 = G.bbox(poly)
    vb = f"{_n(x0 - 20)} {_n(y0 - 20)} {_n(x1 - x0 + 40)} {_n(y1 - y0 + 40)}"
    return (f'<svg xmlns="{NS_SVG}" viewBox="{vb}" style="width:100%;height:auto;max-height:80vh" role="img">'
            f'<polygon points="{_pts(poly)}" fill="#fafafa" stroke="#333" stroke-width="3"/>{body}'
            f'{services_layer(lab, res, rid) if res else ""}</svg>')


LAYERS = (("floor", "floor and benches"), ("under", "under benches"), ("on", "on benches"),
          ("wall", "walls and shelves"))
LAYOUT_FILE = "labs.svg"
ROOM_GAP = 150  # cm between rooms in the combined layout
STAGE_MIN = (150, 200)  # cm: smallest "not placed yet" area, so there's always somewhere to drag things out to
MOVE_SHEETS = ("placeables", "services", "equipment")  # what a pull can change
LAYER_MOUNT = {"floor": "floor", "under": "under", "on": "on"}  # moved to this layer in Inkscape: mounted like this


def abs_matrix(lab, i):
    """An object's transform in room coordinates, through its parent chain. None if it or a parent isn't placed."""
    P = lab.placeables
    lt = local_transform(lab, i)
    if lt is None:
        return None
    (ox, oy), a = lt
    t = math.radians(a)
    m = (math.cos(t), math.sin(t), -math.sin(t), math.cos(t), ox, oy)
    parent = P[i].get("parent")
    if parent and P[i].get("mount") in ("on", "under", "part"):
        pm = abs_matrix(lab, parent) if parent in P else None
        return None if pm is None else svg.mul(pm, m)
    return m


def _apply(m, p):
    return m[0] * p[0] + m[2] * p[1] + m[4], m[1] * p[0] + m[3] * p[1] + m[5]


def _depth(lab, i):
    n, j, seen = 0, lab.placeables[i].get("parent"), set()
    while j in lab.placeables and j not in seen:
        seen.add(j)
        n, j = n + 1, lab.placeables[j].get("parent")
    return n


def _room_poly(room):
    w, d = room.get("width") or 500, room.get("depth") or 400
    return room.get("poly") or [(0, 0), (w, 0), (w, d), (0, d)]


def _shell(lab, rid):
    """(the room outline file's root element, its viewBox as (x0, y0, x1, y1)) or (None, None)."""
    shell = lab.folder / "rooms" / (lab.rooms[rid].get("shell") or "")
    if not shell.is_file():
        return None, None
    src = ET.parse(shell).getroot()
    vb = [float(n) for n in svg.NUM.findall(src.get("viewBox") or "")]
    return src, ((vb[0], vb[1], vb[0] + vb[2], vb[1] + vb[3]) if len(vb) == 4 else None)


def _block(lab, rid):
    """One room's part of the combined layout, in room coordinates: its objects, its staging area, its extent."""
    P = lab.placeables
    poly = _room_poly(lab.rooms[rid])
    x0, y0, x1, y1 = G.bbox(poly)
    ids = [i for i, r in P.items() if r.get("room") == rid and r.get("mount") in ("floor", "wall", "on", "under")]

    def order(i):
        r, pts = P[i], outline(lab, i) or [(0, 0)]
        z = (r.get("z") or 0) if r.get("mount") == "wall" else 0
        return (_depth(lab, i), z >= OVERHEAD, z, -abs(G.area(pts)) if len(pts) > 2 else 0)

    placed, staged = [], []
    sx, sy, sw = x1 + STAGE_GAP, y0 + 30, 0
    for i in sorted(ids, key=order):
        m = abs_matrix(lab, i)
        if m is not None:
            placed.append((i, m))
            continue
        pts = outline(lab, i)
        if not pts:
            continue
        bx0, by0, bx1, by1 = G.bbox(pts)
        staged.append((i, (sx - bx0, sy - by0)))
        sy += by1 - by0 + 20
        sw = max(sw, bx1 - bx0)
    stage = (x1 + STAGE_GAP - 15, y0, sx + max(sw, STAGE_MIN[0]) + 15, max(sy, y0 + STAGE_MIN[1]))
    shell, vb = _shell(lab, rid)
    ex0, ey0, ex1, ey1 = min(x0, 0) - 50, min(y0, 0) - 60, stage[2] + 50, max(y1 + 80, stage[3] + 20)
    if vb:
        ex0, ey0, ex1, ey1 = min(ex0, vb[0]), min(ey0, vb[1]), max(ex1, vb[2]), max(ey1, vb[3])
    return dict(rid=rid, poly=poly, placed=placed, staged=staged, stage=stage, extent=(ex0, ey0, ex1, ey1),
                shell=shell)


def _prefixed(el, prefix):
    """A copy of an SVG subtree with every id (and every #reference to one) prefixed, so rooms can share a file."""
    el = copy.deepcopy(el)
    ids = {e.get("id") for e in el.iter() if e.get("id")}
    ref = re.compile(r"#([\w.:-]+)")
    for e in el.iter():
        for k, v in list(e.attrib.items()):
            if k == "id":
                e.set(k, prefix + v)
            elif "#" in v:
                e.set(k, ref.sub(lambda m: "#" + (prefix if m.group(1) in ids else "") + m.group(1), v))
    return el


def editable(lab, res):
    """The layout file for Inkscape: every room side by side, each with its "not placed yet" area.

    The room outlines are locked layers; the objects are on one layer per level (floor and benches, under benches,
    on benches, walls and shelves), each its own top-level group in document coordinates, so any of them can be
    dragged anywhere: onto another bench, or into another room. pull works out where each one landed.
    """
    flagged = _flagged(lab, res)
    blocks = [_block(lab, rid) for rid in lab.rooms]
    sizes = {}
    for b in blocks:
        sizes.update(label_plan(lab, res, b["rid"], LABEL_MIN["layout"], covered=True))
    cols = 1 if len(blocks) <= 1 else 2 if len(blocks) <= 4 else 3
    widths, heights = [0.0] * cols, [0.0] * ((len(blocks) + cols - 1) // cols or 1)
    for k, b in enumerate(blocks):
        ex0, ey0, ex1, ey1 = b["extent"]
        widths[k % cols] = max(widths[k % cols], ex1 - ex0)
        heights[k // cols] = max(heights[k // cols], ey1 - ey0)
    rooms_svg, layers = [], {k: [] for k, _ in LAYERS}
    for k, b in enumerate(blocks):
        c, row = k % cols, k // cols
        ox = sum(widths[:c]) + c * ROOM_GAP - b["extent"][0]
        oy = sum(heights[:row]) + row * ROOM_GAP - b["extent"][1]
        rid = b["rid"]
        parts = []
        if b["shell"] is not None:
            for child in b["shell"]:
                tag = child.tag.split("}")[-1]
                if tag in ("namedview", "title", "metadata") or not isinstance(child.tag, str):
                    continue
                el = _prefixed(child, f"{rid}--")
                if el.get(f"{{{NS_INK}}}groupmode") == "layer":
                    el.set(f"{{{NS_SOD}}}insensitive", "true")
                parts.append(ET.tostring(el, encoding="unicode"))
        else:
            parts.append(f'<polygon points="{_pts(b["poly"])}" fill="none" stroke="#333" stroke-width="3"/>'
                         f'<text x="0" y="-30" font-family="sans-serif" font-size="20" font-weight="bold">{esc(rid)}</text>')
        sx0, sy0, sx1, sy1 = b["stage"]
        parts.append(f'<rect id="stage-{esc(rid)}" x="{_n(sx0)}" y="{_n(sy0)}" width="{_n(sx1 - sx0)}" '
                     f'height="{_n(sy1 - sy0)}" fill="#fff7ed" stroke="#e07b00" stroke-width="1" stroke-dasharray="6 4"/>'
                     f'<text x="{_n(sx0 + 8)}" y="{_n(sy0 + 18)}" font-family="sans-serif" font-size="12" fill="#e07b00">'
                     f'{esc(rid)}: not placed yet</text>')
        rooms_svg.append(f'<g xmlns="{NS_SVG}" xmlns:inkscape="{NS_INK}" xmlns:sodipodi="{NS_SOD}" id="room-{esc(rid)}" '
                         f'inkscape:groupmode="layer" inkscape:label="{esc(rid)} (room, locked)" sodipodi:insensitive="true" '
                         f'transform="translate({_n(ox)},{_n(oy)})">{"".join(parts)}</g>')
        for i, m in b["placed"]:
            ang = round(math.degrees(math.atan2(m[1], m[0]))) % 360
            layers[layout_layer(lab, res, i)].append(
                _object(lab, i, (m[4] + ox, m[5] + oy), ang, ang, flagged, sizes=sizes, nest=False))
        for i, (px, py) in b["staged"]:
            layers[layout_layer(lab, res, i)].append(
                _object(lab, i, (px + ox, py + oy), 0, 0, flagged, unplaced=True, nest=False))
    w = sum(widths) + (cols - 1) * ROOM_GAP
    h = sum(heights) + (len(heights) - 1) * ROOM_GAP
    help_y, h = h + 20, h + 90
    root = ET.Element(f"{{{NS_SVG}}}svg")
    root.set("width", f"{_n(w)}cm")
    root.set("height", f"{_n(h)}cm")
    root.set("viewBox", f"0 0 {_n(w)} {_n(h)}")
    root.append(ET.fromstring(
        f'<sodipodi:namedview xmlns:sodipodi="{NS_SOD}" xmlns:inkscape="{NS_INK}" id="namedview" pagecolor="#ffffff" '
        f'bordercolor="#666666" inkscape:document-units="cm" showgrid="false"/>'))
    for text in rooms_svg:
        root.append(ET.fromstring(text))
    for key, name in LAYERS:
        root.append(ET.fromstring(
            f'<g xmlns="{NS_SVG}" xmlns:inkscape="{NS_INK}" id="layer-{key}" inkscape:groupmode="layer" '
            f'inkscape:label="{esc(name)}">{"".join(layers[key])}</g>'))
    help_lines = ("Click anything and drag it: onto another bench, or into another room. pull works out where it "
                  "landed and what it stands on.",
                  "To put something from the floor on a bench (or back), move it to that layer: Layer › Move Selection "
                  "to Layer Above / Below (Shift+Page Up / Page Down), then drag it into place.",
                  "Moving a bench leaves what's on it behind: drag a box around the bench to take everything along. "
                  "Drop something in a room's 'not placed yet' area to take it out of the layout.",
                  "Rotate in 45° steps (Object › Transform). Hide or lock layers (Layer › Layers and Objects) to reach "
                  "what's underneath.",
                  "Save, then: python -m labmap check --layout to try it; python -m labmap pull to keep it.")
    root.append(ET.fromstring(
        f'<g xmlns="{NS_SVG}" xmlns:inkscape="{NS_INK}" xmlns:sodipodi="{NS_SOD}" id="layer-help" '
        f'inkscape:groupmode="layer" inkscape:label="help" sodipodi:insensitive="true">' +
        "".join(f'<text x="50" y="{_n(help_y + 16 * k)}" font-family="sans-serif" font-size="13" '
                f'fill="#595959">{esc(t)}</text>' for k, t in enumerate(help_lines)) + "</g>"))
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


# --- reading moves back -----------------------------------------------------------------------------------

def read_layout(path):
    """({object id: transform in document cm}, {room id: {"m": room frame -> document, "stage": corners}},
    {object id: the level layer it's on: floor, under, on or wall})."""
    root = ET.parse(path).getroot()
    k = svg.cm_per_unit(root)
    scale = (k, 0, 0, k, 0, 0)
    mats, rooms, layers = {}, {}, {}
    keys = {f"layer-{key}": key for key, _ in LAYERS}

    def walk(el, m, layer=None):
        m = svg.mul(m, svg.parse_transform(el.get("transform")))
        gid, tag = el.get("id") or "", el.tag.split("}")[-1]
        if tag == "g" and gid in keys:
            layer = keys[gid]
        if tag == "g" and gid.startswith(PREFIX):
            mats.setdefault(gid[len(PREFIX):], svg.mul(scale, m))
            if layer:
                layers.setdefault(gid[len(PREFIX):], layer)
        elif tag == "g" and gid.startswith("room-"):
            rooms.setdefault(gid[5:], {})["m"] = svg.mul(scale, m)
        elif tag == "rect" and gid.startswith("stage-"):
            x, y = float(el.get("x") or 0), float(el.get("y") or 0)
            w, h = float(el.get("width") or 0), float(el.get("height") or 0)
            rooms.setdefault(gid[6:], {})["stage"] = svg.apply(svg.mul(scale, m), [(x, y), (x + w, y), (x + w, y + h), (x, y + h)])
        for child in el:
            walk(child, m, layer)

    walk(root, svg.IDENTITY)
    return mats, {rid: r for rid, r in rooms.items() if "m" in r}, layers


def _carrier(r):
    from .checks import STACKABLE

    s = r.get("stackable")
    return s == "yes" or (s != "no" and r.get("category") in STACKABLE)


def no_moves():
    return {sheet: {} for sheet in MOVE_SHEETS}


def count(moves):
    return sum(len(v) for v in moves.values())


def moves_from(lab, mats, rooms, layers=None):
    """({"placeables": {id: {column: value}}, "services": ..., "equipment": ...}, [notes]): what the layout says
    has changed.

    Each object lands in the room (or staging area) under its centre. Something mounted on or under another object
    gets a new parent if it now sits over a different one: on = the topmost thing it can stand on (a bench, table,
    shelf, cabinet, cart, or anything with stackable = yes); under = something with free_under. Over nothing of the
    kind, it's standing on the floor now. What moves to another room takes along what's in it (drawers) and on it
    (sockets on a bench spine); equipment whose socket stays behind gets its outlet cleared.

    layers: {id: layer} from read_layout. Moving an object to another layer changes its mount: *floor and benches*
    = standing on the floor, *under benches* = under the bench it's dropped beneath, *on benches* = on whatever it's
    dropped on. (The *walls and shelves* layer holds things on shelves too, so moving there changes nothing.)
    """
    P, S, E = lab.placeables, lab.services, lab.equipment
    frames = {rid: (_inv(r["m"]), _room_poly(lab.rooms[rid])) for rid, r in rooms.items() if rid in lab.rooms}
    stages = {rid: G.bbox([_apply(frames[rid][0], p) for p in r["stage"]])
              for rid, r in rooms.items() if rid in frames and r.get("stage")}
    ids = [i for i, r in P.items() if r.get("mount") in ("floor", "wall", "on", "under", "part") and i in mats]
    ids = [i for i in ids if P[i].get("shape") != "group"] + [i for i in ids if P[i].get("shape") == "group"]
    notes = []

    def pinned(j):
        r = P.get(j, {})
        return r.get("fixed") == "yes" or (r.get("mount") == "part" and P.get(r.get("parent"), {}).get("fixed") == "yes")

    def locate(pt):
        for rid, (inv, poly) in frames.items():
            if G.inside(_apply(inv, pt), poly):
                return rid, False
        for rid, (x0, y0, x1, y1) in stages.items():
            px, py = _apply(frames[rid][0], pt)
            if x0 <= px <= x1 and y0 <= py <= y1:
                return rid, True
        return None, None

    land, ignored = {}, set()  # id -> (room, in its staging area); dropped outside everything: left as it was
    for i in ids:
        r = P[i]
        if r.get("mount") == "part":
            continue
        pts = outline(lab, i)
        if not pts:
            continue
        rid, staged = locate(_apply(mats[i], G.centroid(pts)))
        if rid is None and not pinned(i):
            notes.append(f"{i} is outside every room and 'not placed yet' area, so it was left as it was")
            ignored.add(i)
        land[i] = (r.get("room"), r.get("x") is None) if rid is None or pinned(i) else (rid, staged)
    for i in ids:
        if P[i].get("mount") == "part":
            land[i] = land.get(P[i].get("parent"))
            if P[i].get("parent") in ignored:
                ignored.add(i)
    rm = {i: svg.mul(frames[land[i][0]][0], mats[i]) for i in ids if land.get(i) and land[i][0] in frames}
    feet = {}

    def frame(j):
        """Where j is in its room: as drawn, except that a fixed object stays where the spreadsheet has it."""
        if pinned(j) or j in ignored:
            m = abs_matrix(lab, j)
            if m is not None:
                return m
        return rm.get(j)

    def footprint(j):
        if j not in feet:
            pts = outline(lab, j) if frame(j) is not None and P[j].get("shape") != "group" else None
            feet[j] = [_apply(frame(j), p) for p in pts] if pts else None
        return feet[j]

    def below(i):
        out, todo = set(), [i]
        while todo:
            for c in lab.children.get(todo.pop(), []):
                if c not in out:
                    out.add(c)
                    todo.append(c)
        return out

    def host(i, mount, rid, centre):
        mine = below(i) | {i}
        ok = (lambda r: _carrier(r)) if mount == "on" else (lambda r: r.get("free_under") is not None)
        cands = [j for j, r in P.items() if land.get(j) == (rid, False) and j not in mine and ok(r)
                 and r.get("mount") in ("floor", "wall", "on", "part") and footprint(j) and G.inside(centre, footprint(j))]
        if P[i].get("parent") in cands:
            return P[i]["parent"]
        return max(cands, key=lambda j: (_depth(lab, j), -abs(G.area(footprint(j))))) if cands else None

    new = {}
    for i in ids:
        r = P[i]
        if not land.get(i) or i not in rm or i in ignored:
            continue
        rid, staged = land[i]
        parent, mount = r.get("parent"), r.get("mount")
        target = LAYER_MOUNT.get((layers or {}).get(i))
        if target and target != mount and mount in ("floor", "wall", "on", "under") and r.get("shape") != "group":
            names = dict(LAYERS)
            notes.append(f"{i} was moved to the '{names[layers[i]]}' layer, so it's mounted '{target}' now"
                         + ("" if target == "floor" else f": {target} whatever it's dropped on"))
            parent, mount = None, target
        if staged:  # waiting to be placed; in another room's area, it can't keep a parent in the old room
            if rid != r.get("room") and mount != "part":
                parent = None if parent and P.get(parent, {}).get("room") != rid else parent
                mount = "floor" if not parent and mount in ("wall", "part") else mount
            new[i] = dict(x=None, y=None, faces=r.get("faces") or "S", parent=parent, mount=mount, room=rid)
            continue
        m = rm[i]
        pts = outline(lab, i, {k: (v["x"], v["y"], v["faces"]) for k, v in new.items() if v["x"] is not None})
        if not pts:
            continue
        centre = _apply(m, G.centroid(pts))
        if mount in ("on", "under"):
            h = host(i, mount, rid, centre)
            if h is None:
                notes.append(f"{i} isn't {mount} anything any more, so it's standing on the floor now")
                parent, mount = None, "floor"
            else:
                parent = h
        base = None
        if parent:
            base = svg.mul(frames[rid][0], mats[parent]) if mount == "part" and parent in mats else frame(parent)
            if base is None:
                continue
        a, b, c, d, e, f = svg.mul(_inv(base), m) if parent else m
        ang = math.degrees(math.atan2(b, a)) % 360
        snap = int(round(ang / 45) * 45) % 360
        if abs((ang - snap + 180) % 360 - 180) > 2:
            notes.append(f"{i} is turned {ang:.0f}°, rounded to {snap}°")
        if abs(math.hypot(a, b) - 1) > 0.01:
            notes.append(f"{i} was resized in Inkscape: sizes come from the spreadsheet, so that was ignored")
        rp = [G.rot(snap, u, v) for u, v in pts]
        x, y = round(e + min(p[0] for p in rp)), round(f + min(p[1] for p in rp))
        new[i] = dict(x=x, y=y, faces=FACES[snap], parent=parent, mount=mount, room=rid)

    moves = no_moves()
    for i, v in new.items():
        r = P[i]
        faces = None if v["faces"] == "S" and not r.get("faces") else v["faces"]
        if v["x"] is None:
            faces = r.get("faces")
        same_xy = (v["x"] is None and r.get("x") is None) or (v["x"] is not None and r.get("x") is not None
                                                             and abs(v["x"] - r["x"]) < 0.6 and abs(v["y"] - r["y"]) < 0.6)
        change = {k: v[k] for k in ("parent", "mount", "room") if v[k] != r.get(k)}
        if same_xy and not change and (faces or "S") == (r.get("faces") or "S"):
            continue
        if r.get("fixed") == "yes":
            notes.append(f"{i} is fixed = yes, so its move in the layout was ignored")
            continue
        moves["placeables"][i] = dict(x=v["x"], y=v["y"], faces=faces, **change)

    def room_now(i):
        """The room i ends up in: its own move; else, if it isn't drawn itself (a drawer), its nearest ancestor's."""
        j, seen = i, set()
        while j in P and j not in seen:
            seen.add(j)
            if "room" in moves["placeables"].get(j, {}):
                return moves["placeables"][j]["room"]
            if j in mats:
                return P[j].get("room")
            j = P[j].get("parent")
        return P[i].get("room")

    for i, r in P.items():
        if i not in moves["placeables"] and r.get("parent") and room_now(i) != r.get("room"):
            moves["placeables"][i] = dict(room=room_now(i))
    for sid, s in S.items():
        if s.get("parent") in P and room_now(s["parent"]) != s.get("room"):
            moves["services"][sid] = dict(room=room_now(s["parent"]))
    for eid, e in E.items():
        out = e.get("outlet")
        if eid in P and out in S:
            where = moves["services"].get(out, {}).get("room", S[out].get("room"))
            if room_now(eid) != where:
                moves["equipment"][eid] = dict(outlet=None)
                notes.append(f"{eid} moves to {room_now(eid)} but its outlet {out} is in {where}: outlet cleared "
                             f"(the nearest socket is assumed until you fill it in)")
    return moves, notes


def layout_moves(lab):
    """What the layout file says has changed: (moves, notes) as moves_from() gives them."""
    path = layout_path(lab.folder)
    if not path.exists():
        return no_moves(), []
    mats, rooms, layers = read_layout(path)
    return moves_from(lab, mats, rooms, layers)


def describe_move(lab, sheet, i, change):
    """'SPEC-02: LAB-A, on BENCH-04.B at 10, 5  ->  LAB-B, on BENCH-14.A at 30, 5 E' for printing a pull."""
    if sheet == "services":
        return f"{i} (socket/tap): moves with {lab.services[i].get('parent')} to {change['room']}"
    if sheet == "equipment":
        return f"outlet {lab.equipment[i].get('outlet')} cleared (it stays in the old room)"
    r = lab.placeables[i]

    def where(room, parent, mount, x, y, faces):
        spot = "not placed" if x is None else f"{x}, {y}" + (f" {faces}" if faces and faces != "S" else "")
        return f"{room}, " + (f"{mount} {parent} at {spot}" if parent else spot)

    if set(change) == {"room"}:
        return f"{r.get('room')}  ->  {change['room']} (with {r.get('parent')})"
    after = {**r, **change}
    return (f"{where(r.get('room'), r.get('parent'), r.get('mount'), r.get('x'), r.get('y'), r.get('faces'))}  ->  "
            f"{where(after.get('room'), after.get('parent'), after.get('mount'), after.get('x'), after.get('y'), after.get('faces'))}"
            + ("  (now standing on the floor)" if change.get("mount") == "floor" and r.get("mount") != "floor" else ""))


def layout_path(folder):
    return Path(folder) / "build" / "layout" / LAYOUT_FILE


def write_layouts(lab, res, force=False):
    """Write build/layout/labs.svg with every room. Left alone if it has moves not pulled yet, unless force.
    Returns (path, status)."""
    path = layout_path(lab.folder)
    if path.exists() and not force:
        try:
            pending, _ = layout_moves(lab)
        except (ET.ParseError, KeyError):
            pending = no_moves()
        if count(pending):
            names = sorted({i for v in pending.values() for i in v})
            return path, f"kept: it has moves not pulled into lab-data.xlsx yet ({', '.join(names[:6])}" + \
                         (" ..." if len(names) > 6 else "") + ")"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(editable(lab, res), encoding="utf-8")
    for rid in lab.rooms:  # one file per room, from before the combined layout: out of date now
        (path.parent / f"{rid}.svg").unlink(missing_ok=True)
    return path, "written"
