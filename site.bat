@echo off
rem Builds the lab directory in build\site and opens it.
cd /d "%~dp0"
python -m labmap site . --open
pause
