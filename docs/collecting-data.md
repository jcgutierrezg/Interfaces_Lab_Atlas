# Collecting the data

[← Back to the README](../README.md)

In what order to fill in the spreadsheet, and how to measure so everyone measures the same way.

## Order of work

One walk-around per step. Partial rows are fine: fill in what you know and come back later.

0. **Triage first.** List every piece of equipment (placeables: `id`, `name`, `category`, `room`) and fill `plan`,
   `usage` and `condition` on the equipment sheet. Decide what leaves *before* spending time measuring it.
1. **Rooms.** Measure each room (including the diagonals: walls are rarely square), add a row on `rooms`, and
   draw its outline from `rooms/_TEMPLATE.svg`.
2. **Tape measure → placeables.** Dimensions, clearances, door hinges (see [Measuring protocol](#measuring-protocol)).
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
  shapes: see [Shapes](spreadsheet-reference.md#shapes).
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
