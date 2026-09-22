@echo off
rem Puts the example back as it came: the original workbook, and no generated files (layouts, report, site).
rem Your moves are gone after this. The workbook you had is kept as example\lab-data.before-reset.xlsx.
cd /d "%~dp0"
choice /m "Undo all changes to the example"
if errorlevel 2 exit /b
copy /y "lab-data.xlsx" "lab-data.before-reset.xlsx" >nul
copy /y "lab-data.original.xlsx" "lab-data.xlsx" >nul
if exist "build" rmdir /s /q "build"
echo The example is back as it came. Run layout.bat to draw it again.
pause
