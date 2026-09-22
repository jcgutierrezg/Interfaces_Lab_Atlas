"""Worked example, whole cm: LAB-A (720 x 540 wet lab) and LAB-B (L-shaped instrument room with a chamfered
corner). It holds exactly the deliberate problems listed in example/README.md, one per check."""
from example_helpers import D, P
from example_lab_b import LAB_B
from example_equipment import EQUIPMENT
from example_items import DOCUMENTS, ITEMS
from example_services import CIRCUITS, LINKS, SERVICES

ROOMS = [
    dict(id="LAB-A", name="Wet lab (EXAMPLE)", building="Building 1", floor="2", width=720, depth=540,
         ceiling=270, shell="LAB-A.svg", cooling=8000, notes="EXAMPLE: plain rectangular room"),
    dict(id="LAB-B", name="Instrument room (EXAMPLE)", building="Building 1", floor="2", width=780, depth=600,
         ceiling=280, shell="LAB-B.svg", cooling=3000,
         notes="EXAMPLE: L-shaped, chamfered corner, a column and a pilaster"),
]

LAB_A = [
    # --- architecture, structure, safety (fixed) ---
    P("DOOR-01", "Main door", "door", "LAB-A", None, "floor", x=590, y=535, faces="N", w=100, d=5, h=210,
      clear_front=100, fixed="yes", notes="clear_front = door swing"),
    P("WIN-01", "Window, right wall", "window", "LAB-A", None, "wall", x=710, y=180, z=100, faces="W", w=160,
      d=10, h=120, fixed="yes", notes="sill at 100 cm: benches fit under, tall units block it"),
    P("COL-01", "Structural column", "structure", "LAB-A", None, "floor", x=0, y=220, w=30, d=30, h=270,
      fixed="yes", notes="pilaster on the left wall"),
    P("PANEL-01", "Distribution board DB-2", "structure", "LAB-A", None, "wall", x=705, y=380, z=120, faces="W",
      w=60, d=15, h=80, clear_front=100, fixed="yes", notes="keep clear in front (check local rules)"),
    P("EYE-01", "Eyewash station", "safety", "LAB-A", None, "wall", x=530, y=525, z=90, faces="N", w=40, d=15,
      h=40, clear_front=100, fixed="yes", notes="must stay unobstructed"),
    P("HOOD-01", "Fume hood", "fume-hood", "LAB-A", None, "floor", x=270, y=0, w=150, d=90, h=240,
      clear_front=100, fixed="yes"),
    P("HP-01", "Hotplate stirrer 1", "instrument", "LAB-A", "HOOD-01", "in", w=20, d=30, h=12),
    P("HP-02", "Hotplate stirrer 2", "instrument", "LAB-A", "HOOD-01", "in", w=20, d=30, h=12),
    # --- sink bench (solid cupboard base: no free_under) ---
    P("BENCH-01", "Sink bench", "bench", "LAB-A", None, "floor", x=450, y=0, w=270, d=75, h=90, clear_front=90,
      fixed="yes", notes="fixed: plumbing; cupboard base, so nothing fits under it"),
    P("WB-01", "Water bath", "instrument", "LAB-A", "BENCH-01", "on", x=10, y=10, w=50, d=35, h=30),
    P("AUTO-01", "Benchtop autoclave", "instrument", "LAB-A", "BENCH-01", "on", x=70, y=5, w=55, d=65, h=50,
      clear_top=40, notes="top-loading lid"),
    P("PH-01", "pH meter", "instrument", "LAB-A", "BENCH-01", "on", x=130, y=10, w=25, d=20, h=15),
    P("SINK-01", "Sink bowl and tap", "sink", "LAB-A", "BENCH-01", "on", x=180, y=10, w=60, d=50, h=30,
      fixed="yes", stackable="no", notes="an occupant, not a cutout: blocks this bit of bench top"),
    # --- composed L-bench and what's on/under it ---
    P("BENCH-04", "Corner bench (L)", "bench", "LAB-A", None, "floor", x=0, y=0, shape="group",
      notes="geometry lives in its parts .A and .B"),
    P("BENCH-04.A", "Corner bench, long leg", "bench", "LAB-A", "BENCH-04", "part", x=0, y=0, w=240, d=60, h=90,
      free_under=88, clear_front=90),
    P("BENCH-04.B", "Corner bench, short leg", "bench", "LAB-A", "BENCH-04", "part", x=0, y=60, faces="E", w=120,
      d=60, h=90, free_under=88, clear_front=90, notes="faces E: its front is the inside of the L"),
    P("SPEC-01", "UV-Vis spectrophotometer", "instrument", "LAB-A", "BENCH-04.A", "on", x=10, y=10, w=60, d=45,
      h=30, clear_back=10),
    P("CEN-01", "Benchtop centrifuge", "instrument", "LAB-A", "BENCH-04.A", "on", x=80, y=5, w=50, d=55, h=35,
      clear_left=10, clear_right=10, clear_top=40,
      notes="EXAMPLE PROBLEM: open lid reaches 165 cm, SHELF-01 is at 150 cm"),
    P("WS-01", "Working area", "workspace", "LAB-A", "BENCH-04.A", "on", x=140, y=0, w=90, d=60, h=50,
      notes="reserves bench top for actual work"),
    P("PED-01", "Drawer pedestal", "pedestal", "LAB-A", "BENCH-04.A", "under", x=185, y=5, w=45, d=50, h=60,
      clear_front=50, mobile="yes", notes="clear_front = drawer pull-out"),
    P("PED-01.D1", "Top drawer", "drawer", "LAB-A", "PED-01", "in", w=38, d=45, h=8, fill=60, checked=D),
    P("PED-01.D2", "Middle drawer", "drawer", "LAB-A", "PED-01", "in", w=38, d=45, h=12, fill=90, checked=D),
    P("PED-01.D3", "Bottom drawer", "drawer", "LAB-A", "PED-01", "in", w=38, d=45, h=25, fill=30),
    P("SPEC-02", "Old spectrophotometer", "instrument", "LAB-A", "BENCH-04.B", "on", x=10, y=5, w=70, d=50, h=35,
      notes="broken, plan = dispose: frees bench top"),
    P("FRZ-02", "-20 freezer (under bench)", "freezer", "LAB-A", "BENCH-04.B", "under", x=10, y=0, w=60, d=55,
      h=85, clear_front=60, notes="exactly as tall as the space under the bench"),
    P("SHELF-01", "Wall shelf above corner bench", "shelf", "LAB-A", None, "wall", x=0, y=0, z=150, w=240, d=30,
      h=3),
    P("BOX-01", "Red parts box", "container", "LAB-A", "SHELF-01", "on", x=10, y=2, w=40, d=25, h=15, fill=50),
    # --- window bench ---
    P("BENCH-02", "Window bench", "bench", "LAB-A", None, "floor", x=645, y=180, faces="W", w=180, d=75, h=90,
      free_under=80, clear_front=90, notes="under the window"),
    P("BAL-01", "Analytical balance", "instrument", "LAB-A", "BENCH-02", "on", x=20, y=15, w=35, d=45, h=35,
      clear_front=30, notes="vibration-sensitive: away from door, HVAC, centrifuge"),
    P("VORT-01", "Vortex mixer", "instrument", "LAB-A", "BENCH-02", "on", x=50, y=20, w=15, d=15, h=15,
      notes="EXAMPLE PROBLEM: placed on top of BAL-01"),
    P("BENCH-02.D1", "Bench drawer 1", "drawer", "LAB-A", "BENCH-02", "in", w=50, d=60, h=10, fill=40),
    P("BENCH-02.D2", "Bench drawer 2", "drawer", "LAB-A", "BENCH-02", "in", w=50, d=60, h=10, fill=75),
    P("FRG-01", "Under-bench fridge", "fridge", "LAB-A", "BENCH-02", "under", x=60, y=5, w=55, d=55, h=85,
      clear_front=60, notes="EXAMPLE PROBLEM: 85 cm tall, only 80 cm free under BENCH-02"),
    P("PUMP-01", "Vacuum pump", "instrument", "LAB-A", "BENCH-02", "under", x=130, y=15, w=40, d=30, h=35,
      clear_back=10, notes="noisy and warm"),
    # --- bottom wall ---
    P("FRZ-01", "-80 freezer", "freezer", "LAB-A", None, "floor", x=30, y=440, faces="N", w=90, d=90, h=198,
      clear_front=100, clear_back=10, clear_left=5, clear_right=5, notes="10 cm off the wall for ventilation"),
    P("CAB-01", "Tall storage cabinet", "cabinet", "LAB-A", None, "floor", x=140, y=480, faces="N", w=100, d=60,
      h=200, clear_front=70),
    P("CAB-01.S1", "Top shelf", "shelf", "LAB-A", "CAB-01", "in", w=95, d=55, h=40, fill=80),
    P("CAB-01.S2", "Shelf 2", "shelf", "LAB-A", "CAB-01", "in", w=95, d=55, h=40, fill=45, checked=D),
    P("DESK-01", "PC desk", "desk", "LAB-A", None, "floor", x=280, y=460, faces="N", w=160, d=80, h=75,
      free_under=68, clear_front=90),
    P("PC-01", "Instrument PC", "computer", "LAB-A", "DESK-01", "under", x=130, y=15, w=20, d=45, h=45),
    P("MON-01", "Monitor", "monitor", "LAB-A", "DESK-01", "on", x=50, y=10, w=60, d=20, h=45),
    P("WS-02", "Legroom", "workspace", "LAB-A", "DESK-01", "under", x=30, y=20, w=70, d=55, h=65,
      notes="keeps the space under the desk free for legs"),
    # --- central table (open underneath) ---
    P("TBL-01", "Central lab table", "table", "LAB-A", None, "floor", x=200, y=230, w=180, d=90, h=90,
      free_under=75, clear_front=90, clear_back=60, notes="open frame: free_under 75"),
    P("MIC-01", "Microscope", "instrument", "LAB-A", "TBL-01", "on", x=20, y=20, w=35, d=45, h=50),
    P("LAP-02", "Microscope laptop", "computer", "LAB-A", "TBL-01", "on", x=70, y=25, w=35, d=25, h=3),
    P("SMU-01", "Source measure unit 1", "instrument", "LAB-A", "TBL-01", "on", x=120, y=20, w=21, d=45, h=9,
      stackable="yes", notes="bottom of a stack of three"),
    P("SMU-02", "Source measure unit 2", "instrument", "LAB-A", "SMU-01", "on", x=0, y=0, w=21, d=45, h=9,
      stackable="yes", notes="stacked on SMU-01"),
    P("SMU-03", "Source measure unit 3", "instrument", "LAB-A", "SMU-02", "on", x=0, y=0, w=21, d=45, h=9,
      notes="top of the stack"),
    P("BIN-01", "Waste bin", "other", "LAB-A", None, "floor", x=330, y=270, shape="circle", w=35, d=35, h=60,
      notes="not a child of TBL-01, but fits under it"),
    # --- loose and new things ---
    P("CART-01", "Trolley", "cart", "LAB-A", None, "floor", x=440, y=300, w=80, d=50, h=90, mobile="yes",
      notes="position = parking spot"),
    P("CART-02", "Waste trolley", "cart", "LAB-A", None, "floor", x=520, y=440, w=60, d=50, h=90, mobile="yes",
      notes="EXAMPLE PROBLEM: parked in the eyewash clear zone"),
    P("GAS-01", "N2 cylinder", "gas-cylinder", "LAB-A", None, "floor", x=5, y=280, shape="circle", w=23, d=23,
      h=150, notes="chain to the wall"),
    P("GAS-02", "Ar cylinder", "gas-cylinder", "LAB-A", None, "floor", x=5, y=308, shape="circle", w=23, d=23,
      h=150),
    P("INC-01", "Incubator (arriving)", "instrument", "LAB-A", None, "floor", w=70, d=70, h=90, clear_front=70,
      notes="no x/y yet: lands in the staging area, drag it into place"),
]

