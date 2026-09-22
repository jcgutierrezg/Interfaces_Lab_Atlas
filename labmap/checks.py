"""The rules. Every finding names its rule, the objects involved and the room.

Thresholds come from the settings sheet (defaults in model.SETTINGS). Each rule is a problem (something is
wrong) or a warning (worth a look). example/README.md explains each rule with numbers.
"""
from __future__ import annotations

import datetime as dt
import math
from collections import defaultdict
from dataclasses import dataclass, field

from . import geometry as G
from . import md
from .model import Finding, stock

NOT_OBSTACLES = {"door", "window", "workspace"}
SPRINKLER_EXEMPT = {"door", "window", "structure", "overhead", "workspace"}  # built in, not stored or placed
LINK_FOR = {"gas": {"gas-line"}, "vacuum": {"vacuum-line", "gas-line"}, "air": {"gas-line"},
            "water": {"water-line", "cooling-line"}, "drain": {"water-line"}, "exhaust": {"exhaust"},
            "network": {"ethernet"}}  # links that meet a need
STACKABLE = {"bench", "optical-table", "desk", "table", "shelf", "cabinet", "cart"}  # things may stand on these unless stackable = no

RULES = {  # rule: (title, what it means, level). {placeholders} are settings.
    "data": ("Data problems", "Rows the checks couldn't use as they are. Fix these first: they can hide other problems.", "problem"),
    "outside-room": ("Outside the room", "The footprint crosses the room's outline.", "problem"),
    "off-parent": ("Off its support", "Sits on or under something but sticks out of it.", "problem"),
    "under-fit": ("Doesn't fit underneath", "Taller than the free space under its parent less {fit_margin} cm of slack, "
                                            "or the parent has no free_under.", "problem"),
    "in-fit": ("Doesn't fit inside", "Taller than the working space inside its fume hood (or other enclosure), less "
                                     "{fit_margin} cm of slack.", "problem"),
    "overlap": ("Overlap", "Two footprints overlap on the plan and in height.", "problem"),
    "clear-zone": ("Clear zone blocked", "Something stands in space that has to stay free.", "problem"),
    "headroom": ("Headroom", "Not enough space above: a lid, sash or stack hits a shelf, or comes within {fit_margin} cm "
                             "of the ceiling.", "problem"),
    "sprinkler": ("Too close to the sprinklers", "Reaches higher than {sprinkler_clearance} cm below the ceiling of a room "
                                                "with sprinklers (built-in things, fixed = yes, excepted).", "problem"),
    "wall-clearance": ("Clear zone into a wall", "The space that has to stay free runs into a wall.", "problem"),
    "walkway": ("Can't be reached", "No path at least {walkway_width} cm wide from a door to the space in front of it.", "problem"),
    "no-socket": ("No socket", "Needs power, but there's no socket or strip in the room to plug into.", "problem"),
    "sockets": ("Not enough sockets", "More plugs than sockets. A strip plugged in takes one socket too.", "problem"),
    "strip-chain": ("Strip into strip", "A power strip plugged into another strip.", "problem"),
    "circuit-load": ("Circuit overloaded", "Running load above {circuit_limit}% of the breaker rating.", "problem"),
    "critical-shared": ("Critical load at risk",
                        "Must never lose power, but shares its circuit with something peaking at {heavy_load} W or more.", "problem"),
    "heat": ("Too much heat", "Equipment gives off more heat than the room's cooling can remove.", "problem"),
    "cable-reach": ("Too far apart", "The cable or tubing run is longer than allowed.", "problem"),
    "utility": ("Service out of reach", "Needs gas, water, drain, vacuum, air, network, exhaust or earth (needs column), and there "
                                       "isn't one within {utility_reach} cm, or a link to one.", "problem"),
    "socket-load": ("Socket or strip overloaded", "Running load above its rating_a.", "problem"),
    "keep-apart": ("Too close together", "Things the keep_apart sheet says must be kept apart, closer than allowed.",
                   "problem"),
    "document-expired": ("Document expired", "A form or certificate on the documents sheet is past its expiry date.",
                         "problem"),
    "document-expiring": ("Document expiring soon", "Expires within {expiry_warning_days} days.", "warning"),
    "document-unapproved": ("Document not approved", "A form or certificate whose status isn't approved.", "warning"),
    "window": ("Window covered", "Something stands in front of a window, between its sill and its top.", "warning"),
    "not-stackable": ("Stacked on something not stackable",
                      "Sits on something whose stackable is no (or blank, for a category that isn't usually stacked on). "
                      "Set stackable = yes on the one underneath if that's intended.", "warning"),
    "spare-out": ("Spare part out of stock",
                  "A required spare (min_qty filled on the items sheet) with none left. A blank qty counts as none.",
                  "warning"),
    "spare-low": ("Spare part running low", "Fewer in stock than its min_qty.", "warning"),
    "left-behind": ("Still pointing at something decommissioned", "It's gone, but rows or files still refer to it: "
                    "move, re-link, delete or archive them (the Decommissioning section lists them all).", "warning"),
    "keep-apart-near": ("Close together", "Things the keep_apart sheet would rather keep apart, closer than it suggests.",
                        "warning"),
    "sash": ("Too close to the sash", "Inside a fume hood, less than {sash_clearance} cm behind the sash.", "warning"),
    "door-fit": ("Won't fit through the door", "Arriving or moving (plan new or relocate), but bigger than every door of "
                                               "its room, even on its side, allowing {fit_margin} cm.", "warning"),
}


