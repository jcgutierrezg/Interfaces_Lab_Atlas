# Lab map

One set of files that describes every room, every piece of furniture and equipment, and where the small stuff
lives. Three things are generated from it: a check report (collisions, clear zones, walkways, power, heat, cable
reach, bench space), room layouts you rearrange in Inkscape, and a searchable lab directory for everyone.

**You edit:** `lab-data.xlsx`, the room outlines in `rooms/`, SOPs in `sops/`, photos in `photos/`, all in one
**data folder** (see *Where your data lives*).
**This repository holds the tools, the empty templates and the fictional example only.** Real lab data is kept
outside it; `.gitignore` keeps anything added to `rooms/`, `shapes/`, `sops/` and `photos/` here out of git, apart
from the templates.
**Generated:** everything in the data folder's `build/`. Don't edit it by hand, except the layout drawing
`build/layout/labs.svg`, which you rearrange in Inkscape and then pull back (see *Rearranging in Inkscape*).

## What's in here

| Path | What it is |
|---|---|
| `lab-data.xlsx` | **The data template.** One sheet per kind of thing, with dropdowns, hints and error highlighting. Empty: copy it into your data folder and fill it in there. |
| `labmap.example.ini` | Copy to `labmap.ini` and set where your data folder is (a synced Teams or OneDrive folder, say). |
| `rooms/_TEMPLATE.svg` | Copy once per room and trace the room's outline (instructions inside the file). |
| `shapes/_TEMPLATE.svg` | Only for the rare object that isn't a rectangle, a circle or a group of rectangles. |
| `sops/_TEMPLATE.md` | Copy once per procedure. |
| `photos/` | Photos, linked to objects by file name. See `photos/README.md`. |
| `example/` | A complete, fictional two-room lab filled in the same way: every case below, plus a known list of problems for testing the checks. Has its own `.bat` files to play with, and `reset.bat` to start over. See `example/README.md`. |
| `check.bat`, `layout.bat`, `try-layout.bat`, `pull.bat`, `site.bat` | Double-click shortcuts for the commands: see *Double-click shortcuts* below. |
| `labmap/`, `tests/` | The code that checks, draws and builds the directory, and its tests. |
| `tools/` | Regenerates the empty template and the example workbook: `python tools/make_workbooks.py`. |
| `build/` (in the data folder) | Everything generated: the report, the layout drawing, the directory, move lists, backups of the workbook. |

You can add a `manuals/` folder for PDFs and put the relative path in the `manual` column on the equipment sheet.

## Where your data lives

