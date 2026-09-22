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


def editable(lab, res, rid):
    """The layout file for Inkscape: the room outline file's layers, locked, plus one layer of objects per level.

    Every object is its own top-level group (a group's parts stay inside it), placed in room coordinates, so any of
    them can be clicked and dragged, including onto another bench: pull works out what it now stands on.
    """
    P = lab.placeables
    flagged = _flagged(lab, res)
    sizes = label_plan(lab, res, rid, LABEL_MIN["layout"], covered=True)
    room = lab.rooms[rid]
    poly = room.get("poly") or [(0, 0), (room.get("width") or 500, 0),
                                (room.get("width") or 500, room.get("depth") or 400), (0, room.get("depth") or 400)]
    x0, y0, x1, y1 = G.bbox(poly)
    ids = [i for i, r in P.items() if r.get("room") == rid and r.get("mount") in ("floor", "wall", "on", "under")]

    def layer(i):
        return layout_layer(lab, res, i)

    def order(i):
        r, pts = P[i], outline(lab, i) or [(0, 0)]
        z = (r.get("z") or 0) if r.get("mount") == "wall" else 0
        return (_depth(lab, i), z >= OVERHEAD, z, -abs(G.area(pts)) if len(pts) > 2 else 0)

    layers = {k: [] for k, _ in LAYERS}
    staged = []
    for i in sorted(ids, key=order):
        m = abs_matrix(lab, i)
        if m is None:
            staged.append(i)
            continue
        ang = round(math.degrees(math.atan2(m[1], m[0]))) % 360
        layers[layer(i)].append(_object(lab, i, (m[4], m[5]), ang, ang, flagged, sizes=sizes, nest=False))
    sx, sy, sw = x1 + STAGE_GAP, y0 + 25, 0
    for i in staged:
        pts = outline(lab, i)
        if not pts:
            continue
        bx0, by0, bx1, by1 = G.bbox(pts)
        layers[layer(i)].append(_object(lab, i, (sx - bx0, sy - by0), 0, 0, flagged, unplaced=True, nest=False))
        sy += by1 - by0 + 20
        sw = max(sw, bx1 - bx0)
    ex0, ey0 = min(x0, 0) - 50, min(y0, 0) - 60
    ex1, ey1 = max(x1 + 50, sx + sw + 50 if staged else 0), max(y1 + 80, sy + 20)

    shell = lab.folder / "rooms" / (room.get("shell") or "")
    root = ET.Element(f"{{{NS_SVG}}}svg")
    if shell.is_file():
        src = ET.parse(shell).getroot()
        vb = [float(n) for n in svg.NUM.findall(src.get("viewBox") or "")]
        if len(vb) == 4:
            ex0, ey0, ex1, ey1 = min(ex0, vb[0]), min(ey0, vb[1]), max(ex1, vb[0] + vb[2]), max(ey1, vb[1] + vb[3])
        for child in src:
            el = copy.deepcopy(child)
            if el.get(f"{{{NS_INK}}}groupmode") == "layer":
                el.set(f"{{{NS_SOD}}}insensitive", "true")
            root.append(el)
    else:
        root.append(ET.fromstring(f'<g xmlns="{NS_SVG}"><polygon points="{_pts(poly)}" fill="none" stroke="#333" '
                                  f'stroke-width="3"/></g>'))
    help_y, ey1 = ey1 + 12, ey1 + 70
    w, h = ex1 - ex0, ey1 - ey0
    root.set("width", f"{_n(w)}cm")
    root.set("height", f"{_n(h)}cm")
    root.set("viewBox", f"{_n(ex0)} {_n(ey0)} {_n(w)} {_n(h)}")
    help_lines = ("Click anything and drag it, including onto another bench: pull works out what it stands on now.",
                  "Moving a bench leaves what's on it behind: drag a box around the bench to take everything along.",
                  "Rotate in 45° steps (Object › Transform). Hide or lock layers (Layer › Layers and Objects) to reach "
                  "what's underneath.",
                  "Save, then: python -m labmap check --layout to try it; python -m labmap pull to keep it.")
    if staged:
        layers["floor"].insert(0, f'<text x="{_n(sx)}" y="{_n(y0 + 12)}" font-family="sans-serif" font-size="12" '
                                  f'fill="#e07b00">Not placed yet: drag into the room</text>')
    for key, name in LAYERS:
        root.append(ET.fromstring(
            f'<g xmlns="{NS_SVG}" xmlns:inkscape="{NS_INK}" id="layer-{key}" inkscape:groupmode="layer" '
            f'inkscape:label="{esc(name)}">{"".join(layers[key])}</g>'))
    root.append(ET.fromstring(
        f'<g xmlns="{NS_SVG}" xmlns:inkscape="{NS_INK}" xmlns:sodipodi="{NS_SOD}" id="layer-help" '
        f'inkscape:groupmode="layer" inkscape:label="help" sodipodi:insensitive="true">' +
        "".join(f'<text x="{_n(ex0 + 50)}" y="{_n(help_y + 14 * k)}" font-family="sans-serif" font-size="11" '
                f'fill="#595959">{esc(t)}</text>' for k, t in enumerate(help_lines)) + "</g>"))
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


