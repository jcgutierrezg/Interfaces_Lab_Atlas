# The 3D model

[← Back to the README](../README.md)

```
python -m labmap model            # writes build/model/<ROOM>.glb, one per room (or double-click model.bat)
python -m labmap model --layout   # the arrangement drawn in Inkscape, before you pull it: <ROOM>-layout.glb
python -m labmap model --plain    # just the room, without the checks: the one to send to someone
python -m labmap model --room 30.18_ML --walls 250
```

Open a `.glb` in **Open3D Viewer** or **Blender** (Microsoft's 3D Viewer has been discontinued), or any other glTF
viewer, including PowerPoint and VS Code. It's a single file you can email to the safety office or to whoever is
quoting for the move.

**No app needed: the directory shows every room in 3D too.** `python -m labmap site` gives each room a
*see the room in 3D* page, and every object page a *see it in 3D* link that flies to it. Drag to turn, right-drag
or Shift-drag (or two fingers) to move, scroll or pinch to zoom, and click anything to see what it is, what the
checks say about it, and a link to its page. Walls and clear zones can be switched off. It runs in any current
browser, straight off a shared drive with no internet, and the `.glb` is next to it for anyone who'd rather
download it.

Nothing extra needs measuring. Every placed object already has a footprint and a height band, so the model is
those footprints extruded: rotations, `@profile` shapes, groups, `mount` and `z` all come through, and each object
keeps its id and name in the viewer's object list. Lengths are centimetres here and metres in the file.

**Reading the checks in it.** Unless you ask for `--plain`, the model shows what the report says:

| Colour | Means |
|---|---|
| **Red** | a problem: it's in the way of something, or something is in its way |
| **Amber** | a warning |
| **Yellow, painted on the floor or the bench** | space that has to stay clear: `clear_front` and the other sides, door swings, the sash of a fume hood |
| **See-through yellow above something** | room kept above it (`clear_top`): a lid, a sash |
| **Purple** (with `--layout`) | moved in the drawing and not pulled yet, or carried along by something that was |
| **See-through purple** (with `--layout`) | where it stands now, in `lab-data.xlsx` |

Clear zones are painted, not drawn as volumes: in front of anything on the floor that space is a person tall,
and a person-tall block in front of every bench would fill the room with haze. Something red standing in a yellow
patch is what the report's *Clear zone blocked* means. Each flagged object also carries what the checks said
about it (`extras.findings` in the file), for viewers that show it.

**Before you pull.** `model --layout` builds the room as drawn in `labs.svg`, the same way `check --layout` checks
it, and writes it next to the current model instead of over it, so you can open the two side by side.
`try-layout.bat` does both. Nothing is written to `lab-data.xlsx`.

**What it looks like.** A massing model — everything is its footprint pushed up to its height. No handles, no
sashes, no screens on arms. That is enough to see whether you can see over something, how tight an aisle is, what
is hiding behind what, and to show the room to someone who has never been in it.

A few deliberate choices:

- **Benches float.** Anything with `free_under` is drawn as its top alone, hanging at the height its leg room
  ends, so you can see the pedestals, freezers and bins parked underneath — which is most of what you want to look
  at from inside the room.
- **The colours are the plan's, deepened.** Same hue, darker and a little more saturated, because a viewer has no
  black outlines and adds its own light, which turns the drawings' pastels into one undifferentiated off-white. A
  few categories whose plan colour is nearly white, such as doors and windows, are given a colour of their own.
  Each face also carries its own shade, lightest on top, so edges read as edges.
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
