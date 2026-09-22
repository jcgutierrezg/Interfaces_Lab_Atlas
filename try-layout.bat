@echo off
rem Checks the arrangement as drawn in the Inkscape layouts, without writing anything to lab-data.xlsx.
cd /d "%~dp0"
python -m labmap check . --layout --open
pause
