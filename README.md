# Metal Gear Acid Recomp

Source-only Windows static recompilation of **Metal Gear Acid
(ULUS-10006 v1.00)**. The project uses the PSP static recompiler/runtime fork
developed for the Killzone: Liberation recompilation.

No game executable, generated game C, disc data, or other copyrighted game
assets belong in this repository. You must supply your own supported USA disc.

## Repository

Private development repository:

```text
https://github.com/Tzeentchnet/MetalGearAcid-Recomp
```

Clone with the tested public runtime fork:

```powershell
git clone --recurse-submodules `
  https://github.com/Tzeentchnet/MetalGearAcid-Recomp.git
```

The parent currently pins `Tzeentchnet/psp-recomp` branch `kzl` at commit
`40447fd`.

## Documentation

- [Documentation index](docs/README.md)
- [Project status and repository history](docs/STATUS.md)
- [Project completion plan](docs/PLAN.md)
- [Live project TODO](docs/TODO.md)
- [Evidence-backed findings](docs/FINDINGS.md)
- [Upstream framework improvements](docs/UPSTREAM.md)
- [Reproduction and acceptance checks](docs/REPRODUCTION.md)

## Requirements

- Windows 10/11 x64
- Git with submodule support
- Python 3.11 or newer
- CMake 3.25 or newer and Ninja
- Visual Studio 2022 Build Tools with clang-cl, MSVC libraries, and a Windows
  SDK
- SDL3 only when enabling the optional D3D12 renderer

## Set up

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

Run it against the same verified disc:

```powershell
$env:PSP_ISO = "C:\path\to\Metal Gear Acid (USA).iso"
$env:SR_FPS_COUNTER = "1"
out\build\clang-cl\mga.exe --boot `
  build\mga\gen\mga_image.bin 08804000 0880432c none --gui
```

For a local Windows checkout, double-click `Launch Metal Gear Acid.bat`.
The launcher prefers the D3D12 build, falls back to the software build, opens
the Metal Gear Acid graphics and controller settings, and then starts the
game. It uses `Metal Gear Acid (USA)\Metal Gear Acid (USA).iso` by default;
set `PSP_ISO` first to use a supported disc image at another location.

The first GUI run creates portable `graphics.ini` and `input.ini` beside the
executable and opens controller setup. Metal Gear Acid exposes standard PSP
button bindings without the Killzone-specific twin-stick controls. The runtime
uses its conservative one-million-instruction fallback cap; override it only
for diagnostics with `SR_INTERP_MAX_STEPS`.

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
