"""A 3D model of a room from the same data as the drawings: build/model/<ROOM>.glb.

Every placed object already has a footprint polygon and a height band, so the model is those footprints extruded
and nothing more: a massing model to orbit in Open3D Viewer, Blender, VS Code or any glTF viewer, or in the
directory's 3D page (view3d.py), which needs no app at all. Rotations, profiles, groups and mount heights all come through, because they are already in the
geometry the checks and the drawings use.

glTF is JSON and one binary buffer, so it is written here rather than pulling in a library, the way svg.py and
xlsx.py are. Lengths are centimetres in the spreadsheet and metres in glTF. Y is up: a room's x runs to X, and its
y, which goes down the drawing, runs to Z, so the model is the plan seen from above.

Walls stop at waist height by default, a dollhouse view: full-height walls hide the room from every angle outside
it, and cutting real openings for doors and windows would need solid modelling for no real gain. Enclosures with a
working space inside (inner_w, inner_d) are built as a shell around it, open at the front, so you can see in.

It is also a way of reading the checks: what they flag is coloured the way the report outlines it, clear zones
are painted on the floor, and a model of the arrangement drawn in Inkscape (model --layout) colours what a pull
would move, with a see-through ghost where each thing stands now. --plain leaves all that out, for sending.
"""
from __future__ import annotations

import json
import struct
from pathlib import Path

from . import geometry as G
from .checks import zones
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
PROBLEM, WARNING = "#c62828", "#e08a00"  # as the report outlines them
MOVED = GHOST = "#7e57c2"  # what a pending pull would move, and see-through where it stands now
ZONE = "#f2c200"  # hazard-tape yellow, see-through
MARK = (0.3, 1.3)  # cm above the surface a clear zone is painted on: clear of it, so the two don't flicker


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
    """Write {name: (Mesh, colour[, alpha[, extras]])} as a .glb. One material per colour and opacity, one mesh
    per node, no transforms: the geometry is already in room coordinates. extras rides along on the node (what the
    checks said about it), where a viewer that knows to look can find it."""
    buf, views, accessors, meshes, materials, out, colours = bytearray(), [], [], [], [], [], {}

    def chunk(fmt, values, target):
        while len(buf) % 4:
            buf.append(0)
        start = len(buf)
        buf.extend(struct.pack(f"<{len(values)}{fmt}", *values))
        views.append({"buffer": 0, "byteOffset": start, "byteLength": len(buf) - start, "target": target})
        return len(views) - 1

    for name, (mesh, colour, *rest) in nodes.items():
        if not mesh:
            continue
        alpha = rest[0] if rest else 1.0
        extras = rest[1] if len(rest) > 1 else None
        key = (colour or DEFAULT, alpha)
        if key not in colours:
            base = _linear(key[0])[:3] + [alpha]
            material = {"name": key[0] if alpha == 1 else f"{key[0]} {alpha:g}", "doubleSided": True,
                        "pbrMetallicRoughness": {"baseColorFactor": base, "metallicFactor": 0.0,
                                                 "roughnessFactor": 0.75}}
            if alpha < 1:
                material["alphaMode"] = "BLEND"  # see-through: clear zones, and where moved things used to be
            materials.append(material)
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
        out.append({"name": name, "mesh": len(meshes) - 1, **({"extras": extras} if extras else {})})
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


def _zones(r, g, person):
    """The space i needs kept clear, painted on whatever it stands on like hazard tape on a lab floor: a volume
    would fill the room with red haze, since in front of anything on the floor that space is a person tall. Room
    kept above something (clear_top: a sash, a lid) is the exception, and is drawn as the volume it is."""
    mesh = Mesh()
    for side, poly, (z0, z1) in zones(r, g, person):
        if side == "top":
            mesh.prism(poly, z0, z1)
        else:
            mesh.prism(poly, z0 + MARK[0], z0 + MARK[1])
    return mesh


def moved_between(before, after):
    """Ids whose place in the room changed between two sets of geometry, carried along or moved themselves,
    arriving or leaving. Half a centimetre is rounding, not a move."""
    def spot(g):
        return g.room, tuple(sorted((round(x * 2), round(y * 2)) for x, y in g.poly)), round(g.z[0]), round(g.z[1])

    placed = lambda geo: {i: spot(g) for i, g in geo.items() if g and g.poly}
    a, b = placed(before), placed(after)
    return {i for i in set(a) | set(b) if a.get(i) != b.get(i)}


def scene(lab, rid, geo, walls=WALL_H, flagged=None, moved=(), ghosts=None, person=200):
    """({name: (Mesh, colour[, alpha, extras])}, ids with no geometry to draw) for one room.

    flagged is {id: (messages, is a problem)} from the checks, and colours those objects the way the report
    outlines them. moved is what a pending pull would move, drawn in its own colour; ghosts is their old geometry,
    drawn see-through where they stand now. Pass neither for a plain model to send to someone."""
    nodes, skipped = room(lab, rid, walls), []
    plain, flagged = flagged is None, flagged or {}
    for i, g in (ghosts or {}).items():
        if g and g.poly and g.room == rid:
            nodes[f"{i} (was here)"] = (Mesh().prism(g.poly, *g.z), GHOST, 0.28)
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
        msgs, bad = flagged.get(i, ([], False))
        colour = PROBLEM if bad else MOVED if i in moved else WARNING if msgs else colour_of(r.get("category"))
        notes = {k: v for k, v in (("findings", msgs), ("moved", i in moved)) if v}
        nodes[name] = (mesh, colour, 1.0, notes or None)
        if not plain:
            clear = _zones(r, g, person)
            if clear:
                nodes[f"{i} clear zone"] = (clear, ZONE, 0.45)
    return nodes, skipped


def write_models(lab, res, folder=None, rooms=None, walls=WALL_H, plain=False, before=None, suffix=""):
    """A .glb per room in build/model. Returns [(path, how many objects, ids skipped)].

    Unless plain, what the checks flag is coloured and clear zones are painted in. before is the lab as it was,
    for a model of the arrangement drawn in Inkscape: what moved is coloured, with a ghost where it came from."""
    from .layout import _flagged

    geo = getattr(res, "geo", None) or G.place_all(lab)[0]
    old = G.place_all(before)[0] if before is not None else {}
    moved = moved_between(old, geo) if before is not None else set()
    flagged = {} if plain else _flagged(lab, res)
    out = []
    for rid in (rooms or lab.rooms):
        if rid not in lab.rooms:
            continue
        nodes, skipped = scene(lab, rid, geo, walls, None if plain else flagged, moved,
                               {i: old[i] for i in moved if old.get(i)}, lab.settings["person_height"])
        path = Path(folder or lab.folder) / "build" / "model" / f"{rid}{suffix}.glb"
        things = [k for k, n in nodes.items() if n[0] and not k.endswith((" clear zone", " (was here)"))
                  and k not in (f"{rid} floor", f"{rid} walls")]
        out.append((write(nodes, path), len(things), skipped))
    return out
