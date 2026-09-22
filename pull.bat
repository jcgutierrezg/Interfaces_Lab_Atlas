@echo off
rem Writes the arrangement in the Inkscape layout into lab-data.xlsx (close it in Excel first), saves a
rem printable move list, then re-checks.
rem Works on the data folder named in labmap.ini (or this folder, if there's no labmap.ini).
cd /d "%~dp0"
python -m labmap pull
python -m labmap check --open
pause
