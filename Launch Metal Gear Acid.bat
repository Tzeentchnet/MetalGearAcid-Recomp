@echo off
setlocal

set "MGA_ROOT=%~dp0"
set "MGA_IMAGE=%MGA_ROOT%build\mga\gen\mga_image.bin"
if not defined MGA_ISO_CONFIG set "MGA_ISO_CONFIG=%MGA_ROOT%config\mga_iso_path.txt"

if defined PSP_ISO goto iso_ready
if exist "%MGA_ISO_CONFIG%" (
    set /p "PSP_ISO="<"%MGA_ISO_CONFIG%"
    if defined PSP_ISO goto iso_ready
)
set "PSP_ISO=%MGA_ROOT%Metal Gear Acid (USA)\Metal Gear Acid (USA).iso"

:iso_ready

set "MGA_COMBINED_EXE=%MGA_ROOT%out\build\clang-cl\mga.exe"
set "MGA_SOFTWARE_EXE=%MGA_ROOT%out\build\clang-cl-software\mga.exe"
set "MGA_D3D12_EXE=%MGA_ROOT%out\build\clang-cl-d3d12\mga.exe"
set "MGA_VULKAN_EXE=%MGA_ROOT%out\build\clang-cl-vulkan\mga.exe"

if defined MGA_RENDERER goto renderer_override
goto select_default_build

:renderer_override
if /I "%MGA_RENDERER%"=="d3d12" goto override_d3d12
if /I "%MGA_RENDERER%"=="vulkan" goto override_vulkan
if /I "%MGA_RENDERER%"=="vk" goto override_vulkan
if /I "%MGA_RENDERER%"=="software" goto override_software
if /I "%MGA_RENDERER%"=="sw" goto override_software
if /I "%MGA_RENDERER%"=="gdi" goto override_software
echo Invalid MGA_RENDERER value "%MGA_RENDERER%".
echo Expected d3d12, vulkan, or software.
pause
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

if /I "%MGA_LAUNCH_DRY_RUN%"=="1" goto launch_dry_run

echo Build: %MGA_BUILD_NAME%
echo Renderer: %MGA_RENDERER_NAME%

pushd "%MGA_ROOT%"

echo Opening Metal Gear Acid settings...
"%MGA_EXE%" --configure
if errorlevel 2 goto settings_failed

echo Starting Metal Gear Acid...
"%MGA_EXE%" --boot "%MGA_IMAGE%" 08804000 0880432c none --gui %*
set "MGA_EXIT_CODE=%ERRORLEVEL%"

popd

if not "%MGA_EXIT_CODE%"=="0" goto game_failed
exit /b 0

:launch_dry_run
echo Build: %MGA_BUILD_NAME%
echo Renderer: %MGA_RENDERER_NAME%
echo Executable: %MGA_EXE%
echo ISO: %PSP_ISO%
echo SR_GPU=%SR_GPU%
echo SR_VIDEO=%SR_VIDEO%
exit /b 0

:missing_selected_renderer
echo The selected %MGA_RENDERER_NAME% build was not found.
echo Build the combined clang-cl preset or the matching compatibility preset.
pause
exit /b 1

:missing_executable
echo Metal Gear Acid is not built.
echo Build mga_driver with the clang-cl or clang-cl-software preset.
pause
exit /b 1

:missing_image
echo The generated game image was not found:
echo %MGA_IMAGE%
echo Run tools\mga\gen.py before launching the game.
pause
exit /b 1

:missing_iso
echo The Metal Gear Acid ISO was not found:
echo %PSP_ISO%
echo Run "Install Metal Gear Acid.bat" or set PSP_ISO to the full path
echo of a supported USA disc image.
pause
exit /b 1

:settings_failed
echo The Metal Gear Acid settings launcher failed.
popd
pause
exit /b 2

:game_failed
echo Metal Gear Acid exited with code %MGA_EXIT_CODE%.
pause
exit /b %MGA_EXIT_CODE%