def describe(rule, settings):
    title, what, level = RULES[rule]
    return title, what.format(**settings), level


@dataclass
class Result:
    lab: object
    geo: dict
    findings: list
    assign: dict = field(default_factory=dict)      # device -> socket or strip it's plugged into
    nearest: dict = field(default_factory=dict)     # device -> (socket, cm) where outlet was blank
    used: dict = field(default_factory=dict)        # socket or strip -> sockets in use
    circuit_of: dict = field(default_factory=dict)  # socket or strip -> circuit
    load: dict = field(default_factory=dict)        # circuit -> running W
    members: dict = field(default_factory=dict)     # circuit -> devices
    heat: dict = field(default_factory=dict)        # room -> W
    runs: list = field(default_factory=list)        # (link, run in cm or None, limit in cm or None)
    walk_notes: dict = field(default_factory=dict)  # room -> why walkways weren't checked
    socket_load: dict = field(default_factory=dict)  # socket or strip with a rating_a -> running W through it

    def add(self, rule, message, ids=(), room=None):
        self.findings.append(Finding(rule, message, tuple(ids), room))

    def by_rule(self, level=None):
        out = {}
        for f in self.findings:
            if level is None or RULES[f.rule][2] == level:
                out.setdefault(f.rule, []).append(f)
        return {k: out[k] for k in RULES if k in out}


def run(lab, today=None):
    geo, issues = G.place_all(lab)
    res = Result(lab, geo, list(lab.issues) + issues)
    _geometry(res)
    _documents(res, today or dt.date.today())
    _spares(res)
    _power(res)
    _links(res)
    _utilities(res)
    _keep_apart(res)
    _doors(res)
    _left_behind(res)
    blocked = {f.ids[0] for f in res.findings if f.rule == "clear-zone"}
    for rid in lab.rooms:
        _walkways(res, rid, blocked)
    return res


def zones(r, g, person=200, door_gap=G.DOOR_GAP):
    """[(side, polygon, height band)] of the space an object needs kept free."""
    zr = (0, person) if r.get("mount") in ("floor", "wall", "part") else g.z
    if r.get("category") == "window":
        zr = g.z  # a window only needs its own height kept clear
    out = []
    if g.zone:
        out.append(("front", g.zone, zr))
    else:
        for side, (u0, v0, u1, v1) in G.clear_boxes(r, *g.size, door_gap).items():
            out.append((side, [g.T(u0, v0), g.T(u1, v0), g.T(u1, v1), g.T(u0, v1)], zr))
    if r.get("clear_top"):
        out.append(("top", g.poly, (g.z[1], g.z[1] + r["clear_top"])))
    return out


