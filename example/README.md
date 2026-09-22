# Example lab

A complete, fictional two-room lab, filled in the way `lab-data.xlsx` should be. Use it to see how each case is
entered, and as the test case for the build steps while the real data is collected: the layout generator, the
check report and the directory should all work on this folder before they're pointed at real data.

Everything follows the conventions in `../README.md`. The photos are placeholders and the SOP text is
illustrative, not validated procedure.

## Playing with it

The `.bat` files in this folder do the same as the ones in the main folder (see *Double-click shortcuts* in
`../README.md`), but on the example. Double-click them in this order to see the whole workflow:

1. `check.bat`: the report, with the eleven deliberate problems and three warnings listed below.
2. `site.bat`: the lab directory. Search for "allen key", open `MIC-01`, try the level and sockets buttons.
3. `layout.bat`: opens `build\layout`. Open `LAB-A.svg` in Inkscape, drag `SPEC-02` onto the central table
   (`TBL-01`), save.
4. `try-layout.bat`: the report for the arrangement as drawn, with nothing written yet.
5. `pull.bat`: writes the move into this folder's `lab-data.xlsx`, then re-checks.

`reset.bat` puts everything back as it came: the original workbook (from `lab-data.original.xlsx`, which you
shouldn't edit) and no generated files. Reset before running the tests (`python -m unittest`): they expect the
example exactly as shipped.

## The two rooms

| | LAB-A · Wet lab | LAB-B · Instrument room |
|---|---|---|
| Shape | 720 × 540 cm rectangle | L-shaped, 780 × 600 cm, chamfered corner, a column and a pilaster |
| Benches | L-bench, sink bench, window bench, central table, desk | corner unit, bench around the chamfer, two-tier bench, notched island, write-up table |
| Equipment | spectrophotometers, centrifuge, balance, autoclave, hotplates, two freezers, fridge, microscope | LC-MS, GC, FTIR, nitrogen generator, data server |
| Cooling | 8 kW | 3 kW (deliberately too little) |

In numbers: 113 rows on the placeables sheet (90 with a position, 18 inside other things, 4 group rows, 1 not
placed yet), 42 pieces of equipment, 21 sockets, strips and network ports, 10 circuits, 19 links, 50 items,
5 SOPs, 5 forms and certificates on the documents sheet, and 8 photos.

## Cases covered

| Case | Where |
|---|---|
| L-shaped bench as a group | `BENCH-04` (`.A`, `.B`) |
| Bench around a chamfered corner, with a diagonal piece | `BENCH-11` (`.B` faces `SW`; `BOX-02` sits on it) |
| Two-tier bench: worktop plus a raised back tier, split by a pilaster | `BENCH-13`, `PIL-01` |
| Island notched around a column | `BENCH-14` (`.B` is the notched middle), `COL-02` |
| Profile shape | `BENCH-10` → `shapes/corner-45.svg` |
| Instruments stacked on each other | `SMU-01` → `SMU-02` → `SMU-03` on `TBL-01` (the lower two are `stackable = yes`), GPIB daisy chain |
| Sink as an occupant of a bench | `SINK-01` |
| Tables open underneath (`free_under`), with legroom and a bin under them | `TBL-01` + `BIN-01`; `TBL-02` + `WS-06` + `BIN-02`; `DESK-01` + `WS-02` |
| Things under benches | `PED-01`–`PED-03`, `FRZ-02`, `FRG-01`, `PUMP-01`, `PUMP-02`, `PC-02`, `SRV-01` |
| Things inside other things, without a position | drawers `*.D1`–`D3`, cabinet shelves `*.S1`–`S3`, `HP-01`/`HP-02` in the hood |
| Wall-mounted: shelf, window, eyewash, panel | `SHELF-01`, `WIN-01`, `EYE-01`, `PANEL-01` |
| Round objects | `GAS-01`–`GAS-04`, `BIN-01`, `BIN-02` |
| Fixed things with mandatory clear zones | `DOOR-01`, `DOOR-02`, `EYE-01`, `PANEL-01` |
| Not placed yet | `INC-01` (`plan = new`) |
| Being thrown out, or undecided | `SPEC-02` (`dispose`), `FTIR-01` (`undecided`) |
| Sockets on bench spines, on the hood, in a floor box | `OUT-02`, `OUT-10`–`OUT-12`; `OUT-05`; `OUT-07` |
| Explicit socket vs nearest socket | `outlet` filled for most of LAB-B, blank for most of LAB-A |
| UPS- and generator-backed circuits | `DB3-C02`, `DB2-C09` |
| Hardwired equipment | `HOOD-01` |
| Tubing as well as cables | `GAS-03`/`GAS-04` → `GC-01`, `N2G-01` → `MS-01`, `PUMP-02` → `MS-01` |
| One SOP for several instruments | `SRV-01-data-backup.md`, `FRZ-01-alarm-response.md` |
| Equipment page with photo, SOP and COSHH form | `MIC-01`: `photos/MIC-01.png`, `sops/MIC-01-operation.md`, `COSHH-014` |
| Spare parts: stocked, low, out, and kept in a store outside the labs | `GC-01` (liners out, column and ferrules fine), `HPLC-01` (guard cartridges low), `N2G-01` (filters in `elsewhere`) |
| Ordering: RS number and supplier link | `rs_part` on the fuses, pump oil, liners, multimeter and cable ties (EXAMPLE numbers); `buy_link` on the C18 column, N2 filters and gloves |
| Forms and certificates | documents sheet: COSHH, risk assessment, calibration (one form for two balances), PAT tests for a whole room, and one still pending |

## Deliberate problems: the expected check results

The example contains exactly these eleven problems and three warnings, each testing a different rule. Everything else is meant to pass, so if a check
reports anything beyond this list, either the check or the example has a bug.

| # | Rule | Expected finding |
|---|---|---|
| 1 | Clear zone blocked | `EYE-01`'s clear zone is blocked by `CART-02` |
| 2 | Headroom | `CEN-01`'s open lid (165 cm) hits `SHELF-01` (150 cm) |
| 3 | Overlap | `VORT-01` is placed on top of `BAL-01` |
| 4 | Doesn't fit underneath | `FRG-01` is 85 cm tall; only 80 cm free under `BENCH-02` |
| 5 | Outside the room | `N2G-01` straddles LAB-B's wall into the missing corner |
| 6 | Too many plugs | `OUT-01`: 4 plugs for 2 sockets |
| 7 | Strip into strip | `STRIP-03` is plugged into `STRIP-02` |
| 8 | Circuit overload | `DB2-C10`: 4005 W running against a 2944 W limit |
| 9 | Critical load at risk | `FRZ-02` (critical) shares `DB2-C07` with `CEN-01` (peak 1000 W) |
| 10 | Heat vs cooling | LAB-B: 5080 W of equipment against 3000 W of cooling |
| 11 | Cable reach | USB `PC-01 → SPEC-01` needs about 8.1 m; USB 2 is good for 5 m |
| + | Document not approved (a warning, not a problem) | `COSHH-022` for `HPLC-01` and `MS-01` is still pending |
| + | Spare part out of stock (warning) | `I-0036` GC inlet liners for `GC-01`: 0 in stock, keep at least 5 |
| + | Spare part running low (warning) | `I-0031` guard cartridges for `HPLC-01`: 2 in stock, keep at least 4 |

## How those results are worked out

These are the rules `python -m labmap check` applies (thresholds at the top of `labmap/checks.py`); the numbers
above follow from them. Walkways are checked too: every clear zone in front of a bench, cabinet, door or safety
station must be reachable from a door along a path at least 60 cm wide. The example has no walkway problem; the
unit tests in `tests/` cover that rule, and the others the example doesn't trigger.

- **Positions:** every object is converted to room coordinates through its parent chain (see `../README.md`).
  Profiles use their own footprint and clearance outlines.
- **Collisions:** two footprints collide when they overlap on the plan *and* in height. Furniture with
  `free_under` only occupies the band from `free_under` up to `h`, so anything up to `free_under` tall can sit
  underneath it. An object never collides with its own parent chain.
- **Clear zones:** objects on the floor or on a wall keep theirs free from the floor up to 2 m; objects on a bench
  keep theirs free at their own height. Different parts of one group don't block each other (the inside corner of
  an L is a dead zone). `clear_top` is checked above the object.
- **Under:** an object mounted `under` something must be no taller than the parent's `free_under`, and the parent
  must have one.
- **Sockets:** each device uses `plugs` sockets at its `outlet`, or, when that's blank, at the nearest socket or
  strip in the same room (plan distance from the device's centre). A strip takes one socket of whatever it's
  plugged into. Things inside other things, like the hotplates in the hood, use their parent's position.
- **Circuits:** a strip is on its feeding socket's circuit. Running load = sum of `watts_typ`; the limit is 80% of
  `rating_a × volts`.
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
  filled on the items sheet) with none in stock, or fewer than `min_qty`. The example has exactly three warnings,
  on purpose: `COSHH-022` (the LC-MS solvents) is still pending, the GC inlet liners are out and the guard
  cartridges are low.
- **Unplaced things** (`INC-01`) are left out of every check and simply listed.
- The thresholds (60 cm walkways, 80% circuit limit, 1000 W heavy load, ...) are on the `settings` sheet.
