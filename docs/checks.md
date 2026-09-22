# The checks and the report

[← Back to the README](../README.md)

Needs Python 3 with `openpyxl` (`pip install openpyxl` if it's missing). From this folder:

```
python -m labmap check             # your data: the folder in labmap.ini (or this one)
python -m labmap check example     # the worked example
python -m labmap check --open      # ...and open the report in the browser
```

Or double-click `check.bat`. The report goes to `build/report.html` (`example/build/report.html` for the example):
the problems grouped by rule, then progress, rooms, bench space, fume hoods, power, connections, documents, spare parts, triage, decommissioning, workflow groups,
containers and what isn't placed yet. Findings are **problems** (something's wrong) or **warnings** (worth a look:
covered windows, stacks on things not marked stackable, forms not approved or about to expire, spare parts
out of stock or running low, things closer than `keep_apart` suggests, arrivals too big for the door). It's fine
to run on half-filled data: missing data shows up under progress, not as problems. [example/README.md](../example/README.md) explains
each rule.

The thresholds are on the **`settings` sheet** of `lab-data.xlsx`: walkway width (60 cm), how close a clear zone
must be to a path (30 cm), clear-zone height (200 cm), what counts as in the way (anything starting below
150 cm), circuit limit (80%), heavy load (1000 W), the raster size (5 cm), `fit_margin` (2 cm of slack for
measuring error and ventilation, under benches, below the ceiling and through doors), `door_gap` (10 cm),
`utility_reach` (3 m), `sprinkler_clearance` (45 cm) and `sash_clearance` (15 cm). Change them to match your
safety office's numbers.

`python -m unittest discover -s tests -t .` confirms the example still produces exactly its fourteen problems and
eight warnings.


## The example

`example/` is a complete, fictional two-room lab for thin-film photovoltaics and electronic interfaces: a 720 ×
540 cm device fabrication lab (`LAB-A`) and an L-shaped characterisation lab with a chamfered corner, a column and
a pilaster (`LAB-B`). It has 116 placeables, 44 pieces of equipment, sockets,
circuits, links, 51 items, SOPs and placeholder photos, covering every case in these pages.

It also contains **exactly fourteen deliberate problems and eight deliberate warnings**, each testing a different
rule. The problems: a blocked clear zone, a lid hitting a shelf, an overlap, a fridge too tall for the space under
a bench, an object outside the room, a cabinet too close to the sprinklers, too many plugs on a socket, a strip plugged into a strip, an overloaded socket, an overloaded circuit, a critical freezer on a shared
circuit, too much heat for the cooling, a USB run that's too long, and a solar simulator with no extraction
within reach. The warnings: a pending risk assessment, a spare part out of stock, one running low, a vacuum pump
next to a balance, an LED source too close to a dark box, a glovebox too big for the door, a hotplate too close to
a fume hood's sash, and a spare part still listed for an oven that's been decommissioned. [example/README.md](../example/README.md) lists each one with the exact expected finding, and the rules behind them.
