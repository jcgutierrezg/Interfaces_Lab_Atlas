@echo off
rem Checks the example's arrangement as drawn in its Inkscape layouts, without writing anything.
rem Works on the worked EXAMPLE in this folder, not your own data. reset.bat puts it back as it came.
cd /d "%~dp0.."
python -m labmap check example --layout --open
pause
