@echo off
rem Writes the positions from the example's layouts into example\lab-data.xlsx, then re-checks.
rem Works on the worked EXAMPLE in this folder, not your own data. reset.bat puts it back as it came.
cd /d "%~dp0.."
python -m labmap pull example
python -m labmap check example --open
pause
