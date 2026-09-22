@echo off
rem Runs the checks on lab-data.xlsx and opens the report.
rem Works on the data folder named in labmap.ini (or this folder, if there's no labmap.ini).
cd /d "%~dp0"
python -m labmap check --open
pause
