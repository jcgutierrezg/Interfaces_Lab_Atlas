@echo off
rem Draws build\layout\labs.svg, every room in one file, to rearrange in Inkscape, and opens its folder.
rem Works on the data folder named in labmap.ini (or this folder, if there's no labmap.ini).
cd /d "%~dp0"
python -m labmap layout --open
pause
