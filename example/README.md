# Example lab

A complete, fictional two-room lab for thin-film photovoltaics and electronic interfaces, filled in the way
`lab-data.xlsx` should be: a device fabrication lab and a characterisation lab. Use it to see how each case is
entered, and as the test case for the build steps while the real data is collected: the layout generator, the
check report and the directory should all work on this folder before they're pointed at real data.

Everything follows the [spreadsheet reference](../docs/spreadsheet-reference.md). The photos are placeholders and the SOP text is
illustrative, not validated procedure.

## Playing with it

The `.bat` files in this folder do the same as the ones in the main folder (see [Double-click shortcuts](../docs/setup.md#double-click-shortcuts-bat-files)), but on the example. Double-click them in this order to see the whole workflow:

1. `check.bat`: the report, with the fourteen deliberate problems and eight warnings listed below.
2. `site.bat`: the lab directory. Search for "allen key", open `MIC-01`, try the level and sockets buttons.
3. `layout.bat`: opens `build\layout`. Open `labs.svg` in Inkscape: both rooms side by side. Drag `SPEC-02`
   onto the central table (`TBL-01`), and the FTIR (`FTIR-01`) from LAB-B onto LAB-A's window bench
   (`BENCH-02`). Save.
4. `try-layout.bat`: the report for the arrangement as drawn, with nothing written yet. At the top, how it
   compares with the current one, and the move list: the FTIR changes room, and its socket stays behind.
5. `pull.bat`: writes the moves into this folder's `lab-data.xlsx`, saves a printable move list in
   `build\move-lists`, then re-checks.

`reset.bat` puts everything back as it came: the original workbook (from `lab-data.original.xlsx`, which you
shouldn't edit) and no generated files. Reset before running the tests (`python -m unittest`): they expect the
example exactly as shipped.

## The two rooms

| | LAB-A · Fabrication lab | LAB-B · Characterisation lab |
|---|---|---|
| Shape | 720 × 540 cm rectangle | L-shaped, 780 × 600 cm, chamfered corner, a column and a pilaster |
| Benches | L-bench, sink bench, window bench, central I-V table, desk | corner unit, optics bench, bench around the chamfer, two-tier cryostat bench, notched island, write-up table |
| Equipment | fume hood with hotplates, UV-ozone cleaner, split tube furnace, ultrasonic bath, UV-Vis, balance, vacuum pump, precursor freezers and fridge, microscope, a stack of three SMUs | solar simulator, probe station, optical cryostat, 405 nm laser, corona charging box, LED source and dark box, FTIR, nitrogen generator, data server; a glovebox arriving |
| Cooling | 8 kW | 3 kW (deliberately too little) |
| Sprinklers | yes | yes, and a ventilation duct overhead |

In numbers: 116 rows on the placeables sheet (93 with a position, 16 inside other things without one, 4 group
rows, 2 not placed yet, 1 decommissioned), 44 pieces of equipment, 23 sockets, strips, network ports, extraction
points and earth points, 10 circuits, 19 links, 51 items, 5 SOPs, 5 forms and certificates on the documents
sheet, 8 keep-apart rules and 8 photos.

## Cases covered

| Case | Where |
|---|---|
| L-shaped bench as a group | `BENCH-04` (`.A`, `.B`) |
| Bench around a chamfered corner, with a diagonal piece | `BENCH-11` (`.B` faces `SW`; `BOX-02` sits on it) |
| Two-tier bench: worktop plus a raised back tier, split by a pilaster | `BENCH-13`, `PIL-01` |
| Island notched around a column | `BENCH-14` (`.B` is the notched middle), `COL-02` |
| Profile shape | `BENCH-10` → `shapes/corner-45.svg` |
| Instruments stacked on each other | `SMU-01` → `SMU-02` → `SMU-03` on `TBL-01` (the lower two are `stackable = yes`), GPIB daisy chain |
| Categories for this kind of lab | `SUN-01` sun-simulator, `LAS-01` laser, `LED-01` light-source, `DARK-01` dark-box, `COR-01` corona-box, `PRB-01` probe-station, `VAC-01`/`VAC-02` vacuum-pump, `SMU-01`–`03` power-supply, `FURN-01` oven, `HP-01`/`HP-02` hotplate, `GB-01` glovebox |
| Sink as an occupant of a bench | `SINK-01` |
| Tables open underneath (`free_under`), with legroom and a bin under them | `TBL-01` + `BIN-01`; `TBL-02` + `WS-06` + `BIN-02`; `DESK-01` + `WS-02` |
| Things under benches | `PED-01`–`PED-03`, `FRZ-02`, `FRG-01`, `VAC-01`, `VAC-02`, `PC-02`, `SRV-01` |
| Things inside other things, without a position | drawers `*.D1`–`D3`, cabinet shelves `*.S1`–`S3` |
| Working space inside a fume hood, with things placed in it | `HOOD-01` (`inner_w` × `inner_d` × `inner_h` = 130 × 65 × 110 cm, work surface at 90 cm); hotplates `HP-01`, `HP-02` (`mount = in`, with x and y) |
| Wall-mounted: shelf, window, eyewash, panel | `SHELF-01`, `WIN-01`, `EYE-01`, `PANEL-01` |
| Round objects | `GAS-01`–`GAS-04`, `BIN-01`, `BIN-02` |
| Fixed things with mandatory clear zones | `DOOR-01`, `DOOR-02`, `EYE-01`, `PANEL-01` |
| Not placed yet | `OVEN-02`, `GB-01` (`plan = new`) |
| Overhead obstruction | `DUCT-01` (category `overhead`, a wall mount with `z` = its underside) |
| Door hinges | `FRZ-01` (right), `FRG-01` (left), `CAB-01` and `CAB-02` (double doors) |
| Services needed besides power | `SUN-01` (exhaust for its lamp's ozone: out of reach), `CRYO-01` (He and N2: met by its gas lines), `PC-02` (network: `NET-03` within reach), `SMU-01` (a clean earth: `EARTH-01`) |
| Tags kept apart | `vibrates` on the pumps, `vibration-sensitive` on the balance and the microscope; `emits-light` on the solar simulator, laser, LED source and UV-ozone cleaner, `needs-dark` on the dark box; `emi-source` on a pump and the corona box, `emi-sensitive` on the SMUs; `ignition-source` on the hotplates, furnace and corona box, `flammable` on the solvent cabinet |
| Socket and strip ratings | `OUT-06` (10 A), the strips (13 A) |
| Being thrown out, or undecided | `SPEC-02` (`dispose`: on the report's Decommissioning list), `FTIR-01` (`undecided`) |
| Decommissioned, kept as a record | `OVEN-01` (`decommissioned` 2026-06-30, `plan = decommissioned`); a spare part still listed for it |
| Sockets on bench spines, on the hood, in a floor box | `OUT-02`, `OUT-10`–`OUT-12`; `OUT-05`; `OUT-07` |
| Explicit socket vs nearest socket | `outlet` filled for most of LAB-B, blank for most of LAB-A |
| UPS- and generator-backed circuits | `DB3-C02`, `DB2-C09` |
| Hardwired equipment | `HOOD-01` |
| Tubing as well as cables | `GAS-03`/`GAS-04` → `CRYO-01` (gas lines), `VAC-02` → `PRB-01` (vacuum line), `N2G-01` → `GB-01` (for the glovebox when it arrives) |
| Measurement links | `PC-02` → `PRB-01` (triax), `LAS-01` → `PRB-01` (optical fibre), `SMU-01` → `SMU-02` → `SMU-03` (GPIB) |
| One SOP for several instruments | `SRV-01-data-backup.md`, `FRZ-01-alarm-response.md` |
| Equipment page with photo, SOP and COSHH form | `MIC-01`: `photos/MIC-01.png`, `sops/MIC-01-operation.md`, `COSHH-014` |
| Spare parts: stocked, low, out, and kept in a store outside the labs | `CRYO-01` (O-rings out, window and indium foil fine), `PRB-01` (probe tips low), `SUN-01` (spare xenon lamp), `N2G-01` (filters in `elsewhere`) |
| Ordering: RS number and supplier link | `rs_part` on the fuses, pump oil, O-rings, multimeter and cable ties (EXAMPLE numbers); `buy_link` on the xenon lamp, N2 filters and gloves |
| Items for this kind of lab | substrates (glass, ITO), optics (ND filters), electronics (BNC-to-triax adapters), a calibrated reference cell, shadow masks, silver paste, indium |
| Forms and certificates | documents sheet: COSHH, risk assessment, calibration (one form for a balance and the solar simulator), PAT tests for a whole room, and an optical-radiation risk assessment still pending |

## Deliberate problems: the expected check results

The example contains exactly these fourteen problems and eight warnings, each testing a different rule. Everything
else is meant to pass, so if a check reports anything beyond this list, either the check or the example has a bug.

| # | Rule | Expected finding |
|---|---|---|
| 1 | Clear zone blocked | `EYE-01`'s clear zone is blocked by `CART-02` |
| 2 | Headroom | `UVO-01`'s open lid (165 cm) hits `SHELF-01` (150 cm) |
| 3 | Overlap | `VORT-01` is placed on top of `BAL-01` |
| 4 | Doesn't fit underneath | `FRG-01` is 85 cm tall; only 80 cm free under `BENCH-02` |
| 5 | Outside the room | `N2G-01` straddles LAB-B's wall into the missing corner |
| 6 | Too close to the sprinklers | `CAB-01` reaches 230 cm; nothing may go above 225 cm (270 cm ceiling, 45 cm clearance) |
| 7 | Too many plugs | `OUT-01`: 4 plugs for 2 sockets |
| 8 | Strip into strip | `STRIP-03` is plugged into `STRIP-02` |
| 9 | Circuit overload | `DB2-C10`: 4005 W running against a 2944 W limit |
| 10 | Critical load at risk | `FRZ-02` (critical) shares `DB2-C07` with `UVO-01` (peak 1000 W) |
| 11 | Heat vs cooling | LAB-B: 5080 W of equipment against 3000 W of cooling |
| 12 | Cable reach | USB `PC-01 → SPEC-01` needs about 8.1 m; USB 2 is good for 5 m |
| 13 | Service out of reach | `SUN-01` needs exhaust (its xenon lamp makes ozone); the only extraction point, `EXH-01`, is about 5.6 m away |
| 14 | Socket overloaded | `OUT-06`, a 10 A socket (2300 W), runs the tube furnace and the heated bath: 2805 W |
| + | Document not approved (a warning, not a problem) | `RA-022`, the optical-radiation risk assessment for `SUN-01` and `LAS-01`, is still pending |
| + | Spare part out of stock (warning) | `I-0036` cold-head O-rings for `CRYO-01`: 0 in stock, keep at least 5 |
| + | Spare part running low (warning) | `I-0031` tungsten probe tips for `PRB-01`: 2 in stock, keep at least 4 |
| + | Close together (warning) | vacuum pump `VAC-01` is 75 cm from balance `BAL-01`; the vibration rule asks for 100 cm |
| + | Close together (warning) | LED source `LED-01` is 145 cm from dark box `DARK-01`; the stray-light rule asks for 200 cm |
| + | Won't fit through the door (warning) | the arriving glovebox `GB-01`, 180 × 105 × 190 cm, can't pass LAB-B's 100 cm door even on its side |
| + | Too close to the sash (warning) | hotplate `HP-02` is 5 cm behind `HOOD-01`'s sash; work is kept at least 15 cm inside |
| + | Still pointing at something decommissioned (warning) | `I-0051`, the oven door seal, is still a spare for `OVEN-01`, which left on 2026-06-30 |

## How those results are worked out

These are the rules `python -m labmap check` applies (thresholds at the top of `labmap/checks.py`); the numbers
above follow from them. Walkways are checked too: every clear zone in front of a bench, cabinet, door or safety
station must be reachable from a door along a path at least 60 cm wide. The example has no walkway problem; the
unit tests in `tests/` cover that rule, and the others the example doesn't trigger.

- **Positions:** every object is converted to room coordinates through its parent chain (see the [spreadsheet reference](../docs/spreadsheet-reference.md#where-things-are-parent-mount-position)).
  Profiles use their own footprint and clearance outlines.
- **Collisions:** two footprints collide when they overlap on the plan *and* in height. Furniture with
  `free_under` only occupies the band from `free_under` up to `h`, so anything up to `free_under` tall can sit
  underneath it. An object never collides with its own parent chain.
- **Clear zones:** objects on the floor or on a wall keep theirs free from the floor up to 2 m; objects on a bench
  keep theirs free at their own height. Different parts of one group don't block each other (the inside corner of
  an L is a dead zone). `clear_top` is checked above the object.
- **Under:** an object mounted `under` something must be no taller than the parent's `free_under` less
  `fit_margin` (2 cm), and the parent must have one. The same 2 cm is kept below the ceiling (not for columns and
  other structure, which reach it by design) and through doors.
- **Doors on things:** `door` (left, right, both) keeps the door's swing clear in front (its width; half each for
  double doors) and `door_gap` (10 cm) beside the hinge. They're ordinary clear zones from then on.
- **Sprinklers:** in a room with `sprinklers = yes`, nothing may reach higher than `sprinkler_clearance` (45 cm) below
  the ceiling. Built-in things (`fixed = yes`, such as the ducted fume hood), structure, overhead things, doors and
  windows are exempt.
- **Services needed:** each entry in `needs` is met by a link of the matching kind (gas-line, vacuum-line,
  water-line or cooling-line, exhaust, ethernet), or by a tap, port, extraction or earth point of that type (and medium, if given) in the same room within
  `utility_reach` (3 m), measured like a cable run.
- **Keep apart:** for each row of the `keep_apart` sheet, every object tagged `tag` and every object tagged
  `away_from` in the same room, measured edge to edge on the plan. An object's category counts as one of its tags
  (so the laser rule can say `laser` and `door`). The row's `level` makes it a problem or a warning.
- **Inside a fume hood:** things with `mount = in` and an x and y are placed in the hood's working space
  (`inner_w` × `inner_d`, centred left to right and flush with the front, on a work surface `inner_z` up). They must
  fit in it, and be no taller than `inner_h` less `fit_margin`; in a fume hood, anything less than
  `sash_clearance` (15 cm) behind the sash is a warning.
- **Door fit:** equipment with `plan` new or relocate must pass through a door of its room: its smallest dimension
  plus `fit_margin` within the door's width, and its middle one within the door's height.
- **Sockets:** each device uses `plugs` sockets at its `outlet`, or, when that's blank, at the nearest socket or
  strip in the same room (plan distance from the device's centre). A strip takes one socket of whatever it's
  plugged into. Things inside other things without a position of their own use their parent's position.
- **Circuits:** a strip is on its feeding socket's circuit. Running load = sum of `watts_typ`; the limit is 80% of
  `rating_a × volts`.
- **Sockets and strips with a `rating_a`:** everything plugged into it, and into strips plugged into it, against
  `rating_a × volts` (the circuit's volts, else 230 V).
- **Critical loads:** flagged when a `critical` device shares its circuit with a non-critical one whose `watts_max`
  is 1000 W or more.
- **Heat:** sum of `watts_typ` of all placed equipment in the room, against `cooling`.
- **Links:** the distance between the two devices' centres, measured along x, y and height separately and added up
  (cables run along walls and benches, not diagonally), against `max_len` or the type's default.
- **Headroom:** `clear_top` and the tops of stacks are checked against shelves above and against the room's `ceiling`.
- **Warnings** (listed separately, not counted as problems): something standing in front of a window between its
  sill and its top, and something sitting on an object that isn't stackable (`stackable = no`, or blank for a
  category other than bench, desk, table, shelf, cabinet or cart). Also forms on the documents sheet that aren't
  approved, or that expire within `expiry_warning_days`; an expired one is a problem. And required spares (`min_qty`
  filled on the items sheet) with none in stock, or fewer than `min_qty`. And keep-apart rows marked `warning`, and
  arrivals too big for the door, work too close to a fume hood's sash, and anything still pointing at something
  decommissioned. The example has exactly eight warnings, on purpose: `RA-022` (optical radiation) is still
  pending, the cold-head O-rings are out, the probe tips are low, the vacuum pump is next to the balance, the LED
  source is too close to the dark box, the glovebox won't get through the door, a hotplate sits right behind the
  hood's sash, and the old oven's door seal is still listed as its spare.
- **Decommissioned** things (a `decommissioned` date, or `plan = decommissioned`), with their drawers and parts, are
  left out of every check, map and count. What still refers to them is listed: things on or in them, items kept in
  them, spares listed for them, sockets on them, links, documents, SOPs and photos.
- **Unplaced things** (`OVEN-02`, `GB-01`) are left out of the placement checks and simply listed; the door check
  still applies to them. `OVEN-01` has no position either, but it's decommissioned, so it isn't listed.
- The thresholds (60 cm walkways, 80% circuit limit, 1000 W heavy load, ...) are on the `settings` sheet.
