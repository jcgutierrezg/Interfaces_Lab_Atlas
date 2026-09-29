"""A 3D model of a room from the same data as the drawings: build/model/<ROOM>.glb.

Every placed object already has a footprint polygon and a height band, so the model is those footprints extruded
and nothing more: a massing model to orbit in Windows 3D Viewer (double-click the file), Blender, VS Code or any
glTF viewer. Rotations, profiles, groups and mount heights all come through, because they are already in the
geometry the checks and the drawings use.

glTF is JSON and one binary buffer, so it is written here rather than pulling in a library, the way svg.py and
xlsx.py are. Lengths are centimetres in the spreadsheet and metres in glTF. Y is up: a room's x runs to X, and its
y, which goes down the drawing, runs to Z, so the model is the plan seen from above.

Walls stop at waist height by default, a dollhouse view: full-height walls hide the room from every angle outside
it, and cutting real openings for doors and windows would need solid modelling for no real gain. Enclosures with a
working space inside (inner_w, inner_d) are built as a shell around it, open at the front, so you can see in.
"""
from __future__ import annotations

import json
import struct
from pathlib import Path

from . import geometry as G
from .layout import FILL

CM = 0.01  # glTF is metres
WALL_H = 120  # cm: walls you can see over
WALL_T = 15
FLOOR_T = 4
ROOM_COLOUR = {"floor": "#b8b2a6", "wall": "#8f959c"}
DEFAULT = "#b9bcc2"
SOLID = {  # where deepening the plan's colour isn't enough to tell things apart under a viewer's lighting
    "door": "#9a7b4f", "window": "#5f9ec4", "structure": "#6e6e6e", "safety": "#2f9e4f",
    "sink": "#4f8fb5", "gas-cylinder": "#c6a419", "dark-box": "#4a5260", "laser": "#d4a017",
    "fume-hood": "#7d8a96", "glovebox": "#7d8a96", "computer": "#8f7bc0", "monitor": "#8f7bc0",
}
SHADE = {"top": 1.0, "bottom": 0.5}  # a flat model needs its faces telling apart: the top is the lit one


def _hsl(r, g, b):
    high, low = max(r, g, b), min(r, g, b)
    light = (high + low) / 2
    if high == low:
        return 0.0, 0.0, light
    d = high - low
    sat = d / (2 - high - low) if light > 0.5 else d / (high + low)
    hue = ((g - b) / d + (6 if g < b else 0)) if high == r else ((b - r) / d + 2) if high == g else ((r - g) / d + 4)
    return hue / 6, sat, light


def _rgb(hue, sat, light):
    if sat == 0:
        return (light,) * 3
    q = light * (1 + sat) if light < 0.5 else light + sat - light * sat
    p = 2 * light - q
    out = []
    for t in (hue + 1 / 3, hue, hue - 1 / 3):
        t = t % 1
        out.append(p + (q - p) * 6 * t if t < 1 / 6 else q if t < 1 / 2 else
                   p + (q - p) * (2 / 3 - t) * 6 if t < 2 / 3 else p)
    return tuple(out)


def deepen(hex_colour):
    """A plan colour, made solid enough to read in a 3D viewer.

    The drawings are pastel because they sit on white paper with black outlines. In a viewer there are no outlines
    and the lighting adds its own white, so those colours all come out as the same off-white. Same hue, deeper and
    more saturated, keeps what people have learnt from the plans while telling things apart on screen.
    """
    h = (hex_colour or DEFAULT).lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6 or any(c not in "0123456789abcdefABCDEF" for c in h):
        return DEFAULT
    hue, sat, light = _hsl(*(int(h[k:k + 2], 16) / 255 for k in (0, 2, 4)))
    if sat < 0.06:  # a grey stays a grey, just darker
        return "#%02x%02x%02x" % tuple(round(255 * c) for c in _rgb(hue, sat, min(max(light * 0.72, 0.28), 0.62)))
    sat, light = min(0.45, sat * 0.9 + 0.08), min(max(light * 0.68, 0.34), 0.60)  # readable, not fluorescent
    return "#%02x%02x%02x" % tuple(round(255 * c) for c in _rgb(hue, sat, light))


def colour_of(category):
    """The colour a category is drawn in, in three dimensions."""
    return SOLID.get(category) or deepen(FILL.get(category, DEFAULT))