# --- reading moves back -----------------------------------------------------------------------------------

def read_matrices(path):
    """{object id: transform matrix in room centimetres} for every obj-<ID> group in a layout file."""
    root = ET.parse(path).getroot()
    k = svg.cm_per_unit(root)
    out = {}

    def walk(el, m):
        m = svg.mul(m, svg.parse_transform(el.get("transform")))
        gid = el.get("id") or ""
        if el.tag == f"{{{NS_SVG}}}g" and gid.startswith(PREFIX):
            out.setdefault(gid[len(PREFIX):], svg.mul((k, 0, 0, k, 0, 0), m))
        for child in el:
            walk(child, m)

    walk(root, svg.IDENTITY)
    return out


def _carrier(r):
    from .checks import STACKABLE

    s = r.get("stackable")
    return s == "yes" or (s != "no" and r.get("category") in STACKABLE)


def positions(lab, rid, mats):
    """({id: (x, y, faces)} where the layout differs from lab-data.xlsx, [notes]).

    Something mounted on or under another object that now sits over a different one gets
    (x, y, faces, new parent, new mount) instead: on = the topmost thing it can stand on (a bench, table, shelf,
    cabinet, cart, or anything with stackable = yes) under its centre; under = something with free_under. Over
    nothing of the kind, it's standing on the floor now.
    """
    P = lab.placeables
    poly = lab.rooms[rid].get("poly")
    room_right = G.bbox(poly)[2] if poly else None
    ids = [i for i, r in P.items() if r.get("room") == rid and r.get("mount") in ("floor", "wall", "on", "under", "part")]
    ids = [i for i in ids if P[i].get("shape") != "group"] + [i for i in ids if P[i].get("shape") == "group"]
    feet = {}

    def pinned(j):
        r = P.get(j, {})
        return r.get("fixed") == "yes" or (r.get("mount") == "part" and P.get(r.get("parent"), {}).get("fixed") == "yes")

    def frame(j):
        """Where j really is: as drawn, except that a fixed object stays where the spreadsheet has it."""
        if pinned(j):
            m = abs_matrix(lab, j)
            if m is not None:
                return m
        return mats.get(j)

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

    def host(i, mount, centre):
        mine = below(i) | {i}
        ok = (lambda r: _carrier(r)) if mount == "on" else (lambda r: r.get("free_under") is not None)
        cands = [j for j, r in P.items() if r.get("room") == rid and j not in mine and ok(r)
                 and r.get("mount") in ("floor", "wall", "on", "part") and footprint(j) and G.inside(centre, footprint(j))]
        if P[i].get("parent") in cands:
            return P[i]["parent"]
        return max(cands, key=lambda j: (_depth(lab, j), -abs(G.area(footprint(j))))) if cands else None

    new, notes = {}, []
    for i in ids:
        r = P[i]
        placed = r.get("x") is not None and r.get("y") is not None
        parent, mount = r.get("parent"), r.get("mount")
        if i not in mats:
            if placed and (not parent or parent in mats):
                notes.append(f"{i} isn't in the layout (deleted or ungrouped?), so it was left as it is")
            continue
        m = mats[i]
        pts = outline(lab, i, {k: v[:3] for k, v in new.items() if v[0] is not None})
        if not pts:
            continue
        cu, cv = G.centroid(pts)
        cx, cy = _apply(m, (cu, cv))
        staged = mount != "part" and room_right is not None and cx > room_right + STAGE_GAP / 2
        if mount in ("on", "under") and not staged:
            h = host(i, mount, (cx, cy))
            if h is None:
                notes.append(f"{i} isn't {mount} anything any more, so it's standing on the floor now")
                parent, mount = None, "floor"
            else:
                parent = h
        if parent and parent not in mats:
            continue
        base = mats[parent] if mount == "part" else frame(parent)
        a, b, c, d, e, f = svg.mul(_inv(base), m) if parent else m
        ang = math.degrees(math.atan2(b, a)) % 360
        snap = int(round(ang / 45) * 45) % 360
        if abs((ang - snap + 180) % 360 - 180) > 2:
            notes.append(f"{i} is turned {ang:.0f}°, rounded to {snap}°")
        if abs(math.hypot(a, b) - 1) > 0.01:
            notes.append(f"{i} was resized in Inkscape: sizes come from the spreadsheet, so that was ignored")
        rp = [G.rot(snap, u, v) for u, v in pts]
        x, y = (None, None) if staged else (e + min(p[0] for p in rp), f + min(p[1] for p in rp))
        new[i] = (None if x is None else round(x), None if y is None else round(y), FACES[snap], parent, mount)
    updates = {}
    for i, (x, y, faces, parent, mount) in new.items():
        r = P[i]
        if faces == "S" and not r.get("faces"):
            faces = None
        if x is None:
            faces = r.get("faces")
        same_xy = (x is None and r.get("x") is None) or (x is not None and r.get("x") is not None
                                                         and abs(x - r["x"]) < 0.6 and abs(y - r["y"]) < 0.6)
        same_host = (parent, mount) == (r.get("parent"), r.get("mount"))
        if same_xy and same_host and (faces or "S") == (r.get("faces") or "S"):
            continue
        if r.get("fixed") == "yes":
            notes.append(f"{i} is fixed = yes, so its move in the layout was ignored")
            continue
        updates[i] = (x, y, faces) if same_host else (x, y, faces, parent, mount)
    return updates, notes


