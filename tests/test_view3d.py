"""The directory's 3D page per room: what gets embedded is consistent, and everything it links to exists."""
import base64
import json
import re
import shutil
import struct
import tempfile
import unittest
from pathlib import Path

from labmap import checks, model, site, view3d

ROOT = Path(__file__).resolve().parent.parent


def embedded(page):
    """The LAB3D data a 3D page carries, with its arrays decoded."""
    d = json.loads(re.search(r"window\.LAB3D=(\{.*?\});</script>", page.read_text(encoding="utf-8")).group(1))
    raw = {k: base64.b64decode(d[k]) for k in ("pos", "col", "pick", "idx")}
    d["pos"] = struct.unpack(f"<{len(raw['pos']) // 4}f", raw["pos"])
    d["col"] = raw["col"]
    d["pick"] = struct.unpack(f"<{len(raw['pick']) // 2}H", raw["pick"])
    d["idx"] = struct.unpack(f"<{len(raw['idx']) // 4}I", raw["idx"])
    return d


class Pages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.lab = model.load(ROOT / "example")
        site.build(cls.lab, checks.run(cls.lab), cls.tmp)
        cls.page = cls.tmp / "rooms" / "LAB-A-3d.html"
        cls.d = embedded(cls.page)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_every_room_with_an_outline_gets_a_page_the_model_and_the_viewer(self):
        for rid in self.lab.rooms:
            self.assertTrue((self.tmp / "rooms" / f"{rid}-3d.html").exists(), rid)
            self.assertTrue((self.tmp / "rooms" / f"{rid}.glb").exists(), rid)
        self.assertIn("webgl2", (self.tmp / "view3d.js").read_text(encoding="utf-8"))

    def test_the_arrays_agree_with_each_other(self):
        d, vertices = self.d, len(self.d["pos"]) // 3
        self.assertEqual(len(d["pos"]) % 3, 0)
        self.assertEqual(len(d["col"]), vertices * 3)
        self.assertEqual(len(d["pick"]), vertices)
        self.assertLess(max(d["idx"]), vertices)
        self.assertEqual(len(d["idx"]) % 3, 0)
        self.assertLess(max(d["pick"]), len(d["objects"]))

    def test_the_layers_cover_the_index_buffer_end_to_end(self):
        at = 0
        for layer in view3d.LAYERS:
            start, count = self.d["ranges"][layer]
            self.assertEqual(start, at, layer)
            at += count
        self.assertEqual(at, len(self.d["idx"]))
        for layer in ("floor", "walls", "things", "zones"):
            self.assertGreater(self.d["ranges"][layer][1], 0, layer)

    def test_clicking_the_floor_selects_nothing(self):
        start, count = self.d["ranges"]["floor"]
        self.assertEqual({self.d["pick"][k] for k in self.d["idx"][start:start + count]}, {0})
        self.assertIsNone(self.d["objects"][0])

    def test_what_the_checks_flag_says_so(self):
        cart = next(o for o in self.d["objects"][1:] if o["id"] == "CART-02")
        self.assertTrue(cart["bad"])
        self.assertTrue(any("EYE-01" in f for f in cart["find"]))

    def test_every_object_links_to_its_page(self):
        for o in self.d["objects"][1:]:
            self.assertTrue((self.page.parent / o["href"]).resolve().exists(), o)

    def test_the_plan_and_object_pages_link_in(self):
        self.assertIn("LAB-A-3d.html", (self.tmp / "rooms" / "LAB-A.html").read_text(encoding="utf-8"))
        self.assertIn("rooms/LAB-A-3d.html#SPEC-02", (self.tmp / "o" / "SPEC-02.html").read_text(encoding="utf-8"))


class NoOutline(unittest.TestCase):
    def test_a_room_without_an_outline_has_no_3d_page_and_no_link_to_one(self):
        lab = model.build(ROOT, {"rooms": [{"id": "R", "ceiling": 250}],
                                 "placeables": [dict(id="B", room="R", mount="floor", category="bench", x=0, y=0,
                                                     w=100, d=60, h=90)]})
        tmp = Path(tempfile.mkdtemp())
        try:
            site.build(lab, checks.run(lab), tmp)
            self.assertFalse((tmp / "rooms" / "R-3d.html").exists())
            self.assertNotIn("-3d.html", (tmp / "rooms" / "R.html").read_text(encoding="utf-8"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
