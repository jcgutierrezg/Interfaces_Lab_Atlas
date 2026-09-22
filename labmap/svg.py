"""Minimal SVG reading for room outlines and shape profiles: outlines by id, in centimetres, transforms applied.

Copes with what Inkscape writes: relative path commands, curves (flattened), transforms on elements and layers,
and documents whose units aren't centimetres.
"""
from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET

UNIT_CM = {"cm": 1.0, "mm": 0.1, "m": 100.0, "in": 2.54, "pt": 2.54 / 72, "pc": 2.54 / 6, "px": 2.54 / 96}
IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
NUM = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
TOKEN = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
SHAPES = {"path", "rect", "polygon", "polyline", "circle", "ellipse"}


def mul(m, n):
    """Matrix product m·n: apply n first, then m."""
    a, b, c, d, e, f = m
    A, B, C, D, E, F = n
    return (a * A + c * B, b * A + d * B, a * C + c * D, b * C + d * D, a * E + c * F + e, b * E + d * F + f)


def apply(m, pts):
    a, b, c, d, e, f = m
    return [(a * x + c * y + e, b * x + d * y + f) for x, y in pts]


def parse_transform(s):
    m = IDENTITY
    for name, args in re.findall(r"(\w+)\s*\(([^)]*)\)", s or ""):
        v = [float(n) for n in NUM.findall(args)]
        if name == "matrix" and len(v) == 6:
            t = tuple(v)
        elif name == "translate" and v:
            t = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0)
        elif name == "scale" and v:
            t = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif name == "rotate" and v:
            r = math.radians(v[0])
            t = (math.cos(r), math.sin(r), -math.sin(r), math.cos(r), 0, 0)
            if len(v) == 3:
                t = mul(mul((1, 0, 0, 1, v[1], v[2]), t), (1, 0, 0, 1, -v[1], -v[2]))
        elif name == "skewX" and v:
            t = (1, 0, math.tan(math.radians(v[0])), 1, 0, 0)
        elif name == "skewY" and v:
            t = (1, math.tan(math.radians(v[0])), 0, 1, 0, 0)
        else:
            continue
        m = mul(m, t)
    return m


def _bezier(p0, ctrl, p3, steps):
    pts = []
    for k in range(1, steps + 1):
        t = k / steps
        if len(ctrl) == 1:
            (x1, y1), = ctrl
            pts.append(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * x1 + t * t * p3[0],
                        (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * y1 + t * t * p3[1]))
        else:
            (x1, y1), (x2, y2) = ctrl
            a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3
            pts.append((a * p0[0] + b * x1 + c * x2 + d * p3[0], a * p0[1] + b * y1 + c * y2 + d * p3[1]))
    return pts


