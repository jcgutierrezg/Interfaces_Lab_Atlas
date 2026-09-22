"""Where everything is: room coordinates for every placeable, and the polygon maths the checks need.

Frames: every object has its own frame with the origin at its back-left corner (as you face its front), u running
to your right along the front and v from the back towards you. A child's x/y is the top-left corner of its
footprint's bounding box in its parent's frame, and `faces` turns it relative to the parent. A room is a frame
facing S with its origin at the top-left of the drawing.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .model import Finding

ANG = {"S": 0, "SW": 45, "W": 90, "NW": 135, "N": 180, "NE": 225, "E": 270, "SE": 315}
MOUNTS = {"floor", "wall", "on", "under", "part"}
EPS = 0.6  # cm: touching isn't overlapping, and rounding to whole centimetres stays quiet


def rot(t, u, v):
    c, s = math.cos(math.radians(t)), math.sin(math.radians(t))
    return u * c - v * s, u * s + v * c


@dataclass
class Geo:
    id: str
    room: str
    poly: list | None      # footprint in room coordinates (None for groups)
    pieces: list           # convex pieces of poly
    z: tuple               # (bottom, top) in cm
    zc: tuple              # height band that collides: from free_under up, for open furniture
    origin: tuple          # own frame origin (back-left corner) in room coordinates
    theta: float           # facing in the room, degrees (S = 0, clockwise on the drawing)
    T: object = None       # own frame (u, v) -> room (x, y)
    size: tuple = (0, 0)   # (w, d)
    local: list = None     # footprint in its own frame
    zone: list = None      # a profile's own clearance, room coordinates


# --- polygons ---------------------------------------------------------------------------------------------

def area(poly):
    return sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1])) / 2


def centroid(poly):
    a = area(poly)
    if abs(a) < 1e-9:
        return sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly)
    cx = sum((x1 + x2) * (x1 * y2 - x2 * y1) for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]))
    cy = sum((y1 + y2) * (x1 * y2 - x2 * y1) for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]))
    return cx / (6 * a), cy / (6 * a)


def bbox(poly):
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


def _cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def is_convex(poly):
    signs = {c > 0 for c in (_cross(poly[k - 2], poly[k - 1], poly[k]) for k in range(len(poly))) if abs(c) > 1e-9}
    return len(signs) <= 1


def triangulate(poly):
    """Ear clipping, for concave profile outlines."""
    pts = list(poly) if area(poly) > 0 else list(reversed(poly))
    tris, guard = [], 0
    while len(pts) > 3 and guard < 10000:
        guard += 1
        for k in range(len(pts)):
            a, b, c = pts[k - 1], pts[k], pts[(k + 1) % len(pts)]
            if _cross(a, b, c) <= 1e-9:
                continue
            if any(_in_triangle(p, a, b, c) for p in pts if p not in (a, b, c)):
                continue
            tris.append([a, b, c])
            del pts[k]
            break
        else:
            break
    return tris + [pts]


def _in_triangle(p, a, b, c):
    return _cross(a, b, p) > 0 and _cross(b, c, p) > 0 and _cross(c, a, p) > 0


def convex_pieces(poly):
    return [poly] if is_convex(poly) else triangulate(poly)


def sat(P, Q):
    """Convex polygons overlap by more than EPS (separating-axis test)."""
    for poly in (P, Q):
        for k in range(len(poly)):
            (x1, y1), (x2, y2) = poly[k - 1], poly[k]
            L = math.hypot(x2 - x1, y2 - y1)
            if L < 1e-9:
                continue
            nx, ny = (y2 - y1) / L, (x1 - x2) / L
            pa = [nx * x + ny * y for x, y in P]
            pb = [nx * x + ny * y for x, y in Q]
            if max(pa) <= min(pb) + EPS or max(pb) <= min(pa) + EPS:
                return False
    return True


def overlaps(pieces_a, za, pieces_b, zb):
    """Two footprints overlap in plan and in height."""
    if not (za[0] < zb[1] - EPS and zb[0] < za[1] - EPS):
        return False
    return any(sat(p, q) for p in pieces_a for q in pieces_b)


def inside(pt, poly):
    """Point inside the polygon, or on its boundary within EPS."""
    x, y = pt
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / L2))
        if math.hypot(x1 + t * dx - x, y1 + t * dy - y) <= EPS:
            return True
    c = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


def _side(a, b, p):
    L = math.dist(a, b)
    return _cross(a, b, p) / L if L > 1e-9 else 0.0


def crosses(a, b, c, d):
    """Segments ab and cd cross properly (not just touch or run along each other)."""
    s1, s2, s3, s4 = _side(a, b, c), _side(a, b, d), _side(c, d, a), _side(c, d, b)
    return (s1 > EPS and s2 < -EPS or s1 < -EPS and s2 > EPS) and (s3 > EPS and s4 < -EPS or s3 < -EPS and s4 > EPS)


def contains(outer, poly):
    """poly lies within outer (touching the boundary is fine)."""
    if not all(inside(p, outer) for p in poly):
        return False
    edges = list(zip(outer, outer[1:] + outer[:1]))
    return not any(crosses(a, b, c, d) for a, b in zip(poly, poly[1:] + poly[:1]) for c, d in edges)


# --- placement --------------------------------------------------------------------------------------------

DOOR_GAP = 10  # cm beside a door's hinge; the settings sheet's door_gap overrides it in the checks


def clear_boxes(r, w, d, door_gap=DOOR_GAP):
    """Clearance rectangles in the object's own frame: {side: (u0, v0, u1, v1)}.

    A door (door column: hinged left, right or both, as you face it) widens them: its swing in front (the door's
    width, half each for double doors) and door_gap beside the hinge, so it opens past 90 degrees."""
    c = {k: r.get(f"clear_{k}") or 0 for k in ("front", "back", "left", "right")}
    door = r.get("door")
    if door in ("left", "right", "both"):
        c["front"] = max(c["front"], w / 2 if door == "both" else w)
        for side in ("left", "right") if door == "both" else (door,):
            c[side] = max(c[side], door_gap)
    boxes = {"front": (0, d, w, d + c["front"]), "back": (0, -c["back"], w, 0),
             "left": (-c["left"], 0, 0, d), "right": (w, 0, w + c["right"], d)}
    return {k: b for k, b in boxes.items() if c[k] > 0}


def shape_local(lab, i, r, issues):
    """(footprint, profile clearance or None) in the object's own frame, or None if it can't be drawn."""
    shape = r.get("shape") or "rect"
    w, d, h = r.get("w"), r.get("d"), r.get("h")
    if shape == "circle" and d is None:
        d = w
    missing = [k for k, v in (("w", w), ("d", d), ("h", h)) if v is None]
    if missing:
        issues.append(Finding("data", f"{i} is placed but has no {', '.join(missing)}", (i,), r.get("room")))
        return None
    if shape == "circle":
        return [(w / 2 * (1 + math.cos(k * math.pi / 12)), w / 2 * (1 + math.sin(k * math.pi / 12)))
                for k in range(24)], None
    if str(shape).startswith("@"):
        prof = lab.profile(shape[1:])
        if prof is None:
            issues.append(Finding("data", f"{i}: shapes/{shape[1:]}.svg is missing or has no 'footprint' outline",
                                  (i,), r.get("room")))
        else:
            fp, zone = prof
            x0, y0, x1, y1 = bbox(fp)
            if abs(x1 - x0 - w) > 1 or abs(y1 - y0 - d) > 1:
                issues.append(Finding("data", f"{i}: w × d is {w} × {d} but shapes/{shape[1:]}.svg is "
                                              f"{x1 - x0:.0f} × {y1 - y0:.0f}", (i,), r.get("room")))
            fp = [(u - x0, v - y0) for u, v in fp]
            return fp, [(u - x0, v - y0) for u, v in zone] if zone else None
    return [(0, 0), (w, 0), (w, d), (0, d)], None


def in_frame(lab, i, r, origin, theta, issues):
    """Place r in a frame at `origin` facing `theta`: (footprint, zone, T, facing) or None."""
    shp = shape_local(lab, i, r, issues)
    rel = ANG.get(r.get("faces") or "S")
    if shp is None or rel is None:
        return None
    local, lzone = shp
    rp = [rot(rel, u, v) for u, v in local]
    p0 = (r["x"] - min(p[0] for p in rp), r["y"] - min(p[1] for p in rp))

    def T(u, v):
        a, b = rot(rel, u, v)
        px, py = rot(theta, p0[0] + a, p0[1] + b)
        return origin[0] + px, origin[1] + py

    return local, lzone, T, (theta + rel) % 360


def place_all(lab):
    """{id: Geo or None} for every placeable, plus data findings for rows that can't be placed."""
    P, geo, issues, busy = lab.placeables, {}, [], set()

    def place(i):
        if i in geo:
            return geo[i]
        if i in busy:  # parent loop, already reported
            return None
        busy.add(i)
        geo[i] = _place(i)
        busy.discard(i)
        return geo[i]

    def _place(i):
        r = P[i]
        mount, parent = r.get("mount"), r.get("parent")
        if mount not in MOUNTS:
            return None
        if parent:
            pg = place(parent) if parent in P else None
            if pg is None:
                return None
            origin, theta, (pz0, pz1) = pg.origin, pg.theta, pg.z
        else:
            origin, theta, pz0, pz1 = (0.0, 0.0), 0, 0, 0
        if r.get("x") is None or r.get("y") is None:
            return None
        if r.get("shape") == "group":
            return _place_group(i, r, origin, theta, pz0)
        got = in_frame(lab, i, r, origin, theta, issues)
        if got is None:
            return None
        local, lzone, T, facing = got
        z0 = {"floor": 0, "wall": r.get("z"), "on": pz1, "under": pz0, "part": pz0}[mount]
        if z0 is None:
            return None  # wall mount without z, reported by the model
        z1, fu = z0 + r["h"], r.get("free_under")
        zc = (z0 + fu, z1) if fu is not None and fu < r["h"] else (z0, z1)
        poly = [T(u, v) for u, v in local]
        return Geo(i, r.get("room"), poly, convex_pieces(poly), (z0, z1), zc, T(0, 0), facing, T,
                   (r["w"], r["d"] if r.get("d") is not None else r["w"]), local,
                   [T(u, v) for u, v in lzone] if lzone else None)

    def _place_group(i, r, origin, theta, z0):
        pts = []
        for c in lab.children.get(i, []):
            cr = P[c]
            if cr.get("mount") == "part" and cr.get("x") is not None and cr.get("y") is not None:
                got = in_frame(lab, c, cr, (0.0, 0.0), 0, [])
                if got:
                    pts += [got[2](u, v) for u, v in got[0]]
        rel = ANG.get(r.get("faces") or "S")
        if not pts or rel is None:
            issues.append(Finding("data", f"{i} is a group but none of its parts can be placed yet", (i,), r.get("room")))
            return None
        rp = [rot(rel, u, v) for u, v in pts]
        p0 = (r["x"] - min(p[0] for p in rp), r["y"] - min(p[1] for p in rp))
        ox, oy = rot(theta, *p0)
        return Geo(i, r.get("room"), None, [], (z0, z0), (z0, z0), (origin[0] + ox, origin[1] + oy), (theta + rel) % 360)

    for i in P:
        place(i)
    unique = list({(f.message, f.ids): f for f in issues}.values())
    return geo, unique


