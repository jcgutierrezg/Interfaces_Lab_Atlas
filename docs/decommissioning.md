# Decommissioning equipment or furniture

[← Back to the README](../README.md)

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
