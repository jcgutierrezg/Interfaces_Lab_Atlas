# Setup and everyday use

[← Back to the README](../README.md)

Where the data lives, the double-click shortcuts that run everything, and tips for working in Excel and Inkscape.

## Where your data lives

The tools live here; the data lives in a **data folder** of its own, e.g. a Teams channel's files synced to your
OneDrive. It holds `lab-data.xlsx` (start from this repository's empty one) and, beside it, `rooms/`, `shapes/`,
`sops/` and `photos/` (copy the templates across as you need them). Generated files go to a `build/` folder inside
it: the report, the layout drawing, the directory, move lists and workbook backups.

Don't edit anything in `build/` by hand, except the layout drawing `build/layout/labs.svg`, which you rearrange in
Inkscape and then pull back (see [Rearranging in Inkscape](rearranging.md)). This repository holds only the tools,
the empty templates and the fictional example; `.gitignore` keeps anything added to `rooms/`, `shapes/`, `sops/`
and `photos/` here out of git, apart from the templates, so real lab data can't end up on GitHub by accident.

Tell the tools where it is once: copy `labmap.example.ini` to `labmap.ini` (in the repository's main folder, next to `README.md`) and set
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
