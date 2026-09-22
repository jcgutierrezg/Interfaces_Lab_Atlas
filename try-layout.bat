@echo off
rem Checks the arrangement as drawn in the Inkscape layout, compares it with the current one and lists
rem the moves. Writes nothing to lab-data.xlsx.
rem Works on the data folder named in labmap.ini (or this folder, if there's no labmap.ini).
cd /d "%~dp0"
python -m labmap check --layout --open
pause
