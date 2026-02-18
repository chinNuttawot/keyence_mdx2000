@echo off
REM Install Keyence MD-X2000 script to Windows Startup
REM Run this script as Administrator for best results

echo =====================================================
echo  Keyence MD-X2000 - Add to Windows Startup
echo =====================================================
echo.

REM Get the directory where this script is located
set PROJECT_DIR=%~dp0
REM Remove trailing backslash
set PROJECT_DIR=%PROJECT_DIR:~0,-1%
set STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup

echo Project Directory: %PROJECT_DIR%
echo Startup Folder: %STARTUP_FOLDER%
echo.

REM Create shortcut in Startup folder
echo Creating startup shortcut...

set SCRIPT="%TEMP%\create_shortcut.vbs"
echo Set oWS = WScript.CreateObject("WScript.Shell") > %SCRIPT%
echo sLinkFile = "%STARTUP_FOLDER%\Keyence_MDX2000.lnk" >> %SCRIPT%
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> %SCRIPT%
echo oLink.TargetPath = "%PROJECT_DIR%\run_keyence_silent.vbs" >> %SCRIPT%
echo oLink.WorkingDirectory = "%PROJECT_DIR%" >> %SCRIPT%
echo oLink.Description = "Keyence MD-X2000 Laser Marker Monitor" >> %SCRIPT%
echo oLink.Save >> %SCRIPT%

cscript //nologo %SCRIPT%
del %SCRIPT%

if exist "%STARTUP_FOLDER%\Keyence_MDX2000.lnk" (
    echo.
    echo =====================================================
    echo  SUCCESS! Startup shortcut created.
    echo =====================================================
    echo.
    echo The script will run automatically when Windows starts.
    echo.
    echo To remove: Delete the shortcut from:
    echo   %STARTUP_FOLDER%\Keyence_MDX2000.lnk
    echo.
) else (
    echo.
    echo ERROR: Failed to create startup shortcut.
    echo Please try running this script as Administrator.
    echo.
)

pause
