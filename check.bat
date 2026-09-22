@echo off
rem Runs the checks on lab-data.xlsx in this folder and opens the report.
cd /d "%~dp0"
python -m labmap check . --open
pause
