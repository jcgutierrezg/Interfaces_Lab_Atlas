# Rearranging in Inkscape

[← Back to the README](../README.md)

```
python -m labmap layout          # draws build/layout/labs.svg, every room (or double-click layout.bat)
                                 # ...open it in Inkscape, drag things around, save...
python -m labmap check --layout  # checks it as drawn, compares, lists the moves (or double-click try-layout.bat)
python -m labmap pull            # keeps it: writes it into lab-data.xlsx (or double-click pull.bat)
python -m labmap xy BENCH-11.B   # where its corners are, and the x, y that puts one where you measured it
```

The layout is drawn at real scale with a **10 cm grid**, a metre in bold, and every room's origin sits on a grid
line, so a grid square is 10 cm in room coordinates wherever you are. Snapping to it is on: drag a bench and its
bounding box lands on round centimetres. In Inkscape, `#` shows or hides the grid and `%` turns snapping on and
off (View › Page Grid, and the snapping toggle at the top right).

Whatever you change there — grid spacing, snapping, zoom — is kept when the layout is redrawn: the file's
`namedview` is carried over from the old one.

**One file, every room.** `labs.svg` has all the rooms side by side, each with its own *not placed yet* area, so
equipment can be reorganised across labs as easily as across a bench. It replaces the per-room files: one drawing
means nothing to keep in sync. Zoom to a room with the mouse wheel, or `5` to fit the whole drawing.

**Try before you keep.** `check --layout` reads the drawing, runs every check on it and writes
`build/report-layout.html`, leaving `lab-data.xlsx` alone. At the top: the arrangement in the spreadsheet against
the one drawn (problems and warnings, rule by rule, free bench space per room, how spread out each workflow group
is, better in green and worse in red), and the **move list**: what moves where, and which socket it plugs into
before and after. `pull` when you're happy; it saves the move list as a printable page with a tick box per move in
`build/move-lists/`, for moving day.

**The move list is in the order to do it**, in rounds. Everything in a round can be done in any order, or by
different people at once; a round starts when the one before it is finished. What decides the order:

- **Something in the way goes first.** If a cupboard is going where a bench stands now, the bench moves in an
  earlier round.
- **A bench goes in before what goes on it**, and anything leaving a bench comes off before the bench moves.
- **A swap parks one of them.** Two things that want each other's place (or a longer ring of them) can't either
  go first, so the smallest is parked somewhere clear in the first round — in the corridor, in a free corner —
  and brought back in its turn. Nothing unrelated waits for it.

Each row also says **what to do before lifting it**: agree a time to switch off anything marked `critical`, that
it loses its UPS or generator backing if the new socket doesn't have it, which gas, vacuum, air, water, drain or
exhaust lines to disconnect (from `needs`), which cables to unplug (from the links sheet), and what to clear off
it and put back after.

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
- **Contents aren't drawn.** Drawers, and the cupboards inside a fume hood or a pedestal (`mount = in`, category
  `drawer`, `cabinet`, `shelf`, `container` or `pedestal`), are part of the thing that holds them: they don't
  appear on the plan and never wait in the *not placed yet* area. Equipment inside an enclosure, such as a hotplate
  in a fume hood, does.
- **Clearances** are drawn as dashed red boxes: what you measured into `clear_front` and the rest, and the swing
  in front of anything with a `door`.
- **Rotate** in 45° steps (*Object › Transform › Rotate*). Anything else is rounded to the nearest 45°.
- **Fixed things are locked, once they're somewhere.** Walls and notes, and every object with `fixed = yes`
  (doors, windows, the eyewash, plumbed-in benches, columns) **that has an `x` and `y`**, can't be selected or
  dragged on the canvas: *Edit › Unlock All* overrides that for a session, but `pull` still ignores their moves and
  says so, and what stands on them is measured from where they really are. To move one for good: clear `fixed`,
  drag it, `pull`, then set `fixed = yes` again (or just change its `x`/`y` in the spreadsheet). Things standing on
  or inside a fixed object, such as hotplates in a fume hood, stay movable; the parts of a fixed bench are locked
  with it.
- **A new fixed thing can be dragged in once.** Something marked `fixed = yes` that has never been placed has
  nothing to be pinned to yet, so it waits in *not placed yet* unlocked. The drag that puts it in the room is kept
  like any other, `pull` says so, and from then on it's locked. So a new door or column goes: fill in the row with
  `fixed = yes` and no `x`/`y`, `layout`, drag it where it belongs, `pull`.
- Sizes come from the spreadsheet: resizing in Inkscape is ignored.
- `pull` writes into `lab-data.xlsx`, so save and close it in Excel first. A copy goes to `build/backups/` every
  time, and `pull --dry-run` shows the changes without writing them. Afterwards the drawing is redrawn to match:
  in Inkscape, *File › Revert* to load the new version.
- `layout` won't overwrite a drawing with moves you haven't pulled yet. `layout --force` throws them away.
- **Formulas in the spreadsheet** (`=903-30`, `=rooms!E3-M26`) are fine to use. Excel stores a formula *and* its
  last result, and everything here reads the result, so `pull` changes only the cells it has to and copies the rest
  of the file across untouched: formulas keep their stored results, and so do conditional formatting and
  validation. It asks Excel to recalculate next time the workbook is opened, because a formula that reads a cell
  the pull changed still shows its old value until then. A formula `pull` had to replace — you dragged that
  object, so the number is the truth now — is listed by name as it goes.
- If a position ever does read as blank (an older `pull` rewrote the workbook, or another tool did), `check` says
  which cells, and `pull` refuses to start rather than write the drawing's numbers over those formulas: open
  `lab-data.xlsx` in Excel, save it once, and the stored results are back.

## Weighing up several ideas

`labs.svg` is the working drawing, but an arrangement is just a drawing, so keep as many as you like. Arrange
one idea, then *File › Save As* `build/layout/option-A.svg`; open `labs.svg` again for the next, and so on. Then

```
python -m labmap compare                      # every drawing in build/layout, side by side (or compare.bat)
python -m labmap check --layout option-A      # one of them in full: build/report-option-A.html
python -m labmap model --layout option-A      # ...in 3D: build/model/<ROOM>-option-A.glb
python -m labmap pull --layout option-A       # keep it
```

`compare` writes `build/compare.html`: the arrangement in `lab-data.xlsx` and a column per drawing, on every row
where they don't all agree — problems and warnings rule by rule, free bench space per room, how spread out each
workflow group is — and at the bottom how much work each one is on the day: things to lift, rounds, things
parked. The best on each row is in green, and each column links to that option's full report and move list.

Pulling an option writes it into `lab-data.xlsx` and redraws `labs.svg` to match, keeping a copy of the old one in
`build/backups/`. The other options are left as they were; since they were drawn against the old arrangement,
compare them again and each is shown as a change from the new one.
