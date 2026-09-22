"""Figures for the report: bench space, floor space, triage, workflow groups, containers, completeness."""
from __future__ import annotations

import itertools
import math
from collections import defaultdict

from . import geometry as G
from .checks import NOT_OBSTACLES

SURFACES = {"bench", "table", "desk", "shelf", "cart"}
CONTAINERS = {"drawer", "shelf", "cabinet", "container", "pedestal"}


def location(lab, i):
    """'LAB-A › BENCH-04.A › PED-01 › PED-01.D2'"""
    chain, j = [], i
    while j in lab.placeables and j not in chain:
        chain.append(j)
        j = lab.placeables[j].get("parent")
    room = lab.placeables.get(i, {}).get("room")
    return " › ".join(([room] if room else []) + chain[::-1])


def _grid_mark(grid, poly, w, d):
    ny, nx = len(grid), len(grid[0])
    bx0, by0, bx1, by1 = G.bbox(poly)
    for iy in range(max(0, int(by0 / d * ny)), min(ny, int(by1 / d * ny) + 1)):
        for ix in range(max(0, int(bx0 / w * nx)), min(nx, int(bx1 / w * nx) + 1)):
            if G.inside(((ix + 0.5) * w / nx, (iy + 0.5) * d / ny), poly):
                grid[iy][ix] = True


def surfaces(res):
    """Bench tops and other surfaces: how much is used, reserved and free, and the largest free rectangle."""
    lab, geo, P = res.lab, res.geo, res.lab.placeables
    out = []
    for i, r in P.items():
        g = geo.get(i)
        on = [c for c in lab.children.get(i, []) if P[c].get("mount") == "on" and P[c].get("x") is not None]
        if not g or not g.poly or not (r.get("category") in SURFACES or on):
            continue
        w, d = g.size
        nx, ny = max(1, round(w / lab.settings["grid"])), max(1, round(d / lab.settings["grid"]))
        top = [[G.inside(((ix + 0.5) * w / nx, (iy + 0.5) * d / ny), g.local) for ix in range(nx)] for iy in range(ny)]
        used = [[False] * nx for _ in range(ny)]
        kept = [[False] * nx for _ in range(ny)]
        for c in on:
            cr = P[c]
            got = G.in_frame(lab, c, cr, (0.0, 0.0), 0, [])
            if not got:
                continue
            local, _, T, _ = got
            _grid_mark(kept if cr.get("category") == "workspace" else used, [T(u, v) for u, v in local], w, d)
            for u0, v0, u1, v1 in G.clear_boxes(cr, cr["w"], cr.get("d") or cr["w"]).values():
                _grid_mark(kept, [T(u0, v0), T(u1, v0), T(u1, v1), T(u0, v1)], w, d)
        cell = (w / nx) * (d / ny)
        total = sum(t for row in top for t in row)
        n_used = sum(t and u for tr, ur in zip(top, used) for t, u in zip(tr, ur))
        n_kept = sum(t and k and not u for tr, kr, ur in zip(top, kept, used) for t, k, u in zip(tr, kr, ur))
        free = [[t and not u and not k for t, u, k in zip(tr, ur, kr)] for tr, ur, kr in zip(top, used, kept)]
        cols, rows = G.largest_rectangle(free)
        out.append(dict(id=i, room=r.get("room"), name=r.get("name"), area=total * cell / 1e4,
                        used=n_used / total if total else 0, kept=n_kept / total if total else 0,
                        free=(total - n_used - n_kept) / total if total else 0,
                        largest=(round(cols * w / nx), round(rows * d / ny)), items=len(on)))
    return sorted(out, key=lambda s: (s["room"] or "", s["id"]))


def rooms(res):
    lab, geo, P = res.lab, res.geo, res.lab.placeables
    out = []
    for rid, room in lab.rooms.items():
        poly = room.get("poly")
        floor = sum(abs(G.area(g.poly)) for i, g in geo.items() if g and g.poly and g.room == rid
                    and not P[i].get("parent") and P[i].get("category") not in NOT_OBSTACLES and g.zc[0] < lab.settings["blocks_walking_below"])
        floor += sum(abs(G.area(g.poly)) for i, g in geo.items() if g and g.poly and g.room == rid
                     and P[i].get("mount") == "part" and g.zc[0] < lab.settings["blocks_walking_below"])
        area = abs(G.area(poly)) if poly else None
        out.append(dict(id=rid, name=room.get("name"), area=area / 1e4 if area else None,
                        covered=floor / area if area else None, heat=res.heat.get(rid, 0), cooling=room.get("cooling"),
                        objects=sum(1 for r in P.values() if r.get("room") == rid),
                        walk=res.walk_notes.get(rid)))
    return out


