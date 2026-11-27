@echo off
setlocal

set "MGA_ROOT=%~dp0"
set "MGA_IMAGE=%MGA_ROOT%build\mga\gen\mga_image.bin"
set "MGA_CONVERTED_ISO=%MGA_ROOT%build\mga\disc\Metal Gear Acid (USA).iso"
if not defined MGA_ISO_CONFIG set "MGA_ISO_CONFIG=%MGA_ROOT%config\mga_iso_path.txt"

rem --game <disc> and --data-dir <folder> are read here; every other
rem argument goes to the game unchanged.
set "MGA_GAME="
set "MGA_ARGS="
:parse_args
if "%~1"=="" goto args_done
if /I "%~1"=="--game" goto arg_game
if /I "%~1"=="--data-dir" goto arg_data_dir
set MGA_ARGS=%MGA_ARGS% "%~1"
shift
goto parse_args
:arg_game
set "MGA_GAME=%~2"
shift
shift
goto parse_args
:arg_data_dir
set "SR_DATA_DIR=%~2"
shift
shift
goto parse_args
:args_done

if defined MGA_GAME set "PSP_ISO=%MGA_GAME%"
if defined PSP_ISO goto iso_ready
if exist "%MGA_ISO_CONFIG%" (
    set /p "PSP_ISO="<"%MGA_ISO_CONFIG%"
    if defined PSP_ISO goto iso_ready
)
set "PSP_ISO=%MGA_ROOT%Metal Gear Acid (USA)\Metal Gear Acid (USA).iso"

:iso_ready
rem Setup converts a CSO or CHD to an ISO once; start from that copy.
for %%F in ("%PSP_ISO%") do set "MGA_ISO_EXT=%%~xF"
if /I "%MGA_ISO_EXT%"==".cso" goto use_converted_iso
if /I "%MGA_ISO_EXT%"==".chd" goto use_converted_iso
goto iso_resolved
:use_converted_iso
if not exist "%MGA_CONVERTED_ISO%" goto missing_converted_iso
set "PSP_ISO=%MGA_CONVERTED_ISO%"
:iso_resolved

rem One folder for settings, saves and logs.
if not defined SR_DATA_DIR set "SR_DATA_DIR=%LOCALAPPDATA%\Metal Gear Acid Recomp"
if not exist "%SR_DATA_DIR%" mkdir "%SR_DATA_DIR%"

set "MGA_COMBINED_EXE=%MGA_ROOT%out\build\clang-cl\mga.exe"
set "MGA_SOFTWARE_EXE=%MGA_ROOT%out\build\clang-cl-software\mga.exe"
set "MGA_D3D12_EXE=%MGA_ROOT%out\build\clang-cl-d3d12\mga.exe"
set "MGA_VULKAN_EXE=%MGA_ROOT%out\build\clang-cl-vulkan\mga.exe"

if defined MGA_RENDERER goto renderer_override
rem The combined build reads its renderer from graphics.ini. Without it,
rem a single dedicated build is used as is.
if exist "%MGA_COMBINED_EXE%" goto select_default_build
if not exist "%MGA_D3D12_EXE%" if not exist "%MGA_VULKAN_EXE%" goto select_default_build
if not exist "%MGA_D3D12_EXE%" if not exist "%MGA_SOFTWARE_EXE%" goto select_default_build
if not exist "%MGA_VULKAN_EXE%" if not exist "%MGA_SOFTWARE_EXE%" goto select_default_build

rem Several dedicated builds. MGA_NONINTERACTIVE=1 (set by RecompLauncher)
rem picks the best one, skips the settings windows and never waits for a key.
if "%MGA_NONINTERACTIVE%"=="1" (
    if exist "%MGA_D3D12_EXE%" (set "MGA_RENDERER=d3d12") else set "MGA_RENDERER=vulkan"
    goto renderer_override
)