def poly_distance(p, q):
    """Shortest distance between two polygons on the plan, 0 if they touch or overlap."""
    if sat_any(p, q):
        return 0.0

    def seg(pt, a, b):
        (px, py), (ax, ay), (bx, by) = pt, a, b
        dx, dy = bx - ax, by - ay
        t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
        return math.hypot(px - ax - t * dx, py - ay - t * dy)

    return min(min(seg(pt, a, b) for pt in p for a, b in zip(q, q[1:] + q[:1])),
               min(seg(pt, a, b) for pt in q for a, b in zip(p, p[1:] + p[:1])))


def sat_any(p, q):
    """True if two polygons overlap or touch (either may be concave)."""
    return any(sat(a, b) for a in convex_pieces(p) for b in convex_pieces(q)) or inside(p[0], q) or inside(q[0], p)


def position(lab, geo, i):
    """(x, y, z) centre of a placeable, taken from its nearest placed ancestor if it has no footprint itself."""
    j, seen = i, set()
    while j in lab.placeables and j not in seen:
        seen.add(j)
        g = geo.get(j)
        if g and g.poly:
            cx, cy = centroid(g.poly)
            return cx, cy, (g.z[0] + g.z[1]) / 2
        j = lab.placeables[j].get("parent")
    return None


def service_position(lab, geo, s):
    """(x, y) of a socket, strip or tap in room coordinates, or None if it can't be worked out yet."""
    if s.get("x") is None or s.get("y") is None:
        return None
    if s.get("parent"):
        g = geo.get(s["parent"])
        return g.T(s["x"], s["y"]) if g and g.T else None
    return float(s["x"]), float(s["y"])


