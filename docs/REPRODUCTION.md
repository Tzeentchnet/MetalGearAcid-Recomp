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

The parent currently pins tested fork tip `2bf37a0`. The relevant sequence is:

- `51aa462` - runtime PRX modules and synthetic runtime tests;
- `1225147` - runtime import patches and initial VFPU7 codegen;
- `abad642` - UID/file fidelity, module policy, library dispatch, pad neutrality,
  variable-import rejection, and GE immediate state; and
- `7980eb7` - library-qualified generated imports and executable VFPU7 vectors;
- `2bf37a0` - native overlay dispatch, live-code fallback, scratchpad memory,
  scheduler-aware interpreter continuation, renderer/FPS diagnostics,
  memory-stick state, and continuous XAudio2 buffering.

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
main:           9914/9914 functions, 0 trapping stubs
KJFS:             527/527 functions, 0 trapping stubs
ZLIB:             121/121 functions, 0 trapping stubs
KCEJ_SOUND:       904/904 functions, 0 trapping stubs
stage/init:       636/636 functions, 0 trapping stubs
stage/title:      997/997 functions, 0 trapping stubs
stage/prologue: 1091/1091 functions, 0 trapping stubs
stage/st00:      1000/1000 functions, 0 trapping stubs
46628 relocations
117 imports across 19 libraries
```

The analyzer discovers 9,913 conventional entries. The title config supplies
the verified computed callback entry `0x08919f10`, bringing generated native
dispatch to 9,914 entries.

Generated files include:

- `build/mga/gen/mga_image.bin`;
- `build/mga/gen/mga_imports.toml`;
- `build/mga/gen/mga_functions.toml`;
- split `mga_recomp_*.c` translation units; and
- `mga_recomp_register.c`, including guest-image import patches; and
- prefixed generated modules under `build/mga/modules/<id>/`.

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

Build the recommended D3D12 performance path separately so the software
reference remains available:

```powershell
cmake --preset clang-cl-d3d12 `
  -DSDL3_DIR="C:\path\to\SDL3\cmake"
cmake --build --preset clang-cl-d3d12 `
  --target mga_driver --parallel
```

Select it with:

```powershell
$env:SR_GPU = "d3d12"
$env:SR_D3D12_SCALE = "1"
$env:SR_FPS_COUNTER = "1"
```

For unattended runs from a fresh output directory, set
`SR_GRAPHICS_CONFIG=0` and `SR_INPUT_CONFIG=0` to suppress first-run dialogs.

Configuration captions can be checked directly:

```powershell
out\build\clang-cl\mga.exe --configure
out\build\clang-cl\mga.exe --configure-input
```

Expected titles are `Metal Gear Acid Graphics` and
`Metal Gear Acid Controller`; no Metal Gear Acid dialog should refer to
Killzone.

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
| `mga_menu_probe.pad` | Boot pulses plus deterministic START/DOWN/UP/CIRCLE probes |

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
$env:SR_MEMSTICK = "$PWD\build\mga\fixtures\empty-native\ms0"
$env:SR_MEMSTICK_STATE = "inserted"
```

The tool refuses to overwrite an existing output path. Every run therefore
uses an isolated clone. `.mga-fixture.json` detects accidental fixture
mutation, but it and all save files remain protected/local.

Exercise a physically removed card without changing the host fixture:

```powershell
$env:SR_MEMSTICK_STATE = "removed"
```

This must remain on the memory-stick check and make no save-slot `Getstat`
calls. Restore `inserted` for empty and existing-save cases. Existing-save
validation uses a protected, PSP/PPSSPP-compatible `ULUS10006001` template;
after the run, `memstick.py verify` must still pass.

For a post-tutorial route, GameFAQs save #8725 is North American
`ULUS10006002` after Forest. Its verified ZIP SHA-256 is:

```text
fab05c1a904144dea3395734b2db00a27b6d8ae91ac3bf405fb357ce728c1de2
```

Keep the folder name unchanged. It appears under LOAD GAME, not initial
CONTINUE. Clone the protected template with `memstick.py create`; never run
against the downloaded source directory.

Current parent-tool test result:

```text
Ran 21 tests
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
$env:SR_MEMSTICK = "$env:SR_FSDIR\ms0"
$env:SR_MEMSTICK_STATE = "inserted"
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
0 permissive fallbacks
82 module-qualified overlay fallback targets
```

The log must mark KJFS, ZLIB, KCEJ_SOUND, init, and title as `(native)`.

The title log must not contain `unhandled command 0xf0` through `0xf9`.
Nonzero `VAP` immediate drawing remains explicitly unsupported and must surface
as a GE diagnostic if a later route uses it.

Reduce the protected log with `tools\mga\native_summary.py` as documented in
[PPSSPP_REFERENCE.md](PPSSPP_REFERENCE.md).

