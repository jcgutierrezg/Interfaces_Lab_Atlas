"""Command line: python -m labmap <check | layout | pull | site | xy | lists | model> [folder]

The folder is the one holding lab-data.xlsx (with rooms/, shapes/, sops/, photos/ beside it). Without one, the
folder named in labmap.ini (next to this package) is used, e.g. a synced Teams or OneDrive folder; failing that,
the current folder. "example" is the worked example. Output goes to <folder>/build/.
"""
from __future__ import annotations

import argparse
import configparser
import datetime as dt
import os
import sys
import webbrowser
from pathlib import Path

from . import checks, metrics, model, report
from .checks import describe

CONFIG = Path(__file__).resolve().parent.parent / "labmap.ini"


def data_folder(arg):
    """Where the data is: the folder given, else $LABMAP_DATA, else labmap.ini's [data] folder, else here."""
    if arg:
        return Path(arg)
    if os.environ.get("LABMAP_DATA"):
        return Path(os.path.expandvars(os.path.expanduser(os.environ["LABMAP_DATA"])))
    if CONFIG.exists():
        ini = configparser.ConfigParser(interpolation=None)
        ini.read(CONFIG, encoding="utf-8")
        value = ini.get("data", "folder", fallback="").strip().strip('"')
        if value:
            folder = Path(os.path.expandvars(os.path.expanduser(value)))
            return folder if folder.is_absolute() else CONFIG.parent / folder
    return Path(".")


def _load(folder, moves=None):
    if not (folder / "lab-data.xlsx").exists():
        where = f" (set in {CONFIG.name})" if CONFIG.exists() else ""
        print(f"No lab-data.xlsx in {folder.resolve()}{where}")
        return None
    try:
        return model.load(folder, moves)
    except PermissionError:
        print("Couldn't read lab-data.xlsx. If it's open in Excel with unsaved changes, save it and try again. "
              "If it's in OneDrive or Teams, make sure it has finished syncing.")
        return None


def _summary(res, show):
    groups, warned = res.by_rule("problem"), res.by_rule("warning")
    problems = sum(len(v) for k, v in groups.items() if k != "data")
    warnings = sum(len(v) for v in warned.values())
    print(f"{problems} problem{'' if problems == 1 else 's'}, {warnings} warning{'' if warnings == 1 else 's'}" +
          (f", {len(groups['data'])} data problem{'' if len(groups['data']) == 1 else 's'}" if "data" in groups else ""))
    for rule, found in {**groups, **warned}.items():
        name, _, level = describe(rule, res.lab.settings)
        print(f"  {name} ({len(found)}{', warning' if level == 'warning' else ''})")
        for f in found[:show]:
            print(f"    - {f.message}")
        if len(found) > show:
            print(f"    ... and {len(found) - show} more in the report")


def _print_moves(lab, moves, notes):
    from . import layout

    for n in notes:
        print(f"  note: {n}")
    for sheet in layout.MOVE_SHEETS:
        for i, change in sorted(moves.get(sheet, {}).items()):
            print(f"  {i}: {layout.describe_move(lab, sheet, i, change)}")


def _check(args):
    folder = data_folder(args.folder)
    lab = _load(folder)
    if lab is None:
        return 2
    banner, target, before, moves = None, folder / "build" / "report.html", None, None
    if args.layout:
        from . import layout

        moves, notes = layout.layout_moves(lab)
        n = layout.count(moves)
        print(f"Checking the layout as drawn ({n} change(s) not pulled yet; nothing is written):")
        _print_moves(lab, moves, notes)
        before = checks.run(lab)
        lab = _load(folder, moves)
        if lab is None:
            return 2
        banner = f"Trying the arrangement in the Inkscape layout: {n} change(s) not in lab-data.xlsx yet. Run pull to keep them."
        target = folder / "build" / "report-layout.html"
    res = checks.run(lab)
    out = report.write(res, target, banner, before=before, moves=moves)
    _summary(res, args.show)
    if before is not None:
        b = report.summary(before)
        print(f"Now in lab-data.xlsx: {b['problems']} problems, {b['warnings']} warnings. "
              f"The report compares the two and lists the moves.")
    print(f"Report: {out.resolve()}")
    if args.open:
        webbrowser.open(out.resolve().as_uri())
    return 0


