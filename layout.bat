@echo off
rem Draws build\layout\<room>.svg for each room, to rearrange in Inkscape.
cd /d "%~dp0"
python -m labmap layout .
start "" "build\layout"
pause
