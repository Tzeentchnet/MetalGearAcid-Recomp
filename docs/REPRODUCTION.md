# Reproduction and acceptance checks

Milestone gates are defined in [PLAN.md](PLAN.md), and the live validation work
is tracked in [TODO.md](TODO.md).

All generated game data remains under ignored `build/` and `out/` directories.

The parent currently pins the tested fork tip `1225147`, which contains runtime
module/test commit `51aa462` followed by codegen/import/VFPU7 commit `1225147`.

## 1. Extract the verified disc

```powershell
python tools\mga\extract.py `
  "C:\path\to\Metal Gear Acid (USA).iso"
```

Expected summary:

```text
ISO SHA-1 ok (d29eaba896be28c2575ead246bdaa3a9712929d4)
71 additional plaintext PRXs
8 encrypted PRXs skipped
```

## 2. Generate the main module

```powershell
python tools\mga\gen.py
```

Expected codegen result:

```text
9913/9913 functions
0 trapping stubs
46628 relocations
117 imports across 19 libraries
```

Generated files include:

- `build/mga/gen/mga_image.bin`;
- `build/mga/gen/mga_imports.toml`;
- `build/mga/gen/mga_functions.toml`;
- split `mga_recomp_*.c` translation units; and
- `mga_recomp_register.c`, including guest-image import patches.

## 3. Build

From a Visual Studio x64 developer shell:

```powershell
cmake --preset clang-cl -DMGA_ENABLE_INSTRUCTION_TRACE=OFF
cmake --build --preset clang-cl --target mga_driver --parallel
```

Expected output:

```text
out/build/clang-cl/mga.exe
out/build/clang-cl/assets/vfpu/
out/build/clang-cl/font/
```

## 4. Capture the PPSSPP entry contract

Use the patched PPSSPP v1.20.4 interpreter:

```powershell
$env:PSPRECOMP_MEMSTICK = "$PWD\build\mga\ppsspp\memstick"
$env:PSPRECOMP_TRACE = "$PWD\build\mga\ppsspp\entry.trace"
$env:PSPRECOMP_TRACE_START = "0880432c"
$env:PSPRECOMP_TRACE_STEPS = "1"
$env:PSPRECOMP_TRACE_TARGET = "mga-entry"

& "C:\path\to\PPSSPPHeadless.exe" `
  "C:\path\to\Metal Gear Acid (USA).iso" `
  -i --graphics=software --timeout=8
```

Check the values in MGA-F-004 of [FINDINGS.md](FINDINGS.md).

## 5. Native rendering smoke tests

The `SR_FBDUMP` diagnostic captures and exits after the requested presented
frame. Captures are game-derived and must remain local.

### Memory-stick screen

```powershell
$env:PSP_ISO = "C:\path\to\Metal Gear Acid (USA).iso"
$env:SR_FBDUMP = "60"

out\build\clang-cl\mga.exe --boot `
  build\mga\gen\mga_image.bin 08804000 0880432c none --gui
```

Acceptance:

- exit code `0`;
- log contains `presented frame 60`;
- GE pixels are nonzero;
- local capture reads `Checking Memory Stick Duo`.

Measured reference:

```text
ge_pixels=3584196
tex_samples=1880400
tex_nonzero=186680
```

### KONAMI logo

```powershell
$env:SR_FBDUMP = "300"

out\build\clang-cl\mga.exe --boot `
  build\mga\gen\mga_image.bin 08804000 0880432c none --gui
```

Acceptance:

- exit code `0`;
- log contains `presented frame 300`;
- a content-buffer capture contains the KONAMI logo;
- a second stage overlay loads at `0x09b43c00`.

Measured reference:

```text
ge_pixels=62871776
tex_samples=209395936
tex_nonzero=76569425
```

The displayed buffer can be black during this transition; inspect the content
buffer rather than treating that as a renderer failure.

## 6. Static trace comparison

For a focused main-code comparison, build with:

```powershell
cmake --preset clang-cl -DMGA_ENABLE_INSTRUCTION_TRACE=ON
cmake --build --preset clang-cl --target mga_driver --parallel
```

Capture PPSSPP and native traces starting at `0x088052a4`, then compare:

```powershell
python external\psp-recomp\tools\tracediff.py `
  --ignore-pc-range=08000000-08800000 `
  --ignore-syscall-writes `
  build\mga\trace\ppsspp.trace `
  build\mga\trace\native.trace
```

A 400-step bring-up comparison matched after filtering PPSSPP's kernel
trampoline and syscall-register writes.

Reconfigure with `MGA_ENABLE_INSTRUCTION_TRACE=OFF` for the release build.

## 7. Framework tests

### Python tests

```powershell
python -m unittest discover `
  -s external\psp-recomp\tools\tests `
  -p "test_*.py"
```

Current result:

```text
Ran 23 tests
OK
```

### Synthetic runtime PRX loader

Build and run through CMake/CTest:

```powershell
cmake --build --preset clang-cl --target mga_module_loader_tests
ctest --test-dir out\build\clang-cl `
  -R "^mga_module_loader$" --output-on-failure
```

Expected result:

```text
1/1 Test #1: mga_module_loader ... Passed
100% tests passed
```

The fork also exposes a standalone MSYS2/MinGW target:

```powershell
make -C external\psp-recomp test-module-loader
```

The fixture contains no game data. It validates two PT_LOAD segments, BSS,
every supported type-A relocation, malformed cleanup, import patching, guest
exports, module-start parameters, HLE-only modules, unload, and allocation-base
reuse.

### Interpreter syscall and hybrid callback paths

```powershell
cmake --build --preset clang-cl --target mga_interp_tests
ctest --test-dir out\build\clang-cl `
  -R "^mga_interpreter_fallback$" --output-on-failure
```

The synthetic instruction streams validate:

- `jr ra; syscall` delay-slot behavior;
- HLE execution followed by continued interpretation;
- nested guest calls without replacing the original outer return PC;
- guest-export recursion through `sr_syscall`;
- an interpreted callback into static guest code and its patched HLE import;
  and
- rejection of an unknown runtime syscall code.

Run both standalone native runtime tests in the fork with:

```powershell
make -C external\psp-recomp test-runtime
```

Current combined CTest result:

```text
2/2 tests passed
```

## Useful diagnostics

| Variable | Purpose |
|---|---|
| `SR_MODULE_LOG=1` | Imports, exports, allocations, and module identities |
| `SR_SYSLOG=1` | First HLE/guest-export call per thread |
| `SR_THLOG=1` | Thread creation, start, wait, and deletion |
| `SR_UIDLOG=1` | Kernel UID and modeled object type |
| `SR_SEMALOG=1` | Semaphore operations |
| `SR_EVENTLOG=1` | Event-flag operations |
| `SR_GELOG=1` | GE list, signal, finish, and interrupt flow |
| `SR_WATCHDOG_RAM=1` | Local RAM dump on the first no-frame watchdog |
| `SR_INTERP_MAX_STEPS=N` | Override interpreter call budget |
| `PSP_VFPU_TABLES=path` | Override VFPU table directory |
| `SR_FONTDIR=path` | Override PGF font directory |

RAM, framebuffer, eDRAM, and trace outputs are game-derived. Never commit
them.