def layout_moves(lab):
    """All moves in all of a lab's layout files: ({id: update}, [notes]) as positions() gives them."""
    updates, notes = {}, []
    for rid in lab.rooms:
        path = layout_path(lab.folder, rid)
        if path.exists():
            up, nt = positions(lab, rid, read_matrices(path))
            updates.update(up)
            notes += [f"{rid}: {n}" for n in nt]
    return updates, notes


def describe_move(r, update):
    """'on BENCH-04.B at 10, 0 S  ->  on BENCH-02 at 30, 5 S' for printing a pull."""
    def where(parent, mount, x, y, faces):
        spot = "not placed" if x is None else f"{x}, {y} {faces or 'S'}"
        return f"{mount} {parent} at {spot}" if parent else spot
    x, y, faces, *host = update
    parent, mount = host if host else (r.get("parent"), r.get("mount"))
    return (f"{where(r.get('parent'), r.get('mount'), r.get('x'), r.get('y'), r.get('faces'))}  ->  "
            f"{where(parent, mount if parent else 'floor', x, y, faces)}" + ("  (now standing on the floor)" if host and not parent else ""))


def layout_path(folder, rid):
    return Path(folder) / "build" / "layout" / f"{rid}.svg"


def write_layouts(lab, res, force=False):
    """Write build/layout/<room>.svg for every room. A file with moves not yet pulled is left alone unless force."""
    out = []
    for rid in lab.rooms:
        path = layout_path(lab.folder, rid)
        if path.exists() and not force:
            try:
                pending, _ = positions(lab, rid, read_matrices(path))
            except ET.ParseError:
                pending = {}
            if pending:
                names = ", ".join(sorted(pending)[:6]) + (" ..." if len(pending) > 6 else "")
                out.append((rid, path, f"kept: it has moves not pulled into lab-data.xlsx yet ({names})"))
                continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(editable(lab, res, rid), encoding="utf-8")
        out.append((rid, path, "written"))
    return out