def _chain(P, i):
    out, j = [], P[i].get("parent")
    while j in P and j not in out:
        out.append(j)
        j = P[j].get("parent")
    return out


def _geometry(res):
    lab, geo, P, s = res.lab, res.geo, res.lab.placeables, res.lab.settings
    placed = [i for i, g in geo.items() if g and g.poly]
    up = {i: _chain(P, i) for i in placed}
    part = {i: next((j for j in [i] + up[i] if P[j].get("mount") == "part"), None) for i in placed}
    window = {i for i in placed if P[i].get("category") == "window"}
    covered = set()

    def related(a, b):
        return a in up[b] or b in up[a]

    def dead_zone(a, b):  # the inside corner of a composed bench
        pa, pb = part[a], part[b]
        return bool(pa and pb and pa != pb and P[pa].get("parent") == P[pb].get("parent"))

    def cover(thing, win, rid):
        if (thing, win) not in covered:
            covered.add((thing, win))
            z = geo[win].z
            res.add("window", f"{thing} covers part of {win} (window from {z[0]:.0f} to {z[1]:.0f} cm)", [thing, win], rid)

    by_room = defaultdict(list)
    for i in placed:
        by_room[geo[i].room].append(i)
    for rid, ids in by_room.items():
        room = lab.rooms.get(rid, {})
        outline, ceiling = room.get("poly"), room.get("ceiling")
        for i in ids:
            r, g, parent = P[i], geo[i], P[i].get("parent")
            if outline and not G.contains(outline, g.poly):
                res.add("outside-room", f"{i} is partly outside {rid}", [i], rid)
            pg = geo.get(parent)
            if r.get("mount") in ("on", "under") and pg and pg.poly and not G.contains(pg.poly, g.poly):
                res.add("off-parent", f"{i} sticks out of {parent}", [i, parent], rid)
            if r.get("mount") == "in" and pg:
                inside = G.interior_poly(lab, parent, pg)
                inner_h = G.interior(lab, parent)[4]
                if inside and not G.contains(inside, g.poly):
                    res.add("off-parent", f"{i} sticks out of the working space inside {parent}", [i, parent], rid)
                if inner_h and r["h"] + s["fit_margin"] > inner_h:
                    res.add("in-fit", f"{i} is {r['h']} cm tall, and {parent} has {inner_h} cm inside"
                                      f" (with {s['fit_margin']} cm to spare, {inner_h - s['fit_margin']} cm)", [i, parent], rid)
                if inside and P[parent].get("category") == "fume-hood":
                    (ax, ay), (bx, by) = inside[3], inside[2]  # the front edge: the sash
                    gap = min(abs((bx - ax) * (ay - py) - (ax - px) * (by - ay)) / math.hypot(bx - ax, by - ay)
                              for px, py in g.poly)
                    if gap < s["sash_clearance"]:
                        res.add("sash", f"{i} is {gap:.0f} cm behind {parent}'s sash; keep work at least "
                                        f"{s['sash_clearance']} cm inside", [i, parent], rid)
            if r.get("mount") == "under" and parent in P:
                fu = P[parent].get("free_under")
                if fu is None:
                    res.add("under-fit", f"{i} is under {parent}, but {parent} has no free_under", [i, parent], rid)
                elif r["h"] + s["fit_margin"] > fu:
                    res.add("under-fit", f"{i} is {r['h']} cm tall, and {fu} cm is free under {parent}"
                                         f" (with {s['fit_margin']} cm to spare, {fu - s['fit_margin']} cm)", [i, parent], rid)
            if r.get("mount") == "on" and parent in P:
                pr = P[parent]
                if (pr.get("stackable") or ("yes" if pr.get("category") in STACKABLE else "no")) == "no":
                    res.add("not-stackable", f"{i} sits on {parent}, which isn't marked stackable", [i, parent], rid)
            top = g.z[1] + (r.get("clear_top") or 0)
            slack = 0 if r.get("category") in ("structure", "overhead") else s["fit_margin"]  # built to the ceiling
            if ceiling and top + slack > ceiling + G.EPS:
                what = (f"reaches {g.z[1]:.0f} cm" if g.z[1] + slack > ceiling + G.EPS
                        else f"needs {r['clear_top']} cm above it (up to {top:.0f} cm)")
                res.add("headroom", f"{i} {what}, but the ceiling is at {ceiling} cm", [i, rid], rid)
            if (ceiling and room.get("sprinklers") == "yes" and r.get("category") not in SPRINKLER_EXEMPT
                    and r.get("fixed") != "yes"):  # built-in fittings (a ducted fume hood) are the building's business
                limit = ceiling - s["sprinkler_clearance"]
                if g.z[1] > limit + G.EPS:
                    res.add("sprinkler", f"{i} reaches {g.z[1]:.0f} cm; with sprinklers, nothing above {limit:.0f} cm "
                                         f"({s['sprinkler_clearance']} cm below the {ceiling} cm ceiling)", [i, rid], rid)
            for side, zp, zr in zones(r, g, s["person_height"], s["door_gap"]):
                if (side != "top" and outline and i not in window and r.get("mount") in ("floor", "wall", "part")
                        and not G.contains(outline, zp)):
                    res.add("wall-clearance", f"{i}'s {side} clear zone runs into a wall", [i], rid)
                pieces = G.convex_pieces(zp)
                for j in ids:
                    if j == i or j in window or related(i, j) or dead_zone(i, j):
                        continue
                    if not G.overlaps(pieces, zr, geo[j].pieces, geo[j].zc):
                        continue
                    if i in window:
                        cover(j, i, rid)
                    elif side == "top":
                        res.add("headroom", f"{i} needs {r['clear_top']} cm above it (up to {zr[1]:.0f} cm), but {j} "
                                            f"starts at {geo[j].zc[0]:.0f} cm", [i, j], rid)
                    else:
                        size = f" ({r['clear_' + side]} cm)" if r.get("clear_" + side) else ""
                        res.add("clear-zone", f"{j} stands in {i}'s {side} clear zone{size}", [i, j], rid)
        for n, i in enumerate(ids):
            for j in ids[n + 1:]:
                if related(i, j) or not G.overlaps(geo[i].pieces, geo[i].zc, geo[j].pieces, geo[j].zc):
                    continue
                if i in window or j in window:
                    if not (i in window and j in window):
                        cover(j if i in window else i, i if i in window else j, rid)
                    continue
                a, b = sorted((i, j))
                res.add("overlap", f"{a} and {b} overlap", [a, b], rid)


