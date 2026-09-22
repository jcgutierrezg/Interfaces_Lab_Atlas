"""Layouts: generate, edit the SVG the way Inkscape does, read the moves back, write them to the workbook."""
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from labmap import checks, layout, model

ROOT = Path(__file__).resolve().parent.parent
SVG = "{http://www.w3.org/2000/svg}"


class RoundTrip(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for name in ("lab-data.xlsx", "rooms", "shapes"):
            src = ROOT / "example" / name
            (shutil.copytree if src.is_dir() else shutil.copy2)(src, self.tmp / name)
        self.lab = model.load(self.tmp)
        self.res = checks.run(self.lab)
        layout.write_layouts(self.lab, self.res)
        self.path = layout.layout_path(self.tmp)
        _, self.rooms, _ = layout.read_layout(self.path)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def edit(self, changes):
        """changes: {id: function(old transform) -> new transform}, like dragging in Inkscape."""
        tree = ET.parse(self.path)
        for g in tree.iter(f"{SVG}g"):
            key = (g.get("id") or "")[len(layout.PREFIX):]
            if (g.get("id") or "").startswith(layout.PREFIX) and key in changes:
                g.set("transform", changes.pop(key)(g.get("transform") or ""))
        self.assertEqual(changes, {}, "every edited object should be in the layout")
        tree.write(self.path)

    def relayer(self, i, key):
        """Move i to another layer, like Layer › Move Selection to Layer Above / Below in Inkscape."""
        tree = ET.parse(self.path)
        parents = {c: p for p in tree.iter() for c in p}
        g = next(e for e in tree.iter(f"{SVG}g") if e.get("id") == layout.PREFIX + i)
        parents[g].remove(g)
        next(e for e in tree.iter(f"{SVG}g") if e.get("id") == f"layer-{key}").append(g)
        tree.write(self.path)

    def pull(self):
        moves, notes = layout.layout_moves(model.load(self.tmp))
        return moves["placeables"], moves, notes

    def doc(self, room, x, y):
        """Room coordinates to the layout file's."""
        m = self.rooms[room]["m"]
        return x + m[4], y + m[5]

    def centre(self, i):
        from labmap import geometry as G

        return self.doc(self.lab.placeables[i]["room"], *G.centroid(self.res.geo[i].poly))

    def drag(self, i, to):
        """Move i so that its centre lands on `to` (layout coordinates)."""
        (x, y), (tx, ty) = self.centre(i), to
        return {i: lambda t: f"translate({tx - x:.1f},{ty - y:.1f}) " + t}

    def along(self, i):
        """i and everything on or under it: what dragging a box around it in Inkscape selects."""
        out, todo = [i], [i]
        while todo:
            for c in self.lab.children.get(todo.pop(), []):
                if self.lab.placeables[c].get("mount") in ("on", "under", "part"):
                    out.append(c)
                    todo.append(c)
        return out

    def test_one_file_every_object_once(self):
        import re

        ids = re.findall(r'id="obj-([^"]+)"', self.path.read_text(encoding="utf-8"))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue({"SPEC-02", "HPLC-01", "INC-01", "GB-01"} <= set(ids))  # both rooms, and the staged ones
        self.assertEqual(set(self.rooms), {"LAB-A", "LAB-B"})
        self.assertEqual(sorted(p.name for p in self.path.parent.iterdir()), ["labs.svg"])

    def test_unchanged_layout_has_nothing_to_pull(self):
        self.assertEqual(layout.count(self.pull()[1]), 0)

    def test_moves_come_back_as_data(self):
        stage = self.rooms["LAB-A"]["stage"]
        moves = {k: (lambda t: "translate(-50,0) " + t) for k in self.along("BENCH-02")
                 if self.lab.placeables[k].get("mount") != "part"}
        moves.update({
            "VORT-01": lambda t: "translate(-50,0) " + t + " rotate(90)",  # carried along, and turned on its bench
            "BENCH-01": lambda t: "translate(0,40) " + t,                   # the sink bench is fixed: ignored
        })
        inc = self.doc("LAB-A", 400, 100)
        moves["INC-01"] = lambda t: f"translate({inc[0]:.1f},{inc[1]:.1f})"  # dragged in from the waiting area
        moves.update(self.drag("CART-01", ((stage[0][0] + stage[2][0]) / 2, (stage[0][1] + stage[2][1]) / 2)))
        self.edit(moves)
        placed, _, notes = self.pull()
        self.assertEqual(placed["BENCH-02"], dict(x=595, y=180, faces="W"))
        self.assertEqual(placed["INC-01"], dict(x=400, y=100, faces=None))
        self.assertEqual(placed["CART-01"], dict(x=None, y=None, faces=None))  # out to the waiting area
        self.assertEqual(placed["VORT-01"]["faces"], "W")
        self.assertTrue(any("BENCH-01 is fixed" in n for n in notes))
        self.assertEqual(set(placed), {"BENCH-02", "VORT-01", "INC-01", "CART-01"})  # the rest came along unchanged

    def test_bench_moved_alone_leaves_its_things(self):
        self.edit({"BENCH-02": lambda t: "translate(-30,0) " + t})
        placed, _, _ = self.pull()
        self.assertEqual((placed["BENCH-02"]["x"], placed["BENCH-02"]["y"]), (615, 180))
        self.assertIn("BAL-01", placed)  # stayed where it was drawn: further along its bench now
        self.assertNotIn("parent", placed["BAL-01"])  # still on BENCH-02

    def test_dropped_on_another_bench(self):
        self.edit(self.drag("SPEC-02", self.centre("TBL-01")))
        placed, moves, _ = self.pull()
        self.assertEqual(placed["SPEC-02"]["parent"], "TBL-01")
        self.assertNotIn("room", placed["SPEC-02"])
        self.assertEqual(set(placed), {"SPEC-02"})
        lab = model.load(self.tmp, moves)  # what check --layout does: try it without writing
        self.assertAlmostEqual(checks.run(lab).geo["SPEC-02"].z[0], 90)  # on the table top now
        model.write_moves(self.tmp / "lab-data.xlsx", moves, self.tmp / "build" / "backups")
        lab = model.load(self.tmp)
        self.assertEqual((lab.placeables["SPEC-02"]["parent"], lab.issues), ("TBL-01", []))
        layout.write_layouts(lab, checks.run(lab))
        self.assertEqual(layout.count(self.pull()[1]), 0)

    def test_out_from_under_a_bench(self):
        self.edit({"FRZ-02": lambda t: "translate(0,200) " + t})
        placed, _, notes = self.pull()
        self.assertEqual((placed["FRZ-02"]["parent"], placed["FRZ-02"]["mount"]), (None, "floor"))
        self.assertTrue(any("FRZ-02 isn't under anything" in n for n in notes))

    def test_group_moves_as_one(self):
        self.edit({k: (lambda t: "translate(-20,0) " + t) for k in self.along("BENCH-11")
                   if self.lab.placeables[k].get("mount") != "part"})
        placed, moves, _ = self.pull()
        self.assertEqual(placed, {"BENCH-11": dict(x=440, y=0, faces=None)})
        self.assertEqual(layout.count(moves), 1)

    def test_to_another_lab(self):
        self.edit(self.drag("FTIR-01", self.centre("TBL-01")))  # LAB-B instrument onto the LAB-A table
        placed, moves, notes = self.pull()
        self.assertEqual((placed["FTIR-01"]["room"], placed["FTIR-01"]["parent"]), ("LAB-A", "TBL-01"))
        self.assertEqual(moves["equipment"], {"FTIR-01": {"outlet": None}})  # its socket stayed in LAB-B
        self.assertTrue(any("FTIR-01 moves to LAB-A" in n for n in notes))
        model.write_moves(self.tmp / "lab-data.xlsx", moves, self.tmp / "build" / "backups")
        self.assertEqual(model.load(self.tmp).issues, [])

    def test_things_go_with_what_holds_them(self):
        spot = self.doc("LAB-B", 600, 380)
        self.edit({**self.drag("PED-01", spot), **self.drag("BENCH-02", self.doc("LAB-B", 450, 470))})
        placed, moves, _ = self.pull()
        self.assertEqual((placed["PED-01"]["room"], placed["PED-01"]["mount"]), ("LAB-B", "floor"))
        self.assertEqual({i for i, c in placed.items() if c == {"room": "LAB-B"}},
                         {"PED-01.D1", "PED-01.D2", "PED-01.D3", "BENCH-02.D1", "BENCH-02.D2"})  # drawers go along
        self.assertEqual(moves["services"], {"OUT-02": {"room": "LAB-B"}})  # the socket on BENCH-02's spine
        model.write_moves(self.tmp / "lab-data.xlsx", moves, self.tmp / "build" / "backups")
        self.assertEqual(model.load(self.tmp).issues, [])

    def test_layers_change_the_mount(self):
        # the arriving incubator, onto the central table: move it to 'on benches', then drag it there
        self.relayer("INC-01", "on")
        inc_to = self.centre("TBL-01")  # it's 70 x 70 and waiting unrotated: its corner goes 35 cm up and left
        self.edit({"INC-01": lambda t: f"translate({inc_to[0] - 35:.1f},{inc_to[1] - 35:.1f})"})
        self.relayer("FRZ-02", "floor")  # out from under the bench, where it is
        self.relayer("BIN-01", "under")  # the bin, under the table it already stands beneath
        placed, _, notes = self.pull()
        self.assertEqual((placed["INC-01"]["mount"], placed["INC-01"]["parent"]), ("on", "TBL-01"))
        self.assertEqual((placed["FRZ-02"]["mount"], placed["FRZ-02"]["parent"]), ("floor", None))
        self.assertEqual((placed["BIN-01"]["mount"], placed["BIN-01"]["parent"]), ("under", "TBL-01"))
        self.assertTrue(any("FRZ-02 was moved to the 'floor and benches' layer" in n for n in notes))
        model.write_moves(self.tmp / "lab-data.xlsx", self.pull()[1], self.tmp / "build" / "backups")
        lab = model.load(self.tmp)
        self.assertEqual(lab.issues, [])
        layout.write_layouts(lab, checks.run(lab))
        self.assertEqual(layout.count(self.pull()[1]), 0)  # redrawn on the right layers: nothing left to pull

    def test_dropped_outside_every_room(self):
        self.edit(self.drag("BENCH-02", self.doc("LAB-B", 700, 550)))  # LAB-B's missing corner: not a room
        placed, moves, notes = self.pull()
        self.assertEqual(layout.count(moves), 0)  # nothing changes, not even what stands on it
        self.assertTrue(any("BENCH-02 is outside every room" in n for n in notes))

    def test_written_to_workbook_and_layout_protected(self):
        self.edit({"CART-01": lambda t: "translate(-30,0) " + t})
        _, moves, _ = self.pull()
        lab = model.load(self.tmp)
        path, status = layout.write_layouts(lab, checks.run(lab))  # moves not pulled yet: must not overwrite
        self.assertIn("kept", status)
        backup, missing = model.write_moves(self.tmp / "lab-data.xlsx", moves, self.tmp / "build" / "backups")
        self.assertTrue(backup.exists())
        self.assertEqual(missing, [])
        lab = model.load(self.tmp)
        self.assertEqual((lab.placeables["CART-01"]["x"], lab.placeables["CART-01"]["y"]), (410, 300))
        self.assertEqual(lab.issues, [])
        self.assertEqual(layout.count(self.pull()[1]), 0)  # layout and workbook agree again

    def test_comparison_and_move_list(self):
        from labmap import report

        self.edit(self.drag("SPEC-02", self.centre("TBL-01")))
        _, moves, _ = self.pull()
        before = self.res
        after = checks.run(model.load(self.tmp, moves))
        rows = report.move_rows(before, after, moves)
        self.assertEqual(len(rows), 1)
        what, frm, to, plug, _ = rows[0]
        self.assertTrue(what.startswith("SPEC-02") and "BENCH-04.B" in frm and "TBL-01" in to)
        self.assertEqual(plug, "OUT-01 → OUT-07 (nearest)")
        html = report.comparison(before, after)
        self.assertIn("Overlap", html)  # dropped on the middle of the table: it lands on the microscope's spot
        self.assertIn("worse", html)
        page = report.write_move_list(self.tmp / "moves.html", before, after, moves, "test")
        self.assertIn("SPEC-02", page.read_text(encoding="utf-8"))


class Levels(unittest.TestCase):
    """Floor / bench tops / walls views: what's hidden under a bench can be picked in the floor view."""

    @classmethod
    def setUpClass(cls):
        cls.lab = model.load(ROOT / "example")
        cls.res = checks.run(cls.lab)

    def test_levels_follow_real_heights(self):
        level = lambda i: layout.level_of(self.lab, self.res, i)
        self.assertEqual(level("FRZ-02"), "floor")  # under BENCH-04.B
        self.assertEqual(level("PED-01"), "floor")
        self.assertEqual(level("BENCH-04.B"), "bench")
        self.assertEqual(level("BENCH-04"), "bench")  # group row, from its parts
        self.assertEqual(level("SPEC-02"), "bench")
        self.assertEqual(level("SMU-03"), "bench")  # top of a stack
        self.assertEqual(level("SHELF-01"), "wall")
        self.assertEqual(level("BOX-01"), "wall")  # on the shelf

    def test_drawing_tags_levels_and_labels_each_level(self):
        svg = layout.drawing(self.lab, self.res, "LAB-A", flag=False)
        self.assertIn('id="obj-FRZ-02" class="lv-floor"', svg)
        self.assertIn('id="obj-SPEC-02" class="lv-bench"', svg)
        frz = svg.split('id="obj-FRZ-02"')[1].split("</g>")[0]
        self.assertIn('class="lb-level"', frz)  # FRZ-02 gets a label of its own in the floor view


    def test_every_member_of_a_stack_is_labelled(self):
        import re

        for min_size in (4.5, 2.5):  # read-only maps, Inkscape layouts
            plan = layout.label_plan(self.lab, self.res, "LAB-A", min_size)
            self.assertTrue(all(plan[i][0] for i in ("SMU-01", "SMU-02", "SMU-03")))
        text = layout.editable(self.lab, self.res)
        for i in ("SMU-01", "SMU-02", "SMU-03"):  # each label inside its own object, so it moves with it
            own = text.split(f'id="obj-{i}"')[1].split("</g>")[0]
            self.assertRegex(own, rf">{i}</text>")
        own = text.split('id="obj-SMU-02"')[1].split("</g>")[0]
        self.assertIn(f'fill-opacity="{layout.STACK_FILL}"', own)  # faint, so the labels below show through,
        self.assertGreater(layout.STACK_FILL, 0)  # but not empty: Inkscape only picks shapes with some fill

    def test_sockets_layer(self):
        svg = layout.drawing(self.lab, self.res, "LAB-A", flag=False)
        layer = svg.split('<g class="svc-layer">')[1]
        out1 = layer.split('id="svc-OUT-01"')[1].split("</g>")[0]
        self.assertIn(">+2</text>", out1)  # 4 plugs for 2 sockets
        self.assertIn('fill="#f97066"', out1)
        self.assertIn('id="svc-NET-01"', layer)  # ports and taps too
        self.assertIn('data-s="OUT-07" data-e="STRIP-05"', layer)  # a strip's feed
        self.assertEqual(layer.count('data-s="OUT-01"'), 4)  # a line per device plugged in
        self.assertNotIn("svc-OUT-08", layer)  # LAB-B's


if __name__ == "__main__":
    unittest.main()
