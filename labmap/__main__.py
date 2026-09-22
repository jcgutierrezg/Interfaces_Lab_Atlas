"""Command line: python -m labmap check [folder] [--open]

Run from the Lab_Map folder. The folder argument is the one holding lab-data.xlsx: "." for your own data
(the default), "example" for the worked example. Output goes to <folder>/build/.
"""
from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path

from . import checks, model, report
from .checks import RULES, describe


def _check(args):
    folder = Path(args.folder)
    if not (folder / "lab-data.xlsx").exists():
        print(f"No lab-data.xlsx in {folder.resolve()}")
        return 2
    try:
        lab = model.load(folder)
        banner, target = None, folder / "build" / "report.html"
        if args.layout:
            from . import layout

            moves, notes = layout.layout_moves(lab)
            print(f"Checking the layouts as drawn ({len(moves)} move(s) not pulled yet; nothing is written):")
            for n in notes:
                print(f"  note: {n}")
            for i, mv in sorted(moves.items()):
                print(f"  {i}: {layout.describe_move(lab.placeables[i], mv)}")
            lab = model.load(folder, moves)
            banner = (f"Trying the arrangement in the Inkscape layouts: {len(moves)} move(s) not in lab-data.xlsx yet. "
                      f"Run pull to keep them.")
            target = folder / "build" / "report-layout.html"
    except PermissionError:
        print("Couldn't read lab-data.xlsx. If it's open in Excel with unsaved changes, save it and try again.")
        return 2
    res = checks.run(lab)
    out = report.write(res, target, banner)
    groups, warned = res.by_rule("problem"), res.by_rule("warning")
    problems = sum(len(v) for k, v in groups.items() if k != "data")
    warnings = sum(len(v) for v in warned.values())
    print(f"{problems} problem{'' if problems == 1 else 's'}, {warnings} warning{'' if warnings == 1 else 's'}" +
          (f", {len(groups['data'])} data problem{'' if len(groups['data']) == 1 else 's'}" if "data" in groups else ""))
    for rule, found in {**groups, **warned}.items():
        name, _, level = describe(rule, lab.settings)
        print(f"  {name} ({len(found)}{', warning' if level == 'warning' else ''})")
        for f in found[: args.show]:
            print(f"    - {f.message}")
        if len(found) > args.show:
            print(f"    ... and {len(found) - args.show} more in the report")
    print(f"Report: {out.resolve()}")
    if args.open:
        webbrowser.open(out.resolve().as_uri())
    return 0


def _load(folder):
    if not (folder / "lab-data.xlsx").exists():
        print(f"No lab-data.xlsx in {folder.resolve()}")
        return None
    try:
        return model.load(folder)
    except PermissionError:
        print("Couldn't read lab-data.xlsx. If it's open in Excel with unsaved changes, save it and try again.")
        return None


def _layout(args):
    from . import layout

    lab = _load(Path(args.folder))
    if lab is None:
        return 2
    for rid, path, status in layout.write_layouts(lab, checks.run(lab), force=args.force):
        print(f"{rid}: {status}  {path.resolve()}")
    print("Open these in Inkscape, drag things around and save. Then:")
    print("  python -m labmap check --layout   to check the arrangement as drawn (nothing is written)")
    print("  python -m labmap pull             to keep it: writes the positions into lab-data.xlsx")
    return 0


def _pull(args):
    from . import layout

    folder = Path(args.folder)
    lab = _load(folder)
    if lab is None:
        return 2
    updates, notes = layout.layout_moves(lab)
    for n in notes:
        print(f"  note: {n}")
    if not updates:
        print("No moves to pull: lab-data.xlsx already matches the layouts.")
        return 0
    P = lab.placeables
    for i, move in sorted(updates.items()):
        print(f"  {i}: {layout.describe_move(P[i], move)}")
    if args.dry_run:
        print(f"{len(updates)} change(s); nothing written (--dry-run).")
        return 0
    try:
        backup, missing = model.write_positions(folder / "lab-data.xlsx", updates, folder / "build" / "backups")
    except PermissionError:
        print("Couldn't write lab-data.xlsx: close it in Excel and run pull again.")
        return 2
    print(f"{len(updates) - len(missing)} change(s) written to lab-data.xlsx. Backup: {backup.resolve()}")
    lab = model.load(folder)
    layout.write_layouts(lab, checks.run(lab))
    print("Layouts redrawn to match. If one is open in Inkscape, use File › Revert to see the new version.")
    print("Now run `python -m labmap check` to see the result.")
    return 0


def _site(args):
    from . import site

    lab = _load(Path(args.folder))
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
    c = sub.add_parser("check", help="run the checks and write build/report.html")
    c.add_argument("folder", nargs="?", default=".", help="folder holding lab-data.xlsx (default: this one)")
    c.add_argument("--open", action="store_true", help="open the report in the browser")
    c.add_argument("--show", type=int, default=5, help="problems to print per rule (default 5)")
    c.add_argument("--layout", action="store_true",
                   help="check the arrangement as drawn in the Inkscape layouts, without pulling it "
                        "(writes build/report-layout.html)")
    c.set_defaults(run=_check)
    lay = sub.add_parser("layout", help="write build/layout/<room>.svg to rearrange in Inkscape")
    lay.add_argument("folder", nargs="?", default=".")
    lay.add_argument("--force", action="store_true", help="overwrite layouts even if they have moves not pulled yet")
    lay.set_defaults(run=_layout)
    pl = sub.add_parser("pull", help="write the positions from the layouts back into lab-data.xlsx")
    pl.add_argument("folder", nargs="?", default=".")
    pl.add_argument("--dry-run", action="store_true", help="show the changes without writing them")
    pl.set_defaults(run=_pull)
    st = sub.add_parser("site", help="build the lab directory in build/site")
    st.add_argument("folder", nargs="?", default=".")
    st.add_argument("--open", action="store_true", help="open it in the browser")
    st.set_defaults(run=_site)
    args = ap.parse_args(argv)
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
