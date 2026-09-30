"""Several arrangements side by side: options saved beside labs.svg, checked, modelled, compared and pulled."""
import io
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from contextlib import redirect_stdout
from pathlib import Path

from labmap import __main__ as cli
from labmap import layout, model

ROOT = Path(__file__).resolve().parent.parent
G = "{http://www.w3.org/2000/svg}g"


class Options(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for name in ("lab-data.xlsx", "rooms", "shapes"):
            src = ROOT / "example" / name
            (shutil.copytree if src.is_dir() else shutil.copy2)(src, self.tmp / name)
        self.run_cli("layout")
        self.here = self.tmp / "build" / "layout"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_cli(self, *args, code=0):
        out = io.StringIO()
        with redirect_stdout(out):
            got = cli.main([args[0], str(self.tmp), *args[1:]])
        self.assertEqual(got, code, out.getvalue())
        return out.getvalue()

    def option(self, name, drags):
        """Save As name.svg, with some things dragged: what someone weighing up an idea does in Inkscape."""
        shutil.copy2(self.here / "labs.svg", self.here / f"{name}.svg")
        tree = ET.parse(self.here / f"{name}.svg")
        for g in tree.iter(G):
            i = (g.get("id") or "")[len(layout.PREFIX):]
            if (g.get("id") or "").startswith(layout.PREFIX) and i in drags:
                g.set("transform", f"translate({drags[i][0]},{drags[i][1]}) " + (g.get("transform") or ""))
        tree.write(self.here / f"{name}.svg")

    def test_every_drawing_is_found_the_working_one_first(self):
        self.option("option-B", {})
        self.option("option-A", {})
        self.assertEqual(list(layout.drawings(self.tmp)), ["labs", "option-A", "option-B"])

    def test_compare_puts_them_side_by_side(self):
        self.option("option-A", {"CART-02": (-120, 0)})
        self.option("option-B", {"CART-02": (-120, 0), "SPEC-02": (0, 60)})
        out = self.run_cli("compare")
        self.assertRegex(out, r"option-A\s+\d+\s+\d+\s+1\s+1")  # one thing to lift, in one round
        self.assertRegex(out, r"option-B\s+\d+\s+\d+\s+2\s+1")
        page = (self.tmp / "build" / "compare.html").read_text(encoding="utf-8")
        for name in ("labs", "option-A", "option-B"):
            self.assertIn(f"<th>{name}</th>", page)
        self.assertIn("Things to lift on the day", page)
        self.assertIn("class='ok'", page)  # the best on some row
        for report in ("report-layout.html", "report-option-A.html", "report-option-B.html"):
            self.assertTrue((self.tmp / "build" / report).exists(), report)
            self.assertIn(f"href='{report}'", page)

    def test_check_and_model_one_option(self):
        self.option("option-A", {"CART-02": (-120, 0)})
        out = self.run_cli("check", "--layout", "option-A")
        self.assertIn("option-A.svg", out)
        self.assertTrue((self.tmp / "build" / "report-option-A.html").exists())
        self.run_cli("model", "--layout", "option-A", "--room", "LAB-A")
        self.assertTrue((self.tmp / "build" / "model" / "LAB-A-option-A.glb").exists())

    def test_a_name_that_isnt_there_says_what_is(self):
        out = self.run_cli("check", "--layout", "option-Z", code=2)
        self.assertIn("option-Z.svg", out)
        self.assertIn("labs", out)

    def test_pulling_an_option_keeps_it_and_the_working_drawing(self):
        self.option("option-A", {"CART-02": (-120, 0)})
        was = model.load(self.tmp).placeables["CART-02"]["x"]
        before = (self.here / "option-A.svg").read_bytes()
        out = self.run_cli("pull", "--layout", "option-A")
        self.assertEqual(model.load(self.tmp).placeables["CART-02"]["x"], was - 120)
        self.assertEqual((self.here / "option-A.svg").read_bytes(), before)  # the option is left as it was
        kept = list((self.tmp / "build" / "backups").glob("labs-*.svg"))
        self.assertEqual(len(kept), 1, out)  # the working drawing, drawn before the pull, is kept...
        moves, _ = layout.layout_moves(model.load(self.tmp))
        self.assertEqual(layout.count(moves), 0)  # ...and redrawn to match what was pulled


if __name__ == "__main__":
    unittest.main()
