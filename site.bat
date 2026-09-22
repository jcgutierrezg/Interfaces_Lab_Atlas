@echo off
rem Builds the lab directory in build\site and opens it.
rem Works on the data folder named in labmap.ini (or this folder, if there's no labmap.ini).
cd /d "%~dp0"
python -m labmap site --open
pause