def doc_state(doc, today, warn_days):
    """('expired' | 'expiring' | 'ok' | None, days left) for a document."""
    exp = doc.get("expires")
    if not isinstance(exp, dt.date):
        return None, None
    left = (exp - today).days
    return ("expired" if left < 0 else "expiring" if left <= warn_days else "ok"), left


def _documents(res, today):
    lab = res.lab
    for i, d in lab.documents.items():
        targets = d.get("applies_to") or []
        what = f"{i} ({d.get('type')}{', ' + d['title'] if d.get('title') else ''}) for {', '.join(targets)}"
        first = targets[0] if targets else None
        room = (lab.placeables.get(first) or lab.services.get(first) or {}).get("room") or (first if first in lab.rooms else None)
        if d.get("status") and d["status"] != "approved":
            res.add("document-unapproved", f"{what} is {d['status']}", [i], room)
        state, left = doc_state(d, today, lab.settings["expiry_warning_days"])
        if state == "expired":
            res.add("document-expired", f"{what} expired on {d['expires']}", [i], room)
        elif state == "expiring":
            res.add("document-expiring", f"{what} expires on {d['expires']} (in {left} days)", [i], room)


def spare_state(item):
    """('out' | 'low' | 'ok' | None if not a required spare, count in stock or None)."""
    need, have = item.get("min_qty"), stock(item.get("qty"))
    if not need:
        return None, have
    return ("out" if not have else "low" if have < need else "ok"), have


