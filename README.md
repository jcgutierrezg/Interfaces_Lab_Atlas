# Lab map

One set of files that describes every room, every piece of furniture and equipment, and where the small stuff
lives. Three things are generated from it:

- **a check report**: collisions, clear zones, walkways, power, heat, cable and tubing reach, services, bench and
  fume hood space, forms, spare parts, and what's being decommissioned;
- **a layout of all the labs** that you rearrange in Inkscape: drag things between benches and rooms, try the
  result, then keep it;
- **a searchable lab directory** for everyone: where every instrument, drawer and item is, with photos, SOPs,
  forms and spare parts.

**You edit** one **data folder**, kept outside this repository (e.g. a synced Teams folder): `lab-data.xlsx`, the
room outlines in `rooms/`, SOPs in `sops/` and photos in `photos/`. **This repository** holds the tools, the empty
templates and a fictional example. **Everything generated** goes to the data folder's `build/`.

## Quick start

1. **Install Python 3** (with *Add python.exe to PATH* ticked, or from the Microsoft Store), then in a terminal:
   `pip install openpyxl pillow`.
2. **Try the example first:** double-click `example/check.bat`, then `example/site.bat`. The example's
   [README](example/README.md) walks through the rest.
3. **Set up your data folder:** copy the empty `lab-data.xlsx` (and the templates you need) into it, then copy
   `labmap.example.ini` to `labmap.ini` and put the folder's path in it. See [Setup](docs/setup.md).
4. **Collect the data** walk-around by walk-around: [Collecting the data](docs/collecting-data.md).
5. **Double-click** `check.bat` for the report, `layout.bat` / `try-layout.bat` / `pull.bat` to rearrange, and
   `site.bat` for the directory.

## Documentation

| Read this | When you want to |
|---|---|
| [Setup and everyday use](docs/setup.md) | point the tools at your data, use the double-click shortcuts, work in Excel and Inkscape |
| [Collecting the data](docs/collecting-data.md) | know what to fill in first and how to measure |
| [How to add new things](docs/adding-things.md) | add a room, furniture, equipment, drawers, items, sockets, SOPs, photos, forms |
| [Spreadsheet reference](docs/spreadsheet-reference.md) | look up what a column means and how a case is described |
| [The checks and the report](docs/checks.md) | understand the report and change the thresholds |
| [Rearranging in Inkscape](docs/rearranging.md) | move things around, try an arrangement, keep it |
| [Decommissioning](docs/decommissioning.md) | take something out of the lab properly |
| [The lab directory](docs/directory.md) | build and share the directory |
| [The example](example/README.md) | see every case filled in, and what the checks should find |
| [For developers](docs/development.md) | change the code, the columns or the example |

## What's in here

| Path | What it is |
|---|---|
| `lab-data.xlsx` | **The data template.** One sheet per kind of thing, with dropdowns, hints and error highlighting. Empty: copy it into your data folder and fill it in there. |
| `labmap.example.ini` | Copy to `labmap.ini` and set where your data folder is (a synced Teams or OneDrive folder, say). |
| `rooms/_TEMPLATE.svg` | Copy once per room and trace the room's outline (instructions inside the file). |
| `shapes/_TEMPLATE.svg` | Only for the rare object that isn't a rectangle, a circle or a group of rectangles. |
| `sops/_TEMPLATE.md` | Copy once per procedure. |
| `photos/` | Photos, linked to objects by file name. See `photos/README.md`. |
| `example/` | A complete, fictional two-room lab filled in the same way (a worked row for every recipe in [How to add new things](docs/adding-things.md)): every case in the docs, plus a known list of problems for testing the checks. Has its own `.bat` files to play with, and `reset.bat` to start over. See [its README](example/README.md). |
| `check.bat`, `layout.bat`, `try-layout.bat`, `pull.bat`, `site.bat` | Double-click shortcuts for the commands: see [Double-click shortcuts](docs/setup.md#double-click-shortcuts-bat-files). |
| `labmap/`, `tests/` | The code that checks, draws and builds the directory, and its tests. |
| `tools/` | Regenerates the empty template and the example workbook: `python tools/make_workbooks.py`. |
| `build/` (in the data folder) | Everything generated: the report, the layout drawing, the directory, move lists, backups of the workbook. |

You can add a `manuals/` folder for PDFs and put the relative path in the `manual` column on the equipment sheet.