The tools live here; the data lives in a **data folder** of its own, e.g. a Teams channel's files synced to your
OneDrive. It holds `lab-data.xlsx` (start from this repository's empty one) and, beside it, `rooms/`, `shapes/`,
`sops/` and `photos/` (copy the templates across as you need them). Generated files go to a `build/` folder inside
it: the report, the layout drawing, the directory, move lists and workbook backups.

Tell the tools where it is once: copy `labmap.example.ini` to `labmap.ini` (same folder as this README) and set
`folder`. In File Explorer, open the synced folder, click the address bar and copy the path, e.g.

```
[data]
folder = %USERPROFILE%\Your Organisation\Lab Team - Documents\Lab Atlas
```

`labmap.ini` is personal and never goes to GitHub. Every command then uses that folder and says so on its first
line (`Data: ...`). Without `labmap.ini` they use the folder they're run from; a folder given on the command line
(`python -m labmap check S:\Labs`) or in the `LABMAP_DATA` environment variable wins over both.

With the workbook in OneDrive or Teams:

- **One person keeps it up to date.** Others read the directory and the report. Two people editing the workbook
  while `pull` writes to it is how changes get lost.
- **Close it in Excel before `pull`**, and let OneDrive finish syncing (green tick) before running anything.
- **History:** OneDrive/SharePoint keeps previous versions of the workbook (right-click › Version history), and every
  `pull` saves a copy in `build/backups/` first.
- Right-click the data folder › *Always keep on this device*, so the tools never wait for files to download.

## Double-click shortcuts (.bat files)

Five `.bat` files in this folder run the commands for you, so nobody needs to open a terminal. Double-click one
in File Explorer: a black window opens, shows what happened, and waits for a key press before closing, so read
it first. They work on **your data folder** (from `labmap.ini`), never on the example.

| File | What it does | When to use it |
|---|---|---|
| `check.bat` | Runs every check on `lab-data.xlsx`, writes `build\report.html` and opens it in the browser. | After editing the spreadsheet. |
| `layout.bat` | Draws `build\layout\labs.svg`, **every room in one file**, and opens that folder. | Before rearranging: open `labs.svg` in Inkscape. |
| `try-layout.bat` | Checks the arrangement **as drawn**, compares it with the current one and lists the moves, in `build\report-layout.html`. Writes nothing to `lab-data.xlsx`. | After moving things in Inkscape and saving, to see whether an idea works. As often as you like. |
| `pull.bat` | Writes the arrangement from the layout into `lab-data.xlsx`, saves a printable move list, redraws the layout, then runs the checks and opens the report. | When you're happy with an arrangement and want to keep it. |
| `site.bat` | Builds the lab directory in `build\site` and opens it in the browser. | After any change people should see: new items, photos, SOPs, forms, moves. |

**A typical rearranging session:**

1. `layout.bat`, then open `labs.svg` from the folder that appears (right-click › Open with › Inkscape).
2. Drag things around in Inkscape, between rooms too, and save (`Ctrl+S`, as Inkscape SVG).
3. `try-layout.bat`: read the comparison at the top of the report. Not good yet? Back to Inkscape, change it, save,
   `try-layout.bat` again.
4. Close `lab-data.xlsx` in Excel, then `pull.bat` to keep the arrangement. A backup of the workbook goes to
   `build\backups\` first, and the move list to print goes to `build\move-lists\`.
5. In Inkscape, *File › Revert* to load the redrawn layout. `site.bat` when you want the directory updated.

**Good to know:**

- **Python must be installed** and on the PATH, with `openpyxl` (and `Pillow` for photos in the directory):
  `pip install openpyxl pillow`. If the window says `'python' is not recognized`, reinstall Python with *Add
  python.exe to PATH* ticked, or from the Microsoft Store.
- **Close the workbook in Excel before `pull.bat`**: Excel locks the file. If you forget, `pull.bat` says so and
  writes nothing; close it and run `pull.bat` again. The other files only read the workbook, but unsaved changes
  in Excel aren't seen: save first.
- **`layout.bat` won't overwrite a layout with moves you haven't pulled yet**: it says *kept*. Pull them (or throw
  them away with `python -m labmap layout --force`) to get a fresh drawing.
- **`pull.bat` with nothing to pull** says *No moves to pull* and just runs the checks.
- The windows show a short summary (problems per rule, the moves being written); the full detail is in the report
  that opens in the browser.
- **To try everything on the example first**, use the same five files inside `example/`: they work on the example
  instead of your data. `example/reset.bat` puts the example back as it came after you've played with it.

## Order of work

One walk-around per step. Partial rows are fine: fill in what you know and come back later.

0. **Triage first.** List every piece of equipment (placeables: `id`, `name`, `category`, `room`) and fill `plan`,
   `usage` and `condition` on the equipment sheet. Decide what leaves *before* spending time measuring it.
1. **Rooms.** Measure each room (including the diagonals: walls are rarely square), add a row on `rooms`, and
   draw its outline from `rooms/_TEMPLATE.svg`.
2. **Tape measure → placeables.** Dimensions, clearances, door hinges (see *Measuring protocol*).
   Positions are optional, and quicker in Inkscape: anything without `x`/`y` waits beside its room in the
   layout, ready to drag into place.
3. **Nameplates, manuals and people → equipment.** Power, owner, usage, and what else it needs
   (`needs`: gas, water, drain, exhaust, network...).
4. **Electrics → circuits, then services.** The distribution board first, then every socket, power strip and tap.
5. **Connections → links.** Which PC drives which instrument; cable and tubing limits.
6. **Drawers → items.** Start with the ~50 things people actually hunt for. Grow it on demand: whenever someone
   can't find something, that's the next row.

Any time: **documents** (COSHH forms, risk assessments, calibration and PAT certificates), SOPs and photos.

## Measuring protocol

Agree on this before the walk-arounds, so everyone measures the same way. Whole centimetres, rounded **up**.

- **Everything:** the full envelope, including handles, knobs, feet, and connectors and cables sticking out of the
  back: `w` along the front (the side you use), `d` front to back, `h` to the highest point. Diagonal or odd
  shapes: see *Shapes*.
- **Clearances:** from the manual or the maker, not by eye: ventilation gaps (`clear_back`, sides), room to open a
  lid (`clear_top`), room to stand and work (`clear_front`). Include room to reach the back panel if people have to.
- **Fridges, freezers, cabinets:** which side the door is hinged on (`door`: left, right or both, as you face it).
  The door's swing is kept clear in front, and `door_gap` (settings, 10 cm) beside the hinge so it opens fully.
- **Benches and tables:** the top's height `h`; `free_under` at the **lowest** point underneath (rails, braces,
  drawer runners), not the middle.
- **Equipment:** nameplate power; the services it needs besides power (`needs`); critical or not.
- **Fume hoods, biosafety cabinets, gloveboxes, ovens:** the outside (`w`, `d`, `h`) as usual, and the working
  space inside: `inner_w` (left to right), `inner_d` (sash to rear baffle), `inner_h` (above the work surface, up to
  the sash opening) and `inner_z` (the work surface's height above the floor).
- **Overhead:** ducts, low beams, cable trays, light fittings. Enter them as objects (category `overhead`,
  `mount = wall`, `z` = their underside): anything taller underneath is flagged. Note whether the room has
  **sprinklers** (rooms sheet): nothing may then reach within `sprinkler_clearance` (45 cm) of the ceiling.
- **Floor:** drains, trenches, floor boxes (as services or `structure` objects).
- **Safety equipment:** extinguishers, spill kits, first aid, emergency stops, safety showers: category `safety`,
  `fixed = yes`, with the clear zone your safety rules ask for (`clear_front`).
- **Sockets and strips:** how many sockets, and the rating (`rating_a`: often 13 A for a strip, 10 or 16 A for a
  socket; a UPS: its VA ÷ volts).

## Conventions

### Units and numbers

Centimetres, watts, kilograms, whole numbers only: round to the nearest centimetre. No units in cells (`90`, not
`90 cm`). The example uses 230 V: use your local mains voltage.

### IDs

- UPPERCASE letters, digits, `-` and `.` only: `BENCH-04`, `FRZ-01`, `DB2-C07`.
- The ID goes on a **physical label** on the object. If the directory says `BENCH-04 › PED-01 › D2` and nothing in
  the room says BENCH-04, the directory is useless.
- **Never put the location in an ID.** Things move; that's the point of all this. The location is worked out from
  the parent chain, so `BENCH-04` stays correct wherever it goes.
- Parts and containers get the parent's ID plus a suffix: legs `BENCH-04.A`, drawers `PED-01.D1` (numbered from the
  top), shelves `CAB-01.S1` (from the top).
- Never reuse the ID of something that's been thrown away. The `lists` sheet has the agreed prefixes: add new ones
  there so everyone uses the same ones.

### Where things are: parent, mount, position

Everything sits **in**, **on** or **under** something else. That chain is the location:
`LAB-A › BENCH-04.A › PED-01 › PED-01.D2`.

| `mount` | Meaning | `x`, `y` | `z` |
|---|---|---|---|
| `floor` | stands on the room floor | yes (blank = not placed yet) | no |
| `wall` | fixed to a wall: shelf, window, eyewash, panel | yes | **yes**: height of its underside |
| `on` | on top of `parent`: a bench, or another instrument (stacks) | yes | no (= parent's top) |
| `under` | on the floor, beneath `parent`: pedestal, PC tower, under-bench fridge. Must fit the parent's `free_under` | yes | no |
| `in` | inside `parent`: drawer, cabinet shelf | no | no |
| `part` | a piece of a composed `parent` (bench legs) | yes | no |

`parent` is blank for things standing in, or fixed to, the room itself. `room` is filled on every row, children
included, so you can filter by room.

**Positions are always measured in the parent's frame:**

```
          N = top of the drawing (not compass north)
   0,0 ──────────── x ────────────►
    │  ┌──────────────────────────────┐   BENCH-04.A: in the ROOM frame,
    │  │ SPEC-01 ┐                    │   x from the left wall, y from the top wall
    y  │  x=10   │ y=10               │
    │  │         ┘  (in the BENCH's   │   SPEC-01: in the BENCH frame,
    ▼  │             frame)           │   x from the bench's left end, y from its back edge
       └──────────────────────────────┘
                  front: you stand here   (faces = S)
```

- **In a room:** `x` from the drawing's left edge, `y` from its top edge, to the nearest corner of the footprint.
- **On, under or part of something:** stand in front of the parent, facing it. `x` from its left end, `y` from its
  back edge. This works the same on a diagonal bench.
- **`faces`** = which way the object's front (the side you use) points on the drawing: `N`, `NE`, `E`, `SE`, `S`,
  `SW`, `W` or `NW`. Blank = `S`. The diagonals are for pieces that follow a chamfered corner. For children it's
  relative to the parent, so blank = "same way as the parent", which is almost always right.
- `w` is always measured **along the front**, `d` from front to back. A bench along the right-hand wall faces `W`,
  so its `w` runs top to bottom on the drawing. That's expected: the scripts do the rotating.
- For diagonal objects, `x`/`y` is the top-left corner of their **bounding box**, which isn't a physical corner you
  can measure to. Leave them blank and drag the object into place instead.
- In irregular rooms, where the left or top wall is out of sight from much of the floor, the same applies:
  measure sizes, then drag positions in.

### Shapes

| `shape` | Use for | Size columns |
|---|---|---|
| blank / `rect` | almost everything | `w`, `d`, `h` |
| `circle` | gas cylinders, stools, bins, carboys | `w` = `d` = diameter |
| `group` | L-, U- and T-shaped benches, benches around a chamfer: made of `part`s | blank on the group row |
| `@name` | a genuine one-off drawn in `shapes/name.svg` | `w` × `d` = the profile's bounding box |

**L-shaped bench** (from the example): the group carries the room position; each leg is a rectangle with its own
front, clearance and drawers.

| id | parent | mount | x | y | faces | shape | w | d | h |
|---|---|---|---|---|---|---|---|---|---|
| BENCH-04 | | floor | 0 | 0 | | group | | | |
| BENCH-04.A | BENCH-04 | part | 0 | 0 | | | 240 | 60 | 90 |
| BENCH-04.B | BENCH-04 | part | 0 | 60 | E | | 120 | 60 | 90 |

The inside corner of an L is a dead zone by design, so one leg's clearance running into the other leg (or into
what stands on it) isn't reported as a problem.

**Bench following a chamfered corner** (from the example): the straight runs and the diagonal piece are parts of
one group. The diagonal piece is an ordinary rectangle facing `SW` (or `NE`, `SE`, `NW`).

| id | parent | mount | x | y | faces | shape | w | d | h |
|---|---|---|---|---|---|---|---|---|---|
| BENCH-11 | | floor | 460 | 0 | | group | | | |
| BENCH-11.A | BENCH-11 | part | 0 | 0 | | | 235 | 60 | 90 |
| BENCH-11.B | BENCH-11 | part | 235 | 18 | SW | | 35 | 60 | 90 |
| BENCH-11.C | BENCH-11 | part | 260 | 85 | W | | 215 | 60 | 90 |

Measure every piece **along its front edge**, as usual. Real mitred joints are wider at the back than rectangles
can be, so the model loses a small wedge at the back of each joint: about 0.15 m² with 60 cm deep benches. That
slightly under-counts bench surface, which is the safe direction. If you need a joint exact, draw that piece as a
profile instead.

**Cut-outs are occupants, not holes.** A sink in a benchtop is `SINK-01`, `mount = on`, `parent = BENCH-01`,
`stackable = no`. Same for taps and pipe boxings against the back: model the thing that's in the way, and keep the
bench a plain rectangle. The exception is a column or riser that passes *through* a bench from floor to ceiling:
that's a real notch, so the bench becomes a group of rectangles around it (or a profile). Otherwise the column and
the bench would be reported as colliding.

### Tables and open benches

`free_under` is the clear height underneath a table, desk or open-frame bench: from the floor to the underside
of the top or its rail. The piece then only occupies the band from `free_under` up to its top, so anything
shorter can go underneath, whether or not it's entered as a child: a bin pushed under a table is fine.
Things mounted `under` it are checked against it, so an 85 cm fridge under a bench with 80 cm free is flagged.
Leave it blank for anything solid to the floor, like a cupboard base or an instrument. The walkway check will
still treat the piece as blocking, since nobody walks under a table.

To keep legroom free under a desk, add a `workspace` with `mount = under` (see `WS-02`).

### Stacks

Anything can stand on anything: an SMU on an SMU is `mount = on`, `parent = SMU-01`, usually at `x = 0, y = 0`.
Set `stackable = yes` on each one that has something on it; otherwise the check gives a warning, since most
instruments shouldn't carry weight. Benches, desks, tables, shelves, cabinets and carts count as stackable unless
you say `no`. A stack moves as one in the layouts, and its top is checked against shelves above and the ceiling.

### Windows

A window is `mount = wall` with `z` = sill height and `h` = window height. Something standing in front of it,
between sill and top, is a **warning**, not a problem: benches under the sill are fine. To keep a strip in front of
the window clear as well, give the window a `clear_front`.

### Clearances

`clear_front`, `clear_back`, `clear_left`, `clear_right` are measured relative to the object's own front: left
and right are **your** left and right as you face it. `clear_top` is headroom for lids and sashes.

A clearance applies in the plane the object sits in. For something on a bench, `clear_front` is bench surface kept
free in front of it. For something on the floor, it's floor: standing room, drawer pull-out, door swing. Mandatory
clear zones (eyewash, electrical panel, doors) are just large clearances on those objects, with `fixed = yes`.

To stop working space being silently used up, add it as an object: category `workspace`, `mount = on`, with `h` =
the headroom you need (see `WS-01`).

### Doors and keeping things apart

- **Doors on things:** see *Measuring protocol*. For the room's own doors, a `door`-category object: its `w` and `h`
  are the clear opening. Anything arriving or moving (`plan` = new or relocate) that can't pass through any door of
  its room, even on its side, is a warning.
- **Keeping things apart:** tag objects (`tags` on the placeables sheet: `vibrates`, `vibration-sensitive`,
  `heat-source`, `flammable`...) and the **`keep_apart`** sheet says which tags must be how far apart, edge to edge,
  and whether that's a problem or a warning. It starts with vibration, heat, flammables/oxidisers and noise; add
  your own rows.
- **Services other than power:** `needs` on the equipment sheet (`exhaust; gas:N2; network`) is checked against the
  taps, ports and extraction points on the services sheet within `utility_reach` (3 m). A link on the links sheet
  (gas-line, water-line, exhaust, ethernet) counts too: a GC plumbed to its own cylinders needs no gas tap.

### Inside fume hoods and other enclosures

Give a fume hood (or a biosafety cabinet, glovebox, oven...) its working space: `inner_w`, `inner_d`, `inner_h` and
`inner_z` (see *Measuring protocol*). The space is taken to be centred left to right and flush with the front. Then
anything kept in it is a row with `parent` = the hood, `mount = in`, and an `x` and `y` measured inside: from the
working space's left edge and its back (the rear baffle), as you face the hood. It stands on the work surface.

- It has to fit: inside the working space on the plan, and no taller than `inner_h` less `fit_margin`.
- Things inside can't overlap each other.
- In a fume hood, work less than `sash_clearance` (15 cm) behind the sash is a warning: the usual rule for keeping
  fumes inside.
- The report's *Fume hoods and enclosures* table shows how much of each working space is used, the strip kept clear
  behind the sash, how much of the volume the things inside take up, and the largest free spot.
- In the layout, the working space is a dashed outline inside the hood. Drop something inside it and `pull` puts it
  `in` the hood; drag it out onto a bench and it's `on` the bench again.
- A drawer or cabinet shelf (`mount = in` with no `x` and `y`) works as before: no position, just contents.

### Containers

Drawers, cabinet shelves and boxes are ordinary placeables. For `mount = in`, enter the **internal** usable size.
`fill` (0–100, eyeballed) finds half-empty drawers to consolidate; `checked` is the date the contents were last
verified, shown in the directory so people know how far to trust it.

### Items, ordering and spare parts

Each row on the **`items`** sheet is something kept in a `container` (a drawer, shelf or box ID). Things kept
outside the mapped rooms, like a central store, leave `container` blank and say where in `elsewhere` instead.

- **Ordering:** `rs_part` is the RS Components stock number (e.g. `123-4567`); the directory turns it into a link to
  RS. `buy_link` is any other supplier or manufacturer page. Either or both.
- **Spare parts:** `spare_for` lists the equipment it's a spare or replacement for, separated by `;`. Each of those
  pages gets a *Spare parts* table: stock, how many to keep, where it is, where to order it.
- **Required spares:** fill `min_qty` (how many to keep) to have stock checked. The stock count is the first number
  in `qty` (`3`, `~20`, `2 boxes`), and a blank `qty` counts as none. None in stock is a warning, and so is fewer
  than `min_qty`. Leave `min_qty` blank for spares you don't need to keep stocked.

### Power and services

- **circuits:** one row per breaker, named as on the distribution board (`DB2-C07`).
- **services:** every socket, power strip, gas/vacuum/air/water tap and network port. Wall sockets have a blank
  `parent`; sockets on a bench service spine have the bench as `parent` and move with it. Power strips have
  `fed_by` = the socket they're plugged into (strip-into-strip will be flagged).
- **equipment:** `plugs`, `watts_typ`, `watts_max`. If the nameplate only gives amps, W = V × A. `critical = yes`
  for things that must never lose power (freezers, incubators). `outlet` is optional: blank = nearest socket.
- **Ratings:** a socket's or strip's `rating_a` is checked against what runs through it, including strips plugged
  into it; the circuit is checked against its breaker as well.
- An instrument with separately plugged units that take up their own space (pump, chiller, controller) gets one
  placeable per unit.

### Links

Anything that has to stay within a certain distance of something else: USB, serial, GPIB, network, video, gas or
water tubing, exhaust. `max_len` (cm) blank = the default for that type on the `lists` sheet.

### SOPs and photos

- **SOPs:** one Markdown file per procedure in `sops/`, named `<ID>-<topic>.md`. The `equipment:` line at the top
  decides which objects it belongs to; `[[ID]]` anywhere in the text becomes a link.
- **Photos:** named after the ID, e.g. `BENCH-04.jpg`, `BENCH-04--reference.jpg`. Details in `photos/README.md`.
  An object's main photo (`<ID>.jpg`) is shown at the top of its page in the directory.

### Forms and certificates

The **`documents`** sheet lists COSHH assessments, risk assessments, calibration certificates, PAT tests and service
records. The forms themselves stay wherever they already live; each row records its `status` (approved, pending,
draft, withdrawn), when it was `filled`, when it `expires`, who approved it, and a `link`: a web address, or a full
path such as `S:\Safety\RA-003.pdf` or `\\server\share\COSHH\014.pdf`. `applies_to` lists everything it covers,
separated by `;` (equipment, benches, sockets, or a whole room), and it shows on each of their directory pages with
its status and an expiry badge.

The checks treat an expired form as a problem, and one that isn't approved, or expires within
`expiry_warning_days` (settings sheet, default 30), as a warning.

## Excel and Inkscape

**Excel**

- Keep it as `.xlsx`. Saving as CSV loses the dropdowns and lets Excel mangle serial numbers and asset tags.
- Don't delete or rename row 1 (column names) or row 2 (hints). You can reorder columns and add your own extra
  columns: they'll be read by name, and unknown ones are ignored.
- Hover over a column name for an explanation. **Red** = duplicate ID, or an ID that doesn't exist where it points.
  **Orange** = a child in a different room from its parent. Pasted values skip the dropdown checks, but the
  highlighting still works.
- To add a dropdown value (a new category, say), insert a row *inside* the list on the `lists` sheet so the range
  grows with it.

**Inkscape**

- Always save as **Inkscape SVG** (the default). Never *Optimized SVG*: it can strip or rename element IDs, and the
  IDs are how the scripts know which object is which.
- The documents are at real scale: 1 unit = 1 cm. The Measure tool (`M`) reads real centimetres, and the grid is
  10 cm with a heavier line every metre.
- Type room outlines rather than drawing them: *Edit › XML Editor* (`Ctrl+Shift+X`), select `interior`, and enter
  e.g. `M 0,0 H 720 V 540 H 0 Z`. The top of `rooms/_TEMPLATE.svg` shows how to write chamfered corners.
- In the generated layout, drag whole objects. Don't ungroup them or edit their shapes: sizes come from the
  spreadsheet, and only positions and rotations are read back. Rotate in 45° steps only (*Object › Transform ›
  Rotate*).

## The example

`example/` is a complete, fictional two-room lab: a 720 × 540 cm wet lab (`LAB-A`) and an L-shaped instrument room
with a chamfered corner, a column and a pilaster (`LAB-B`). It has 116 placeables, 44 pieces of equipment, sockets,
circuits, links, 51 items, SOPs and placeholder photos, covering every case in this README.

It also contains **exactly fourteen deliberate problems and seven deliberate warnings**, each testing a different
rule. The problems: a blocked clear zone, a lid hitting a shelf, an overlap, a fridge too tall for the space under
a bench, an object outside the room, a cabinet too close to the sprinklers, too many plugs on a socket, a strip plugged into a strip, an overloaded socket, an overloaded circuit, a critical freezer on a shared
circuit, too much heat for the cooling, a USB run that's too long, and an exhaust point out of reach. The warnings:
a pending COSHH form, a spare part out of stock, one running low, a vacuum pump next to a balance, a glovebox
too big for the door, a hotplate too close to a fume hood's sash, and a spare part still listed for an oven that's
been decommissioned. `example/README.md` lists each one with the exact expected finding, and the rules behind them.

## Running the checks

Needs Python 3 with `openpyxl` (`pip install openpyxl` if it's missing). From this folder:

```
python -m labmap check             # your data: the folder in labmap.ini (or this one)
python -m labmap check example     # the worked example
python -m labmap check --open      # ...and open the report in the browser
```

Or double-click `check.bat`. The report goes to `build/report.html` (`example/build/report.html` for the example):
the problems grouped by rule, then progress, rooms, bench space, fume hoods, power, connections, documents, spare parts, triage, decommissioning, workflow groups,
containers and what isn't placed yet. Findings are **problems** (something's wrong) or **warnings** (worth a look:
covered windows, stacks on things not marked stackable, forms not approved or about to expire, spare parts
out of stock or running low, things closer than `keep_apart` suggests, arrivals too big for the door). It's fine
to run on half-filled data: missing data shows up under progress, not as problems. `example/README.md` explains
each rule.

The thresholds are on the **`settings` sheet** of `lab-data.xlsx`: walkway width (60 cm), how close a clear zone
must be to a path (30 cm), clear-zone height (200 cm), what counts as in the way (anything starting below
150 cm), circuit limit (80%), heavy load (1000 W), the raster size (5 cm), `fit_margin` (2 cm of slack for
measuring error and ventilation, under benches, below the ceiling and through doors), `door_gap` (10 cm),
`utility_reach` (3 m), `sprinkler_clearance` (45 cm) and `sash_clearance` (15 cm). Change them to match your
safety office's numbers.

`python -m unittest discover -s tests -t .` confirms the example still produces exactly its fourteen problems and
seven warnings.

## Rearranging in Inkscape

```
python -m labmap layout          # draws build/layout/labs.svg, every room (or double-click layout.bat)
                                 # ...open it in Inkscape, drag things around, save...
python -m labmap check --layout  # checks it as drawn, compares, lists the moves (or double-click try-layout.bat)
python -m labmap pull            # keeps it: writes it into lab-data.xlsx (or double-click pull.bat)
```

**One file, every room.** `labs.svg` has all the rooms side by side, each with its own *not placed yet* area, so
equipment can be reorganised across labs as easily as across a bench. It replaces the per-room files: one drawing
means nothing to keep in sync. Zoom to a room with the mouse wheel, or `5` to fit the whole drawing.

**Try before you keep.** `check --layout` reads the drawing, runs every check on it and writes
`build/report-layout.html`, leaving `lab-data.xlsx` alone. At the top: the arrangement in the spreadsheet against
the one drawn (problems and warnings, rule by rule, free bench space per room, how spread out each workflow group
is, better in green and worse in red), and the **move list**: what moves where, and which socket it plugs into
before and after. `pull` when you're happy; it saves the move list as a printable page with a tick box per move in
`build/move-lists/`, for moving day.

- **Every object moves on its own.** Click it and drag it. Things on a bench don't follow the bench: to move a bench
  with everything on and under it, drag a box around it (rubber-band select) and move the lot.
- **Drop an instrument on another bench** and `pull` gives it that bench as its new `parent`. It stands on the
  topmost thing under its centre that can carry it: a bench, table, desk, shelf, cabinet or cart, or anything with
  `stackable = yes` (so an SMU dropped on another SMU joins the stack). Something `under` a bench goes under
  whichever bench with `free_under` it's dragged beneath. Dragged clear of everything, it's standing on the floor
  now (`mount` becomes `floor`), and `pull` says so.
- **From the floor onto a bench, or back: change its layer.** Select it and use *Layer › Move Selection to Layer
  Above / Below* (`Shift+Page Up` / `Shift+Page Down`), then drag it into place. On *on benches* it stands on
  whatever it's dropped on; on *under benches* it goes under the bench above it; on *floor and benches* it
  stands on the floor. `pull` sets `mount` and `parent` to match, and says so. (The *walls and shelves* layer also
  holds things standing on shelves, so moving something there changes nothing; hang things on walls in the
  spreadsheet: `mount = wall` and a `z`.)
- **Drop it in another room** and its `room` changes too. What's inside it goes along (a pedestal's drawers), and so
  do sockets on its service spine. Equipment whose `outlet` stays behind in the old room gets it cleared (the
  nearest socket is assumed until you fill in the new one), and `pull` says so. Something dropped outside every
  room and waiting area is left as it was.
- **Layers** (*Layer › Layers and Objects*): *floor and benches*, *under benches*, *on benches*, *walls and
  shelves*, for all rooms at once. Hide or lock the ones on top to reach what's below, such as a freezer under a
  bench with an instrument on it. Things under benches are drawn pale blue with a dashed outline.
- **New equipment**: give it a `room` and a `mount` (or change its layer later) and leave `parent`, `x` and `y` blank. It waits
  in that room's *not placed yet* area; drag it onto a bench and `pull` fills in all three. Drag something into a
  waiting area to take it out of the layout: its x and y are cleared.
- **Rotate** in 45° steps (*Object › Transform › Rotate*). Anything else is rounded to the nearest 45°.
- Walls and your notes are locked. Objects with `fixed = yes` can still be dragged, but `pull` ignores the move
  and says so; what stands on them is measured from where they really are.
- Sizes come from the spreadsheet: resizing in Inkscape is ignored.
- `pull` writes into `lab-data.xlsx`, so save and close it in Excel first. A copy goes to `build/backups/` every
  time, and `pull --dry-run` shows the changes without writing them. Afterwards the drawing is redrawn to match:
  in Inkscape, *File › Revert* to load the new version.
- `layout` won't overwrite a drawing with moves you haven't pulled yet. `layout --force` throws them away.

## Decommissioning equipment or furniture

Something leaving the lab goes through four steps. Nothing is deleted: the row stays as a record.

**1. Decide.** Set `plan = dispose` on the equipment sheet (for furniture, which has no equipment row, just go to
step 2 when it's decided). It stays on the maps and in every check. The report's *Triage* table shows how much bench
or floor space removing it frees, and its *Decommissioning* section starts the to-do list: everything still
pointing at it.

**2. Try the lab without it.** In `labs.svg`, drag it into its room's *not placed yet* area and run
`try-layout.bat`: things waiting there are left out of the placement checks, so the comparison shows what removing
it gains. `pull` clears its `x` and `y` if you keep that.

**3. Empty it and unhook it** before it physically leaves. The *Decommissioning* section of the report lists what's
left for each thing marked `dispose`:

- **Items in its drawers or on its shelves:** give them a new `container`, or delete the rows.
- **Things standing on, under or in it:** move them in the layout; `pull` re-parents them.
- **Sockets on its service spine:** give them a new `parent`, or delete them.
- **Links** (cables and tubing to or from it): delete the rows.
- **Documents** (COSHH, calibration): take its ID out of `applies_to`.
- **Spare parts:** take its ID out of `spare_for`; delete spares that only fit it.
- **SOPs:** rename the file with a leading `_` (e.g. `_SPEC-02-operation.md`): it's kept, but the directory skips it.
- **Photos:** move them out of `photos/`.

When the list says *nothing: ready to go*, it's clean.

**4. When it's gone,** put the date in the placeables sheet's `decommissioned` column (or set `plan =
decommissioned` on the equipment sheet). Don't delete the rows: they're the record of what it was, its asset tag
and serial, and when it left. From then on it's out of the maps, the checks, the layout, the room lists and the
search, and its drawers and parts go with it. Its directory page stays, marked *Decommissioned on ...*, so old
links still work. Anything still pointing at it is a **warning** (*Still pointing at something decommissioned*),
so nothing is left behind. **Never reuse its ID.**

## The lab directory

```
python -m labmap site         # builds build/site/ (or double-click site.bat)
```

Copy the whole `build/site` folder to a shared drive; people open `index.html` in any browser. It needs no
server and no internet. It has:

- **Search** across items (and their synonyms and RS numbers), objects, sockets and the text of every SOP. Searching "allen key"
  finds the hex key set and says it's in `LAB-A › BENCH-04 › BENCH-04.A › PED-01 › PED-01.D2`.
- **A page per object**: its photo, where it is, a map with it highlighted, its reference photo ("how it should
  look"), what's on, under and in it, the items kept there, equipment details (owner, usage, which socket and
  circuit it's on), its SOPs, its forms and certificates with their status and expiry, its spare parts with stock
  and where to order them (RS number or supplier link), and what it's connected to.
- **Where it is, at a glance**: every object, drawer and socket page has a red *Show on map* button at the top.
  The map marks the spot with a pulsing red pin, an arrow and its name, drawn above everything else so a drawer
  under a bench is still easy to find, and the object itself flashes. Arriving from a search, the item's row
  flashes too. (With *reduce motion* switched on in Windows, nothing moves.)
- **Maps you can point at**: hovering highlights the object under the mouse (the innermost one, not the bench it
  stands on) and names it; clicking opens its page. Labels stay upright, fully inside their object with a margin,
  clear of each other and of whatever stands on top; each one is moved around its object before it's made
  smaller, and one that can't be shown at a readable size is left off (hover to see it).
- **Level views** above every map: *Everything*, *Floor* (what stands on the floor, including what's under the
  benches), *Bench tops* (benches, tables, desks and what stands on them) and *Walls and shelves* (wall-mounted
  things, and anything starting 120 cm up). The other levels fade and can't be clicked, so a freezer under a
  bench with an instrument on top can be picked in *Floor*. Each level gets its own labels. An object's page
  opens on its own level; otherwise the last one you picked is remembered. The check report has the same switch.
- **Sockets and taps** button next to the level views: shows every socket, strip, network port and gas, water or
  vacuum tap on the plan, with a dashed line from each device to what it's plugged into. A socket's number is how
  many are still free (green free, amber full, red "+2" = two plugs too many); taps and ports are circles with a
  letter (G gas, W water, V vacuum, A air, N network…). Hover over one to see its circuit and what it feeds; the
  lines light up. Click it to open its page, which opens with the sockets shown. Sockets without an x and y aren't
  drawn. The check report has the same button.
- **A page per socket, strip or tap** (which circuit, what's plugged in), per room (a clickable plan) and per SOP
  (with `[[ID]]` links working).
- A copy of the check report.

Photos are shrunk copies (your originals in `photos/` are never changed). Rebuild the site whenever the
spreadsheet, SOPs or photos change.

## The code

`labmap/` is a small Python package (it needs only `openpyxl`, plus `Pillow` for shrinking photos):
`model.py` reads the workbook and SVGs, `geometry.py` places everything, `checks.py` holds the rules and their
thresholds, `report.py`, `layout.py` and `site.py` write the outputs. `tests/` runs against the example:
`python -m unittest discover -s tests -t .`

`tools/make_workbooks.py` regenerates the empty `lab-data.xlsx` and the example workbook from `tools/schema.py`
(the sheets and columns, with their hints and dropdowns), `tools/lists.py` (dropdown values) and
`tools/example_*.py` (the example's rows). Change a column there, never by hand in the template, then run it.