def _spares(res):
    lab = res.lab
    for i, it in lab.items.items():
        state, have = spare_state(it)
        if state not in ("out", "low"):
            continue
        targets = it.get("spare_for") or []
        what = f"{i} {it.get('name') or ''}" + (f" (for {', '.join(targets)})" if targets else "")
        first = targets[0] if targets else it.get("container")
        room = lab.placeables.get(first, {}).get("room")
        need = it["min_qty"]
        if state == "out":
            why = "qty is blank" if it.get("qty") is None else f"qty: {it['qty']}"
            res.add("spare-out", f"{what}: none in stock ({why}), keep at least {need}", [i], room)
        else:
            res.add("spare-low", f"{what}: {have:g} in stock, keep at least {need}", [i], room)


def _power(res):
    lab, geo, P, S, E = res.lab, res.geo, res.lab.placeables, res.lab.services, res.lab.equipment
    derate, heavy = lab.settings["circuit_limit"] / 100, lab.settings["heavy_load"]
    spos = {sid: G.service_position(lab, geo, s) for sid, s in S.items()}
    for eid, e in E.items():
        if (e.get("plugs") or 0) <= 0 or e.get("plug_type") in ("hardwired", "none") or eid not in P:
            continue
        pos = G.position(lab, geo, eid)
        if pos is None:
            continue  # not placed yet
        rid = P[eid].get("room")
        if e.get("outlet"):
            if e["outlet"] in S:
                res.assign[eid] = e["outlet"]
            continue
        cands = [(math.dist(spos[sid], pos[:2]), sid) for sid, s in S.items()
                 if s.get("room") == rid and s.get("type") in ("outlet", "strip") and spos[sid] is not None]
        if not cands:
            res.add("no-socket", f"{eid} needs power, but {rid} has no socket or strip with a position yet", [eid], rid)
            continue
        dist, sid = min(cands)
        res.assign[eid], res.nearest[eid] = sid, (sid, dist)

    for sid, s in S.items():
        j, seen = sid, set()
        while j in S and j not in seen and S[j].get("type") == "strip":
            seen.add(j)
            j = S[j].get("fed_by")
        res.circuit_of[sid] = S[j].get("circuit") if j in S and S[j].get("type") == "outlet" else None

    used = defaultdict(int)
    for eid, sid in res.assign.items():
        used[sid] += E[eid].get("plugs") or 1
    for sid, s in S.items():
        feed = s.get("fed_by")
        if s.get("type") == "strip" and feed in S:
            used[feed] += 1
            if S[feed].get("type") == "strip":
                res.add("strip-chain", f"{sid} is plugged into another strip, {feed}", [sid, feed], s.get("room"))
    res.used = dict(used)
    for sid, s in S.items():
        if s.get("type") in ("outlet", "strip") and s.get("sockets") is not None and used[sid] > s["sockets"]:
            users = [e for e, t in res.assign.items() if t == sid] + [k for k, t in S.items() if t.get("fed_by") == sid]
            res.add("sockets", f"{sid} has {s['sockets']} socket(s) for {used[sid]} plugs: {', '.join(users)}",
                    [sid], s.get("room"))

    for eid, sid in res.assign.items():
        c = res.circuit_of.get(sid)
        if c:
            res.load[c] = res.load.get(c, 0) + (E[eid].get("watts_typ") or 0)
            res.members.setdefault(c, []).append(eid)
    for c in sorted(res.load):
        ci, members = lab.circuits.get(c, {}), res.members[c]
        rooms = sorted({P[e].get("room") for e in members})
        where = rooms[0] if len(rooms) == 1 else None
        if ci.get("rating_a") and ci.get("volts"):
            limit = derate * ci["rating_a"] * ci["volts"]
            if res.load[c] > limit:
                res.add("circuit-load", f"{c} runs {res.load[c]:.0f} W; the limit is {limit:.0f} W "
                                        f"({derate:.0%} of {ci['rating_a']} A × {ci['volts']} V)", [c], where)
        big = [e for e in members if E[e].get("critical") != "yes" and (E[e].get("watts_max") or 0) >= heavy]
        for e in members:
            if E[e].get("critical") == "yes" and big:
                res.add("critical-shared", f"{e} must never lose power, but shares {c} with {', '.join(big)}",
                        [e, c], P[e].get("room"))

    for eid, e in E.items():
        if eid in P and G.position(lab, geo, eid) is not None:
            rid = P[eid].get("room")
            res.heat[rid] = res.heat.get(rid, 0) + (e.get("watts_typ") or 0)
    for rid, w in res.heat.items():
        cool = lab.rooms.get(rid, {}).get("cooling")
        if cool and w > cool:
            res.add("heat", f"{rid} has {w:.0f} W of equipment and {cool} W of cooling", [rid], rid)

    def carried(sid, seen=()):
        """Running W through a socket or strip: what's plugged into it, and into strips it feeds."""
        own = sum(E[e].get("watts_typ") or 0 for e, t in res.assign.items() if t == sid)
        return own + sum(carried(k, seen + (sid,)) for k, t in S.items()
                         if t.get("fed_by") == sid and k not in seen and k != sid)

    for sid, s in S.items():
        if s.get("rating_a") and s.get("type") in ("outlet", "strip"):
            volts = lab.circuits.get(res.circuit_of.get(sid), {}).get("volts") or 230
            w, limit = carried(sid), s["rating_a"] * volts
            res.socket_load[sid] = w
            if w > limit:
                res.add("socket-load", f"{sid} carries {w:.0f} W; it's rated {s['rating_a']} A × {volts} V = {limit:.0f} W",
                        [sid], s.get("room"))


