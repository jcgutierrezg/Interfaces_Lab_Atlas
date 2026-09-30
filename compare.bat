@echo off
rem Puts every arrangement drawn in build\layout side by side (labs.svg, and any option you saved beside it
rem with Inkscape's Save As, such as option-A.svg), against lab-data.xlsx as it is now, and opens the page.
rem Writes nothing to lab-data.xlsx: python -m labmap pull --layout option-A keeps one.
rem Works on the data folder named in labmap.ini (or this folder, if there's no labmap.ini).
cd /d "%~dp0"
python -m labmap compare --open
pause
