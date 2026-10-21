# Reproduction and acceptance checks

Milestone gates are defined in [PLAN.md](PLAN.md), and the live validation work
is tracked in [TODO.md](TODO.md).

All generated game data remains under ignored `build/` and `out/` directories.

Clone the private parent with its public runtime fork:

```powershell
git clone --recurse-submodules `
  https://github.com/Tzeentchnet/MetalGearAcid-Recomp.git
Set-Location MetalGearAcid-Recomp
```

GitHub authentication is required for the private parent.

The parent currently pins tested fork tip `7980eb7`. The relevant sequence is:

- `51aa462` - runtime PRX modules and synthetic runtime tests;
- `1225147` - runtime import patches and initial VFPU7 codegen;
- `abad642` - UID/file fidelity, module policy, library dispatch, pad neutrality,
  variable-import rejection, and GE immediate state; and
- `7980eb7` - library-qualified generated imports and executable VFPU7 vectors.

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

The parent-compiled policy in `tools/mga/module_policy.c` pins boot service
modules by guest path, SHA-1, expected module name, and guest/HLE mode. A hash
or name mismatch fails module load. Unlisted plaintext stage overlays remain
guest-executed; unlisted encrypted modules are rejected.

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

The corresponding native smoke log must begin with:

```text
standalone module_start: uid=0x113
create thread uid=0x114 user_main
create thread uid=0x115 Main
```

With `SR_UIDLOG=1`, the first module sequence must also include:

```text
module loader: KCEJ_FS uid=0x119
module loader: ZLIB uid=0x11f
module loader: KCEJ_SOUND uid=0x12e
module loader: mgp_stage uid=0x174
```

The raw-sector KFS open consumes file-node UID `0x171`, so the following
`KFS_Arc` FPL is `0x172`.

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

## 6. Deterministic input profiles

Validate the committed shared profiles:

```powershell
python tools\mga\padscript.py `
  config\mga_neutral.pad `
  config\mga_boot.pad `
  config\mga_menu_probe.pad

python -m unittest discover -s tools\tests -p "test_*.py"
```

Select the same profile for PPSSPP and native:

```powershell
$env:PSPRECOMP_PADSCRIPT = "$PWD\config\mga_neutral.pad"
$env:SR_PADSCRIPT = "$PWD\config\mga_neutral.pad"
```

Profiles:

| File | Purpose |
|---|---|
| `mga_neutral.pad` | Strict no-input baseline |
| `mga_boot.pad` | Periodic START pulses for boot/logo/title advancement |
| `mga_menu_probe.pad` | Boot pulses plus deterministic START/DOWN/UP/CROSS probes |

The PPSSPP and native columns intentionally differ. PPSSPP reads vblank
timing; native reads presentation timing. Header-only neutral scripts suppress
native automatic input rather than falling through to the legacy periodic
START pulse.

## 7. Isolated memstick fixtures

Create fresh empty roots:

```powershell
python tools\mga\memstick.py create `
  build\mga\fixtures\empty-ppsspp --backend ppsspp

python tools\mga\memstick.py create `
  build\mga\fixtures\empty-native --backend native
```

Clone protected existing-save templates without modifying the originals:

```powershell
python tools\mga\memstick.py create `
  build\mga\fixtures\save-ppsspp `
  --backend ppsspp `
  --template D:\protected\mga-ppsspp-template

python tools\mga\memstick.py create `
  build\mga\fixtures\save-native `
  --backend native `
  --template D:\protected\mga-native-template
```

Verify before each run:

```powershell
python tools\mga\memstick.py verify `
  build\mga\fixtures\empty-ppsspp --backend ppsspp

python tools\mga\memstick.py verify `
  build\mga\fixtures\empty-native --backend native
```

Select the roots:

```powershell
$env:PSPRECOMP_MEMSTICK = "$PWD\build\mga\fixtures\empty-ppsspp"
$env:SR_FSDIR = "$PWD\build\mga\fixtures\empty-native"
```

The tool refuses to overwrite an existing output path. Every run therefore
uses an isolated clone. `.mga-fixture.json` detects accidental fixture
mutation, but it and all save files remain protected/local.

Current parent-tool test result:

```text
Ran 10 tests
OK
```

## 8. Static trace comparison

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

## 9. PPSSPP front-end reference summary

After a protected interpreter run with full logging and call tracing:

```powershell
python tools\mga\ppsspp_summary.py `
  build\mga\reference\ppsspp.log `
  --calls build\mga\reference\calls.txt `
  --timeout 20 `
  --padscript config\mga_boot.pad `
  --out docs\reference\ppsspp_frontend.json
```

The committed reduced report must identify:

```text
init:  uid 0x174, vblank 84, present 42
title: uid 0x17c, vblank 167, present 167
call edges: 2333
call targets: 1119
```

See [PPSSPP_REFERENCE.md](PPSSPP_REFERENCE.md). Never commit the source log,
call trace, memstick, or captures.

## 10. Capture-free native title gate

```powershell
$env:PSP_ISO = "C:\path\to\Metal Gear Acid (USA).iso"
$env:SR_FSDIR = "$PWD\build\mga\fixtures\empty-native"
$env:SR_PADSCRIPT = "$PWD\config\mga_boot.pad"
$env:SR_EXIT_AFTER_PRESENT = "600"
$env:SR_INTERP_MISS_LOG = "$PWD\build\mga\native-title\dispatch-misses.txt"

out\build\clang-cl\mga.exe --boot `
  build\mga\gen\mga_image.bin 08804000 0880432c none --gui
```

Acceptance:

```text
exit code 0
init  uid 0x174, allocation 0xf500
title uid 0x17b, allocation 0x1c100
presentation limit reached at present 600
0 unimplemented HLE
0 host crashes
0 watchdogs
0 interpreter stops
48 unique fallback targets
```

The title log must not contain `unhandled command 0xf0` through `0xf9`.
Nonzero `VAP` immediate drawing remains explicitly unsupported and must surface
as a GE diagnostic if a later route uses it.

Reduce the protected log with `tools\mga\native_summary.py` as documented in
[PPSSPP_REFERENCE.md](PPSSPP_REFERENCE.md).

## 11. Framework tests

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

### Executable VFPU/codegen vectors

```powershell
python external\psp-recomp\tools\tests\test_codegen_ext.py `
  --cc=D:\Tools\msys64\ucrt64\bin\gcc.exe
```

Current result:

```text
207/207 passed
```

The VFPU7 cases execute emitted C and verify source-prefix behavior, unsigned
negative clamp, byte/halfword packing, odd vector sizes, destination
saturation, and destination write masks.

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
reuse. A separate malformed fixture verifies that imported variables fail with
full cleanup instead of being ignored.

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

The module-loader fixture also verifies that a guest export resolves only for
its exact library and that a runtime syscall binding returns both the library
and NID. Regenerated game C should contain library-qualified calls, for
example:

```text
sr_syscall_lib(s, "kjfs", 0x93e9297f)
```

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
