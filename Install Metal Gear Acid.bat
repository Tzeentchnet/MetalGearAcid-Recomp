@echo off
setlocal

cd /d "%~dp0"

set "MGA_PREPARE="
set "MGA_INSTALL_TOOLS="
for %%A in (%*) do (
    if /I "%%~A"=="--prepare" set "MGA_PREPARE=1"
    if /I "%%~A"=="--install-build-tools" set "MGA_INSTALL_TOOLS=1"
)

set "MGA_PYTHON="
where py >nul 2>nul
if not errorlevel 1 set "MGA_PYTHON=py -3"
if not defined MGA_PYTHON (
    where python >nul 2>nul
    if not errorlevel 1 set "MGA_PYTHON=python"
)
if not defined MGA_PYTHON call :find_installed_python
if not defined MGA_PYTHON call :offer_python
if not defined MGA_PYTHON (
    echo Python 3.11 or newer was not found.
    echo Install Python from https://www.python.org/downloads/windows/
    set "MGA_INSTALL_EXIT=1"
    goto finished
)

%MGA_PYTHON% "%~dp0install.py" %*
set "MGA_INSTALL_EXIT=%ERRORLEVEL%"
goto finished

:offer_python
where winget >nul 2>nul
if errorlevel 1 exit /b 0
if defined MGA_INSTALL_TOOLS goto install_python
if defined MGA_PREPARE exit /b 0
echo Python 3.11 or newer was not found.
choice /C YN /M "Install Python 3.13 for your user account with winget now"
if errorlevel 2 exit /b 0
:install_python
echo Installing Python 3.13 with winget...
winget install --exact --id Python.Python.3.13 --scope user --silent --accept-package-agreements --accept-source-agreements
call :find_installed_python
exit /b 0

:find_installed_python
for %%V in (314 313 312 311) do (
    if not defined MGA_PYTHON if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" set "MGA_PYTHON="%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe""
)
exit /b 0

:finished
rem A launcher's --prepare run has no console to answer the pause.
if defined MGA_PREPARE exit /b %MGA_INSTALL_EXIT%
echo.
if "%MGA_INSTALL_EXIT%"=="0" (
    echo Setup finished. Double-click "Launch Metal Gear Acid.bat" to play.
) else (
    echo Setup did not complete. Review the error above, then run this
    echo installer again.
)
pause
exit /b %MGA_INSTALL_EXIT%