## 11. Deterministic title-menu acceptance

Create a fresh output directory, then run the presentation-timed menu route.
The first 3,300 presentations are fast-forwarded; the final 900 run in real
time so XAudio2 behavior is measured:

```powershell
$run = (New-Item -ItemType Directory -Force `
  build\mga\frontend-acceptance-1).FullName
$exe = (Resolve-Path out\build\clang-cl\mga.exe).Path
$image = (Resolve-Path build\mga\gen\mga_image.bin).Path

$env:PSP_ISO = "C:\path\to\Metal Gear Acid (USA).iso"
$env:SR_FSDIR = "$PWD\build\mga\fixtures\empty-native"
$env:SR_MEMSTICK = "$env:SR_FSDIR\ms0"
$env:SR_MEMSTICK_STATE = "inserted"
$env:SR_PADSCRIPT = "$PWD\config\mga_menu_probe.pad"
$env:SR_FAST_FORWARD_PRESENT = "3300"
$env:SR_EXIT_AFTER_PRESENT = "4200"
$env:SR_FBCAPTURE_PRESENTS = "3000,3120,3240,3360"
$env:SR_PADLOG = "1"
$env:SR_AUDIO_LOG = "1"
$env:SR_INTERP_MISS_LOG = "$run\dispatch-misses.txt"

Push-Location $run
& $exe --boot $image 08804000 0880432c none --gui `
  1> stdout.log 2> stderr.log
$runExit = $LASTEXITCODE
Pop-Location
if ($runExit -ne 0) { exit $runExit }

python tools\mga\frontend_acceptance.py `
  "$run\stderr.log" `
  --misses "$run\dispatch-misses.txt" `
  --frames-dir $run `
  --present-limit 4200 `
  --allowlist config\mga_frontend_fallbacks.toml `
  --out "$run\summary.json"
```

The checker requires:

- init `0xf500`, title `0x1c100`, and new-game intro `0x1c600`;
- START, DOWN, UP, and CIRCLE in that order;
- NEW GAME selected at present 3000;
- LOAD GAME selected at present 3120;
- NEW GAME reselected at present 3240;
- title fade after CIRCLE at present 3360;
- exactly the 266 reviewed module-qualified targets in
  `config/mga_frontend_fallbacks.toml`;
- zero unimplemented HLEs, host crashes, watchdogs, interpreter stops, and
  permissive fallbacks;
- XAudio2 at 44.1 kHz stereo, at least one second played, a nonempty device
  queue, zero dropped frames, and zero device underruns.

Run the command three times with fresh `frontend-acceptance-1`, `-2`, and `-3`
directories. The accepted 2026-10-21 runs produced one SHA-256 per checkpoint
across all three runs:

| Present | SHA-256 |
|---:|---|
| `3000` | `d811daee9c251c848ddd43db2ea8bad0e8d5b5ef4b3f13ba7cee64141b5b98ac` |
| `3120` | `46e83a04453079dff90e23554390a50486bd2db03ce5582761379d445de33627` |
| `3240` | `90eb414f7b9e5dc4fcd92acc385b4cf12e1fc073d16ca41fcc12d72c6ec831fe` |
| `3360` | `c4019d29431524e236da888bc7ac749410292d817a162b1f7dacd226ec6204ff` |

The final route classifies those targets as 36 init, 77 title, and 153
prologue. The reduced report is
[reference/native_frontend_menu.json](reference/native_frontend_menu.json).
Never commit the source logs, save fixture, or captures.

The post-fix D3D12 real-time gate shuts down with a 6-8-block device queue,
zero dropped frames, zero underruns, one preservation-silence transition,
seven padding blocks, and 3,072 resynced frames. For a longer
stack/transition regression, set both
`SR_FAST_FORWARD_PRESENT` and `SR_EXIT_AFTER_PRESENT` to `50000`; the accepted
run reached the limit in 108.8s without a host crash or interpreter stop.

### First post-prologue st00 probe

Use `config\mga_st00_probe.pad` with:

```powershell
$env:SR_PADSCRIPT = "$PWD\config\mga_st00_probe.pad"
$env:SR_FAST_FORWARD_PRESENT = "30000"
$env:SR_EXIT_AFTER_PRESENT = "30000"
$env:SR_PADLOG = "1"
$env:SR_MODULE_LOG = "1"
```

The accepted D3D12 run loads init `0xf500`, title `0x1c100`, prologue
`0x1c600`, and st00 `0x19200`. It logs the native-handoff depth cap once and
reaches present 30,000 in 152.8s without a crash, memory fault, unimplemented
instruction, interpreter stop, or permissive fallback.

The deterministic PPSSPP title oracle and a native 20,000-presentation
new-game opening run both make zero MPEG calls. There is no front-end intro
PMF on this route; card/campaign PMFs remain Phase 5/6 validation.

