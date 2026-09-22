"""Run from the Lab_Map folder:  python -m unittest discover -s tests -t ."""
import tempfile
import unittest
from pathlib import Path

from labmap import checks, model

ROOT = Path(__file__).resolve().parent.parent

EXAMPLE = {  # example/README.md: the eleven deliberate problems
    ("clear-zone", ("EYE-01", "CART-02")),
    ("headroom", ("CEN-01", "SHELF-01")),
    ("overlap", ("BAL-01", "VORT-01")),
    ("under-fit", ("FRG-01", "BENCH-02")),
    ("outside-room", ("N2G-01",)),
    ("sockets", ("OUT-01",)),
    ("strip-chain", ("STRIP-03", "STRIP-02")),
    ("circuit-load", ("DB2-C10",)),
    ("critical-shared", ("FRZ-02", "DB2-C07")),
    ("heat", ("LAB-B",)),
    ("cable-reach", ("PC-01", "SPEC-01")),
    ("document-unapproved", ("COSHH-022",)),  # the three deliberate warnings
    ("spare-out", ("I-0036",)),
    ("spare-low", ("I-0031",)),
}


def P(id, mount="floor", parent=None, **kw):
    return dict(id=id, room="R", mount=mount, parent=parent, category=kw.pop("category", "bench"), **kw)


def lab_from(placeables, folder=ROOT, w=400, d=300, ceiling=None, settings=None):
    rows = {"rooms": [{"id": "R", "ceiling": ceiling}], "placeables": placeables}
    return model.build(folder, rows, room_polys={"R": [(0, 0), (w, 0), (w, d), (0, d)]}, settings=settings)


def found(lab):
    return {(f.rule, f.ids) for f in checks.run(lab).findings}


class Example(unittest.TestCase):
    def test_exactly_the_deliberate_problems(self):
        self.assertEqual(found(model.load(ROOT / "example")), EXAMPLE)


class Geometry(unittest.TestCase):
    def test_child_of_rotated_parent(self):
        # bench along the right-hand wall faces W; box 20 cm from its left end, 10 cm from its back
        lab = lab_from([P("B", x=340, y=50, faces="W", w=200, d=60, h=90),
                        P("X", "on", "B", category="container", x=20, y=10, w=30, d=20, h=10)])
        poly = checks.run(lab).geo["X"].poly
        box = tuple(round(f(p[k] for p in poly)) for k in (0, 1) for f in (min, max))
        self.assertEqual(box, (370, 390, 70, 100))

    def test_rotated_group_bbox(self):
        lab = lab_from([P("G", x=100, y=50, faces="N", shape="group"),
                        P("G.A", "part", "G", x=0, y=0, w=200, d=60, h=90),
                        P("G.B", "part", "G", x=0, y=60, faces="E", w=100, d=60, h=90)])
        geo = checks.run(lab).geo
        pts = [p for i in ("G.A", "G.B") for p in geo[i].poly]
        self.assertEqual((round(min(p[0] for p in pts)), round(min(p[1] for p in pts))), (100, 50))

    def test_concave_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "shapes").mkdir()
            (Path(tmp) / "shapes" / "u.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 60">'
                '<path id="footprint" d="m 0,0 h 100 v 60 h -30 v -40 h -40 v 40 h -30 z"/></svg>')
            lab = lab_from([P("U", x=50, y=50, shape="@u", w=100, d=60, h=90),
                            P("IN", x=90, y=80, w=20, d=20, h=50, category="instrument"),  # in the U's notch
                            P("HIT", x=55, y=55, w=10, d=10, h=50, category="instrument")], folder=tmp)
            f = found(lab)
        self.assertNotIn(("overlap", ("IN", "U")), f)
        self.assertIn(("overlap", ("HIT", "U")), f)

    def test_off_parent_and_wall_clearance(self):
        lab = lab_from([P("B", x=0, y=0, w=100, d=60, h=90, clear_back=10),
                        P("X", "on", "B", category="instrument", x=90, y=10, w=30, d=30, h=20)])
        f = found(lab)
        self.assertIn(("wall-clearance", ("B",)), f)
        self.assertIn(("off-parent", ("X", "B")), f)


class Walkways(unittest.TestCase):
    def layout(self, gap, settings=None):
        return lab_from([P("DOOR", x=300, y=295, faces="N", w=90, d=5, h=210, clear_front=90, category="door"),
                         P("BENCH", x=0, y=0, w=300, d=60, h=90, clear_front=90),
                         P("ROW", x=gap, y=160, w=400 - gap, d=40, h=200, category="cabinet")], settings=settings)

    def test_narrow_gap_blocks(self):
        self.assertIn(("walkway", ("BENCH",)), found(self.layout(40)))

    def test_wide_gap_passes(self):
        self.assertNotIn(("walkway", ("BENCH",)), found(self.layout(80)))

    def test_width_comes_from_settings(self):
        self.assertNotIn(("walkway", ("BENCH",)), found(self.layout(40, {"walkway_width": 30})))

    def test_unknown_setting_is_flagged(self):
        lab = self.layout(80, {"walkway_widht": 30})
        self.assertTrue(any("walkway_widht" in f.message for f in lab.issues))


