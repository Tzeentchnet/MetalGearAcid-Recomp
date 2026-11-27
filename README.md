# Metal Gear Acid Recomp

<a href="https://recomplauncher.com"><picture><source media="(prefers-color-scheme: dark)" srcset="https://recomplauncher.com/assets/press/launcher/badge-light.svg"><img alt="Get it on RecompLauncher" src="https://recomplauncher.com/assets/press/launcher/badge-dark.svg" height="48"></picture></a>

Source-only Windows static recompilation of **Metal Gear Acid
(ULUS-10006 v1.00)**. The project uses the PSP static recompiler/runtime fork
developed for the Killzone: Liberation recompilation.

No game executable, generated game C, disc data, or other copyrighted game
assets belong in this repository. You must supply your own supported USA disc.

## Development status

This project is under active development. The deterministic front end and
selected gameplay routes work, but the full campaign, save creation and
reload, movies, renderer parity, and long-run stability are not yet validated.
Treat current builds as experimental. See the [project status](docs/STATUS.md)
and [completion plan](docs/PLAN.md) for the current scope and release gates.

## Repository

[Tzeentchnet/MetalGearAcid-Recomp](https://github.com/Tzeentchnet/MetalGearAcid-Recomp)

Clone with the tested public runtime fork:

```powershell
git clone --recurse-submodules `
  https://github.com/Tzeentchnet/MetalGearAcid-Recomp.git
```

The parent tracks the maintained `Tzeentchnet/psp-recomp` `main` branch and
pins commit `66c18a5`. The legacy `kzl` branch remains available for
compatibility.

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
- Vulkan SDK when enabling the optional Vulkan renderer

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

`--install-build-tools` installs missing Build Tools without asking, and
`--sdl3-dir "C:\path\to\SDL3\cmake"` uses an SDL3 package you already have.
Use `--renderer vulkan` after installing the Vulkan SDK. The installer reports
missing Git, CMake, Ninja, Visual Studio, Clang, or Windows SDK components
with an actionable error. It also works from a source archive by cloning the
exact runtime commit recorded in `config\mga.toml`.

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

From a Visual Studio x64 developer shell, build the software-renderer
baseline:

```powershell
cmake --preset clang-cl
cmake --build --preset clang-cl --target mga_driver
```

The build copies required VFPU tables and fonts beside the executable.

For the recommended high-performance renderer, install an SDL3 development
package and build the dedicated preset:

```powershell
cmake --preset clang-cl-d3d12 `
  -DSDL3_DIR="C:\path\to\SDL3\cmake"
cmake --build --preset clang-cl-d3d12 --target mga_driver
```

Run `out\build\clang-cl-d3d12\mga.exe` with `SR_GPU=d3d12`. Keep the
`clang-cl` software build for pixel-exact reference captures.

For the Vulkan GE renderer, install the Vulkan SDK and configure its dedicated
preset with the same SDL3 package:

```powershell
cmake --preset clang-cl-vulkan `
  -DSDL3_DIR="C:\path\to\SDL3\cmake"
cmake --build --preset clang-cl-vulkan --target mga_driver
```

Run `out\build\clang-cl-vulkan\mga.exe` with `SR_GPU=vk`. To use the Vulkan
window/presenter with the pixel-exact software GE instead, set `SR_GPU=sw` in
that build. The Vulkan build requires a working Vulkan 1.1-capable driver.

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

The baseline build uses the Win32 GDI presenter. Select it explicitly with
`SR_GPU=sw` and `SR_VIDEO=gdi`.

For a local Windows checkout, double-click `Launch Metal Gear Acid.bat`.
When multiple builds are available, the launcher prompts for D3D12
(recommended), Vulkan, or the software/GDI reference renderer. If only one
renderer build exists, it is selected automatically. Set
`MGA_RENDERER=d3d12`, `MGA_RENDERER=vulkan`, or
`MGA_RENDERER=software` before launching to skip the prompt.

The launcher opens the Metal Gear Acid graphics and controller settings, then
starts the selected executable with the matching renderer override. It first
uses `--game`, then `PSP_ISO` when set, then the ISO path saved by the
installer, and finally `Metal Gear Acid (USA)\Metal Gear Acid (USA).iso`.

The first GUI run creates `graphics.ini` and `input.ini` in the data folder
(see [Settings, saves and logs](#settings-saves-and-logs)) and opens
controller setup. Run `mga.exe` directly without `SR_DATA_DIR` or
`--data-dir` and they stay beside the executable, with saves in the working
directory's `memstick\`, as before. Metal Gear Acid exposes standard PSP
button bindings without the Killzone-specific twin-stick controls. The runtime
uses its conservative one-million-instruction fallback cap; override it only
for diagnostics with `SR_INTERP_MAX_STEPS`.

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