def _linear(hex_colour):
    """A CSS colour as glTF's linear base colour, so it looks like the drawings rather than washed out."""
    h = (hex_colour or DEFAULT).lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6 or any(c not in "0123456789abcdefABCDEF" for c in h):
        h = DEFAULT.lstrip("#")
    out = []
    for k in (0, 2, 4):
        c = int(h[k:k + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return out + [1.0]


class Mesh:
    """Triangles for one node, with a normal per corner so flat faces read as flat in every viewer."""

    def __init__(self):
        self.pos, self.nrm, self.col, self.idx = [], [], [], []

    def face(self, points, normal, shade=1.0):
        """A convex face, wound so its front is the way the normal points. `shade` multiplies the colour there:
        without it a box is one flat colour and its edges vanish, whatever the viewer's lighting does."""
        first = len(self.pos) // 3
        for x, y, z in points:
            self.pos += [x * CM, z * CM, y * CM]  # room x, y (down the plan) and height z -> glTF X, Z, Y up
            self.nrm += [normal[0], normal[2], normal[1]]
            self.col += [shade, shade, shade, 1.0]
        for k in range(1, len(points) - 1):
            self.idx += [first, first + k, first + k + 1]

    def prism(self, poly, z0, z1):
        """A footprint extruded between two heights: the whole model is made of these."""
        if z1 - z0 <= 0 or len(poly) < 3:
            return self
        ring = list(poly) if G.area(poly) > 0 else list(reversed(poly))  # anticlockwise on the plan
        for piece in G.convex_pieces(ring):
            self.face([(x, y, z1) for x, y in piece], (0, 0, 1), SHADE["top"])
            self.face([(x, y, z0) for x, y in reversed(piece)], (0, 0, -1), SHADE["bottom"])
        for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
            dx, dy = x2 - x1, y2 - y1
            length = (dx * dx + dy * dy) ** 0.5
            if length < 1e-9:
                continue
            n = (dy / length, -dx / length, 0)  # outward for an anticlockwise ring on the plan
            lit = 0.72 + 0.16 * (n[0] * 0.45 - n[1] * 0.89)  # a sun over the top-right of the plan
            self.face([(x1, y1, z0), (x2, y2, z0), (x2, y2, z1), (x1, y1, z1)], n, lit)
        return self

    def box(self, x0, y0, x1, y1, z0, z1):
        return self.prism([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1)

    def __bool__(self):
        return bool(self.idx)


def write(nodes, path):
    """Write {name: (Mesh, colour)} as a .glb. One material per colour, one mesh per node, no transforms: the
    geometry is already in room coordinates."""
    buf, views, accessors, meshes, materials, out, colours = bytearray(), [], [], [], [], [], {}

    def chunk(fmt, values, target):
        while len(buf) % 4:
            buf.append(0)
        start = len(buf)
        buf.extend(struct.pack(f"<{len(values)}{fmt}", *values))
        views.append({"buffer": 0, "byteOffset": start, "byteLength": len(buf) - start, "target": target})
        return len(views) - 1

    for name, (mesh, colour) in nodes.items():
        if not mesh:
            continue
        key = colour or DEFAULT
        if key not in colours:
            materials.append({"name": key, "doubleSided": True,
                              "pbrMetallicRoughness": {"baseColorFactor": _linear(key), "metallicFactor": 0.0,
                                                       "roughnessFactor": 0.75}})
            colours[key] = len(materials) - 1
        xyz = [mesh.pos[k::3] for k in range(3)]
        accessors.append({"bufferView": chunk("f", mesh.pos, 34962), "componentType": 5126, "type": "VEC3",
                          "count": len(mesh.pos) // 3, "min": [min(v) for v in xyz], "max": [max(v) for v in xyz]})
        accessors.append({"bufferView": chunk("f", mesh.nrm, 34962), "componentType": 5126, "type": "VEC3",
                          "count": len(mesh.nrm) // 3})
        accessors.append({"bufferView": chunk("f", mesh.col, 34962), "componentType": 5126, "type": "VEC4",
                          "count": len(mesh.col) // 4})
        accessors.append({"bufferView": chunk("I", mesh.idx, 34963), "componentType": 5125, "type": "SCALAR",
                          "count": len(mesh.idx)})
        meshes.append({"name": name, "primitives": [{"attributes": {"POSITION": len(accessors) - 4,
                                                                    "NORMAL": len(accessors) - 3,
                                                                    "COLOR_0": len(accessors) - 2},
                                                     "indices": len(accessors) - 1, "material": colours[key]}]})
        out.append({"name": name, "mesh": len(meshes) - 1})
    gltf = {"asset": {"version": "2.0", "generator": "labmap"}, "scene": 0,
            "scenes": [{"nodes": list(range(len(out)))}], "nodes": out, "meshes": meshes, "materials": materials,
            "accessors": accessors, "bufferViews": views, "buffers": [{"byteLength": len(buf)}]}
    js = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    js += b" " * (-len(js) % 4)
    buf.extend(b"\0" * (-len(buf) % 4))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(buf)))
        f.write(struct.pack("<II", len(js), 0x4E4F534A) + js)
        f.write(struct.pack("<II", len(buf), 0x004E4942) + bytes(buf))
    return path


def _shell(lab, i, g, mesh):
    """An enclosure as five slabs around its working space, open at the front, so the inside can be seen."""
    inner = G.interior(lab, i)
    if inner is None or not g.local:
        return False
    u0, v0, iw, idp, ih, iz = inner
    if not ih:
        return False
    x0, y0, x1, y1 = G.bbox(g.local)
    z0, z1 = g.z
    top, bottom = min(z1, z0 + iz + ih), z0 + iz
    for u_a, v_a, u_b, v_b, a, b in ((x0, y0, x1, y1, z0, bottom),            # under the working space
                                     (x0, y0, x1, y1, top, z1),               # over it
                                     (x0, y0, u0, y1, bottom, top),           # left
                                     (u0 + iw, y0, x1, y1, bottom, top),      # right
                                     (u0, y0, u0 + iw, v0, bottom, top)):     # back
        if u_b - u_a > 0.01 and v_b - v_a > 0.01 and b - a > 0.01:
            mesh.prism([g.T(u_a, v_a), g.T(u_b, v_a), g.T(u_b, v_b), g.T(u_a, v_b)], a, b)
    return True


def room(lab, rid, walls=WALL_H):
    """{name: (Mesh, colour)} for the room shell: a floor slab and a wall along each side of the outline."""
    poly = lab.rooms[rid].get("poly")
    if not poly:
        return {}
    out = {f"{rid} floor": (Mesh().prism(poly, -FLOOR_T, 0), ROOM_COLOUR["floor"])}
    if not walls:
        return out
    ring = list(poly) if G.area(poly) > 0 else list(reversed(poly))
    band = Mesh()
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        dx, dy = x2 - x1, y2 - y1
        length = (dx * dx + dy * dy) ** 0.5
        if length < 1e-9:
            continue
        ox, oy = dy / length * WALL_T, -dx / length * WALL_T  # outwards
        band.prism([(x1, y1), (x2, y2), (x2 + ox, y2 + oy), (x1 + ox, y1 + oy)], -FLOOR_T, walls)
    out[f"{rid} walls"] = (band, ROOM_COLOUR["wall"])
    return out


def scene(lab, rid, geo, walls=WALL_H):
    """({name: (Mesh, colour)}, ids with no geometry to draw) for one room."""
    nodes, skipped = room(lab, rid, walls), []
    for i, r in lab.placeables.items():
        if r.get("room") != rid or i in lab.gone:
            continue
        if FILL.get(r.get("category")) == "none":
            continue  # reserved working space, drawn as an outline on the plan: a solid block would hide the bench
        g = geo.get(i)
        if g is None or not g.poly or g.z[1] - g.z[0] <= 0:
            contents = r.get("mount") == "in" and (r.get("x") is None or r.get("y") is None)
            if r.get("shape") != "group" and not contents:  # drawers and shelves inside things have no place of
                skipped.append(i)                           # their own: they are contents, not things left out
            continue
        mesh = Mesh()
        if not _shell(lab, i, g, mesh):
            z0, z1 = g.z
            fu = r.get("free_under")
            if fu is not None and 0 < fu < z1 - z0:
                z0 += fu  # the top only, floating: a bench that fills its own leg room hides what is parked there
            mesh.prism(g.poly, z0, z1)
        name = f"{i} {r.get('name')}" if r.get("name") else i
        nodes[name] = (mesh, colour_of(r.get("category")))
    return nodes, skipped


def write_models(lab, res, folder=None, rooms=None, walls=WALL_H):
    """A .glb per room in build/model. Returns [(path, how many objects, ids skipped)]."""
    geo = getattr(res, "geo", None) or G.place_all(lab)[0]
    out = []
    for rid in (rooms or lab.rooms):
        if rid not in lab.rooms:
            continue
        nodes, skipped = scene(lab, rid, geo, walls)
        path = Path(folder or lab.folder) / "build" / "model" / f"{rid}.glb"
        out.append((write(nodes, path), sum(1 for m, _ in nodes.values() if m), skipped))
    return out
