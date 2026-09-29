"""Run from the Lab_Map folder:  python -m unittest discover -s tests -t ."""
import datetime as dt
import tempfile
import unittest
from pathlib import Path

from labmap import checks, model

ROOT = Path(__file__).resolve().parent.parent

EXAMPLE = {  # example/README.md: the fourteen deliberate problems
    ("clear-zone", ("EYE-01", "CART-02")),
    ("headroom", ("UVO-01", "SHELF-01")),
    ("overlap", ("BAL-01", "VORT-01")),
    ("under-fit", ("FRG-01", "BENCH-02")),
    ("outside-room", ("N2G-01",)),
    ("sockets", ("OUT-01",)),
    ("strip-chain", ("STRIP-03", "STRIP-02")),
    ("circuit-load", ("DB2-C10",)),
    ("critical-shared", ("FRZ-02", "DB2-C07")),
    ("heat", ("LAB-B",)),
    ("cable-reach", ("PC-01", "SPEC-01")),
    ("sprinkler", ("CAB-01", "LAB-A")),
    ("utility", ("SUN-01", "EXH-01")),
    ("socket-load", ("OUT-06",)),
    ("document-unapproved", ("RA-022",)),  # the nine deliberate warnings
    ("spare-out", ("I-0036",)),
    ("spare-low", ("I-0031",)),
    ("stock-stale", ("I-0031",)),
    ("keep-apart-near", ("VAC-01", "BAL-01")),
    ("keep-apart-near", ("LED-01", "DARK-01")),
    ("door-fit", ("GB-01", "DOOR-02")),
    ("sash", ("HP-02", "HOOD-01")),
    ("left-behind", ("I-0051", "OVEN-01")),
}


def P(id, mount="floor", parent=None, **kw):
    return dict(id=id, room="R", mount=mount, parent=parent, category=kw.pop("category", "bench"), **kw)


def lab_from(placeables, folder=ROOT, w=400, d=300, ceiling=None, settings=None, room=None, **sheets):
    rows = {"rooms": [{"id": "R", "ceiling": ceiling, **(room or {})}], "placeables": placeables, **sheets}
    return model.build(folder, rows, room_polys={"R": [(0, 0), (w, 0), (w, d), (0, d)]}, settings=settings)


def model_geo(lab):
    from labmap import geometry as G

    return {i: g for i, g in G.place_all(lab)[0].items() if g and g.poly}


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


