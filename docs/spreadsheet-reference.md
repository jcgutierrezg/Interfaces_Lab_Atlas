# Spreadsheet reference

[← Back to the README](../README.md)

How each kind of thing is described in `lab-data.xlsx`: units, IDs, where things are, shapes, clearances and every other column. Hover over a column name in the spreadsheet for a short version.

## Units and numbers

Centimetres, watts, kilograms, whole numbers only: round to the nearest centimetre. No units in cells (`90`, not
`90 cm`). The example uses 230 V: use your local mains voltage.

## IDs

- UPPERCASE letters, digits, `-` and `.` only: `BENCH-04`, `FRZ-01`, `DB2-C07`.
- The ID goes on a **physical label** on the object. If the directory says `BENCH-04 › PED-01 › D2` and nothing in
  the room says BENCH-04, the directory is useless.
- **Never put the location in an ID.** Things move; that's the point of all this. The location is worked out from
  the parent chain, so `BENCH-04` stays correct wherever it goes.
- Parts and containers get the parent's ID plus a suffix: legs `BENCH-04.A`, drawers `PED-01.D1` (numbered from the
  top), shelves `CAB-01.S1` (from the top).
- Never reuse the ID of something that's been thrown away. The `lists` sheet has the agreed prefixes: add new ones
  there so everyone uses the same ones.

## Where things are: parent, mount, position

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

## Shapes

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

## Tables and open benches

`free_under` is the clear height underneath a table, desk or open-frame bench: from the floor to the underside
of the top or its rail. The piece then only occupies the band from `free_under` up to its top, so anything
shorter can go underneath, whether or not it's entered as a child: a bin pushed under a table is fine.
Things mounted `under` it are checked against it, so an 85 cm fridge under a bench with 80 cm free is flagged.
Leave it blank for anything solid to the floor, like a cupboard base or an instrument. The walkway check will
still treat the piece as blocking, since nobody walks under a table.

To keep legroom free under a desk, add a `workspace` with `mount = under` (see `WS-02`).

## Stacks

Anything can stand on anything: an SMU on an SMU is `mount = on`, `parent = SMU-01`, usually at `x = 0, y = 0`.
Set `stackable = yes` on each one that has something on it; otherwise the check gives a warning, since most
instruments shouldn't carry weight. Benches, desks, tables, shelves, cabinets and carts count as stackable unless
you say `no`. In the layout each unit of a stack can be dragged on its own (drag a box around the stack to move
it whole), and its top is checked against shelves above and the ceiling.

## Windows

A window is `mount = wall` with `z` = sill height and `h` = window height. Something standing in front of it,
between sill and top, is a **warning**, not a problem: benches under the sill are fine. To keep a strip in front of
the window clear as well, give the window a `clear_front`.

## Clearances

`clear_front`, `clear_back`, `clear_left`, `clear_right` are measured relative to the object's own front: left
and right are **your** left and right as you face it. `clear_top` is headroom for lids and sashes.

A clearance applies in the plane the object sits in. For something on a bench, `clear_front` is bench surface kept
free in front of it. For something on the floor, it's floor: standing room, drawer pull-out, door swing. Mandatory
clear zones (eyewash, electrical panel, doors) are just large clearances on those objects, with `fixed = yes`.

To stop working space being silently used up, add it as an object: category `workspace`, `mount = on`, with `h` =
the headroom you need (see `WS-01`).

## Doors and keeping things apart

