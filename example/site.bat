@echo off
rem Builds the example's lab directory in example\build\site and opens it.
rem Works on the worked EXAMPLE in this folder, not your own data. reset.bat puts it back as it came.
cd /d "%~dp0.."
python -m labmap site example --open
pause
