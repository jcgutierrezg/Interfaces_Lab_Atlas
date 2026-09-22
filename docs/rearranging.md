# Rearranging in Inkscape

[← Back to the README](../README.md)

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