- **Doors on things:** see [Measuring protocol](collecting-data.md#measuring-protocol). For the room's own doors, a `door`-category object: its `w` and `h`
  are the clear opening. Anything arriving or moving (`plan` = new or relocate) that can't pass through any door of
  its room, even on its side, is a warning.
- **Keeping things apart:** tag objects (`tags` on the placeables sheet) and the **`keep_apart`** sheet says which
  tags must be how far apart, edge to edge, and whether that's a problem or a warning. An object's **category counts
  as a tag too**, so a rule can name `laser` or `door` without tagging anything. The sheet starts with:

  | Tag | Away from | Distance | Level | Why |
  |---|---|---|---|---|
  | `vibrates` | `vibration-sensitive` | 100 cm | warning | pumps and chillers shake probe stations, balances, microscopes, optics |
  | `emits-light` | `needs-dark` | 200 cm | warning | stray light from solar simulators, lasers and lamps spoils dark I-V, PL, EQE |
  | `laser` (category) | `door` (category) | 150 cm | warning | class 3B / 4 beams away from doorways, or behind interlocked curtains |
  | `emi-source` | `emi-sensitive` | 150 cm | warning | motors, RF and high-voltage supplies add noise to low-current measurements |
  | `ignition-source` | `flammable` | 300 cm | problem | hotplates, furnaces, corona and sparks away from solvents |
  | `flammable` | `oxidiser` | 300 cm | problem | stored apart, or in separate cabinets |
  | `heat-source` | `heat-sensitive` | 50 cm | warning | samples, gloveboxes and fridges next to furnaces and lamp housings |
  | `noisy` | `quiet` | 200 cm | warning | desks and write-up areas away from pumps and compressors |

  Typical tags: a solar simulator `emits-light; heat-source`; a laser or LED source `emits-light`; a dark box or
  PL / EQE setup `needs-dark`; a vacuum pump `vibrates; noisy; emi-source`; a corona box `high-voltage;
  ignition-source; emi-source`; SMUs, electrometers and lock-ins `emi-sensitive`; a probe station or optical table
  `vibration-sensitive`; hotplates and furnaces `heat-source; ignition-source`; a solvent cabinet `flammable`. Add
  your own tags and rows.
- **Services other than power:** `needs` on the equipment sheet (`exhaust; gas:N2; network; earth`) is checked against the
  taps, ports and extraction points on the services sheet within `utility_reach` (3 m). A link on the links sheet
  (gas-line, water-line, exhaust, ethernet) counts too: a GC plumbed to its own cylinders needs no gas tap.

## Inside fume hoods and other enclosures

Give a fume hood (or a biosafety cabinet, glovebox, oven...) its working space: `inner_w`, `inner_d`, `inner_h` and
`inner_z` (see [Measuring protocol](collecting-data.md#measuring-protocol)). The space is taken to be centred left to right and flush with the front. Then
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

## Containers

Drawers, cabinet shelves and boxes are ordinary placeables. For `mount = in`, enter the **internal** usable size.
`fill` (0–100, eyeballed) finds half-empty drawers to consolidate; `checked` is the date the contents were last
verified, shown in the directory so people know how far to trust it.

## Items, ordering and spare parts

Each row on the **`items`** sheet is something kept in a `container` (a drawer, shelf or box ID). Things kept
outside the mapped rooms, like a central store, leave `container` blank and say where in `elsewhere` instead.

- **Ordering:** `rs_part` is the RS Components stock number (e.g. `123-4567`); the directory turns it into a link to
  RS. `buy_link` is any other supplier or manufacturer page. Either or both.
- **Spare parts:** `spare_for` lists the equipment it's a spare or replacement for, separated by `;`. Each of those
  pages gets a *Spare parts* table: stock, how many to keep, where it is, where to order it.
- **Required spares:** fill `min_qty` (how many to keep) to have stock checked. The stock count is the first number
  in `qty` (`3`, `~20`, `2 boxes`), and a blank `qty` counts as none. None in stock is a warning, and so is fewer
  than `min_qty`. Leave `min_qty` blank for spares you don't need to keep stocked.

## Power and services

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

## Links

Anything that has to stay within a certain distance of something else: USB, serial, GPIB, network, video, gas or
water tubing, exhaust. `max_len` (cm) blank = the default for that type on the `lists` sheet.

## SOPs and photos

- **SOPs:** one Markdown file per procedure in `sops/`, named `<ID>-<topic>.md`. The `equipment:` line at the top
  decides which objects it belongs to; `[[ID]]` anywhere in the text becomes a link.
- **Photos:** named after the ID, e.g. `BENCH-04.jpg`, `BENCH-04--reference.jpg`. Details in [photos/README.md](../photos/README.md).
  An object's main photo (`<ID>.jpg`) is shown at the top of its page in the directory.

## Forms and certificates

The **`documents`** sheet lists COSHH assessments, risk assessments, calibration certificates, PAT tests and service
records. The forms themselves stay wherever they already live; each row records its `status` (approved, pending,
draft, withdrawn), when it was `filled`, when it `expires`, who approved it, and a `link`: a web address, or a full
path such as `S:\Safety\RA-003.pdf` or `\\server\share\COSHH\014.pdf`. `applies_to` lists everything it covers,
separated by `;` (equipment, benches, sockets, or a whole room), and it shows on each of their directory pages with
its status and an expiry badge.

The checks treat an expired form as a problem, and one that isn't approved, or expires within
`expiry_warning_days` (settings sheet, default 30), as a warning.