class BeforeMeasuring(unittest.TestCase):
    """Doors, fit margin, sprinklers, services needed, keep-apart, socket ratings, door fit."""

    def test_nothing_is_kept_clear_beside_a_hinge(self):
        """Cupboards stand in rows and in corners; a door opening to 90 degrees needs only the swing in front."""
        fridge = dict(x=5, y=100, w=60, d=60, h=180, category="fridge")  # 5 cm from the left wall, facing S
        self.assertEqual(found(lab_from([P("F", door="left", **fridge)])), set())
        beside = found(lab_from([P("F", door="left", **fridge),
                                 P("X", x=0, y=100, w=5, d=60, h=180, category="cabinet")]))
        self.assertEqual(beside, set())

    def test_but_a_clearance_you_measured_is_a_problem(self):
        """clear_left is a measurement, not a nicety: a door that has to open further back is said so explicitly."""
        fridge = dict(x=5, y=100, w=60, d=60, h=180, category="fridge", clear_left=20)
        self.assertIn(("wall-clearance", ("F",)), found(lab_from([P("F", door="left", **fridge)])))

    def test_the_swing_in_front_of_a_door_is_a_problem(self):
        fridge = dict(x=5, y=100, w=60, d=60, h=180, category="fridge")
        f = found(lab_from([P("F", door="right", **fridge), P("X", x=30, y=200, w=20, d=20, h=50, category="instrument")]))
        self.assertIn(("clear-zone", ("F", "X")), f)  # standing in the door's swing (60 cm in front)

    def test_fit_margin(self):
        def under(free):
            return found(lab_from([P("T", x=0, y=0, w=100, d=60, h=90, free_under=free, category="table"),
                                   P("F", "under", "T", category="fridge", x=10, y=0, w=50, d=50, h=85)]))
        self.assertIn(("under-fit", ("F", "T")), under(86))  # 1 cm to spare: less than the 2 cm margin
        self.assertNotIn(("under-fit", ("F", "T")), under(87))
        self.assertIn(("headroom", ("C", "R")), found(lab_from([P("C", x=0, y=100, w=80, d=50, h=249, category="cabinet")],
                                                                  ceiling=250)))
        self.assertEqual(found(lab_from([P("COL", x=0, y=100, w=30, d=30, h=250, category="structure")], ceiling=250)),
                         set())  # built to the ceiling

    def test_sprinklers(self):
        rows = [P("TALL", x=0, y=100, w=80, d=50, h=220, category="cabinet"),
                P("HOOD", x=100, y=0, w=150, d=90, h=240, category="fume-hood", fixed="yes")]
        self.assertEqual({x for x in found(lab_from(rows, ceiling=260, room={"sprinklers": "yes"})) if x[0] == "sprinkler"},
                         {("sprinkler", ("TALL", "R"))})
        self.assertEqual(found(lab_from(rows, ceiling=260)), set())  # no sprinklers, no limit

    def test_services_needed(self):
        rows = [P("GC", x=0, y=0, w=60, d=50, h=50, category="instrument"),
                P("CYL", x=380, y=0, w=20, d=20, h=150, category="gas-cylinder")]
        taps = [dict(id="T-HE", type="gas", room="R", x=350, y=10, z=100, medium="He"),
                dict(id="T-N2", type="gas", room="R", x=100, y=10, z=100, medium="N2")]
        def run(needs, links=()):
            return found(lab_from(rows, equipment=[dict(id="GC", needs=needs)], services=taps, links=list(links)))
        self.assertEqual(run("gas:N2"), set())  # 1.5 m away
        self.assertIn(("utility", ("GC", "T-HE")), run("gas:He"))  # 4.5 m away: too far
        self.assertEqual(run("gas:He", [dict(**{"from": "CYL", "to": "GC", "type": "gas-line"})]), set())  # a line to it
        self.assertIn(("utility", ("GC",)), run("drain"))  # none in the room
        lab = lab_from(rows, equipment=[dict(id="GC", needs="steam")])
        self.assertTrue(any("needs 'steam'" in i.message for i in lab.issues))

    def test_keep_apart(self):
        rules = [dict(tag="vibrates", away_from="vibration-sensitive", distance=100, level="warning"),
                 dict(tag="flammable", away_from="oxidiser", distance=300, level="problem")]
        rows = [P("PUMP", x=0, y=0, w=40, d=30, h=35, category="instrument", tags="Vibrates"),
                P("BAL", x=120, y=0, w=35, d=45, h=35, category="instrument", tags="vibration-sensitive"),
                P("FL", x=0, y=200, w=60, d=50, h=100, category="cabinet", tags="flammable"),
                P("OX", x=300, y=200, w=60, d=50, h=100, category="cabinet", tags="oxidiser")]
        f = found(lab_from(rows, keep_apart=rules))
        self.assertIn(("keep-apart", ("FL", "OX")), f)  # 240 cm apart, 300 needed
        self.assertIn(("keep-apart-near", ("PUMP", "BAL")), f)  # 80 cm apart, 100 suggested (tags ignore case)
        self.assertEqual(checks.RULES["keep-apart-near"][2], "warning")

    def test_socket_and_strip_ratings(self):
        rows = [P("B", x=0, y=0, w=200, d=60, h=90),
                P("K1", "on", "B", category="instrument", x=0, y=0, w=40, d=40, h=40),
                P("K2", "on", "B", category="instrument", x=50, y=0, w=40, d=40, h=40)]
        eq = [dict(id="K1", plugs=1, watts_typ=2000, outlet="S1"), dict(id="K2", plugs=1, watts_typ=1500, outlet="S1")]
        svc = [dict(id="W1", type="outlet", room="R", x=0, y=0, circuit="C1", sockets=2, rating_a=16),
               dict(id="S1", type="strip", room="R", x=10, y=10, fed_by="W1", sockets=4, rating_a=13)]
        res = checks.run(lab_from(rows, equipment=eq, services=svc, circuits=[dict(id="C1", rating_a=32, volts=230)]))
        f = {(x.rule, x.ids) for x in res.findings}
        self.assertIn(("socket-load", ("S1",)), f)  # 3500 W on a 13 A strip (2990 W)
        self.assertEqual(res.socket_load["W1"], 3500)  # the wall socket carries the strip's load too
        self.assertNotIn(("socket-load", ("W1",)), f)  # 16 A × 230 V = 3680 W: enough

    def test_inside_a_fume_hood(self):
        from labmap import metrics

        hood = P("H", x=100, y=0, w=150, d=90, h=240, category="fume-hood", fixed="yes",
                 inner_w=130, inner_d=60, inner_h=100, inner_z=90)
        rows = [hood,
                P("OK", "in", "H", category="instrument", x=10, y=5, w=30, d=30, h=40),
                P("TALL", "in", "H", category="instrument", x=50, y=5, w=20, d=20, h=99),
                P("FRONT", "in", "H", category="instrument", x=80, y=30, w=20, d=25, h=10),
                P("OUT", "in", "H", category="instrument", x=120, y=5, w=20, d=20, h=10),
                P("DRAWER", "in", "B", category="drawer", w=40, d=50, h=10),
                P("B", x=0, y=200, w=100, d=60, h=90)]
        res = checks.run(lab_from(rows))
        f = {(x.rule, x.ids) for x in res.findings}
        g = res.geo["OK"]  # inside: 10 cm in from the working space's left (hood x + 10), 5 cm from its back (90 - 60 + 5)
        self.assertEqual((round(min(p[0] for p in g.poly)), round(min(p[1] for p in g.poly)), g.z[0]), (120, 35, 90))
        self.assertIn(("in-fit", ("TALL", "H")), f)  # 99 + 2 cm margin > 100
        self.assertIn(("sash", ("FRONT", "H")), f)  # its front edge is 5 cm behind the sash
        self.assertIn(("off-parent", ("OUT", "H")), f)  # 120 + 20 > 130 wide
        self.assertNotIn("OK", {i for _, ids in f for i in ids})
        self.assertIsNone(res.geo.get("DRAWER"))  # an ordinary drawer still has no position
        e = metrics.enclosures(res)[0]
        self.assertEqual((e["id"], e["items"]), ("H", 4))
        self.assertGreater(e["kept"], 0)  # the strip behind the sash
        lab = lab_from([dict(hood, inner_w=None), P("X", "in", "H", category="instrument", x=0, y=0, w=10, d=10, h=10)])
        self.assertTrue(any("has no inner_w and inner_d" in i.message for i in lab.issues))

    def test_door_fit(self):
        rows = [P("DOOR", x=100, y=295, faces="N", w=90, d=5, h=210, category="door"),
                P("BIG", w=150, d=95, h=190, category="instrument"), P("OK", w=150, d=85, h=190, category="instrument")]
        eq = [dict(id="BIG", plan="new"), dict(id="OK", plan="new")]
        f = found(lab_from(rows, equipment=eq))
        self.assertIn(("door-fit", ("BIG", "DOOR")), f)
        self.assertNotIn(("door-fit", ("OK", "DOOR")), f)  # 85 + 2 cm margin fits a 90 cm door