def _layout(args):
    from . import layout

    lab = _load(data_folder(args.folder))
    if lab is None:
        return 2
    stale = [s for s in lab.stale if s[0] in layout.MOVE_SHEETS]
    if stale:
        print(f"Careful: {len(stale)} cell(s) hold a formula with no stored result, so they read as blank and what "
              f"they place lands in 'not placed yet'. Open lab-data.xlsx in Excel and save it, then draw again.")
    res = checks.run(lab)
    path, status = layout.write_layouts(lab, res, force=args.force)
    print(f"All rooms: {status}  {path.resolve()}")
    waiting = metrics.unplaced(res)
    if waiting:
        names = ", ".join(i for i, _, _ in waiting[:8]) + (" ..." if len(waiting) > 8 else "")
        print(f"{len(waiting)} thing(s) have no x and y yet, so they're in the 'not placed yet' area beside their "
              f"room, off to the right of it: {names}")
        print("  drag each one where it goes, save, then pull.")
    if args.open:
        os.startfile(path.parent) if hasattr(os, "startfile") else webbrowser.open(path.parent.resolve().as_uri())
    print("Open it in Inkscape, drag things around (between rooms too) and save. Then:")
    print("  python -m labmap check --layout   to check the arrangement as drawn (nothing is written)")
    print("  python -m labmap pull             to keep it: writes it into lab-data.xlsx")
    return 0


def _pull(args):
    from . import layout

    folder = data_folder(args.folder)
    lab = _load(folder)
    if lab is None:
        return 2
    stale = [s for s in lab.stale if s[0] in layout.MOVE_SHEETS]
    if stale:
        print(f"Not pulling: {len(stale)} cell(s) hold a formula with no stored result, so they read as blank and "
              f"pull would write the drawing's numbers over the formulas.")
        for sheet, row, col, name in stale[:8]:
            print(f"  {name}: {col} ({sheet} row {row})")
        if len(stale) > 8:
            print(f"  ... and {len(stale) - 8} more")
        print("Open lab-data.xlsx in Excel, save it (that stores the results), then run pull again.")
        return 2
    moves, notes = layout.layout_moves(lab)
    _print_moves(lab, moves, notes)
    n = layout.count(moves)
    if not n:
        print("No moves to pull: lab-data.xlsx already matches the layout.")
        return 0
    if args.dry_run:
        print(f"{n} change(s); nothing written (--dry-run).")
        return 0
    before = checks.run(lab)
    moved = _load(folder, moves)  # the result, worked out before writing: the file's own formulas read blank after
    if moved is None:
        return 2
    try:
        backup, missing, note = model.write_moves(folder / "lab-data.xlsx", moves, folder / "build" / "backups")
    except PermissionError:
        print("Couldn't write lab-data.xlsx: close it in Excel (and let OneDrive finish syncing), then run pull again.")
        return 2
    print(f"{n - len(missing)} change(s) written to lab-data.xlsx. Backup: {backup.resolve()}")
    for i, col, formula in note["replaced"]:
        print(f"  note: {i}'s {col} was the formula {formula}; the drawing's number replaced it")
    if note["rewrote"]:
        print(f"  note: the cells couldn't be changed one by one ({note['rewrote']}), so the whole workbook was "
              f"rewritten. Open lab-data.xlsx in Excel and save it once: its formulas have no stored result now.")
    after = checks.run(moved)
    stamp = dt.datetime.now()
    sheet = report.write_move_list(folder / "build" / "move-lists" / f"move-list-{stamp:%Y%m%d-%H%M}.html",
                                   before, after, moves, f"Pulled {stamp:%Y-%m-%d %H:%M} from {folder.resolve().name}")
    print(f"Move list to print: {sheet.resolve()}")
    layout.write_layouts(moved, after, force=True)
    print("Layout redrawn to match. If it's open in Inkscape, use File › Revert to see the new version.")
    if note["formulas"] and not note["rewrote"]:
        print(f"The workbook's {note['formulas']} formula(s) kept their stored results, and Excel will work them "
              f"out again next time you open it: any that read a cell this pull changed still show the old value.")
    print("Now run `python -m labmap check` to see the result.")
    return 0