def triage(res):
    """Equipment whose future is being decided, and how much space leaving would free."""
    lab, geo, P = res.lab, res.geo, res.lab.placeables
    out = []
    for eid, e in lab.equipment.items():
        plan = e.get("plan")
        rare = e.get("usage") in ("yearly", "never")
        if plan in (None, "keep") and not rare:
            continue
        g, where = geo.get(eid), None
        if g and g.poly:
            where = "bench" if P[eid].get("mount") == "on" else "floor"
        out.append(dict(id=eid, name=P.get(eid, {}).get("name"), room=P.get(eid, {}).get("room"), plan=plan or "",
                        usage=e.get("usage") or "", condition=e.get("condition") or "",
                        area=abs(G.area(g.poly)) / 1e4 if g and g.poly else None, where=where))
    order = {"dispose": 0, "storage": 1, "undecided": 2, "relocate": 3, "new": 4, "": 5, "keep": 6}
    return sorted(out, key=lambda t: (order.get(t["plan"], 5), t["id"]))


def workflows(res):
    lab, geo = res.lab, res.geo
    groups = defaultdict(list)
    for eid, e in lab.equipment.items():
        if e.get("workflow"):
            groups[e["workflow"]].append(eid)
    out = []
    for tag, ids in sorted(groups.items()):
        pos = {i: G.position(lab, geo, i) for i in ids}
        rooms = sorted({lab.placeables.get(i, {}).get("room") for i in ids} - {None})
        placed = [p for p in pos.values() if p]
        split = len(rooms) > 1
        spread = None
        if len(placed) > 1 and not split:
            spread = max(math.dist(a[:2], b[:2]) for a, b in itertools.combinations(placed, 2)) / 100
        out.append(dict(tag=tag, ids=ids, rooms=rooms, split=split, spread=spread))
    return out


def containers(res):
    lab, P = res.lab, res.lab.placeables
    count = defaultdict(int)
    for it in lab.items.values():
        count[it.get("container")] += 1
    out = []
    for i, r in P.items():
        if r.get("category") in CONTAINERS or count.get(i):
            out.append(dict(id=i, name=r.get("name"), where=location(lab, i), fill=r.get("fill"),
                            checked=r.get("checked"), items=count.get(i, 0)))
    return out


def completeness(res):
    lab, geo, P, E, S = res.lab, res.geo, res.lab.placeables, res.lab.equipment, res.lab.services
    solid = [r for r in P.values() if r.get("shape") != "group"]
    placeable = [i for i, r in P.items() if r.get("mount") not in ("in", None) and r.get("shape") != "group"]
    powered = [e for e in E.values() if e.get("plug_type") not in ("hardwired", "none")]
    sockets = [s for s in S.values() if s.get("type") in ("outlet", "strip")]
    return [
        ("Rooms with an outline", sum(1 for r in lab.rooms.values() if r.get("poly")), len(lab.rooms)),
        ("Objects measured (w, d, h)", sum(1 for r in solid if r.get("w") and r.get("h") and (r.get("d") or r.get("shape") == "circle")), len(solid)),
        ("Objects placed", sum(1 for i in placeable if geo.get(i) and geo[i].poly), len(placeable)),
        ("Equipment with power data", sum(1 for e in powered if e.get("watts_typ") is not None), len(powered)),
        ("Equipment with usage", sum(1 for e in E.values() if e.get("usage")), len(E)),
        ("Equipment with a plan", sum(1 for e in E.values() if e.get("plan")), len(E)),
        ("Sockets and strips traced to a circuit", sum(1 for s in sockets if res.circuit_of.get(s["id"])), len(sockets)),
        ("Containers checked", sum(1 for r in P.values() if r.get("checked")), sum(1 for r in P.values() if r.get("category") in CONTAINERS)),
    ]


def unplaced(res):
    lab, geo, P = res.lab, res.geo, res.lab.placeables
    return [(i, r.get("name"), r.get("room")) for i, r in P.items()
            if r.get("mount") in ("floor", "wall", "part") and r.get("shape") != "group"
            and (r.get("x") is None or r.get("y") is None)]
