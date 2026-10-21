# Metal Gear Acid Recomp

Experimental source-only Windows static recompilation of **Metal Gear Acid
(ULUS-10006 v1.00)**. The project uses the PSP static recompiler/runtime fork
developed for the Killzone: Liberation recompilation.

No game executable, generated game C, disc data, or other copyrighted game
assets belong in this repository. You must supply your own supported USA disc.

## Documentation

- [Documentation index](docs/README.md)
- [Project completion plan](docs/PLAN.md)
- [Live project TODO](docs/TODO.md)
- [Evidence-backed findings](docs/FINDINGS.md)
- [Upstream framework improvements](docs/UPSTREAM.md)
- [Reproduction and acceptance checks](docs/REPRODUCTION.md)

## Current status

- The supported ISO is pinned by size and SHA-1.
- The plaintext `mgp_main` PRX is extracted reproducibly.
- The main module relocates at `0x08804000`, enters at `0x0880432c`, and
  contains 9,913 discovered functions.
- PPSSPP oracle capture confirms the initial argument, 256 KiB start-thread
  stack, next UID, and initial GE list ID.
- Plaintext runtime PRXs are loaded, relocated, linked to HLE, and executed
  through interpreter fallback. This covers `kjfs`, `zlibdec`, `sound`, and
  stage overlays; Sony media modules use the fork's native HLE replacements.
- Native software rendering, XAudio2, VFPU tables, fonts, and hybrid callbacks
  are active. Automated captures reach the KONAMI logo.
- Gameplay is not yet validated. Runtime modules are still interpreted, so
  compiling hot modules/overlays and completing full boot/gameplay validation
  are the next milestones.

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

Run it against the same verified disc:

```powershell
$env:PSP_ISO = "C:\path\to\Metal Gear Acid (USA).iso"
out\build\clang-cl\mga.exe --boot `
  build\mga\gen\mga_image.bin 08804000 0880432c none --gui
```

The first GUI run creates portable `graphics.ini` and `input.ini` beside the
executable and opens controller setup. Current interpreted modules use a
100-million-instruction per-call safety cap; override it for diagnostics with
`SR_INTERP_MAX_STEPS`.

## License

The recompiler/runtime is derived in part from PPSSPP and is
GPL-2.0-or-later. See [LICENSE](LICENSE), [CREDITS.md](CREDITS.md), and the
runtime fork's license notices for full third-party provenance.
