# The 3D model

[← Back to the README](../README.md)

```
python -m labmap model            # writes build/model/<ROOM>.glb, one per room (or double-click model.bat)
python -m labmap model --room 30.18_ML --walls 250
```

Double-click a `.glb` and Windows opens it in **3D Viewer**: drag to orbit, right-drag or two fingers to pan, wheel
to zoom. It also opens in Blender, PowerPoint, VS Code and any glTF viewer, and it's a single file you can email to
the safety office or to whoever is quoting for the move.

Nothing extra needs measuring. Every placed object already has a footprint and a height band, so the model is
those footprints extruded: rotations, `@profile` shapes, groups, `mount` and `z` all come through, and each object
keeps its id and name in the viewer's object list. Lengths are centimetres here and metres in the file.

**What it looks like.** A massing model — everything is its footprint pushed up to its height. No handles, no
sashes, no screens on arms. That is enough to see whether you can see over something, how tight an aisle is, what
is hiding behind what, and to show the room to someone who has never been in it.

A few deliberate choices:

- **Walls stop at 120 cm** so you can look in from any angle. `--walls 250` for full height (you then have to put
  the camera inside), `--walls 0` for a floor plate and no walls.
- **Doors and windows are objects**, so they appear as panels where the wall is, not as holes cut in it. Cutting
  real openings needs solid modelling, for very little gain in a massing model.
- **Fume hoods, gloveboxes and ovens** (anything with `inner_w` / `inner_d`) are built as a shell around their
  working space, open at the front, so you can see the space inside and what stands in it.
- **Reserved working space** (category `workspace`) is left out: as a solid block it would hide the bench it
  protects. The plan drawings show it as an outline.
- **Anything with no size or no position yet** can't be drawn, and is listed by name when the command runs.

The model is built from the same geometry as the report and the drawings, so it is only ever as right as the
spreadsheet: run `python -m labmap check` first and fix what it finds.
