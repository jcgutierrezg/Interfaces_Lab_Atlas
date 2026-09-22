@echo off
rem Runs the checks on the example and opens the report.
rem Works on the worked EXAMPLE in this folder, not your own data. reset.bat puts it back as it came.
cd /d "%~dp0.."
python -m labmap check example --open
pause
