@echo off
REM Setup script for CHDMAN executable

echo RetroClamp CHDMAN Setup
echo ======================
echo.

REM Check if bin directory exists
if not exist bin (
    echo Creating bin directory...
    mkdir bin
)

echo.
echo Please copy the chdman.exe file to the bin directory.
echo You can download CHDMAN from the MAME project website or extract it from a MAME distribution.
echo.
echo Once you have placed chdman.exe in the bin directory, you can run the RetroClamp application.
echo.

REM Check if chdman.exe already exists in the bin directory
if exist bin\chdman.exe (
    echo CHDMAN executable found in bin directory.
    echo Version information:
    bin\chdman.exe --version
) else (
    echo CHDMAN executable not found in bin directory.
    echo Please copy chdman.exe to the bin directory.
)

echo.
echo Press any key to exit...
pause > nul