PLACEABLES = LAB_A + LAB_B + [
    P("GB-01", "Glovebox (arriving)", "instrument", "LAB-B", None, "floor", w=180, d=105, h=190, clear_front=90,
      notes="EXAMPLE WARNING: 105 cm deep, too big for a 100 cm door even on its side"),
    P("DUCT-01", "Ventilation duct", "overhead", "LAB-B", None, "wall", x=100, y=0, z=240, w=300, d=40, h=30,
      fixed="yes", notes="overhead things are wall mounts with z = their underside"),
]

# Doors, tags, sprinklers, services needed: added on top of the rows above, by ID.
_MORE_ROOMS = {
    "LAB-A": dict(sprinklers="yes"),
    "LAB-B": dict(sprinklers="yes"),
}
_MORE_PLACEABLES = {
    "CAB-01": dict(h=230, door="both", notes="EXAMPLE PROBLEM: 230 cm tall, within 45 cm of a sprinklered ceiling"),
    "CAB-02": dict(door="both"),
    "FRZ-01": dict(door="right"), "FRG-01": dict(door="left"),
    "PUMP-01": dict(tags="vibrates; noisy"), "PUMP-02": dict(tags="vibrates; noisy"),
    "CEN-01": dict(tags="vibrates"), "CEN-02": dict(tags="vibrates"),
    "BAL-01": dict(tags="vibration-sensitive"), "BAL-02": dict(tags="vibration-sensitive"),
    "MIC-01": dict(tags="vibration-sensitive"),
    "AUTO-01": dict(tags="heat-source"),
}
_MORE_EQUIPMENT = {
    "MS-01": dict(needs="exhaust"), "GC-01": dict(needs="gas:He; gas:H2"), "PC-02": dict(needs="network"),
}
_MORE_SERVICES = {"OUT-06": dict(rating_a=10, notes="EXAMPLE PROBLEM: a 10 A socket with the autoclave on it"),
                  "STRIP-01": dict(rating_a=13), "STRIP-02": dict(rating_a=13), "STRIP-04": dict(rating_a=13),
                  "STRIP-05": dict(rating_a=13)}


def _merge(rows, more):
    known = {r["id"] for r in rows}
    assert set(more) <= known, set(more) - known
    for r in rows:
        r.update(more.get(r["id"], {}))


_merge(ROOMS, _MORE_ROOMS)
_merge(PLACEABLES, _MORE_PLACEABLES)
_merge(EQUIPMENT, _MORE_EQUIPMENT)
_merge(SERVICES, _MORE_SERVICES)
SERVICES.append(dict(id="EXH-01", type="exhaust", room="LAB-B", x=100, y=0, z=200,
                     medium="snorkel", notes="the only extraction point in LAB-B"))
EQUIPMENT.append(dict(id="GB-01", maker="ExampleCo", model="Glove-2", owner="Analytics group", plan="new", plugs=1,
                      plug_type="standard", watts_typ=300, watts_max=600, volts=230, weight=250))

EXTRA_LISTS = {"shape": [("@corner-45", "example profile: shapes/corner-45.svg")]}
ROWS = {"rooms": ROOMS, "placeables": PLACEABLES, "equipment": EQUIPMENT, "services": SERVICES,
        "circuits": CIRCUITS, "links": LINKS, "items": ITEMS, "documents": DOCUMENTS}