def _model(args):
    """A 3D model per room, from the same geometry as the drawings."""
    from . import glb

    folder = data_folder(args.folder)
    lab = _load(folder)
    if lab is None:
        return 2
    rooms = [r.strip().upper() for r in args.room.split(",")] if args.room else None
    if rooms and any(r not in lab.placeables and r not in lab.rooms for r in rooms):
        print(f"Rooms on the rooms sheet: {', '.join(lab.rooms)}")
        return 2
    before, suffix = None, ""
    if args.layout:
        from . import layout

        moves, notes = layout.layout_moves(lab)
        n = layout.count(moves)
        print(f"Modelling the layout as drawn: {n} change(s) not pulled yet, in purple, with a ghost where each "
              f"thing stands now. Nothing is written to lab-data.xlsx.")
        _print_moves(lab, moves, notes)
        before, lab = lab, _load(folder, moves)
        if lab is None:
            return 2
        suffix = "-layout"
    built = glb.write_models(lab, checks.run(lab), folder, rooms, args.walls, args.plain, before, suffix)
    if not built:
        print("No rooms to model: the rooms sheet is empty, or none of them has an outline yet.")
        return 2
    if not args.plain:
        print("Red: a problem. Amber: a warning. Yellow on the floor: space that has to stay clear."
              + (" Purple: moved in the drawing." if args.layout else ""))
    for path, parts, skipped in built:
        print(f"{path.stem}: {parts} part(s)  {path.resolve()}")
        if skipped:
            print(f"  not drawn, nothing to draw them from yet (no size or no place): {', '.join(skipped[:8])}" + (" ..." if len(skipped) > 8 else ""))
    print("Open a .glb in Open3D Viewer or Blender, or look at the room in 3D in the directory (python -m labmap "
              "site): no app needed there.")
    print(f"Walls stop at {args.walls} cm so you can see in: --walls 250 for full height, --walls 0 for none.")
    if args.open:
        os.startfile(built[0][0].parent) if hasattr(os, "startfile") else None
    return 0


def _lists(args):
    """Copy list values the blank template has gained (a new category, say) into this workbook's lists sheet."""
    folder = data_folder(args.folder)
    source = Path(args.source) if args.source else CONFIG.parent / "lab-data.xlsx"
    target = folder / "lab-data.xlsx"
    if not source.exists():
        print(f"No workbook to copy from at {source.resolve()}")
        return 2
    if not target.exists():
        print(f"No lab-data.xlsx in {folder.resolve()}")
        return 2
    if source.resolve() == target.resolve():
        print("That's the same workbook: give me the folder holding your data, or --source.")
        return 2
    try:
        added = model.sync_lists(target, source, folder / "build" / "backups")
    except PermissionError:
        print("Couldn't write lab-data.xlsx: close it in Excel (and let OneDrive finish syncing), then try again.")
        return 2
    if not added:
        print(f"Nothing to add: the lists in {target.name} already have everything {source.name} offers.")
        return 0
    for name, values in sorted(added.items()):
        print(f"  {name}: {', '.join(str(v) for v in values)}")
    print(f"Added to the lists sheet of {target.resolve()}, dropdowns stretched to match. A backup went to "
          f"{(folder / 'build' / 'backups').resolve()}.")
    return 0