class LastSeen(unittest.TestCase):
    """When a count was last verified: the item's checked date, its container's, or the day the workbook was saved."""

    def lab(self, items, saved=None):
        lab = lab_from([P("B", x=0, y=0, w=100, d=60, h=90),
                        P("B.D1", "in", "B", category="drawer", w=40, d=50, h=10, checked="2026-03-01")],
                       items=items)
        lab.saved = saved
        return lab

    def test_where_the_date_comes_from(self):
        items = [dict(id="I-1", name="own", container="B.D1", checked="2026-08-01"),
                 dict(id="I-2", name="from the drawer", container="B.D1"),
                 dict(id="I-3", name="no dates at all", container="B")]
        lab = self.lab(items, saved=dt.date(2026, 9, 1))
        self.assertEqual(model.last_seen(lab, lab.items["I-1"]), (dt.date(2026, 8, 1), "counted"))
        self.assertEqual(model.last_seen(lab, lab.items["I-2"]), (dt.date(2026, 3, 1), "container checked"))
        self.assertEqual(model.last_seen(lab, lab.items["I-3"]), (dt.date(2026, 9, 1), "spreadsheet saved"))
        self.assertEqual(model.load(ROOT / "example").saved, dt.date.fromtimestamp(
            (ROOT / "example" / "lab-data.xlsx").stat().st_mtime))

    def test_required_spares_go_stale(self):
        items = [dict(id="I-1", name="old spare", container="B.D1", checked="2026-01-01", min_qty=2, qty=5),
                 dict(id="I-2", name="fresh spare", container="B.D1", checked="2026-08-01", min_qty=2, qty=5),
                 dict(id="I-3", name="not a tracked spare", container="B.D1", checked="2026-01-01", qty=5)]
        found = {(f.rule, f.ids) for f in checks.run(self.lab(items), today=dt.date(2026, 9, 1)).findings}
        self.assertEqual({x for x in found if x[0] == "stock-stale"}, {("stock-stale", ("I-1",))})
        later = checks.run(self.lab(items, saved=dt.date(2026, 9, 1)), today=dt.date(2026, 9, 1))
        self.assertEqual({x.ids for x in later.findings if x.rule == "stock-stale"}, {("I-1",)})


