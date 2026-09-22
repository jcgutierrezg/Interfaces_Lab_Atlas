"""The directory: every link and image resolves, and search knows the synonyms."""
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from labmap import checks, model, site

ROOT = Path(__file__).resolve().parent.parent


class Directory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        lab = model.load(ROOT / "example")
        cls.index = site.build(lab, checks.run(lab), cls.tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_every_link_resolves(self):
        broken = []
        for page in self.tmp.rglob("*.html"):
            for ref in re.findall(r"""(?:href|src)=['"]([^'"#?]+)""", page.read_text(encoding="utf-8")):
                if not re.match(r"[a-z]+:", ref) and not (page.parent / ref).resolve().exists():
                    broken.append(f"{page.relative_to(self.tmp)} -> {ref}")
        self.assertEqual(broken, [])

    def test_no_unknown_references(self):
        pages = [p for p in self.tmp.rglob("*.html") if p.name != "report.html"]
        self.assertFalse([p.name for p in pages if "class='unknown'" in p.read_text(encoding="utf-8")])

    def test_search_index(self):
        data = json.loads(re.search(r"window\.LABMAP=(\[.*?\]);", (self.tmp / "search.js").read_text(encoding="utf-8")).group(1))
        allen = [e for e in data if "allen" in e["h"]]
        self.assertEqual([e["id"] for e in allen], ["I-0001"])
        self.assertEqual(allen[0]["u"], "o/PED-01.D2.html#I-0001")
        self.assertTrue(any(e["t"] == "procedure" and "vacuum" in e["h"] for e in data))

    def test_equipment_page_has_photo_sop_and_forms(self):
        text = (self.tmp / "o" / "MIC-01.html").read_text(encoding="utf-8")
        self.assertIn("class='hero' src='../photos/MIC-01.jpg'", text)
        self.assertIn("<th>Procedures</th><td><a href='../sops/MIC-01-operation.html'>", text)
        for expected in ("Forms and certificates", "COSHH-014", "status ok'>approved", "2029-03-02",
                         "https://intranet.example.org/coshh/COSHH-014.pdf"):
            self.assertIn(expected, text)

    def test_spare_parts_on_equipment_pages(self):
        gc = (self.tmp / "o" / "CRYO-01.html").read_text(encoding="utf-8")
        self.assertIn("<h2 id='spares'>Spare parts</h2>", gc)
        self.assertIn("status bad'>none left", gc)  # GC inlet liners
        self.assertIn("href='https://uk.rs-online.com/web/c/?searchTerm=0000103'>RS 000-0103</a>", gc)
        n2 = (self.tmp / "o" / "N2G-01.html").read_text(encoding="utf-8")
        self.assertIn("Main stores, building 2, cage 3", n2)  # kept outside the labs: no map link
        self.assertIn("id='spare-I-0050'", n2)
        drawer = (self.tmp / "o" / "BOX-01.html").read_text(encoding="utf-8")
        self.assertIn(">RS 000-0104</a>", drawer)  # ordering info in the drawer's item list too

    def test_where_it_is_stands_out(self):
        page = (self.tmp / "o" / "PED-01.D2.html").read_text(encoding="utf-8")  # a drawer: the pin is on its pedestal
        self.assertIn("href='#where'", page)
        self.assertIn("id='where'", page)
        self.assertEqual(page.count('class="pin"'), 1)
        self.assertIn(">PED-01.D2</text>", page)  # the pin names the drawer, not the pedestal it's shown on
        self.assertIn("markflash", page)
        self.assertNotIn('class="pin"', (self.tmp / "rooms" / "LAB-A.html").read_text(encoding="utf-8"))

    def test_decommissioned_kept_as_a_record(self):
        page = (self.tmp / "o" / "OVEN-01.html").read_text(encoding="utf-8")
        self.assertIn("class='gone'>Decommissioned on 2026-06-30", page)
        self.assertIn("spare part I-0051", page)  # what still points at it
        self.assertNotIn('"OVEN-01"', (self.tmp / "search.js").read_text(encoding="utf-8"))  # not searched
        self.assertNotIn("OVEN-01", (self.tmp / "rooms" / "LAB-A.html").read_text(encoding="utf-8"))

    def test_document_links(self):
        self.assertEqual(site.doc_href("\\\\server\\share\\COSHH\\014.pdf"), "file://server/share/COSHH/014.pdf")
        self.assertEqual(site.doc_href("S:\\Safety\\RA-003.pdf"), "file:///S:/Safety/RA-003.pdf")
        self.assertIsNone(site.doc_href("somewhere on the intranet"))

    def test_labels_are_legible(self):
        """For every object: its label is fully inside it with a margin, clear of every other label, and at least
        the minimum size, or hidden (0)."""
        from labmap import geometry as G, layout

        lab = model.load(ROOT / "example")
        res = checks.run(lab)
        for rid in lab.rooms:
            for kind, covered in (("map", False), ("layout", True)):
                plan = layout.label_plan(lab, res, rid, layout.LABEL_MIN[kind], covered=covered)
                shown = {i: v for i, v in plan.items() if v[0]}
                self.assertGreater(len(shown), 20, rid)
                boxes = [v[1] for v in shown.values()]
                clashes = [(a, b) for n, a in enumerate(boxes) for b in boxes[n + 1:]
                           if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]]
                self.assertEqual(clashes, [], (rid, kind))
                for i, (size, (x0, y0, x1, y1), _) in shown.items():
                    self.assertGreaterEqual(size, layout.LABEL_MIN[kind], i)
                    m = max(1.0, 0.3 * size) - 0.01
                    corners = [(x0 - m, y0 - m), (x1 + m, y0 - m), (x1 + m, y1 + m), (x0 - m, y1 + m)]
                    self.assertTrue(all(G.inside(c, res.geo[i].poly) for c in corners), (rid, kind, i))
            self.assertTrue(plan["PED-01"][0] if rid == "LAB-A" else True)  # under a bench, labelled in Inkscape

    def test_object_page_contents(self):
        text = (self.tmp / "o" / "PED-01.D2.html").read_text(encoding="utf-8")
        for expected in ("Hex key set", "Items kept here", "BENCH-04.A", "PED-01.D2.jpg"):
            self.assertIn(expected, text)


if __name__ == "__main__":
    unittest.main()