# --- rasters ----------------------------------------------------------------------------------------------

def chamfer(seeds, step):
    """Distance (cm) from every cell to the nearest seed cell. seeds: 2D list of bools."""
    ny, nx = len(seeds), len(seeds[0]) if seeds else 0
    INF, diag = 1e12, step * math.sqrt(2)
    d = [[0.0 if seeds[y][x] else INF for x in range(nx)] for y in range(ny)]
    for y in range(ny):
        for x in range(nx):
            v = d[y][x]
            if x:
                v = min(v, d[y][x - 1] + step)
            if y:
                v = min(v, d[y - 1][x] + step)
                if x:
                    v = min(v, d[y - 1][x - 1] + diag)
                if x + 1 < nx:
                    v = min(v, d[y - 1][x + 1] + diag)
            d[y][x] = v
    for y in range(ny - 1, -1, -1):
        for x in range(nx - 1, -1, -1):
            v = d[y][x]
            if x + 1 < nx:
                v = min(v, d[y][x + 1] + step)
            if y + 1 < ny:
                v = min(v, d[y + 1][x] + step)
                if x + 1 < nx:
                    v = min(v, d[y + 1][x + 1] + diag)
                if x:
                    v = min(v, d[y + 1][x - 1] + diag)
            d[y][x] = v
    return d


def largest_rectangle(free):
    """(columns, rows) of the largest all-True rectangle in a 2D list of bools."""
    best, heights = (0, 0), [0] * (len(free[0]) if free else 0)
    for row in free:
        heights = [h + 1 if f else 0 for h, f in zip(heights, row)]
        stack = []
        for k, h in enumerate(heights + [0]):
            start = k
            while stack and stack[-1][1] >= h:
                start, sh = stack.pop()
                if (k - start) * sh > best[0] * best[1]:
                    best = (k - start, sh)
            stack.append((start, h))
    return best