class Decommissioning(unittest.TestCase):
    def test_gone_but_not_forgotten(self):
        from labmap import metrics

        rows = [P("B", x=0, y=0, w=200, d=60, h=90, decommissioned="2026-06-30"),
                P("B.D1", "in", "B", category="drawer", w=40, d=50, h=10),
                P("X", "on", "B", category="instrument", x=10, y=10, w=30, d=30, h=20),
                P("PED", x=250, y=0, w=40, d=50, h=70, category="pedestal"),
                P("OLD", x=100, y=200, w=50, d=50, h=50, category="instrument")]
        lab = lab_from(rows, equipment=[dict(id="OLD", plan="decommissioned"), dict(id="PED", plan="dispose")],
                       items=[dict(id="I-1", name="tape", container="B.D1"), dict(id="I-2", name="fuse", container="PED", spare_for="OLD")],
                       documents=[dict(id="RA-1", type="risk-assessment", applies_to="OLD", status="approved")],
                       services=[dict(id="S1", type="outlet", room="R", parent="B", x=0, y=0)])
        self.assertEqual(lab.gone, {"B", "B.D1", "OLD"})  # the drawer goes with its bench
        self.assertEqual(lab.issues, [])  # still on the sheet: nothing points at a missing ID
        res = checks.run(lab)
        self.assertIsNone(res.geo["B"])  # off the maps and out of the checks
        self.assertIsNone(res.geo["X"])  # what stood on it is waiting for a new place
        f = {(x.rule, x.ids) for x in res.findings if x.rule == "left-behind"}
        self.assertEqual(f, {("left-behind", ("X", "B")), ("left-behind", ("I-1", "B")), ("left-behind", ("S1", "B")),
                             ("left-behind", ("I-2", "OLD")), ("left-behind", ("RA-1", "OLD"))})
        self.assertEqual(checks.RULES["left-behind"][2], "warning")
        plan = {d["id"]: (d["status"], len(d["todo"])) for d in metrics.decommissioning(res)}
        self.assertEqual(plan, {"PED": ("to go", 1), "B": ("gone since 2026-06-30", 3), "OLD": ("gone", 2)})  # PED: empty it first
        self.assertNotIn("B", [u[0] for u in metrics.unplaced(res)])


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


