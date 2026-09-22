# For developers

[← Back to the README](../README.md)

## The code

The documentation is `README.md` (an overview) and the pages in `docs/`; the example has its own
`example/README.md`, which lists exactly what the checks should find.

`labmap/` is a small Python package (it needs only `openpyxl`, plus `Pillow` for shrinking photos):
`model.py` reads the workbook and SVGs, `geometry.py` places everything, `checks.py` holds the rules and their
thresholds, `report.py`, `layout.py` and `site.py` write the outputs. `tests/` runs against the example:
`python -m unittest discover -s tests -t .`

`tools/make_workbooks.py` regenerates the empty `lab-data.xlsx` and the example workbook from `tools/schema.py`
(the sheets and columns, with their hints and dropdowns), `tools/lists.py` (dropdown values) and
`tools/example_*.py` (the example's rows). Change a column there, never by hand in the template, then run it.
