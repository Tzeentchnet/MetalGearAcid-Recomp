@echo off
setlocal

set "MGA_ROOT=%~dp0"
set "MGA_IMAGE=%MGA_ROOT%build\mga\gen\mga_image.bin"

if defined PSP_ISO goto iso_ready
set "PSP_ISO=%MGA_ROOT%Metal Gear Acid (USA)\Metal Gear Acid (USA).iso"

:iso_ready

set "MGA_D3D12_EXE=%MGA_ROOT%out\build\clang-cl-d3d12\mga.exe"
set "MGA_VULKAN_EXE=%MGA_ROOT%out\build\clang-cl-vulkan\mga.exe"
set "MGA_SOFTWARE_EXE=%MGA_ROOT%out\build\clang-cl\mga.exe"

if defined MGA_RENDERER goto renderer_override

if exist "%MGA_D3D12_EXE%" if not exist "%MGA_VULKAN_EXE%" if not exist "%MGA_SOFTWARE_EXE%" goto select_d3d12
if not exist "%MGA_D3D12_EXE%" if exist "%MGA_VULKAN_EXE%" if not exist "%MGA_SOFTWARE_EXE%" goto select_vulkan
if not exist "%MGA_D3D12_EXE%" if not exist "%MGA_VULKAN_EXE%" if exist "%MGA_SOFTWARE_EXE%" goto select_software

if not exist "%MGA_D3D12_EXE%" if not exist "%MGA_VULKAN_EXE%" if not exist "%MGA_SOFTWARE_EXE%" goto missing_executable

echo Select a renderer:
if exist "%MGA_D3D12_EXE%" (echo   [D] D3D12 ^(recommended^)) else (echo   [D] D3D12 ^(not built^))
if exist "%MGA_VULKAN_EXE%" (echo   [V] Vulkan) else (echo   [V] Vulkan ^(not built^))
if exist "%MGA_SOFTWARE_EXE%" (echo   [S] Software / GDI reference) else (echo   [S] Software / GDI ^(not built^))
choice /C DVS /N /M "Renderer [D/V/S]: "
if errorlevel 3 goto select_software
if errorlevel 2 goto select_vulkan
goto select_d3d12

:renderer_override
if /I "%MGA_RENDERER%"=="d3d12" goto select_d3d12
if /I "%MGA_RENDERER%"=="vulkan" goto select_vulkan
if /I "%MGA_RENDERER%"=="vk" goto select_vulkan
if /I "%MGA_RENDERER%"=="software" goto select_software
if /I "%MGA_RENDERER%"=="sw" goto select_software
if /I "%MGA_RENDERER%"=="gdi" goto select_software
echo Invalid MGA_RENDERER value "%MGA_RENDERER%".
echo Expected d3d12, vulkan, or software.
pause
exit /b 2

:select_d3d12
set "MGA_RENDERER=d3d12"
set "MGA_RENDERER_NAME=D3D12"
set "MGA_EXE=%MGA_D3D12_EXE%"
set "SR_GPU=d3d12"
set "SR_VIDEO="
goto executable_ready

:select_vulkan
set "MGA_RENDERER=vulkan"
set "MGA_RENDERER_NAME=Vulkan"
set "MGA_EXE=%MGA_VULKAN_EXE%"
set "SR_GPU=vk"
set "SR_VIDEO="
goto executable_ready

:select_software
set "MGA_RENDERER=software"
set "MGA_RENDERER_NAME=Software / GDI"
set "MGA_EXE=%MGA_SOFTWARE_EXE%"
set "SR_GPU=sw"
set "SR_VIDEO=gdi"
goto executable_ready

:executable_ready

if not exist "%MGA_EXE%" goto missing_selected_renderer
if not exist "%MGA_IMAGE%" goto missing_image
if not exist "%PSP_ISO%" goto missing_iso

if /I "%MGA_LAUNCH_DRY_RUN%"=="1" (
    echo Renderer: %MGA_RENDERER_NAME%
    echo Executable: %MGA_EXE%
    echo SR_GPU=%SR_GPU%
    echo SR_VIDEO=%SR_VIDEO%
    exit /b 0
)

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

:missing_selected_renderer
echo The selected %MGA_RENDERER_NAME% build was not found:
echo %MGA_EXE%
echo Build the matching mga_driver preset, or choose another renderer.
pause
exit /b 1

:missing_executable
echo Metal Gear Acid is not built.
echo Build mga_driver with the clang-cl, clang-cl-d3d12, or clang-cl-vulkan preset.
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
echo Set PSP_ISO to the full path of a supported USA disc image.
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
