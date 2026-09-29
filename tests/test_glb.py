"""The 3D model: footprints extruded into a .glb that any glTF viewer can open."""
import json
import struct
import tempfile
import unittest
from pathlib import Path

from labmap import checks, geometry as G, glb, model

ROOT = Path(__file__).resolve().parent.parent


def read(path):
    """(the glTF JSON, the binary chunk) of a .glb, checking the container as it goes."""
    raw = Path(path).read_bytes()
    magic, version, length = struct.unpack("<III", raw[:12])
    assert magic == 0x46546C67, "not a glb"
    assert version == 2, version
    assert length == len(raw), (length, len(raw))
    n, kind = struct.unpack("<II", raw[12:20])
    assert kind == 0x4E4F534A, "first chunk should be JSON"
    js = json.loads(raw[20:20 + n])
    size, kind = struct.unpack("<II", raw[20 + n:28 + n])
    assert kind == 0x004E4942, "second chunk should be BIN"
    return js, raw[28 + n:28 + n + size]


def lab_with(rows, **room):
    return model.build(ROOT, {"rooms": [{"id": "R", "ceiling": 250, **room}], "placeables": rows},
                       room_polys={"R": [(0, 0), (400, 0), (400, 300), (0, 300)]})


class Model(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def build(self, rows, walls=glb.WALL_H, **room):
        lab = lab_with(rows, **room)
        built = glb.write_models(lab, checks.run(lab), self.tmp, None, walls)
        self.assertEqual(len(built), 1)
        path, parts, skipped = built[0]
        js, binary = read(path)
        return js, binary, skipped, lab

    def mesh(self, js, name):
        for m in js["meshes"]:
            if m["name"] == name or m["name"].split(" ")[0] == name:
                return m
        raise AssertionError(f"{name} isn't in the model: {[m['name'] for m in js['meshes']]}")

    def box(self, js, name):
        """(min, max) of a node, in metres."""
        pos = js["accessors"][self.mesh(js, name)["primitives"][0]["attributes"]["POSITION"]]
        return pos["min"], pos["max"]

    def test_the_container_and_its_offsets(self):
        js, binary, _, _ = self.build([dict(id="B", room="R", mount="floor", category="bench",
                                            x=50, y=20, w=200, d=60, h=90)])
        self.assertEqual(js["buffers"][0]["byteLength"], len(binary))
        for a in js["accessors"]:
            view = js["bufferViews"][a["bufferView"]]
            self.assertLessEqual(view["byteOffset"] + view["byteLength"], len(binary))
            self.assertLessEqual(a["count"] * (12 if a["type"] == "VEC3" else 4), view["byteLength"])
            self.assertEqual(view["byteOffset"] % 4, 0)  # glTF wants its views aligned

    def test_centimetres_become_metres_with_y_up(self):
        js, _, _, _ = self.build([dict(id="B", room="R", mount="floor", category="bench",
                                       x=50, y=20, w=200, d=60, h=90)])
        low, high = self.box(js, "B")
        self.assertEqual([round(v, 4) for v in low], [0.5, 0.0, 0.2])
        self.assertEqual([round(v, 4) for v in high], [2.5, 0.9, 0.8])  # x, height, y down the plan

    def test_what_stands_on_a_bench_is_at_bench_height(self):
        js, _, _, _ = self.build([dict(id="B", room="R", mount="floor", category="bench", x=0, y=0, w=200, d=60, h=90),
                                  dict(id="SMU", room="R", parent="B", mount="on", category="power-supply",
                                       x=10, y=5, w=40, d=40, h=15)])
        low, high = self.box(js, "SMU")
        self.assertAlmostEqual(low[1], 0.9, places=4)
        self.assertAlmostEqual(high[1], 1.05, places=4)

    def test_a_wall_shelf_floats_at_its_z(self):
        js, _, _, _ = self.build([dict(id="S", room="R", mount="wall", category="shelf", x=0, y=0, z=150,
                                       w=100, d=30, h=4)])
        low, high = self.box(js, "S")
        self.assertAlmostEqual(low[1], 1.5, places=4)
        self.assertAlmostEqual(high[1], 1.54, places=4)

    def test_walls_stop_where_you_asked(self):
        rows = [dict(id="B", room="R", mount="floor", category="bench", x=0, y=0, w=200, d=60, h=90)]
        js, _, _, _ = self.build(rows)
        self.assertAlmostEqual(self.box(js, "R walls")[1][1], 1.2, places=4)  # 120 cm by default
        js, _, _, _ = self.build(rows, walls=250)
        self.assertAlmostEqual(self.box(js, "R walls")[1][1], 2.5, places=4)
        js, _, _, _ = self.build(rows, walls=0)
        self.assertEqual([m["name"] for m in js["meshes"] if m["name"].endswith("walls")], [])

    def test_the_floor_is_the_room(self):
        js, _, _, _ = self.build([dict(id="B", room="R", mount="floor", category="bench", x=0, y=0, w=10, d=10, h=10)])
        low, high = self.box(js, "R")  # the floor node comes first
        self.assertEqual([round(v, 3) for v in high[::2]], [4.0, 3.0])  # the 400 x 300 cm room

    def test_a_colour_per_category(self):
        js, _, _, _ = self.build([dict(id="B", room="R", mount="floor", category="bench", x=0, y=0, w=99, d=60, h=90)])
        material = js["materials"][self.mesh(js, "B")["primitives"][0]["material"]]
        self.assertEqual(material["pbrMetallicRoughness"]["baseColorFactor"], glb._linear(glb.colour_of("bench")))

    def test_the_plan_colours_are_deepened_not_replaced(self):
        """Same hue as the drawings, so what people have learnt from them carries over; darker, so a viewer's
        lighting doesn't wash every category into the same off-white."""
        for plan in ("#e9dcc3", "#bcd7f0", "#fecaca", "#c3cdb8"):
            solid = glb.deepen(plan)
            was, now = glb._hsl(*(int(plan[k:k + 2], 16) / 255 for k in (1, 3, 5))), \
                glb._hsl(*(int(solid[k:k + 2], 16) / 255 for k in (1, 3, 5)))
            self.assertAlmostEqual(was[0], now[0], places=2, msg=f"{plan} changed hue")
            self.assertLess(now[2], was[2] - 0.15, f"{plan} -> {solid} isn't darker")
            self.assertLess(now[1], 0.5, f"{plan} -> {solid} is too saturated")
        self.assertEqual(glb._hsl(*(int(glb.deepen("#d6d6d6")[k:k + 2], 16) / 255 for k in (1, 3, 5)))[1], 0)  # grey

    def test_faces_are_shaded_so_edges_show(self):
        js, binary, _, _ = self.build([dict(id="B", room="R", mount="floor", category="bench",
                                            x=0, y=0, w=200, d=60, h=90)])
        prim = self.mesh(js, "B")["primitives"][0]
        self.assertIn("COLOR_0", prim["attributes"])
        a = js["accessors"][prim["attributes"]["COLOR_0"]]
        view = js["bufferViews"][a["bufferView"]]
        shades = struct.unpack_from(f"<{a['count'] * 4}f", binary, view["byteOffset"])[0::4]
        self.assertEqual(max(shades), glb.SHADE["top"])
        self.assertEqual(min(shades), glb.SHADE["bottom"])
        self.assertGreater(len(set(round(s, 3) for s in shades)), 3)  # the four sides differ too

    def test_a_bench_floats_above_its_leg_room(self):
        """Filling in the leg room would hide the pedestal parked in it: only the top is drawn."""
        js, _, _, _ = self.build([dict(id="B", room="R", mount="floor", category="bench", x=0, y=0, w=200, d=60,
                                       h=90, free_under=85),
                                  dict(id="PED", room="R", mount="floor", category="pedestal", x=20, y=5, w=50,
                                       d=50, h=80)])
        low, high = self.box(js, "B")
        self.assertAlmostEqual(low[1], 0.85, places=4)  # the worktop starts where the leg room ends
        self.assertAlmostEqual(high[1], 0.9, places=4)
        self.assertAlmostEqual(self.box(js, "PED")[1][1], 0.8, places=4)  # ...and the pedestal is visible under it

    def test_without_free_under_it_is_solid(self):
        js, _, _, _ = self.build([dict(id="C", room="R", mount="floor", category="cabinet", x=0, y=0, w=60, d=50,
                                       h=80)])
        self.assertAlmostEqual(self.box(js, "C")[0][1], 0.0, places=4)

    def test_nothing_to_draw_it_from_is_reported_but_contents_are_not(self):
        js, _, skipped, _ = self.build([
            dict(id="B", room="R", mount="floor", category="bench", x=0, y=0, w=200, d=60, h=90, free_under=85),
            dict(id="NEW", room="R", mount="floor", category="instrument"),  # no size, no place: arriving
            dict(id="B.D1", room="R", parent="B", mount="in", category="drawer", w=40, d=50, h=10)])
        self.assertEqual(skipped, ["NEW"])
        self.assertNotIn("B.D1", [m["name"].split(" ")[0] for m in js["meshes"]])

    def test_reserved_working_space_is_left_out(self):
        js, _, skipped, _ = self.build([
            dict(id="B", room="R", mount="floor", category="bench", x=0, y=0, w=200, d=60, h=90),
            dict(id="WS", room="R", parent="B", mount="on", category="workspace", x=0, y=0, w=80, d=60, h=40)])
        self.assertNotIn("WS", [m["name"].split(" ")[0] for m in js["meshes"]])
        self.assertEqual(skipped, [])


class FromTheExample(unittest.TestCase):
    """The example has the awkward cases: a profile footprint, a diagonal piece, a fume hood with a working space."""

    @classmethod
    def setUpClass(cls):
        cls.lab = model.load(ROOT / "example")
        cls.geo = G.place_all(cls.lab)[0]
        cls.tmp = Path(tempfile.mkdtemp())
        glb.write_models(cls.lab, checks.run(cls.lab), cls.tmp)
        cls.js = {rid: read(cls.tmp / "build" / "model" / f"{rid}.glb")[0] for rid in ("LAB-A", "LAB-B")}

    def bounds(self, room, name):
        for m in self.js[room]["meshes"]:
            if m["name"].split(" ")[0] == name:
                a = self.js[room]["accessors"][m["primitives"][0]["attributes"]["POSITION"]]
                return a["min"], a["max"]
        raise AssertionError(f"{name} isn't in {room}")

    def triangles(self, room, name):
        for m in self.js[room]["meshes"]:
            if m["name"].split(" ")[0] == name:
                return self.js[room]["accessors"][m["primitives"][0]["indices"]]["count"] // 3
        raise AssertionError(name)

    def matches_geometry(self, room, name):
        """The footprint on the plan and the height it reaches; where it starts depends on free_under."""
        low, high = self.bounds(room, name)
        g = self.geo[name]
        x0, y0, x1, y1 = G.bbox(g.poly)
        for got, want in zip((low[0], low[2], high[0], high[2], high[1]), (x0, y0, x1, y1, g.z[1])):
            self.assertAlmostEqual(got, want / 100, places=3, msg=f"{name} {low} {high}")

    def test_a_profile_footprint(self):
        self.matches_geometry("LAB-B", "BENCH-10")  # @corner-45: six corners, not a box
        self.assertGreater(self.triangles("LAB-B", "BENCH-10"), 12)

    def test_a_piece_turned_diagonally(self):
        self.matches_geometry("LAB-B", "BENCH-11.B")

    def test_a_fume_hood_is_a_shell_you_can_see_into(self):
        self.assertGreater(self.triangles("LAB-A", "HOOD-01"), 12 * 4)  # five slabs around the working space
        self.matches_geometry("LAB-A", "HOOD-01")  # ...still the same outside

    def test_every_room_becomes_a_file(self):
        for rid in self.lab.rooms:
            self.assertTrue((self.tmp / "build" / "model" / f"{rid}.glb").exists(), rid)


if __name__ == "__main__":
    unittest.main()
