"""The order to move things in on the day: what has to wait for what, and what to do before lifting it."""
import unittest
from pathlib import Path

from labmap import checks, model, sequence

ROOT = Path(__file__).resolve().parent.parent


def lab(rows, **sheets):
    return model.build(ROOT, {"rooms": [{"id": "R", "ceiling": 250}], "placeables": rows, **sheets},
                       room_polys={"R": [(0, 0), (800, 0), (800, 600), (0, 600)]})


def P(id, x=None, y=None, mount="floor", parent=None, **kw):
    return dict(id=id, room="R", mount=mount, parent=parent, x=x, y=y,
                **{"category": "cabinet", "w": 60, "d": 50, "h": 80, **kw})


def steps(before_rows, after_rows, moved, **sheets):
    before, after = checks.run(lab(before_rows, **sheets)), checks.run(lab(after_rows, **sheets))
    moves = {"placeables": {i: {"x": 0} for i in moved}}
    return sequence.plan(before, after, moves)


def order(plan):
    return [(s.round, s.kind, s.id) for s in plan]


class Order(unittest.TestCase):
    def test_moves_that_dont_touch_all_go_in_the_first_round(self):
        plan = steps([P("A", 0, 0), P("B", 200, 0)], [P("A", 0, 300), P("B", 200, 300)], ["A", "B"])
        self.assertEqual(order(plan), [(1, "move", "A"), (1, "move", "B")])

    def test_whatever_is_in_the_way_goes_first(self):
        """C goes where B is, B where A is, A somewhere free: A, then B, then C."""
        before = [P("A", 0, 0), P("B", 200, 0), P("C", 400, 0)]
        after = [P("A", 0, 300), P("B", 0, 0), P("C", 200, 0)]
        self.assertEqual(order(steps(before, after, ["A", "B", "C"])),
                         [(1, "move", "A"), (2, "move", "B"), (3, "move", "C")])

    def test_a_swap_parks_one_of_them(self):
        """A and B want each other's place: neither can go first, so the smaller is parked, then B, then A."""
        before = [P("A", 0, 0, w=50), P("B", 200, 0)]
        after = [P("A", 200, 0, w=50), P("B", 0, 0)]
        plan = steps(before, after, ["A", "B"])
        self.assertEqual(order(plan), [(1, "park", "A"), (2, "move", "B"), (3, "move", "A")])
        self.assertIn("in the way of B", plan[0].notes[0])

    def test_a_swap_doesnt_hold_up_anything_else(self):
        """Parking happens in the first round, alongside moves that have nothing to do with the swap."""
        before = [P("A", 0, 0, w=50), P("B", 200, 0), P("C", 500, 0)]
        after = [P("A", 200, 0, w=50), P("B", 0, 0), P("C", 500, 300)]
        plan = steps(before, after, ["A", "B", "C"])
        self.assertEqual(order(plan), [(1, "move", "C"), (1, "park", "A"), (2, "move", "B"), (3, "move", "A")])
        self.assertIn("bring it back from where it was parked", plan[-1].notes)

    def test_a_ring_of_three_parks_just_one(self):
        before = [P("A", 0, 0, w=50), P("B", 200, 0), P("C", 400, 0)]
        after = [P("A", 200, 0, w=50), P("B", 400, 0), P("C", 0, 0)]
        plan = steps(before, after, ["A", "B", "C"])
        self.assertEqual([s.kind for s in plan].count("park"), 1)
        self.assertEqual(len([s for s in plan if s.kind == "move"]), 3)

    def test_the_bench_goes_in_before_what_goes_on_it(self):
        before = [P("BENCH", 0, 0, category="bench", w=200, d=60, h=90), P("SMU", 400, 400, category="power-supply",
                                                                          w=40, d=40, h=15)]
        after = [P("BENCH", 0, 300, category="bench", w=200, d=60, h=90),
                 P("SMU", 10, 10, mount="on", parent="BENCH", category="power-supply", w=40, d=40, h=15)]
        plan = steps(before, after, ["BENCH", "SMU"])
        self.assertEqual(order(plan), [(1, "move", "BENCH"), (2, "move", "SMU")])
        self.assertEqual(plan[1].after, [("BENCH", "BENCH is in place")])

    def test_what_leaves_a_bench_comes_off_before_the_bench_moves(self):
        before = [P("BENCH", 0, 0, category="bench", w=200, d=60, h=90),
                  P("SMU", 10, 10, mount="on", parent="BENCH", category="power-supply", w=40, d=40, h=15)]
        after = [P("BENCH", 0, 300, category="bench", w=200, d=60, h=90),
                 P("SMU", 500, 500, category="power-supply", w=40, d=40, h=15)]
        self.assertEqual(order(steps(before, after, ["BENCH", "SMU"])), [(1, "move", "SMU"), (2, "move", "BENCH")])

    def test_drawers_going_along_are_not_lifted_on_their_own(self):
        before, after = [P("A", 0, 0)], [P("A", 0, 300)]
        b, a = checks.run(lab(before)), checks.run(lab(after))
        plan = sequence.plan(b, a, {"placeables": {"A": {"x": 0}, "A.D1": {"room": "S"}}})
        self.assertEqual(order(plan), [(1, "move", "A")])


class BeforeYouLift(unittest.TestCase):
    def notes(self, **sheets):
        before = [P("BENCH", 0, 0, category="bench", w=200, d=60, h=90),
                  P("SMU", 10, 10, mount="on", parent="BENCH", category="power-supply", w=40, d=40, h=15),
                  P("PC", 400, 0, category="computer", w=20, d=45, h=45)]
        after = [P("BENCH", 0, 300, category="bench", w=200, d=60, h=90), before[1], before[2]]
        return steps(before, after, ["BENCH"], **sheets)[0].notes

    def test_what_stands_on_it_is_cleared_and_put_back(self):
        self.assertIn("clear it first, and put back after: SMU", self.notes())

    def test_something_that_must_never_lose_power(self):
        notes = self.notes(equipment=[{"id": "BENCH", "critical": "yes"}])
        self.assertTrue(any(n.startswith("must never lose power") for n in notes), notes)

    def test_its_lines_and_cables(self):
        notes = self.notes(equipment=[{"id": "BENCH", "needs": "gas:N2; vacuum; network"}],
                           links=[{"from": "PC", "to": "BENCH", "type": "usb"}])
        self.assertIn("disconnect its gas (N2), vacuum", notes)  # network isn't a line you disconnect
        self.assertIn("unplug the usb to PC", notes)


class OnThePage(unittest.TestCase):
    def test_the_move_list_goes_round_by_round(self):
        from labmap import report

        before = [P("A", 0, 0, w=50), P("B", 200, 0)]
        after = [P("A", 200, 0, w=50), P("B", 0, 0)]
        b, a = checks.run(lab(before)), checks.run(lab(after))
        moves = {"placeables": {"A": {"x": 200}, "B": {"x": 0}}}
        rows = report.move_rows(b, a, moves)
        self.assertEqual([(r[0], r[1].split(" ")[0]) for r in rows], [(1, "Park"), (2, "B"), (3, "A")])
        self.assertIn("2 moves in 3 rounds, with 1 thing parked", report.move_list(b, a, moves))
        import tempfile

        page = report.write_move_list(Path(tempfile.mkdtemp()) / "m.html", b, a, moves).read_text(encoding="utf-8")
        self.assertIn("Round 3 · once round 2 is done", page)
        self.assertLess(page.index("Park A"), page.index("Round 2"))


if __name__ == "__main__":
    unittest.main()
