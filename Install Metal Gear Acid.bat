@echo off
setlocal

cd /d "%~dp0"

where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0install.py" %*
    set "MGA_INSTALL_EXIT=%ERRORLEVEL%"
    goto finished
)

where python >nul 2>nul
if errorlevel 1 (
    echo Python 3.11 or newer was not found.
    echo Install Python from https://www.python.org/downloads/windows/
    set "MGA_INSTALL_EXIT=1"
    goto finished
)

python "%~dp0install.py" %*
set "MGA_INSTALL_EXIT=%ERRORLEVEL%"

:finished
echo.
if "%MGA_INSTALL_EXIT%"=="0" (
    echo Setup finished. Double-click "Launch Metal Gear Acid.bat" to play.
) else (
    echo Setup did not complete. Review the error above, then run this
    echo installer again.
)
pause
exit /b %MGA_INSTALL_EXIT%