### Native-module benchmark

For an all-interpreted control on the same binary:

```powershell
$env:SR_DISABLE_NATIVE_MODULES = "*"
$env:SR_INTERP_MAX_STEPS = "100000000"
```

For the native/hybrid route, remove both variables. Run the present-600 gate
and record wall/CPU time, then run the menu route with:

```powershell
$env:SR_PERF_LOG = "1"
$env:SR_PERF_START = "3300"
$env:SR_PERF_WINDOW = "120"
```

Measured 2026-10-21 results:

| Metric | All interpreted | Native/hybrid |
|---|---:|---:|
| Present-600 wall | `20,281 ms` | `11,222 ms` |
| Present-600 host CPU | `19,156.25 ms` | `10,531.25 ms` |
| Seven-window mean FPS | `34.54` | `39.22` |
| Mean p95 frame | `156.19 ms` | `153.09 ms` |
| Worst frame | `2,187.80 ms` | `271.16 ms` |

After pixel-exact software-rasterizer optimization and D3D12 enablement:

| Metric | Pre-optimization software | Optimized software | D3D12 1x |
|---|---:|---:|---:|
| Accepted-route wall | `108.6 s` | `83.0 s` | `14.1 s` |
| Mean host presentation FPS | `39.22` | `46.35` | `162.55` |
| Mean frame time | `25.73 ms` | `21.73 ms` | `6.37 ms` |
| Mean p95 frame | `153.09 ms` | `127.54 ms` | `21.41 ms` |

The optimized software captures retain the four exact hashes above. D3D12
captures pass the functional frame metrics but are not pixel-identical. Compare
them with:

```powershell
python external\psp-recomp\tools\ppmdiff.py `
  build\mga\software-captures `
  build\mga\d3d12-captures `
  --threshold 8 `
  --max-threshold-pixels 200000 `
  --max-channel-delta 255 `
  --json build\mga\d3d12-captures\diff.json
```

The measured title checkpoints have maximum channel delta 18-25 and about
13.6% of pixels above delta 8. The fade checkpoint has maximum delta 9 and
0.61% above delta 8.

## 12. Framework tests

### Python tests

```powershell
python -m unittest discover `
  -s external\psp-recomp\tools\tests `
  -p "test_*.py"
```

Current result:

```text
Ran 27 tests
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

### Immutable dispatch tables

```powershell
cmake --build --preset clang-cl --target mga_dispatch_table_tests
ctest --test-dir out\build\clang-cl `
  -R "^mga_dispatch_table$" --output-on-failure
```

The test covers sorted lookup, large tables, concurrent non-overlapping
tables, collision rejection, idempotent activation, deactivation, and
sequential reuse of `0x09b43c00` by two overlays.

### Window FPS counter

```powershell
cmake --build --preset clang-cl --target mga_fps_counter_tests
ctest --test-dir out\build\clang-cl `
  -R "^mga_fps_counter$" --output-on-failure
```

The test verifies rolling FPS/frame-time output and timer-reset behavior.

### Memory-stick state and input mappings

```powershell
cmake --build --preset clang-cl --target `
  mga_memstick_state_tests mga_input_config_tests
ctest --test-dir out\build\clang-cl `
  -R "^mga_(memstick_state|input_config)$" --output-on-failure
```

These public tests cover inserted/removed state values and strict parsing, plus
default/custom keyboard, mouse, and gamepad button mappings, analog response,
and twin-stick behavior.

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
- nested re-entry from interpreted code into an active native dispatch entry;
- VFPU scalar/quad memory forms and VFPU compute continuation; and
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
6/6 tests passed
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
| `SR_MEMSTICK_STATE=inserted|removed` | Select initial Memory Stick presence |
| `SR_PADLOG=1` | Scripted pad edges with present/vblank clocks |
| `SR_INPUT_LOG=1` | Live logical input edges and gamepad presence |
| `SR_FBSNAP_PRESENT=N` | Rotating snapshots every N presentations |
| `SR_FBCAPTURE_PRESENTS=a,b,...` | Exact presentation snapshots for acceptance |
| `SR_FPS_COUNTER=1` | Rolling FPS and average frame time in the window title |
| `SR_DISABLE_NATIVE_MODULES=*|name,...` | Keep selected generated modules interpreted for differential checks |
| `SR_TRACE_RAM=path` | Write protected RAM when a bounded trace completes |
| `SR_WATCHDOG_RAM=1` | Local RAM dump on the first no-frame watchdog |
| `SR_INTERP_MAX_STEPS=N` | Override interpreter call budget |
| `PSP_VFPU_TABLES=path` | Override VFPU table directory |
| `SR_FONTDIR=path` | Override PGF font directory |

RAM, framebuffer, eDRAM, and trace outputs are game-derived. Never commit
them.