class Waiting(unittest.TestCase):
    """What the report and the layout call 'not placed yet': anything with no x and y, wherever it was going."""

    def waiting(self):
        from labmap import metrics

        rows = [P("BENCH", x=0, y=0, w=200, d=60, h=90, free_under=85),
                P("HOOD", "on", "BENCH", category="fume-hood", w=150, d=60, h=120,
                  inner_w=148, inner_d=58, inner_h=80),          # on a bench, nowhere on it yet
                P("FURN", "in", "HOOD", category="oven", w=90, d=35, h=40),  # in the hood, nowhere in it yet
                P("DRW", "in", "BENCH", category="drawer", w=40, d=50, h=15)]  # contents: never has a position
        return {i for i, _, _ in metrics.unplaced(checks.run(lab_from(rows)))}

    def test_things_waiting_on_or_in_something_count(self):
        self.assertEqual(self.waiting(), {"HOOD", "FURN"})


class AcrossAJoin(unittest.TestCase):
    """A bench or a sill made of parts is one surface: something can stand across the join between two of them."""

    def off_parent(self, x, w=40, **second):
        rows = [P("RUN", x=0, y=0, shape="group"),
                P("RUN.A", "part", "RUN", x=0, y=0, w=100, d=60, h=90, free_under=85),
                P("RUN.B", "part", "RUN", x=100, y=0, w=100, d=60, free_under=85, **{"h": 90, **second}),
                P("BOX", "on", "RUN.A", category="container", x=x, y=10, w=w, d=30, h=20)]
        return {f for f in found(lab_from(rows)) if f[0] == "off-parent"}

    def test_a_box_wholly_on_its_own_part(self):
        self.assertEqual(self.off_parent(10), set())

    def test_a_box_across_the_join(self):
        self.assertEqual(self.off_parent(80), set())  # 80..120, over both parts of the run

    def test_a_box_off_the_end_of_the_run(self):
        self.assertEqual(self.off_parent(180), {("off-parent", ("BOX", "RUN.A"))})

    def test_the_next_part_has_to_be_the_same_surface(self):
        """A lower part of the same bench holds nothing up: the box is over thin air past the join."""
        self.assertEqual(self.off_parent(80, h=75), {("off-parent", ("BOX", "RUN.A"))})


class TuckedUnder(unittest.TestCase):
    """A pedestal parked under a bench needs room to open its drawers, not room to stand: the bench top above it
    isn't in its way. Two benches side by side, and a pedestal under the join between them."""

    def lab(self, benches=("A", "B"), free_under=85, **ped):
        bench = dict(w=150, d=60, h=90, free_under=free_under)
        rows = [P(f"BENCH-{n}", x=150 * k, y=0, **bench) for k, n in enumerate(benches)]
        rows.append(P("PED", category="pedestal", w=45, d=50, h=80, clear_front=40,
                      **{"x": 130, "y": 5, **ped}))
        return lab_from(rows)

    def zone(self, lab):
        return [f.ids for f in checks.run(lab).findings if f.rule == "clear-zone"]

    def test_the_bench_over_it_is_not_in_its_way(self):
        self.assertEqual(self.zone(self.lab()), [])

    def test_cover_can_come_from_two_benches_at_once(self):
        """Without the second bench the pedestal is half out in the open, so it needs standing room again."""
        self.assertEqual(self.zone(self.lab(benches=("A",))), [("PED", "BENCH-A")])

    def test_a_bench_it_does_not_fit_under_is_in_its_way(self):
        self.assertIn(("PED", "BENCH-A"), self.zone(self.lab(free_under=70)))

    def test_headroom_is_the_lowest_thing_over_it(self):
        lab = self.lab()
        geo = model_geo(lab)
        self.assertEqual(checks.tucked_under(lab.placeables, geo, list(geo)), {"PED": 85})


if __name__ == "__main__":
    unittest.main()