class WindowsStacksCeilings(unittest.TestCase):
    def test_window_cover_is_a_warning(self):
        f = found(lab_from([P("WIN", "wall", category="window", x=100, y=0, z=100, w=150, d=10, h=120),
                            P("CAB", x=120, y=0, w=80, d=50, h=200, category="cabinet"),
                            P("LOW", x=0, y=0, w=90, d=60, h=90)]))  # under the sill: fine
        self.assertEqual({x for x in f if x[0] in ("window", "overlap")}, {("window", ("CAB", "WIN"))})
        self.assertEqual(checks.RULES["window"][2], "warning")

    def stack(self, stackable=None):
        return found(lab_from([P("T", x=0, y=0, w=100, d=60, h=90, category="table"),
                               P("S1", "on", "T", category="instrument", x=10, y=10, w=21, d=45, h=9, stackable=stackable),
                               P("S2", "on", "S1", category="instrument", x=0, y=0, w=21, d=45, h=9)]))

    def test_stacking(self):
        self.assertIn(("not-stackable", ("S2", "S1")), self.stack())
        self.assertEqual(self.stack("yes"), set())

    def test_ceiling(self):
        f = found(lab_from([P("CAB", x=0, y=100, w=80, d=50, h=240, category="cabinet", clear_top=20)], ceiling=250))
        self.assertIn(("headroom", ("CAB", "R")), f)


class Documents(unittest.TestCase):
    def test_expiry_and_approval(self):
        import datetime as dt

        docs = [dict(id="OLD", type="coshh", applies_to="B", status="approved", expires="2026-01-01"),
                dict(id="SOON", type="calibration", applies_to="B", status="approved", expires="2026-10-01"),
                dict(id="FINE", type="coshh", applies_to="B; R", status="approved", expires="2030-01-01"),
                dict(id="WAIT", type="risk-assessment", applies_to="B", status="pending"),
                dict(id="LOST", type="coshh", applies_to="NOPE", status="approved")]
        lab = model.build(ROOT, {"rooms": [{"id": "R"}], "placeables": [P("B", x=0, y=0, w=100, d=60, h=90)],
                                 "documents": docs}, room_polys={"R": [(0, 0), (400, 0), (400, 300), (0, 300)]})
        f = {(x.rule, x.ids) for x in checks.run(lab, today=dt.date(2026, 9, 21)).findings}
        self.assertLessEqual({("document-expired", ("OLD",)), ("document-expiring", ("SOON",)),
                              ("document-unapproved", ("WAIT",))}, f)
        self.assertFalse(any(ids == ("FINE",) for _, ids in f))
        self.assertTrue(any("NOPE" in x.message for x in lab.issues))


class Spares(unittest.TestCase):
    def test_stock_and_ordering(self):
        items = [dict(id="I-1", name="liners", container="B", qty=0, min_qty=5, spare_for="B"),
                 dict(id="I-2", name="cartridges", container="B", qty="2 boxes", min_qty=4, spare_for="b"),
                 dict(id="I-3", name="filters", elsewhere="Main stores", qty="~20", min_qty=3, spare_for="B"),
                 dict(id="I-4", name="fuses", container="B", min_qty=1),  # blank qty counts as none
                 dict(id="I-5", name="gloves", container="B", rs_part="123-4567",
                      buy_link="https://www.example.com/x"),  # not a tracked spare
                 dict(id="I-6", name="lost", spare_for="NOPE")]
        lab = model.build(ROOT, {"rooms": [{"id": "R"}], "placeables": [P("B", x=0, y=0, w=100, d=60, h=90)],
                                 "items": items}, room_polys={"R": [(0, 0), (400, 0), (400, 300), (0, 300)]})
        f = {(x.rule, x.ids) for x in checks.run(lab).findings if x.rule.startswith("spare")}
        self.assertEqual(f, {("spare-out", ("I-1",)), ("spare-low", ("I-2",)), ("spare-out", ("I-4",))})
        self.assertEqual(lab.items["I-2"]["spare_for"], ["B"])
        messages = " | ".join(x.message for x in lab.issues)
        self.assertIn("I-6: no container, and nothing under elsewhere", messages)
        self.assertIn("spare_for NOPE isn't on the placeables sheet", messages)
        self.assertEqual(model.order_links(lab.items["I-5"]),
                         [("RS 123-4567", "https://uk.rs-online.com/web/c/?searchTerm=1234567"),
                          ("example.com", "https://www.example.com/x")])


class Data(unittest.TestCase):
    def test_problems_in_rows(self):
        lab = lab_from([P("bench-01", x=0, y=0, w=100, d=60, h=90),
                        P("X", "on", "NOPE", category="instrument", x=0, y=0, w=10, d=10, h=10),
                        P("S", "wall", category="shelf", x=0, y=0, w=50, d=20, h=2),
                        P("Y", x=10, w=10, d=10, h=10)])
        messages = " | ".join(f.message for f in lab.issues)
        self.assertIn("BENCH-01", lab.placeables)  # IDs are normalised to upper case
        self.assertIn("parent NOPE isn't on the placeables sheet", messages)
        self.assertIn("S is wall-mounted but has no z", messages)
        self.assertIn("Y has only one of x and y", messages)


if __name__ == "__main__":
    unittest.main()
