"""Reading a position off a corner you can measure: `python -m labmap xy`."""
import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from labmap import __main__ as cli
from labmap import geometry as G
from labmap import model

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "example"


class Corners(unittest.TestCase):
    def setUp(self):
        self.lab = model.load(EXAMPLE)
        self.geo = G.place_all(self.lab)[0]

    def test_every_corner_gives_back_the_row(self):
        """Ask for the x, y that puts a corner where it already is: it must be the x, y the row already has."""
        for i, r in self.lab.placeables.items():
            g = self.geo.get(i)
            if g is None or g.T is None or r.get("shape") == "group":
                continue
            for corner, at in G.corner_points(g).items():
                got = G.xy_for(self.lab, self.geo, i, corner, at)
                self.assertIsNotNone(got, f"{i} {corner}")
                self.assertAlmostEqual(got[0], r["x"], places=3, msg=f"{i} {corner} x")
                self.assertAlmostEqual(got[1], r["y"], places=3, msg=f"{i} {corner} y")

    def test_diagonal_corners_are_not_the_bounding_box(self):
        """The whole point: on a diagonal piece, x, y isn't any of its corners."""
        g = self.geo["BENCH-11.B"]  # part of the chamfer bench in LAB-B, faces SW
        r = self.lab.placeables["BENCH-11.B"]
        corners = G.corner_points(g)
        self.assertEqual(len(corners), 4)
        parent = self.geo["BENCH-11"]
        local = [G.rot(-parent.theta, x - parent.origin[0], y - parent.origin[1]) for x, y in corners.values()]
        self.assertFalse(any(abs(u - r["x"]) < 1 and abs(v - r["y"]) < 1 for u, v in local))
        self.assertAlmostEqual(min(u for u, _ in local), r["x"], places=3)  # it is the box around them
        self.assertAlmostEqual(min(v for _, v in local), r["y"], places=3)

    def test_moving_a_corner_moves_the_object_there(self):
        i, at = "BENCH-11.B", (500.0, 120.0)
        x, y = G.xy_for(self.lab, self.geo, i, "front-right", at)
        lab = model.load(EXAMPLE, {"placeables": {i: {"x": round(x, 4), "y": round(y, 4)}}})
        moved = G.place_all(lab)[0][i]
        got = G.corner_points(moved)["front-right"]
        self.assertAlmostEqual(got[0], at[0], places=2)
        self.assertAlmostEqual(got[1], at[1], places=2)


class Command(unittest.TestCase):
    def run_cli(self, *args):
        out = io.StringIO()
        with redirect_stdout(out):
            code = cli.main(["xy", *args, "--folder", str(EXAMPLE)])
        self.assertEqual(code, 0, out.getvalue())
        return out.getvalue()

    def test_reports_corners(self):
        out = self.run_cli("BENCH-11.B")
        self.assertIn("faces SW", out)
        self.assertIn("back-left", out)
        self.assertIn("front-right", out)

    def test_works_out_the_xy(self):
        out = self.run_cli("BENCH-11.B", "500", "120", "--corner", "front-right")
        self.assertIn("type on the placeables sheet", out)
        self.assertIn("it would then sit at", out)

    def test_warns_that_a_group_shifts(self):
        """Pushing a part outside the group's box slides the whole group: say so, and preview the fix."""
        out = self.run_cli("BENCH-11.B", "440", "5")
        self.assertIn("BENCH-11's x, y pin the bounding box", out)
        self.assertIn("setting BENCH-11 x = 397.6, y = 0", out)
        self.assertRegex(out, r"with both of those.*\n\s+back-left\s+440, 5")

    def test_unknown_id(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = cli.main(["xy", "NOPE-99", "--folder", str(EXAMPLE)])
        self.assertEqual(code, 2)
        self.assertIn("No row with id", out.getvalue())


if __name__ == "__main__":
    unittest.main()