def _xy(args):
    """Where an object's corners are, and what x, y would put a corner on a spot you measured."""
    from . import geometry as G

    folder = data_folder(args.folder)
    over = {k: v for k, v in (("faces", args.faces), ("w", args.w), ("d", args.d)) if v is not None}
    lab = _load(folder, {"placeables": {args.id: over}} if over else None)
    if lab is None:
        return 2
    if args.id not in lab.placeables:
        print(f"No row with id {args.id} on the placeables sheet.")
        return 2
    r = lab.placeables[args.id]
    geo = G.place_all(lab)[0]
    g = geo.get(args.id)
    if g is None or g.T is None:
        print(f"{args.id} isn't placed yet: it needs w, d, h, x, y (and its parent placed) before it has corners.")
        return 2
    frame = f"in {r['parent']}'s frame" if r.get("parent") else f"in {g.room}"
    size = f"{r['w']} x {r.get('d') if r.get('d') is not None else r['w']}"
    print(f"{args.id}  {r.get('name') or ''}  {size} cm, faces {r.get('faces') or 'S'}"
          + (f", {'part of' if r.get('mount') == 'part' else r.get('mount')} {r['parent']}"
             if r.get("parent") else ""))
    print(f"  x, y on the sheet: {_n(r['x'])}, {_n(r['y'])}  ({frame}: the top-left of its bounding box"
          + (", not a corner of the object itself while it is turned diagonally)"
             if (r.get("faces") or "S") in ("NE", "SE", "SW", "NW") else ")"))
    _corners(lab, g, "  corners in " + str(g.room) + ":")
    if args.x is None:
        print()
        print("  To place it, measure one of those corners and run this again with where it should go, e.g.")
        print(f"    python -m labmap xy {args.id} 820 25 --corner back-left")
        return 0
    got = G.xy_for(lab, geo, args.id, args.corner, (args.x, args.y))
    if got is None:
        print("Couldn't work that out: check faces, w and d, and that the parent is placed.")
        return 2
    x, y = got
    print()
    print(f"  To put its {args.corner} corner on {_n(args.x)}, {_n(args.y)}, type on the placeables sheet:")
    print(f"    x = {_n(x)}   y = {_n(y)}   ({frame})")
    moves = {"placeables": {args.id: dict(over, x=round(x, 1), y=round(y, 1))}}
    after = _load(folder, moves)
    if after is None:
        return 2
    ageo = G.place_all(after)[0]
    parent = r.get("parent")
    if parent and lab.placeables[parent].get("shape") == "group" and ageo.get(parent) and geo.get(parent):
        dx = ageo[parent].origin[0] - geo[parent].origin[0]
        dy = ageo[parent].origin[1] - geo[parent].origin[1]
        if abs(dx) > 0.05 or abs(dy) > 0.05:
            pr = lab.placeables[parent]
            px, py = round(pr["x"] - dx, 1), round(pr["y"] - dy, 1)
            print()
            print(f"  Careful: {parent}'s x, y pin the bounding box of all its parts together, and this part "
                  f"changes that box, so the whole group would slide {_n(dx)}, {_n(dy)} cm. Keep the other parts "
                  f"where they are by setting {parent} x = {_n(px)}, y = {_n(py)} at the same time.")
            moves["placeables"][parent] = {"x": px, "y": py}
            after = _load(folder, moves)
            if after is None:
                return 2
            ageo = G.place_all(after)[0]
    if ageo.get(args.id) is not None:
        _corners(after, ageo[args.id], "\n  with both of those, it would sit at:" if len(moves["placeables"]) > 1
                 else "\n  it would then sit at:")
    return 0


def _corners(lab, g, title):
    from . import geometry as G

    poly = lab.rooms.get(g.room, {}).get("poly")
    print(title)
    for name, (x, y) in G.corner_points(g).items():
        out = "   outside the room" if poly and not G.inside((x, y), poly) else ""
        print(f"    {name:<12} {_n(x)}, {_n(y)}{out}")


def _n(v):
    return "?" if v is None else f"{round(v, 1):g}"