echo Select a renderer:
if exist "%MGA_D3D12_EXE%" (echo   [D] D3D12 ^(recommended^)) else (echo   [D] D3D12 ^(not built^))
if exist "%MGA_VULKAN_EXE%" (echo   [V] Vulkan) else (echo   [V] Vulkan ^(not built^))
if exist "%MGA_SOFTWARE_EXE%" (echo   [S] Software / GDI reference) else (echo   [S] Software / GDI ^(not built^))
choice /C DVS /N /M "Renderer [D/V/S]: "
set "MGA_RENDERER=d3d12"
if errorlevel 2 set "MGA_RENDERER=vulkan"
if errorlevel 3 set "MGA_RENDERER=software"
goto renderer_override

:renderer_override
if /I "%MGA_RENDERER%"=="d3d12" goto override_d3d12
if /I "%MGA_RENDERER%"=="vulkan" goto override_vulkan
if /I "%MGA_RENDERER%"=="vk" goto override_vulkan
if /I "%MGA_RENDERER%"=="software" goto override_software
if /I "%MGA_RENDERER%"=="sw" goto override_software
if /I "%MGA_RENDERER%"=="gdi" goto override_software
echo Invalid MGA_RENDERER value "%MGA_RENDERER%".
echo Expected d3d12, vulkan, or software.
call :pause_if_interactive
exit /b 2

:override_d3d12
set "MGA_RENDERER_NAME=D3D12 override"
set "SR_GPU=d3d12"
set "SR_VIDEO="
goto select_requested_build

:override_vulkan
set "MGA_RENDERER_NAME=Vulkan override"
set "SR_GPU=vk"
set "SR_VIDEO="
goto select_requested_build

:override_software
set "MGA_RENDERER_NAME=Software / GDI override"
set "SR_GPU=sw"
set "SR_VIDEO=gdi"
goto select_requested_build

:select_requested_build
if exist "%MGA_COMBINED_EXE%" (
    set "MGA_EXE=%MGA_COMBINED_EXE%"
    set "MGA_BUILD_NAME=combined"
    goto executable_ready
)
if /I "%SR_GPU%"=="d3d12" if exist "%MGA_D3D12_EXE%" (
    set "MGA_EXE=%MGA_D3D12_EXE%"
    set "MGA_BUILD_NAME=D3D12-only"
    goto executable_ready
)
if /I "%SR_GPU%"=="vk" if exist "%MGA_VULKAN_EXE%" (
    set "MGA_EXE=%MGA_VULKAN_EXE%"
    set "MGA_BUILD_NAME=Vulkan-only"
    goto executable_ready
)
if /I "%SR_GPU%"=="sw" if exist "%MGA_SOFTWARE_EXE%" (
    set "MGA_EXE=%MGA_SOFTWARE_EXE%"
    set "MGA_BUILD_NAME=software-only"
    goto executable_ready
)
goto missing_selected_renderer

:select_default_build
set "MGA_RENDERER_NAME=graphics.ini"
if exist "%MGA_COMBINED_EXE%" (
    set "MGA_EXE=%MGA_COMBINED_EXE%"
    set "MGA_BUILD_NAME=combined"
    goto executable_ready
)
if exist "%MGA_SOFTWARE_EXE%" (
    set "MGA_EXE=%MGA_SOFTWARE_EXE%"
    set "MGA_BUILD_NAME=software-only"
    set "SR_GPU=sw"
    set "SR_VIDEO=gdi"
    goto executable_ready
)
if exist "%MGA_D3D12_EXE%" (
    set "MGA_EXE=%MGA_D3D12_EXE%"
    set "MGA_BUILD_NAME=D3D12-only"
    set "SR_GPU=d3d12"
    set "SR_VIDEO="
    goto executable_ready
)
if exist "%MGA_VULKAN_EXE%" (
    set "MGA_EXE=%MGA_VULKAN_EXE%"
    set "MGA_BUILD_NAME=Vulkan-only"
    set "SR_GPU=vk"
    set "SR_VIDEO="
    goto executable_ready
)
goto missing_executable

:executable_ready

if not exist "%MGA_IMAGE%" goto missing_image
if not exist "%PSP_ISO%" goto missing_iso

call :migrate_old_data