def _arc(p1, rx, ry, phi, large, sweep, p2, steps):
    """SVG elliptical arc to points (endpoint -> centre parameterisation, SVG spec F.6.5)."""
    (x1, y1), (x2, y2) = p1, p2
    if rx == 0 or ry == 0 or p1 == p2:
        return [p2]
    cp, sp = math.cos(math.radians(phi)), math.sin(math.radians(phi))
    dx, dy = (x1 - x2) / 2, (y1 - y2) / 2
    x1p, y1p = cp * dx + sp * dy, -sp * dx + cp * dy
    rx, ry = abs(rx), abs(ry)
    lam = x1p ** 2 / rx ** 2 + y1p ** 2 / ry ** 2
    if lam > 1:
        rx, ry = rx * math.sqrt(lam), ry * math.sqrt(lam)
    num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
    den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    coef = math.sqrt(max(0.0, num / den)) * (-1 if large == sweep else 1)
    cxp, cyp = coef * rx * y1p / ry, -coef * ry * x1p / rx
    cx, cy = cp * cxp - sp * cyp + (x1 + x2) / 2, sp * cxp + cp * cyp + (y1 + y2) / 2

    def ang(ux, uy, vx, vy):
        return math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)

    t1 = ang(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    dt = ang((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not sweep and dt > 0:
        dt -= 2 * math.pi
    elif sweep and dt < 0:
        dt += 2 * math.pi
    return [(cp * rx * math.cos(t1 + dt * k / steps) - sp * ry * math.sin(t1 + dt * k / steps) + cx,
             sp * rx * math.cos(t1 + dt * k / steps) + cp * ry * math.sin(t1 + dt * k / steps) + cy)
            for k in range(1, steps + 1)]


def path_points(d, steps=8):
    """The first subpath of an SVG path as a list of points, curves flattened."""
    toks, i = TOKEN.findall(d or ""), 0
    subpaths, pts, cmd = [], [], None
    x = y = sx = sy = 0.0
    prev_c = prev_q = None

    def nums(n):
        nonlocal i
        v = [float(t) for t in toks[i:i + n]]
        i += n
        return v

    while i < len(toks):
        if toks[i].isalpha():
            cmd = toks[i]
            i += 1
            if cmd in "Zz":
                if pts:
                    subpaths.append(pts)
                pts, (x, y) = [], (sx, sy)
                continue
        if cmd is None or i >= len(toks) or toks[i].isalpha():
            break
        rel, C = cmd.islower(), cmd.upper()
        ox, oy = (x, y) if rel else (0.0, 0.0)
        c_ctrl = q_ctrl = None
        if C == "M":
            nx, ny = nums(2)
            if pts:
                subpaths.append(pts)
            x, y = sx, sy = ox + nx, oy + ny
            pts = [(x, y)]
            cmd = "l" if rel else "L"
        elif C == "L":
            nx, ny = nums(2)
            x, y = ox + nx, oy + ny
            pts.append((x, y))
        elif C == "H":
            x = (x if rel else 0.0) + nums(1)[0]
            pts.append((x, y))
        elif C == "V":
            y = (y if rel else 0.0) + nums(1)[0]
            pts.append((x, y))
        elif C in "CS":
            if C == "C":
                x1, y1, x2, y2, ex, ey = nums(6)
                c1 = (ox + x1, oy + y1)
            else:
                x2, y2, ex, ey = nums(4)
                c1 = (2 * x - prev_c[0], 2 * y - prev_c[1]) if prev_c else (x, y)
            c2, end = (ox + x2, oy + y2), (ox + ex, oy + ey)
            pts += _bezier((x, y), (c1, c2), end, steps)
            (x, y), c_ctrl = end, c2
        elif C in "QT":
            if C == "Q":
                x1, y1, ex, ey = nums(4)
                q1 = (ox + x1, oy + y1)
            else:
                ex, ey = nums(2)
                q1 = (2 * x - prev_q[0], 2 * y - prev_q[1]) if prev_q else (x, y)
            end = (ox + ex, oy + ey)
            pts += _bezier((x, y), (q1,), end, steps)
            (x, y), q_ctrl = end, q1
        elif C == "A":
            rx, ry, phi, large, sweep, ex, ey = nums(7)
            end = (ox + ex, oy + ey)
            pts += _arc((x, y), rx, ry, phi, bool(large), bool(sweep), end, steps)
            x, y = end
        prev_c, prev_q = c_ctrl, q_ctrl
    if pts:
        subpaths.append(pts)
    out = subpaths[0] if subpaths else []
    if len(out) > 1 and math.dist(out[0], out[-1]) < 1e-6:
        out = out[:-1]
    return out


def _f(el, name, default=0.0):
    v = NUM.match(el.get(name) or "")
    return float(v.group()) if v else default


def outline(el):
    """Points of a shape element in its own user units (no transform applied)."""
    tag = el.tag.split("}")[-1]
    if tag == "path":
        return path_points(el.get("d"))
    if tag == "rect":
        x, y, w, h = _f(el, "x"), _f(el, "y"), _f(el, "width"), _f(el, "height")
        return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    if tag in ("polygon", "polyline"):
        v = [float(n) for n in NUM.findall(el.get("points") or "")]
        return list(zip(v[0::2], v[1::2]))
    if tag in ("circle", "ellipse"):
        cx, cy = _f(el, "cx"), _f(el, "cy")
        rx = _f(el, "r") if tag == "circle" else _f(el, "rx")
        ry = _f(el, "r") if tag == "circle" else _f(el, "ry")
        return [(cx + rx * math.cos(k * math.pi / 12), cy + ry * math.sin(k * math.pi / 12)) for k in range(24)]
    return []


def cm_per_unit(root):
    """Centimetres per user unit, from the width attribute and the viewBox. No units given: 1 unit = 1 cm."""
    m = re.fullmatch(r"\s*([\d.]+)\s*([a-z]*)\s*", root.get("width") or "")
    vb = [float(n) for n in NUM.findall(root.get("viewBox") or "")]
    if m and m.group(2) in UNIT_CM and len(vb) == 4 and vb[2] > 0:
        return float(m.group(1)) * UNIT_CM[m.group(2)] / vb[2]
    return 1.0


def outlines(path):
    """{id: points in cm} for every shape element with an id, transforms of the element and its parents applied."""
    root = ET.parse(path).getroot()
    k = cm_per_unit(root)
    out = {}

    def walk(el, m):
        m = mul(m, parse_transform(el.get("transform")))
        if el.get("id") and el.tag.split("}")[-1] in SHAPES:
            pts = outline(el)
            if pts:
                out[el.get("id")] = [(x * k, y * k) for x, y in apply(m, pts)]
        for child in el:
            walk(child, m)

    walk(root, IDENTITY)
    return out
