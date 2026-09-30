"""The order to move things in on the day.

A pull says where everything ends up. On the day some of those moves have to wait for others: a cupboard can't go
where a bench still stands, an instrument can't go on a bench that hasn't arrived yet, and a bench can't move with
things still on it. This works that out in rounds. Everything in a round can be done in any order, or at the same
time by different people, once the round before it is finished. Two things that want each other's place (a swap)
can't either of them go first, so one is parked somewhere clear for a while, the smallest, being the easiest.

It also says what to do before lifting each thing: agree a time with whoever relies on something that must never
lose power, disconnect its gas, vacuum or water, unplug the cables to what it's linked to, and clear off what
stands on it.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import geometry as G


@dataclass
class Step:
    round: int
    id: str
    kind: str = "move"  # or "park": out of the way for now, somewhere clear
    after: list = field(default_factory=list)  # [(id, why)] it waits for
    notes: list = field(default_factory=list)


def _chain(P, i):
    out, j = [], (P.get(i) or {}).get("parent")
    while j in P and j not in out:
        out.append(j)
        j = P[j].get("parent")
    return out


def moving(moves):
    """What is lifted on the day: drawers and the like, whose only change is the room, go with their parent."""
    return sorted(i for i, c in moves.get("placeables", {}).items() if set(c) != {"room"})


def dependencies(before, after, moves):
    """{id: {id it waits for: why}} among the things that move."""
    Pb, Pa, gb, ga = before.lab.placeables, after.lab.placeables, before.geo, after.geo
    M = set(moving(moves))
    waits = {i: {} for i in M}

    def add(first, then, why):
        if first != then and first in M and then in M:
            waits[then].setdefault(first, why)

    for b in M:
        up_before, up_after = _chain(Pb, b), _chain(Pa, b)
        for host in up_after:  # the bench goes in first, then what goes on it
            if Pa[b].get("mount") != "part":
                add(host, b, f"{host} is in place")
        for host in up_before:  # ...and what leaves a bench comes off before the bench moves
            if host not in up_after:
                add(b, host, f"{b} is off it")
        g = ga.get(b)
        if not g or not g.poly:
            continue  # out to the waiting area: it needs nowhere
        for a in M:
            h = gb.get(a)
            if a == b or not h or not h.poly or h.room != g.room or a in up_after or b in _chain(Pb, a):
                continue
            if G.overlaps(g.pieces, g.zc, h.pieces, h.zc):
                add(a, b, f"{a} is out of the way")
    return waits


def _rings(nodes, deps):
    """Groups of things all waiting on one another (a swap, or a longer ring): none of them can ever go first.
    Tarjan's strongly connected components, over the edges 'has to go before'."""
    index, low, stack, on, out, count = {}, {}, [], set(), [], [0]

    def visit(v):
        index[v] = low[v] = count[0]
        count[0] += 1
        stack.append(v)
        on.add(v)
        for w in sorted(k for k in nodes if v in deps[k]):
            if w not in index:
                visit(w)
                low[v] = min(low[v], low[w])
            elif w in on:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            group = []
            while True:
                w = stack.pop()
                on.discard(w)
                group.append(w)
                if w == v:
                    break
            if len(group) > 1:
                out.append(sorted(group))

    for v in sorted(nodes):
        if v not in index:
            visit(v)
    return out


def _notes(before, after, moves, i):
    """What to do before lifting i."""
    lab, out = before.lab, []
    eq = lab.equipment.get(i) or {}
    if eq.get("critical") == "yes":
        out.append("must never lose power: agree when it goes off with whoever relies on it, and switch it back "
                   "on the same day")

    def backed(res):
        socket = res.assign.get(i)
        circuit = res.circuit_of.get(socket) if socket else None
        return (res.lab.circuits.get(circuit) or {}).get("backed") if circuit else None

    was, now = backed(before), backed(after)
    if was in ("ups", "generator") and now not in ("ups", "generator"):
        out.append(f"loses its {was} backing in the new spot")
    lines = [f"{kind} ({medium})" if medium else kind for kind, medium in eq.get("needs") or []
             if kind in ("gas", "vacuum", "air", "water", "drain", "exhaust")]  # the model has parsed these already
    if lines:
        out.append("disconnect its " + ", ".join(dict.fromkeys(lines)))
    links = [(ln.get("type") or "cable", ln["to"] if ln.get("from") == i else ln.get("from"))
             for ln in lab.links if i in (ln.get("from"), ln.get("to"))]
    if links:
        out.append("unplug the " + ", ".join(f"{kind} to {other}" for kind, other in links))
    P, M = lab.placeables, set(moving(moves))
    riding = [c for c in P if i in _chain(P, c) and c not in M and P[c].get("mount") in ("on", "under")
              and not any(h in M for h in _chain(P, c)[:_chain(P, c).index(i)])]
    if riding:
        out.append("clear it first, and put back after: " + ", ".join(sorted(riding)))
    return out


def plan(before, after, moves):
    """[Step] in the order to do them."""
    M = moving(moves)
    if not M:
        return []
    waits = dependencies(before, after, moves)
    deps = {i: set(w) for i, w in waits.items()}
    size = {i: abs(G.area(before.geo[i].poly)) if before.geo.get(i) and before.geo[i].poly else 0 for i in M}
    room = {i: before.lab.placeables[i].get("room") or "" for i in M}
    remaining, parked, steps, r = set(M), set(), [], 1
    while remaining:
        ready = sorted((i for i in remaining if not deps[i] & remaining), key=lambda i: (room[i], i))
        for i in ready:
            notes = (["bring it back from where it was parked"] if i in parked else []) + _notes(before, after, moves, i)
            steps.append(Step(r, i, "move", [(k, waits[i][k]) for k in sorted(waits[i])], notes))
        remaining -= set(ready)
        rings = _rings(remaining, deps)
        for ring in rings:  # parked in this same round, alongside whatever else is going: it waits for nothing
            free = sorted((i for i in ring if i not in parked), key=lambda i: (size[i], i))
            if not free:
                continue
            n = free[0]
            blocked = sorted(k for k in remaining if n in deps[k])
            steps.append(Step(r, n, "park", [], [f"it's in the way of {', '.join(blocked)}, which is in its way too: "
                                                 f"put it somewhere clear for now (the corridor, a free corner)"]))
            parked.add(n)
            for k in remaining:
                deps[k].discard(n)  # its old spot is free now
        if remaining and not ready and not rings:  # can't happen with a tree of hosts, but never loop for ever
            for i in sorted(remaining):
                steps.append(Step(r, i, "move", [], ["the order couldn't be worked out: check this one by hand"]))
            break
        r += 1
    return steps