rem Not a parenthesized block: paths such as "(USA)" would end it early.
if /I not "%MGA_LAUNCH_DRY_RUN%"=="1" goto launch
echo Build: %MGA_BUILD_NAME%
echo Renderer: %MGA_RENDERER_NAME%
echo Executable: %MGA_EXE%
echo ISO: %PSP_ISO%
echo Data: %SR_DATA_DIR%
echo Arguments:%MGA_ARGS%
echo SR_GPU=%SR_GPU%
echo SR_VIDEO=%SR_VIDEO%
exit /b 0

:launch
echo Build: %MGA_BUILD_NAME%
echo Renderer: %MGA_RENDERER_NAME%
echo Settings, saves and logs: %SR_DATA_DIR%

pushd "%MGA_ROOT%"

if "%MGA_NONINTERACTIVE%"=="1" goto start_game
echo Opening Metal Gear Acid settings...
"%MGA_EXE%" --configure
if errorlevel 2 goto settings_failed

:start_game
echo Starting Metal Gear Acid...
"%MGA_EXE%" --boot "%MGA_IMAGE%" 08804000 0880432c none --gui%MGA_ARGS%
set "MGA_EXIT_CODE=%ERRORLEVEL%"

popd

if not "%MGA_EXIT_CODE%"=="0" goto game_failed
exit /b 0

rem Earlier versions kept settings beside each mga.exe and saves in the
rem repository's memstick folder. Copy them once; the originals stay.
:migrate_old_data
if not exist "%SR_DATA_DIR%\memstick" if exist "%MGA_ROOT%memstick\" (
    echo Copying saves from "%MGA_ROOT%memstick" to "%SR_DATA_DIR%\memstick"
    robocopy "%MGA_ROOT%memstick" "%SR_DATA_DIR%\memstick" /E /NFL /NDL /NJH /NJS /NP >nul
)
for %%F in ("%MGA_EXE%") do set "MGA_EXE_DIR=%%~dpF"
for %%N in (graphics.ini input.ini) do (
    if not exist "%SR_DATA_DIR%\%%N" if exist "%MGA_EXE_DIR%%%N" copy /Y "%MGA_EXE_DIR%%%N" "%SR_DATA_DIR%\%%N" >nul
)
exit /b 0

:missing_selected_renderer
echo The selected %MGA_RENDERER_NAME% build was not found.
echo Build the combined clang-cl preset or the matching compatibility preset.
call :pause_if_interactive
exit /b 1

:missing_executable
echo Metal Gear Acid is not built.
echo Run "Install Metal Gear Acid.bat", or build mga_driver with the
echo clang-cl (combined), clang-cl-software, clang-cl-d3d12, or
echo clang-cl-vulkan preset.
call :pause_if_interactive
exit /b 1

:missing_image
echo The generated game image was not found:
echo %MGA_IMAGE%
echo Run "Install Metal Gear Acid.bat" before launching the game.
call :pause_if_interactive
exit /b 1

:missing_converted_iso
echo %PSP_ISO% is a compressed disc image.
echo Run "Install Metal Gear Acid.bat" with it once; setup converts it to
echo %MGA_CONVERTED_ISO%
call :pause_if_interactive
exit /b 1

:missing_iso
echo The Metal Gear Acid disc image was not found:
echo %PSP_ISO%
echo Run "Install Metal Gear Acid.bat", pass --game C:\path\to\disc.iso,
echo or set PSP_ISO to the full path of a supported USA disc image.
call :pause_if_interactive
exit /b 1

:settings_failed
echo The Metal Gear Acid settings launcher failed.
popd
call :pause_if_interactive
exit /b 2

:game_failed
echo Metal Gear Acid exited with code %MGA_EXIT_CODE%.
if exist "%SR_DATA_DIR%\logs\mga.log" echo Log: %SR_DATA_DIR%\logs\mga.log
call :pause_if_interactive
exit /b %MGA_EXIT_CODE%

:pause_if_interactive
if not "%MGA_NONINTERACTIVE%"=="1" pause
exit /b 0
