@echo off
rem Writes a 3D model of each room to build\model and opens the folder.
rem Open a .glb there in Open3D Viewer or Blender; walls stop at waist height so you can see in.
rem The directory (site.bat) shows each room in 3D in the browser too, with no app needed.
rem Works on the data folder named in labmap.ini (or this folder, if there's no labmap.ini).
cd /d "%~dp0"
python -m labmap model --open
pause
