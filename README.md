# Metal Gear Acid Recomp

Source-only Windows static recompilation of **Metal Gear Acid
(ULUS-10006 v1.00)**. The project uses the PSP static recompiler/runtime fork
developed for the Killzone: Liberation recompilation.

No game executable, generated game C, disc data, or other copyrighted game
assets belong in this repository. You must supply your own supported USA disc.


> [!NOTE]
> **Why isn't there just an .exe to download?** Two reasons. First, safety:
> please don't download random .exe files from the internet, even from
> GitHub releases, including this one if it ever shows up! It's just good
> practice to be careful about what you run on your computer. Second, it's
> the law: this project doesn't own Metal Gear Acid, so it's not
> allowed to hand out a ready-to-play build of the game. Instead, you build
> the program yourself from this source code and combine it with a copy of
> the game disc that you already legally own. That way nobody's copyrighted
> game data ever leaves your own computer.

## Development status

This project is under active development. Treat current builds as experimental.

## Repository

[Tzeentchnet/MetalGearAcid-Recomp](https://github.com/Tzeentchnet/MetalGearAcid-Recomp)

Clone with the tested public runtime fork:

```powershell
git clone --recurse-submodules `
  https://github.com/Tzeentchnet/MetalGearAcid-Recomp.git
```

The parent pins the maintained `Tzeentchnet/psp-recomp` fork at tested commit
`138c2b8`.

## Requirements

- Windows 10/11 x64
- Git with submodule support
- Python 3.11 or newer
- CMake 3.25 or newer and Ninja
- Visual Studio 2022 Build Tools with clang-cl, MSVC libraries, and a Windows
  SDK
- Vulkan SDK for the default combined hardware build. A standard
  `C:\VulkanSDK\<version>` install is detected automatically.

## Quick setup

The guided installer verifies the ISO, downloads or initializes the pinned
runtime fork, extracts the required files, generates native sources, detects
the Visual Studio build environment, builds the combined D3D12/Vulkan/software
executable, and remembers the ISO location for the launcher. It downloads the
pinned SDL3 development package when SDL3 is not already discoverable.

Double-click `Install Metal Gear Acid.bat` and enter the ISO path when
prompted. The same setup can be run from a terminal:

```powershell
python install.py "C:\path\to\Metal Gear Acid (USA).iso"
```

For the dependency-light software/GDI build, which needs neither SDL3 nor the
Vulkan SDK, use:

```powershell
python install.py "C:\path\to\Metal Gear Acid (USA).iso" `
  --software-only
```

`--renderer d3d12` and `--renderer vulkan` retain dedicated compatibility
builds. Pass `--sdl3-dir "C:\path\to\SDL3\cmake"` to use a local SDL3 package
instead of the pinned download. The installer reports missing Git, CMake,
Ninja, Visual Studio, Clang, Vulkan SDK, or Windows SDK components with an
actionable error. It also works from a source archive by cloning the exact
runtime commit recorded in `config\mga.toml`.

When setup completes, double-click `Launch Metal Gear Acid.bat`.

### Manual setup

Initialize the runtime fork:

```powershell
git submodule update --init --recursive
```

Extract the verified disc and every plaintext bundled PRX:

```powershell
python tools\mga\extract.py "C:\path\to\Metal Gear Acid (USA).iso"
```

Generate the relocated image, import map, function inventory, and split C:

```powershell
python tools\mga\gen.py
```

From a Visual Studio x64 developer shell, build the combined executable:

```powershell
cmake --preset clang-cl
cmake --build --preset clang-cl --target mga_driver
```

This builds D3D12, Vulkan, and software rendering into
`out\build\clang-cl\mga.exe`. CMake downloads the pinned SDL3 package when
needed and copies SDL3, required VFPU tables, and fonts beside the executable.

The deterministic software-only baseline remains available separately:

```powershell
cmake --preset clang-cl-software
cmake --build --preset clang-cl-software --target mga_driver
```

The `clang-cl-d3d12` and `clang-cl-vulkan` presets remain available for
backend-isolated diagnostics.

D3D12 and Vulkan use PSP-quantized nearest/bilinear texture sampling and
integer texture-function/fog math by default. Set `SR_GPU_PSP_SAMPLER=0` only
for A/B diagnostics against host hardware filtering.

Run it against the same verified disc:

```powershell
$env:PSP_ISO = "C:\path\to\Metal Gear Acid (USA).iso"
$env:SR_FPS_COUNTER = "1"
out\build\clang-cl\mga.exe --boot `
  build\mga\gen\mga_image.bin 08804000 0880432c none --gui
```

For a local Windows checkout, double-click `Launch Metal Gear Acid.bat`. The
launcher prefers the combined build, opens the Metal Gear Acid graphics and
controller settings, and starts the executable with the persisted renderer
choice. It falls back to software-only or dedicated compatibility builds when
needed. Set `MGA_RENDERER=d3d12`, `MGA_RENDERER=vulkan`, or
`MGA_RENDERER=software` only when an environment override is useful for
automation.

The launcher first uses `PSP_ISO` when set, then the ISO path saved by the
installer, and finally
`Metal Gear Acid (USA)\Metal Gear Acid (USA).iso`.

The first GUI run creates portable `graphics.ini` and `input.ini` beside the
executable and opens controller setup. Metal Gear Acid exposes standard PSP
button bindings without the Killzone-specific twin-stick controls. The runtime
uses its conservative one-million-instruction fallback cap; override it only
for diagnostics with `SR_INTERP_MAX_STEPS`.

### Graphics quality

The combined build offers **Automatic**, **D3D12 hardware**,
**Software reference**, and **Vulkan**. Automatic selects D3D12 when it is
compiled in.

For the highest-quality 4K path:

1. Select **D3D12 hardware**.
2. Select **8x (3840x2176)** internal resolution.
3. Select **2x xBRZ** or **3x xBRZ** texture upscaling.
4. Select **Full resolution (best quality)** D3D12 shading.
5. Press **F11** in the game window for borderless desktop fullscreen.

The PSP display is 480:272, so 8x is 3840x2176 rather than exactly 3840x2160.
Presentation preserves that aspect ratio and letterboxes instead of stretching
the image.

| Renderer | Internal GE resolution | Texture scaling | Role |
|---|---|---|---|
| D3D12 | 1x-8x | 1x-5x xBRZ | Recommended high-resolution renderer |
| Vulkan | Native 512x272 target | 1x-5x xBRZ | Alternate hardware renderer |
| Software | Native PSP resolution | None | Pixel-exact reference baseline |

xBRZ scales decoded game textures before hardware upload. It does not scale
framebuffer/render-target textures, and higher factors can use substantially
more GPU memory. D3D12 **Balanced** shading uses variable-rate shading on
supported GPUs; **Full resolution** shades every internal-resolution fragment.

Settings are persisted in `graphics.ini` beside the executable. The equivalent
keys are `renderer`, `internal_resolution`, `texture_scale`, and
`d3d12_full_rate`.

### Using existing PSP saves

Close the game, then copy the complete Metal Gear Acid save folder from the
PSP Memory Stick's `PSP\SAVEDATA\` directory into:

```text
memstick\PSP\SAVEDATA\
```

Keep the save folder and all files inside it together. Supported USA saves use
folder names beginning with `ULUS10006`; do not rename another region's save
to that prefix. For example, a folder named `ULUS10006002` must end up at
`memstick\PSP\SAVEDATA\ULUS10006002\`. It appears under **LOAD GAME**, not
necessarily **CONTINUE**.

The launcher uses the repository's `memstick\` directory by default. To keep
saves elsewhere, set `SR_MEMSTICK` to an alternate Memory Stick root that
contains `PSP\SAVEDATA\` before starting the launcher. Back up the original
save before copying or testing it. See
[Isolated memstick fixtures](docs/REPRODUCTION.md#7-isolated-memstick-fixtures)
for verified copy and validation commands.

`SR_FPS_COUNTER=1` updates the window title every 500 ms with rolling FPS and
average frame time on GDI, Vulkan, and D3D12.

For repeatable profiling, `SR_PERF_FILE` writes per-presentation host/backend/
GPU timing and `SR_INTERP_PROFILE` writes aggregate fallback cost by module and
target. `SR_D3D12_CAPTURE_INTERNAL=1` preserves full scaled output for
resolution analysis. See [REPRODUCTION.md](docs/REPRODUCTION.md) for the
report tools and acceptance matrix.

Serialized D3D12 pipeline-library persistence is not a supported gameplay
setting: it removed the validation GPU on reuse. In-memory asynchronous PSOs
remain enabled; disk persistence requires the explicit
`SR_D3D12_UNSAFE_PSO_CACHE=1` diagnostic acknowledgement.

For deterministic tests, use the shared profiles in `config/` and create
isolated PPSSPP/native memstick roots with `tools\mga\memstick.py`; see
[REPRODUCTION.md](docs/REPRODUCTION.md). The front-end acceptance command
validates exact menu frames, input edges, the overlay route, fallback set, and
real-time XAudio2 output.

## License

The recompiler/runtime is derived in part from PPSSPP and is
GPL-2.0-or-later. See [LICENSE](LICENSE), [CREDITS.md](CREDITS.md), and the
runtime fork's license notices for full third-party provenance.
