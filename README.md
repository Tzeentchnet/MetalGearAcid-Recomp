# Metal Gear Acid Recomp

<a href="https://recomplauncher.com"><picture><source media="(prefers-color-scheme: dark)" srcset="https://recomplauncher.com/assets/press/launcher/badge-light.svg"><img alt="Get it on RecompLauncher" src="https://recomplauncher.com/assets/press/launcher/badge-dark.svg" height="48"></picture></a>

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

The parent tracks the maintained `Tzeentchnet/psp-recomp` `main` branch and
pins commit `9b45870` (tested fork commit `138c2b8` plus local runtime work).
The legacy `kzl` branch remains available for compatibility.

## Documentation

- [Documentation index](docs/README.md)
- [Project status](docs/STATUS.md)
- [Project completion plan](docs/PLAN.md)
- [Evidence-backed findings](docs/FINDINGS.md)
- [Upstream framework improvements](docs/UPSTREAM.md)
- [Reproduction and acceptance checks](docs/REPRODUCTION.md)

## Requirements

- Windows 10/11 x64
- Git with submodule support (not needed for a release zip)
- Python 3.11 or newer (setup can install it with winget)
- CMake 3.25 or newer and Ninja (included with the Build Tools' C++ CMake
  tools)
- Visual Studio 2022 Build Tools with clang-cl, MSVC libraries, and a Windows
  SDK (setup can install them)
- SDL3 when enabling the D3D12 or Vulkan renderer (setup can download it)
- Vulkan SDK for the combined build or the Vulkan renderer. A standard
  `C:\VulkanSDK\<version>` install is detected automatically.

## Quick setup

The guided installer verifies the disc image, downloads or initializes the
pinned runtime fork, extracts the required files, generates native sources,
detects the Visual Studio build environment, builds the selected renderer, and
remembers the disc location for the launcher.

Double-click `Install Metal Gear Acid.bat` and enter the disc path when
prompted. Setup offers to:

- install Python 3.13 with winget when no Python 3.11+ is found;
- install Visual Studio 2022 Build Tools with the C++ Clang tools when they
  are missing (several gigabytes; you accept Microsoft's license terms);
- build the recommended D3D12 renderer, downloading the pinned SDL3 3.4.20
  development package from GitHub and checking its SHA-256. Answer `n` for
  the software renderer, which needs no SDL3.

The same setup runs from a terminal:

```powershell
python install.py "C:\path\to\Metal Gear Acid (USA).iso" `
  --renderer d3d12 --download-sdl3
```

`--renderer combined` builds one executable with D3D12, Vulkan and software
renderers, chosen in `graphics.ini`; it needs the Vulkan SDK. `--software-only`
(or `--renderer software`) builds the dependency-light software/GDI renderer,
which needs neither SDL3 nor the Vulkan SDK. `--renderer vulkan` builds the
dedicated Vulkan renderer.

`--install-build-tools` installs missing Build Tools without asking, and
`--sdl3-dir "C:\path\to\SDL3\cmake"` uses an SDL3 package you already have;
without either SDL3 option, CMake downloads its pinned SDL3 package. The
installer reports missing Git, CMake, Ninja, Visual Studio, Clang, Vulkan SDK,
or Windows SDK components with an actionable error. It also works from a source
archive by cloning the exact runtime commit recorded in `config\mga.toml`.

The disc can be an `.iso`, a `.cso` (CISO v1/v2), or a `.chd` made with
`chdman createdvd`. Setup converts a CSO or CHD once to
`build\mga\disc\Metal Gear Acid (USA).iso`, checking every CHD hunk and the
image's SHA-1, and the game runs from that copy.

Running setup again is quick: `build\mga\install_stamp.json` records what was
extracted, generated and built, and steps whose inputs are unchanged are
skipped. Pass `--force` to redo everything.

When setup completes, double-click `Launch Metal Gear Acid.bat`. It takes
`--game "C:\path\to\disc.iso"` for shortcuts and scripts, and
`--data-dir "C:\path"` to keep settings and saves elsewhere; other arguments,
such as `--fullscreen`, go to the game.

### Settings, saves and logs

Settings (`graphics.ini`, `input.ini`), saves (`memstick\PSP\SAVEDATA`) and
logs (`logs\mga.log`, with `mga.previous.log` from the run before) share one
data folder: `%LOCALAPPDATA%\Metal Gear Acid Recomp` by default, or the folder
in `SR_DATA_DIR` / `--data-dir`. The first launch copies settings and saves
from the locations older versions used (beside `mga.exe` and the repository's
`memstick\`); the originals stay where they were. `SR_SETTINGS_DIR`,
`SR_MEMSTICK` and `SR_LOG_FILE` still override single locations, and `SR_LOG=0`
turns the log off.

F11 switches between a window and full screen. `--fullscreen` starts full
screen, as does RecompLauncher's Big Picture mode
(`RECOMPLAUNCHER_MODE=bigpicture`).

### RecompLauncher

Each release zip carries a `recomplauncher.json`, so
[RecompLauncher](https://recomplauncher.com) can set the game up: pick your
USA `.iso`, `.cso` or `.chd`, and the launcher runs
`Install Metal Gear Acid.bat --prepare <disc>`. Two setup ticks map to
installer options: **Build the D3D12 renderer** (on by default;
`--renderer d3d12 --download-sdl3`) and **Install the build tools if they are
missing** (off until the player accepts Microsoft's license;
`--install-build-tools`). The launcher starts `Launch Metal Gear Acid.bat
--game <disc>` without its settings windows (`MGA_NONINTERACTIVE=1`) and with
`SR_DATA_DIR` set to the game's data folder, so settings, saves and logs live
there. The launcher's settings page exposes the internal resolution, full
screen, and the keyboard and controller bindings in `input.ini`; its Logs
action opens the log folder.

Releases are made by pushing a `v*` tag: `.github/workflows/release.yml` runs
`tools\package_release.py`, which zips the tracked sources and the pinned
runtime into `MetalGearAcid-Recomp-<tag>-Windows-x64.zip`.

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

When only separate D3D12, Vulkan, or software builds exist and there is more
than one, the launcher prompts for D3D12 (recommended), Vulkan, or the
software/GDI reference renderer; RecompLauncher (`MGA_NONINTERACTIVE=1`) picks
the best one without asking. The launcher first uses `--game`, then `PSP_ISO`
when set, then the disc path saved by the installer, and finally
`Metal Gear Acid (USA)\Metal Gear Acid (USA).iso`.

The first GUI run creates `graphics.ini` and `input.ini` in the data folder
(see [Settings, saves and logs](#settings-saves-and-logs)) and opens
controller setup. Run `mga.exe` directly without `SR_DATA_DIR` or
`--data-dir` and they stay beside the executable, with saves in the working
directory's `memstick\`, as before. Metal Gear Acid exposes standard PSP
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
PSP Memory Stick's `PSP\SAVEDATA\` directory into the data folder's:

```text
memstick\PSP\SAVEDATA\
```

That is `%LOCALAPPDATA%\Metal Gear Acid Recomp\memstick\PSP\SAVEDATA\` by
default; RecompLauncher's **Saves** action opens it.

Keep the save folder and all files inside it together. Supported USA saves use
folder names beginning with `ULUS10006`; do not rename another region's save
to that prefix. For example, a folder named `ULUS10006002` must end up at
`memstick\PSP\SAVEDATA\ULUS10006002\`. It appears under **LOAD GAME**, not
necessarily **CONTINUE**.

To keep saves elsewhere, pass `--data-dir`, or set `SR_MEMSTICK` to an
alternate Memory Stick root that contains `PSP\SAVEDATA\` before starting the
launcher. Back up the original
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