def _links(res):
    lab, geo = res.lab, res.geo
    for link in lab.links:
        a, b = G.position(lab, geo, link["from"]), G.position(lab, geo, link["to"])
        limit = link.get("max_len") or lab.link_default(link.get("type"))
        run = sum(abs(p - q) for p, q in zip(a, b)) if a and b else None
        res.runs.append((link, run, limit))
        if run is not None and limit and run > limit:
            res.add("cable-reach", f"{link['from']} → {link['to']} ({link['type']}) needs about {run / 100:.1f} m; "
                                   f"the limit is {limit / 100:.1f} m", [link["from"], link["to"]],
                    lab.placeables.get(link["from"], {}).get("room"))


def _utilities(res):
    lab, geo, P, S = res.lab, res.geo, res.lab.placeables, res.lab.services
    reach = lab.settings["utility_reach"]
    for eid, e in lab.equipment.items():
        needs = e.get("needs") or []
        pos = G.position(lab, geo, eid) if needs and eid in P else None
        if pos is None:
            continue
        rid = P[eid].get("room")
        linked = {link.get("type") for link in lab.links if eid in (link.get("from"), link.get("to"))}
        for kind, medium in needs:
            what = f"{kind} ({medium})" if medium else kind
            if LINK_FOR.get(kind, set()) & linked:
                continue  # connected on the links sheet: its length is checked there
            cands = []
            for sid, s in S.items():
                if s.get("room") != rid or s.get("type") != kind:
                    continue
                if medium and medium.lower() not in str(s.get("medium") or "").lower():
                    continue
                sp = G.service_position(lab, geo, s)
                if sp is not None:
                    run = abs(sp[0] - pos[0]) + abs(sp[1] - pos[1]) + abs((s.get("z") or pos[2]) - pos[2])
                    cands.append((run, sid))
            if not cands:
                res.add("utility", f"{eid} needs {what}, but {rid} has no {what} point with a position", [eid], rid)
            elif min(cands)[0] > reach:
                run, sid = min(cands)
                res.add("utility", f"{eid} needs {what}: the nearest, {sid}, is about {run / 100:.1f} m away "
                                   f"(reach {reach / 100:.1f} m)", [eid, sid], rid)


