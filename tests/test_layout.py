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
        layout.write_layouts(self.lab, checks.run(self.lab))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def edit(self, room, changes):
        """changes: {id: function(old transform) -> new transform}, like dragging in Inkscape."""
        path = layout.layout_path(self.tmp, room)
        tree = ET.parse(path)
        for g in tree.iter(f"{SVG}g"):
            key = (g.get("id") or "")[len(layout.PREFIX):]
            if (g.get("id") or "").startswith(layout.PREFIX) and key in changes:
                g.set("transform", changes.pop(key)(g.get("transform") or ""))
        self.assertEqual(changes, {}, "every edited object should be in the layout")
        tree.write(path)

    def pull(self, room):
        lab = model.load(self.tmp)
        return layout.positions(lab, room, layout.read_matrices(layout.layout_path(self.tmp, room)))

    def test_every_object_drawn_once(self):
        import re

        for room in self.lab.rooms:
            ids = re.findall(r'id="obj-([^"]+)"', layout.layout_path(self.tmp, room).read_text(encoding="utf-8"))
            self.assertEqual(len(ids), len(set(ids)), room)
            self.assertIn("SPEC-02" if room == "LAB-A" else "HPLC-01", ids)

    def test_unchanged_layout_has_nothing_to_pull(self):
        for room in self.lab.rooms:
            self.assertEqual(self.pull(room)[0], {})

    def along(self, i):
        """i and everything on or under it: what dragging a box around it in Inkscape selects."""
        out, todo = [i], [i]
        while todo:
            for c in self.lab.children.get(todo.pop(), []):
                if self.lab.placeables[c].get("mount") in ("on", "under", "part"):
                    out.append(c)
                    todo.append(c)
        return out

    def centre(self, i):
        from labmap import geometry as G

        return G.centroid(checks.run(self.lab).geo[i].poly)

    def test_moves_come_back_as_data(self):
        moves = {k: (lambda t: "translate(-50,0) " + t) for k in self.along("BENCH-02") if k != "BENCH-02.D1"}
        moves = {k: v for k, v in moves.items() if self.lab.placeables[k].get("mount") != "in"}
        moves.update({
            "VORT-01": lambda t: "translate(-50,0) " + t + " rotate(90)",  # carried along, and turned on its bench
            "INC-01": lambda t: "translate(400,100)",                # drag the incubator in from the staging area
            "CART-01": lambda t: "translate(2000,50)",               # drag the trolley out to the staging area
            "BENCH-01": lambda t: "translate(0,40) " + t,            # the sink bench is fixed: ignored
        })
        self.edit("LAB-A", moves)
        updates, notes = self.pull("LAB-A")
        self.assertEqual(updates["BENCH-02"], (595, 180, "W"))
        self.assertEqual(updates["INC-01"], (400, 100, None))
        self.assertEqual(updates["CART-01"], (None, None, None))
        self.assertEqual(updates["VORT-01"][2], "W")
        self.assertNotIn("BENCH-01", updates)
        self.assertTrue(any("BENCH-01 is fixed" in n for n in notes))
        self.assertEqual(set(updates), {"BENCH-02", "VORT-01", "INC-01", "CART-01"})  # the rest came along unchanged

    def test_bench_moved_alone_leaves_its_things(self):
        self.edit("LAB-A", {"BENCH-02": lambda t: "translate(-30,0) " + t})
        updates, _ = self.pull("LAB-A")
        self.assertEqual(updates["BENCH-02"][:2], (615, 180))
        self.assertIn("BAL-01", updates)  # stayed where it was drawn: further along its bench now
        self.assertEqual(len(updates["BAL-01"]), 3)  # still on BENCH-02

    def test_dropped_on_another_bench(self):
        (sx, sy), (bx, by) = self.centre("SPEC-02"), self.centre("TBL-01")
        self.edit("LAB-A", {"SPEC-02": lambda t: f"translate({bx - sx:.1f},{by - sy:.1f}) " + t})
        updates, _ = self.pull("LAB-A")
        self.assertEqual(updates["SPEC-02"][3:], ("TBL-01", "on"))
        self.assertEqual(set(updates), {"SPEC-02"})
        lab = model.load(self.tmp, updates)  # what check --layout does: try it without writing
        self.assertEqual(lab.placeables["SPEC-02"]["parent"], "TBL-01")
        res = checks.run(lab)
        g = res.geo["SPEC-02"]
        self.assertAlmostEqual(g.z[0], 90)  # on the table top now
        model.write_positions(self.tmp / "lab-data.xlsx", updates, self.tmp / "build" / "backups")
        lab = model.load(self.tmp)
        self.assertEqual((lab.placeables["SPEC-02"]["parent"], lab.issues), ("TBL-01", []))
        layout.write_layouts(lab, checks.run(lab))
        self.assertEqual(self.pull("LAB-A")[0], {})

    def test_out_from_under_a_bench(self):
        self.edit("LAB-A", {"FRZ-02": lambda t: "translate(0,200) " + t})
        updates, notes = self.pull("LAB-A")
        self.assertEqual(updates["FRZ-02"][3:], (None, "floor"))
        self.assertTrue(any("FRZ-02 isn't under anything" in n for n in notes))

    def test_group_moves_as_one(self):
        self.edit("LAB-B", {k: (lambda t: "translate(-20,0) " + t) for k in self.along("BENCH-11")
                            if self.lab.placeables[k].get("mount") != "part"})
        updates, _ = self.pull("LAB-B")
        self.assertEqual(updates, {"BENCH-11": (440, 0, None)})

    def test_written_to_workbook_and_layout_protected(self):
        self.edit("LAB-A", {"CART-01": lambda t: "translate(-30,0) " + t})
        updates, _ = self.pull("LAB-A")
        lab = model.load(self.tmp)
        result = layout.write_layouts(lab, checks.run(lab))  # moves not pulled yet: must not overwrite
        self.assertIn("kept", dict((r, s) for r, _, s in result)["LAB-A"])
        backup, missing = model.write_positions(self.tmp / "lab-data.xlsx", updates, self.tmp / "build" / "backups")
        self.assertTrue(backup.exists())
        self.assertEqual(missing, [])
        lab = model.load(self.tmp)
        self.assertEqual((lab.placeables["CART-01"]["x"], lab.placeables["CART-01"]["y"]), (410, 300))
        self.assertEqual(lab.issues, [])
        self.assertEqual(self.pull("LAB-A")[0], {})  # layout and workbook agree again


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
        text = layout.editable(self.lab, self.res, "LAB-A")
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
