@echo off
REM Remove Keyence MD-X2000 script from Windows Startup

echo =====================================================
echo  Keyence MD-X2000 - Remove from Windows Startup
echo =====================================================
echo.

set STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup

if exist "%STARTUP_FOLDER%\Keyence_MDX2000.lnk" (
    del "%STARTUP_FOLDER%\Keyence_MDX2000.lnk"
    echo Startup shortcut removed successfully.
) else (
    echo No startup shortcut found.
)

echo.
pause