def _site(args):
    from . import site

    lab = _load(data_folder(args.folder))
    if lab is None:
        return 2
    index = site.build(lab, checks.run(lab))
    print(f"Directory: {index.resolve()}")
    print("Copy the whole build/site folder to a shared drive; people open index.html in any browser.")
    if args.open:
        webbrowser.open(index.resolve().as_uri())
    return 0


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")  # Windows consoles default to a legacy code page
    ap = argparse.ArgumentParser(prog="python -m labmap", description="Checks, layouts and the lab directory.")
    sub = ap.add_subparsers(dest="command", required=True)
    folder_help = f"folder holding lab-data.xlsx (default: the one in {CONFIG.name}, else this one)"
    c = sub.add_parser("check", help="run the checks and write build/report.html")
    c.add_argument("folder", nargs="?", help=folder_help)
    c.add_argument("--open", action="store_true", help="open the report in the browser")
    c.add_argument("--show", type=int, default=5, help="problems to print per rule (default 5)")
    c.add_argument("--layout", action="store_true",
                   help="check the arrangement as drawn in the Inkscape layout, without pulling it; compares it with "
                        "the current one and lists the moves (writes build/report-layout.html)")
    c.set_defaults(run=_check)
    lay = sub.add_parser("layout", help="write build/layout/labs.svg, every room in one file, to rearrange in Inkscape")
    lay.add_argument("folder", nargs="?", help=folder_help)
    lay.add_argument("--force", action="store_true", help="overwrite the layout even if it has moves not pulled yet")
    lay.add_argument("--open", action="store_true", help="open the folder it's in")
    lay.set_defaults(run=_layout)
    pl = sub.add_parser("pull", help="write the arrangement in the layout back into lab-data.xlsx")
    pl.add_argument("folder", nargs="?", help=folder_help)
    pl.add_argument("--dry-run", action="store_true", help="show the changes without writing them")
    pl.set_defaults(run=_pull)
    md = sub.add_parser("model", help="write build/model/<ROOM>.glb, a 3D model of each room to look around in")
    md.add_argument("folder", nargs="?", help=folder_help)
    md.add_argument("--room", help="one room, or several separated by commas (default: all of them)")
    md.add_argument("--walls", type=int, default=120,
                    help="wall height in cm, so you can see in from outside (default 120; 0 for no walls)")
    md.add_argument("--layout", action="store_true",
                    help="model the arrangement drawn in the Inkscape layout, before pulling it: what moved is "
                         "coloured, with a ghost where it stands now (writes <ROOM>-layout.glb, nothing else)")
    md.add_argument("--plain", action="store_true",
                    help="no problems, warnings or clear zones: just the room, to send to someone")
    md.add_argument("--open", action="store_true", help="open the folder it's in")
    md.set_defaults(run=_model)
    ls = sub.add_parser("lists", help="copy list values the blank template has gained (a new category, say) into "
                                      "your workbook's lists sheet, dropdowns included")
    ls.add_argument("folder", nargs="?", help=folder_help)
    ls.add_argument("--source", help="the workbook to copy from (default: the blank lab-data.xlsx beside labmap)")
    ls.set_defaults(run=_lists)
    xy = sub.add_parser("xy", help="where an object's corners are, and the x, y that puts a corner where you "
                                   "measured it")
    xy.add_argument("id", help="the id on the placeables sheet, e.g. BENCH-02 or BENCH-02.B")
    xy.add_argument("x", nargs="?", type=float, help="where that corner should go, in room coordinates")
    xy.add_argument("y", nargs="?", type=float)
    xy.add_argument("--corner", default="back-left", choices=["back-left", "back-right", "front-right", "front-left"],
                    help="which corner you measured, standing in front of the object (default back-left)")
    xy.add_argument("--faces", help="try a different facing without editing the sheet")
    xy.add_argument("--w", type=float, help="try a different width")
    xy.add_argument("--d", type=float, help="try a different depth")
    xy.add_argument("--folder", help=folder_help)
    xy.set_defaults(run=_xy)
    st = sub.add_parser("site", help="build the lab directory in build/site")
    st.add_argument("folder", nargs="?", help=folder_help)
    st.add_argument("--open", action="store_true", help="open it in the browser")
    st.set_defaults(run=_site)
    args = ap.parse_args(argv)
    folder = data_folder(args.folder)
    if not args.folder:
        print(f"Data: {folder.resolve()}")
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
