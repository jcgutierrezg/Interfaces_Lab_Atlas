@echo off
rem Draws example\build\layout\<room>.svg for each room, to rearrange in Inkscape.
rem Works on the worked EXAMPLE in this folder, not your own data. reset.bat puts it back as it came.
cd /d "%~dp0.."
python -m labmap layout example
if exist "example\build\layout" start "" "example\build\layout"
pause
