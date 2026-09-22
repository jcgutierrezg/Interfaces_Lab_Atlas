# How to add new things

[← Back to the README](../README.md)

One recipe per kind of thing. Everything is a row in `lab-data.xlsx` (in your data folder) unless it says
otherwise; the columns not mentioned can stay blank and be filled in later. `example/lab-data.xlsx` has a worked
row for every case: find a similar one and copy it. After adding, run `check.bat` (data problems show up at the
top of the report), then `layout.bat` to place it, and `site.bat` to update the directory.

Before any of them: **pick an ID** (see [IDs](spreadsheet-reference.md#ids)): unique, UPPERCASE, a prefix from the `lists` sheet (`BENCH-`,
`FRZ-`, `PC-`...) and a number never used before, not even by something that's gone. Put it on a label on the
thing itself.

## A room

1. `rooms` sheet: `id` (e.g. `LAB-C`), `name`, `width` and `depth` (the outline's bounding box, cm), `ceiling` (the
   lowest point), `shell` = `LAB-C.svg`. If you know them: `cooling` (W), `sprinklers` (yes/no).
2. Copy `rooms/_TEMPLATE.svg` to `rooms/LAB-C.svg` in your data folder and type the outline in it (instructions at
   the top of the file). Only the empty room goes there: doors, windows and everything else are rows.
3. Its doors: a `placeables` row each with category `door`, `mount = floor`, `w` = the clear opening, `h` = its height,
   `clear_front` = the swing, `fixed = yes`. Windows: category `window`, `mount = wall`, `z` = the sill height.
4. `layout.bat`: the new room appears in `labs.svg` beside the others.

## Furniture: a bench, table, desk, cabinet, shelf, cart

1. `placeables`: `id`, `name`, `category`, `room`, `mount = floor` (a wall shelf: `mount = wall` and `z` = its
   underside), `w`, `d`, `h`, and its clearances (`clear_front` for standing room, ...).
2. Open underneath (tables, desks, open-frame benches): `free_under` = the clear height below, at the lowest point.
   Built in (plumbing, fixed to the wall): `fixed = yes`.
3. An L-shaped or odd bench: `shape = group` on one row, plus one row per straight piece (`BENCH-05.A`, `.B`,
   `mount = part`, `parent = BENCH-05`); see [Shapes](spreadsheet-reference.md#shapes). Truly odd shapes: a profile in `shapes/` (see [Shapes](spreadsheet-reference.md#shapes)).
4. Leave `x` and `y` blank: it waits in the room's *not placed yet* area in `labs.svg`; drag it into place and
   `pull.bat`.

## Equipment: an instrument, computer, fridge, freezer

1. `placeables`: as for furniture, with its `category` (instrument, computer, freezer...). Standing on a bench:
   `mount = on` (leave `parent` blank: dropping it on a bench in the layout fills it in). Under a bench: `mount =
   under`. On the floor: `mount = floor`. Fridges, freezers, cabinets: `door` = the hinge side.
2. `equipment` sheet, same `id`: maker, model, serial, asset tag, owner; `plan`, `usage`; `plugs`, `watts_typ`,
   `watts_max`, `critical`; `needs` (gas, water, drain, exhaust, network, e.g. `exhaust; gas:N2`); `outlet` only
   if you know which socket it's in (blank = the nearest).
3. Anything that must stay close to another instrument (USB, GPIB, gas line): a row on the `links` sheet.
4. Vibrates, sensitive to vibration, gives off heat, flammable...: `tags` (see [Doors and keeping things apart](spreadsheet-reference.md#doors-and-keeping-things-apart)).
5. Stacked on another instrument (SMUs): `mount = on`, `parent` = the one below, and `stackable = yes` on the one
   below. Or drop it on top of it in the layout.
6. Arriving but not here yet: `plan = new`, no `x`/`y`. The report warns if it won't fit through the door.
7. Optional: its main photo `photos/<ID>.jpg`, its SOP, its forms on the `documents` sheet (recipes below).

## Something inside a fume hood (or biosafety cabinet, glovebox, oven)

1. The hood needs its working space once: `inner_w`, `inner_d`, `inner_h`, `inner_z` (see [Inside fume hoods](spreadsheet-reference.md#inside-fume-hoods-and-other-enclosures)).
2. The thing inside: `parent` = the hood, `mount = in`, `x`/`y` measured from the working space's left edge and its
   back. Or drop it inside the hood's dashed outline in the layout.

## Drawers, cabinet shelves, boxes

1. A drawer unit or cabinet is ordinary furniture (above). Each drawer or shelf is a row of its own: `id` =
   the parent's ID plus `.D1`, `.D2`... (drawers, from the top) or `.S1`, `.S2`... (shelves, from the top),
   `category = drawer` (or `shelf`), `parent` = the unit, `mount = in`, no `x`/`y`, and `w`, `d`, `h` = the
   **inside** usable size.
2. A box or tray on a bench or shelf: category `container`, `mount = on`, placed like anything else.
3. Optional: `fill` (how full, %) and `checked` (the date you last checked its contents).

## Items: tools, consumables, spare parts

1. `items` sheet: `id` = the next `I-` number (`I-0052`), `name`, `synonyms` (every other name people would search
   for), `container` = the drawer, shelf or box it lives in (or `elsewhere`, if it's kept outside these labs),
   `qty`, `category`.
2. Where to buy it: `rs_part` (RS stock number) and/or `buy_link`.
3. A spare part: `spare_for` = the equipment it fits; `min_qty` if it has to be kept in stock (fewer is a warning).
4. Optional photo: `photos/I-0052.jpg`.

## Sockets, power strips, taps, network ports

1. `circuits` sheet, once per breaker: `id` as on the distribution board (`DB2-C12`), `panel`, `rating_a`, `volts`.
2. `services` sheet: `id` (`OUT-14`, `STRIP-06`, `NET-04`...), `type`, `room`, and where it is: `x`, `y` from the
   room's top-left and `z` above the floor; on a bench service spine, `parent` = the bench and `x`/`y` on the bench
   (it then moves with it). `sockets` = how many; `rating_a` if known.
3. A wall socket: `circuit`. A power strip: `fed_by` = the socket it's plugged into (never another strip). Gas,
   water, vacuum, air, network, extraction: `medium` (`N2`, `DI water`, `1 GbE`...).

## Something overhead, or safety equipment

- Duct, beam, cable tray, light fitting: category `overhead`, `mount = wall`, `z` = its underside, `fixed = yes`.
- Eyewash, safety shower, extinguisher, spill kit, first aid, emergency stop: category `safety`, `fixed = yes`, and
  the `clear_front` your safety rules ask for.

## An SOP

1. Copy `sops/_TEMPLATE.md` to `sops/<ID>-<topic>.md` in your data folder (e.g. `CEN-01-operation.md`).
2. Fill in the top: `title`, and `equipment: [CEN-01]` (every ID it applies to). It then shows on each of their
   pages. Write `[[ID]]` anywhere in the text to link to an object, drawer, socket or item.
3. To retire one, rename it with a leading `_`: the directory skips it.

## Photos

Save them in `photos/` in your data folder, named after the ID: `BENCH-04.jpg` (the main photo),
`BENCH-04--2.jpg` (more), `BENCH-04--reference.jpg` (how the area should be kept), `PED-01.D2.jpg` (a drawer's
contents), `I-0001.jpg` (an item). Straight from the phone is fine; see [photos/README.md](../photos/README.md).

## Forms and certificates (COSHH, risk assessment, calibration, PAT)

`documents` sheet: `id` (the form's own reference), `type`, `title`, `applies_to` = every ID it covers (equipment,
benches, sockets, or a whole room, separated by `;`), `status`, `filled`, `expires`, `approved_by`, and `link` to
where the form itself is kept. Expired is a problem; pending or about to expire, a warning.

## A new dropdown value, or a new keep-apart rule

- A category, plan, service type...: on the `lists` sheet, **insert** a row inside that list (not after its last
  entry) so the dropdown grows with it.
- Two kinds of things that must be kept apart: a row on the `keep_apart` sheet (`tag`, `away_from`, `distance`,
  `level`), and those tags in the `tags` column of the objects concerned.
