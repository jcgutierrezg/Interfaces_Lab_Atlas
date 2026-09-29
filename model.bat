@echo off
rem Writes a 3D model of each room to build\model and opens the folder.
rem Double-click a .glb there to look around it in 3D Viewer; walls stop at waist height so you can see in.
rem Works on the data folder named in labmap.ini (or this folder, if there's no labmap.ini).
cd /d "%~dp0"
python -m labmap model --open
pause
