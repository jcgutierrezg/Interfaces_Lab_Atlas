"""Command line: python -m labmap <check | layout | pull | site> [folder]

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

from . import checks, model, report
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
    path, status = layout.write_layouts(lab, checks.run(lab), force=args.force)
    print(f"All rooms: {status}  {path.resolve()}")
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
    try:
        backup, missing = model.write_moves(folder / "lab-data.xlsx", moves, folder / "build" / "backups")
    except PermissionError:
        print("Couldn't write lab-data.xlsx: close it in Excel (and let OneDrive finish syncing), then run pull again.")
        return 2
    print(f"{n - len(missing)} change(s) written to lab-data.xlsx. Backup: {backup.resolve()}")
    lab = _load(folder)
    if lab is None:
        return 2
    after = checks.run(lab)
    stamp = dt.datetime.now()
    sheet = report.write_move_list(folder / "build" / "move-lists" / f"move-list-{stamp:%Y%m%d-%H%M}.html",
                                   before, after, moves, f"Pulled {stamp:%Y-%m-%d %H:%M} from {folder.resolve().name}")
    print(f"Move list to print: {sheet.resolve()}")
    layout.write_layouts(lab, after)
    print("Layout redrawn to match. If it's open in Inkscape, use File › Revert to see the new version.")
    print("Now run `python -m labmap check` to see the result.")
    return 0


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