def _keep_apart(res):
    lab, geo, P = res.lab, res.geo, res.lab.placeables
    tagged = {}
    for i, r in P.items():
        if geo.get(i) and geo[i].poly:
            for t in set(r.get("tags") or []) | ({r["category"]} if r.get("category") else set()):
                tagged.setdefault(t, []).append(i)  # its category counts as a tag: a rule can say "laser" or "door"
    seen = set()
    for rule in lab.keep_apart:
        a_tag, b_tag, dist = rule.get("tag"), rule.get("away_from"), rule.get("distance")
        if not (a_tag and b_tag and dist):
            continue
        kind = "keep-apart" if rule.get("level") == "problem" else "keep-apart-near"
        for a in tagged.get(a_tag, []):
            for b in tagged.get(b_tag, []):
                if a == b or geo[a].room != geo[b].room or (a, b, a_tag, b_tag) in seen:
                    continue
                seen.add((a, b, a_tag, b_tag))
                gap = G.poly_distance(geo[a].poly, geo[b].poly)
                if gap < dist:
                    why = f": {rule['why']}" if rule.get("why") else ""
                    res.add(kind, f"{a} ({a_tag}) is {gap:.0f} cm from {b} ({b_tag}); keep them at least {dist} cm "
                                  f"apart{why}", [a, b], geo[a].room)


def _doors(res):
    lab, P, m = res.lab, res.lab.placeables, res.lab.settings["fit_margin"]
    doors = {}
    for i, r in P.items():
        if r.get("category") == "door" and r.get("w") and r.get("h"):
            doors.setdefault(r.get("room"), []).append((r["w"], r["h"], i))
    for i, e in lab.equipment.items():
        r = P.get(i)
        if not r or e.get("plan") not in ("new", "relocate") or r.get("shape") == "group":
            continue
        dims = [r.get(k) for k in ("w", "d", "h")]
        if None in dims or not doors.get(r.get("room")):
            continue
        a, b, _ = sorted(dims)
        if not any(a + m <= dw and b + m <= dh for dw, dh, _ in doors[r["room"]]):
            dw, dh, di = max(doors[r["room"]])
            res.add("door-fit", f"{i} is {r['w']} × {r['d']} × {r['h']} cm and won't pass through any door of "
                                f"{r['room']}, even on its side (widest: {di}, {dw} × {dh} cm)", [i, di], r["room"])


def _with_parts(lab, i):
    """i and what goes with it: its drawers, cabinet shelves and parts (not what stands on or in it)."""
    out, todo = {i}, [i]
    while todo:
        for c in lab.children.get(todo.pop(), []):
            r = lab.placeables[c]
            if c not in out and (r.get("mount") == "part" or (r.get("mount") == "in" and r.get("x") is None)):
                out.add(c)
                todo.append(c)
    return out


def references(lab, i):
    """[(kind, id, what)]: everything still pointing at i or its drawers and parts: things standing on or in it,
    items kept in it, spares listed for it, sockets on it, links, documents, SOPs and photos. Before it goes, the
    to-do list; after, what was left behind."""
    P, group, out = lab.placeables, _with_parts(lab, i), []
    for c, r in P.items():
        if r.get("parent") in group and c not in group:
            how = {"on": "stands on", "under": "stands under", "in": "is inside"}.get(r.get("mount"), "is part of")
            out.append(("placeable", c, f"{c} ({r.get('name') or ''}) {how} {r['parent']}"))
    for it_id, it in lab.items.items():
        if it.get("container") in group:
            out.append(("item", it_id, f"item {it_id} ({it.get('name') or ''}) is kept in {it['container']}"))
        if i in (it.get("spare_for") or []):
            out.append(("item", it_id, f"spare part {it_id} ({it.get('name') or ''}) is listed for it"))
    for sid, s in lab.services.items():
        if s.get("parent") in group:
            out.append(("service", sid, f"{sid} ({s.get('type')}) is mounted on {s['parent']}"))
    for link in lab.links:
        if i in (link.get("from"), link.get("to")):
            other = link["to"] if link.get("from") == i else link["from"]
            out.append(("link", other, f"the {link.get('type')} link {link['from']} → {link['to']}"))
    for d_id, d in lab.documents.items():
        if i in (d.get("applies_to") or []):
            out.append(("document", d_id, f"{d_id} ({d.get('type')}) applies to it"))
    sops = lab.folder / "sops"
    for p in sorted(sops.glob("*.md")) if sops.is_dir() else []:
        if p.name.startswith("_"):
            continue
        meta, _ = md.front_matter(p.read_text(encoding="utf-8"))
        eq = meta.get("equipment") or []
        if i in [str(x).strip().upper() for x in (eq if isinstance(eq, list) else [eq])]:
            out.append(("sop", p.name, f"sops/{p.name} lists it (rename it _{p.name} to archive it)"))
    photos = lab.folder / "photos"
    for p in sorted(photos.iterdir()) if photos.is_dir() else []:
        if p.is_file() and any(p.stem == g or p.stem.startswith(g + "--") for g in group):
            out.append(("photo", p.name, f"photos/{p.name}"))
    return out


