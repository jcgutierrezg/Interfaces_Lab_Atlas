@echo off
rem Writes the positions from build\layout back into lab-data.xlsx (close it in Excel first), then re-checks.
cd /d "%~dp0"
python -m labmap pull .
python -m labmap check . --open
pause