def _left_behind(res):
    lab = res.lab
    for i, when in lab.decommissioned.items():
        since = f" on {when}" if when else ""
        for kind, ref, what in references(lab, i):
            ids = [ref, i] if kind in ("placeable", "item", "service", "document") else [i]
            res.add("left-behind", f"{i} was decommissioned{since}, but {what}", ids, lab.placeables[i].get("room"))


def _walkways(res, rid, skip):
    lab, geo, P, s = res.lab, res.geo, res.lab.placeables, res.lab.settings
    step, walk_w, reach, block = s["grid"], s["walkway_width"], s["reach"], s["blocks_walking_below"]
    poly = lab.rooms[rid].get("poly")
    ids = [i for i, g in geo.items() if g and g.poly and g.room == rid]
    doors = [i for i in ids if P[i].get("category") == "door"]
    if not poly:
        return
    if not doors:
        res.walk_notes[rid] = "no doors placed yet, so walkways weren't checked"
        return
    x0, y0, x1, y1 = G.bbox(poly)
    x0, y0 = x0 - step, y0 - step  # a ring of cells outside the room, so the walls count as obstacles
    nx, ny = math.ceil((x1 - x0) / step) + 1, math.ceil((y1 - y0) / step) + 1

    def centre(ix, iy):
        return x0 + (ix + 0.5) * step, y0 + (iy + 0.5) * step

    def cells(p):
        bx0, by0, bx1, by1 = G.bbox(p)
        for iy in range(max(0, int((by0 - y0) // step)), min(ny, int((by1 - y0) // step) + 1)):
            for ix in range(max(0, int((bx0 - x0) // step)), min(nx, int((bx1 - x0) // step) + 1)):
                if G.inside(centre(ix, iy), p):
                    yield ix, iy

    blocked = [[not G.inside(centre(ix, iy), poly) for ix in range(nx)] for iy in range(ny)]
    for i in ids:
        if P[i].get("category") not in NOT_OBSTACLES and geo[i].zc[0] < block:
            for ix, iy in cells(geo[i].poly):
                blocked[iy][ix] = True
    dist = G.chamfer(blocked, step)
    walk = [[dist[iy][ix] >= walk_w / 2 for ix in range(nx)] for iy in range(ny)]
    seen = [[False] * nx for _ in range(ny)]
    stack = [(ix, iy) for d in doors for side, zp, _ in zones(P[d], geo[d]) if side == "front"
             for ix, iy in cells(zp) if walk[iy][ix]]
    if not stack:
        res.walk_notes[rid] = "every door's swing zone is blocked, so walkways couldn't be checked"
        return
    for ix, iy in stack:
        seen[iy][ix] = True
    while stack:
        ix, iy = stack.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            jx, jy = ix + dx, iy + dy
            if 0 <= jx < nx and 0 <= jy < ny and walk[jy][jx] and not seen[jy][jx]:
                seen[jy][jx] = True
                stack.append((jx, jy))
    near = G.chamfer(seen, step)
    for i in ids:
        r = P[i]
        if r.get("category") in NOT_OBSTACLES or i in skip or r.get("mount") not in ("floor", "wall", "part"):
            continue
        front = [zp for side, zp, _ in zones(r, geo[i]) if side == "front"]
        if front and not any(near[iy][ix] <= reach for zp in front for ix, iy in cells(zp)):
            res.add("walkway", f"{i}: no path at least {walk_w} cm wide from a door to the space in front of it", [i], rid)
