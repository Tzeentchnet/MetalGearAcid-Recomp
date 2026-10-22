# Upstream framework improvements

This document converts [FINDINGS.md](FINDINGS.md) into work for the upstream
`psp-recomp` fork. Implementation status and dependencies are tracked in
[TODO.md](TODO.md), primarily Phase 1 and Phase 3.

Status values:

- **Local** - implemented in this worktree but not yet upstreamed.
- **Fork commit** - committed and pushed to the public maintained
  `Tzeentchnet/psp-recomp` `kzl` branch, but not yet reviewed or accepted by
  the original upstream project.
- **Proposed** - design or fidelity work still required.
- **Game config** - should remain title-specific rather than generic runtime
  behavior.

## Priority matrix

| Priority | Work item | Findings | Status | Required upstream result |
|---|---|---|---|---|
| P0 | Import-map stubs outside `.sceStub.text` | MGA-F-011 | Fork commit `9683b44` | Codegen treats every parsed import address as an import stub. |
| P0 | Patch imports in the loaded static image | MGA-F-012 | Fork commits `e2dbc91`, `9683b44` | Interpreted callbacks into static modules reach HLE instead of raw no-op stubs. |
| P0 | Runtime PRX loader and module registry | MGA-F-006 through MGA-F-009 | Fork commit `e2dbc91` + synthetic tests | Load-by-path and load-by-fd, relocation, imports, exports, start, unload, and explicit failures. |
| P0 | Interpreter syscall continuation | MGA-F-013 | Fork commit `e2dbc91` + synthetic tests | Runtime PRX syscalls execute HLE and resume with the original outer return target. |
| P0 | Nested interpreter-to-native re-entry | MGA-F-034 | Fork commit `3f7d48e` + synthetic tests | An interpreted call chain hands targets in the active generated table back to native code, then resumes at the guest `$ra`. |
| P0 | Interpreted VFPU continuation | MGA-F-034 | Fork commit `3f7d48e` + synthetic tests | Fallback reuses tested VFPU compute semantics and implements COP2 plus scalar/quad memory forms. |
| P0 | Per-thread GP | MGA-F-014 | Fork commit `e2dbc91` | Module-created threads run with their module GP. |
| P0 | VFPU7 packed conversions | MGA-F-010 | Fork commits `9683b44`, `96dd536` | `vi2uc`, `vi2c`, `vi2us`, and `vi2s` codegen semantics with executable vectors. |
| P0 | Executable-relative resources | MGA-F-020 | Fork commit `e2dbc91` | VFPU tables and fonts work from any process working directory. |
| P1 | Explicit module replacement policy | MGA-F-015 | Fork commit `245031c` + synthetic tests | Per-title policy selects guest, HLE, or reject by path/name/hash; decryption remains future work. |
| P1 | Static recompilation of runtime modules | MGA-F-021, MGA-F-038, MGA-F-057 | Fork commits `3f7d48e`, `06e7010` + synthetic/protected tests | Prefixed generated modules expose immutable tables activated/deactivated by exact module identity. |
| P1 | Explicit computed function entries | MGA-F-034 | Fork commit `3f7d48e` + protected MGA validation | Codegen accepts validated title-supplied entries that static analysis cannot discover. |
| P1 | Live-code-verified overlay fallback | MGA-F-039, MGA-F-040, MGA-F-057 | Fork commits `3f7d48e`, `06e7010` + protected tests | Recheck live code on every wrapper entry; accept runtime-JAL target changes, while genuinely changed functions fall back with module-qualified identity. |
| P0 | Runtime-JAL-aware repeated verification | MGA-F-057 | Fork commit `06e7010` + codegen/protected tests | Never cache a successful live comparison across later guest patches; verify JAL opcode identity while dispatching its live target bits. |
| P0 | Interpreter-only failed native entries | MGA-F-046 | Fork commit `3f7d48e` + synthetic/protected tests | Once live-code verification fails, interpreter re-entry must not bounce through the same generated wrapper; same-address replacement overlays remain independent. |
| P1 | Continuous XAudio2 blocking-output queue | MGA-F-047 | Fork commit `3f7d48e` + protected route check | Blocking output retains real lead; device-only silence does not advance guest time, and load-gap resume prebuffers/fades instead of alternating bursts. |
| P0 | PSP scratchpad mapping | MGA-F-048 | Fork commit `3f7d48e` + synthetic/protected tests | Native and interpreted accesses share the 16 KiB `0x00010000` scratchpad and its physical aliases. |
| P0 | Bounded scheduler-aware interpreter handoff | MGA-F-049 | Fork commit `3f7d48e` + synthetic/protected tests | Long-lived hybrid loops cannot grow the host fiber stack without bound; deeper execution keeps scheduler progress and explicit semantic failures. |
| P1 | Variable import binding | MGA-F-016 | Fork commit `245031c` explicit rejection | Bind supported variable imports in the future; current load-time rejection prevents silent misuse. |
| P1 | Removable Memory Stick state | MGA-F-032 | Fork commit `3f7d48e` + synthetic tests | Initial inserted/removed device, FAT, callback, capacity, and write-protect behavior matches PPSSPP. |
| P1 | UID-fidelity model | MGA-F-004, MGA-F-025 | Fork commit `245031c`; audited through first stage | Separate current entry UID from next UID and account for PSP file-node objects. |
| P1 | Library-qualified import identity | MGA-F-031 | Fork commits `245031c`, `96dd536` | Preserve `(library, NID)` through generated imports, runtime bindings, guest exports, and diagnostics. |
| P1 | Callback-aware vblank HLE | MGA-F-018 | Fork commit `e2dbc91` | Register `sceDisplayWaitVblankStartCB` with callback-enabled waiting. |
| P1 | Module unload/base reuse | MGA-F-007, MGA-F-026 | Fork commit `e2dbc91` + synthetic tests | Unload invalidates exports, frees memory, and allows deterministic overlay reuse. |
| P1 | Interpreter budget policy | MGA-F-021 | Proposed | Per-module budgets and progress diagnostics replace one global cap. |
| P2 | Generic diagnostic switches | MGA-F-024 through MGA-F-026 | Fork commit `e2dbc91` | UID, event, module, and watchdog-RAM logs are opt-in and title-neutral. |
| P2 | Multi-buffer capture | MGA-F-023 | Proposed | Capture displayed buffer and best render/content buffer with metadata. |
| P2 | GE `0xf0-0xf9` classification | MGA-F-022 | Fork commit `245031c` | Store immediate-vertex state and explicitly report nonzero unsupported VAP draws. |
| P2 | Gate all title patches | MGA-F-019 | Fork commit `e2dbc91` | Killzone-specific data mutations require an explicit build flag. |
| P2 | Shared dual-clock pad scripts | MGA-F-027 | Fork commit `245031c` + parent profiles | Header-only scripts are neutral and v3 profiles drive PPSSPP vblanks plus native presents. |
| P2 | Capture-free presentation limit | MGA-F-030 | Fork commit `245031c` | `SR_EXIT_AFTER_PRESENT` logs the terminal present and exits cleanly without a game-derived capture. |
| P2 | Presentation/input acceptance diagnostics | MGA-F-035, MGA-F-037 | Fork commit `3f7d48e` | Exact presentation captures plus scripted/live input-edge logs remain opt-in and title-neutral. |
| P2 | Window-title FPS counter | MGA-F-042 | Fork commit `3f7d48e` + synthetic test | GDI, Vulkan, and D3D12 expose one opt-in rolling FPS/frame-time diagnostic. |
| P1 | Exact software sampler/raster fast paths | MGA-F-043 | Fork commit `3f7d48e` + protected goldens | Degenerate bilinear weights, through-mode attributes, and decoded-texel reuse avoid work without changing output. |
| P1 | D3D12 front-end performance path | MGA-F-044 | Fork commit `3f7d48e` + protected capture/route checks | A dedicated build preset and GPU readback capture support the accepted native-resolution route. |
| P1 | Structured frame/GPU/interpreter profiles | MGA-F-051, MGA-F-054 | Fork commit `40447fd` + synthetic/protected tests | Opt-in CSV/TSV diagnostics expose percentiles, fenced GPU time, and per-target interpreter cost without changing release timing or the v2 fallback log. |
| P1 | Full-resolution scaled capture | MGA-F-052 | Fork commit `40447fd` + D3D12 layout tests | Preserve the established logical capture by default and expose the actual internal render target for scale-aware analysis. |
| P1 | PSP-quantized GPU texture sampling | MGA-F-053, MGA-F-059 | Fork commit `2584d53` + shader/unit/protected tests | D3D12 and Vulkan use 8-bit bilinear weights, ordered truncation, and explicit wrap/clamp texel fetches by default, with a hardware-filter A/B override. |
| P1 | Safe D3D12 PSO persistence | MGA-F-056 | Fork commit `40447fd` safety gate; redesign proposed | Keep normal in-memory async PSOs, require explicit unsafe acknowledgement for serialized pipeline libraries, and move persistence to independently validated cached-PSO blobs. |
| P2 | Title-aware configuration UI | MGA-F-045 | Fork commit `3f7d48e` + process-level checks | First-run, explicit configuration, and native message dialogs consistently use `SR_GAME_TITLE`. |
| Config | MGA disc and boot contract | MGA-F-001 through MGA-F-005 | Game config | Keep hashes, argument, stack, UID seed, GE ID, and title outside generic defaults. |

## Recommended upstream decomposition

### 1. Generic module-manager library

Move runtime module behavior behind a dedicated interface:

```text
load image -> allocate -> relocate -> parse -> link -> register
start      -> PSP thread + module GP -> wait -> status
stop       -> optional module_stop thread
unload     -> deactivate exports -> release allocation
```

The module registry should own:

- module UID and status;
- path, module name, version, attributes, GP, base, and allocation size;
- start/stop entry points and thread parameters;
- imported functions and variables;
- named exports;
- replacement policy; and
- active generated dispatch table, if available.

The current local implementation in
`external/psp-recomp/src/rt/module.c` is sufficient for bring-up, but upstream
work should split parsing/relocation from kernel-object policy so each can be
tested independently.

### 2. Multi-module native dispatch

Interpreting KJFS, ZLIB, sound, and stage overlays proves correctness but is too
slow for a finished recompilation.

Codegen should support a module identifier or symbol prefix:

```text
sr_register_mgp_main()
sr_register_kjfs()
sr_register_zlib()
sr_register_sound()
sr_register_stage_init()
```

The runtime dispatch layer should allow:

- immutable tables per generated module;
- activation when the matching PRX loads at the expected base/hash;
- deactivation on unload;
- overlapping overlay addresses, with only one active table at a time; and
- interpreter fallback for uncompiled or unexpected modules.

Generated modules must not all export the same `sr_register_all` symbol.

The local implementation now provides prefixed symbols and descriptors,
collision-checked activation/deactivation, exact path/hash/name/base matching,
and three same-base Metal Gear Acid overlays. The remaining upstream work is
API review, broader title regression, and deciding whether live-code
verification belongs in the generic generator or a title integration layer.

### 3. Import identity

PSP linkage is formally `(library, NID)`. The local generated/runtime/guest
dispatch path now retains both values and has synthetic collision coverage.

The remaining upstream step is to namespace the built-in HLE registry itself.
The current HLE table is still keyed globally by NID for compatibility.

NID-only built-in lookup worked for the observed Metal Gear Acid modules but
should not be assumed globally safe.

### 4. Boot-state configuration

Generic standalone boot should accept a structured descriptor rather than
accumulating title macros:

```text
title
main base and entry
argument bytes
entry thread UID
next allocatable UID
priority, stack size, attributes
initial GP and GE list ID
expected ISO identity
```

The important distinction exposed by Metal Gear Acid is:

```text
existing entry thread UID != next allocatable UID
```

### 5. Resource discovery

All runtime resources should use one executable-relative resolver with optional
environment overrides. At minimum:

- VFPU tables;
- PGF fonts;
- renderer shaders;
- configuration files; and
- future replacement assets.

Build integrations should copy the exact required directories beside the
binary.

## Regression test plan

All upstream changes should use synthetic PRXs or homebrew fixtures, not game
payloads.

### Codegen tests

1. Import table points to a stub in `.text`; generated function calls
   `sr_syscall`.
2. Registration output patches every guest-image import stub.
3. Library strings are escaped safely in emitted C.
4. VFPU7 conversion vectors cover:
   - negative clamp for `vi2uc` and `vi2us`;
   - signed byte/halfword extraction;
   - odd vector sizes for halfword packing;
   - source swizzle/negate/constants; and
   - destination saturation/write masks.
5. An explicit aligned function entry inside executable ranges is emitted and
   registered; unaligned or out-of-range entries fail.
6. A symbol prefix namespaces generated functions, the descriptor, and
   registration without changing default single-module output.
7. Runtime-code verification emits an explicit module-qualified interpreter
   fallback rather than executing stale generated operands, and marks the
   failed function pointer interpreter-only before tail entry.

### PRX loader tests

1. Multiple PT_LOAD segments with BSS and an alignment gap.
2. Type-A relocation coverage for:
   - `R_MIPS_NONE`;
   - `R_MIPS_16`;
   - `R_MIPS_32`;
   - `R_MIPS_26`;
   - paired `R_MIPS_HI16`/`R_MIPS_LO16`; and
   - `R_MIPS_GPREL16`.
3. Malformed offsets, segment indexes, unterminated names, and table counts
   fail without partial registration.
4. Imports are patched to stable runtime syscall codes.
5. Named exports resolve only while their module is active.
6. Unload returns success and the allocator reuses the same base.
7. Two overlays export the same address/NID but only the active overlay wins.
8. Two native tables sharing an address cannot be active together; after
   deactivation, the replacement table resolves at that address.
9. Disabling one live-code-mismatched function pointer suppresses only that
   entry; a replacement overlay function at the same address remains native.

Current local coverage is in
`external/psp-recomp/tools/tests/module_loader_test.c`. Its synthetic PRX has
two PT_LOAD segments, explicit BSS, module start parameters, a named import and
export, and a type-A relocation section. It currently covers items 1-6 and
same-base reload. The two-simultaneously-described-overlay dispatch case in
item 7 remains future export-registry work. Dispatch-table items 8-9 are covered
by `dispatch_table_test.c`, including sequential reuse of `0x09b43c00`.

### Interpreter/HLE tests

1. `jr ra; syscall` executes the delay-slot syscall and resumes at `ra`.
2. Two nested syscalls do not replace the outer return target.
3. A guest export called through a static import returns without HLE register
   poisoning.
4. An interpreted callback into static code reaches a patched static import.
5. A nested interpreted call into an active native dispatch entry executes
   natively and resumes the original interpreted frame.
6. VFPU scalar/quad loads and stores plus a compute instruction continue
   through fallback.
7. Scratchpad accesses at `0x00010000-0x00013fff` work through fallback.
8. `vnop`, `vf2i`, `vi2f`, VFPU7 packed conversions, and VFPU condition
   branches match generated semantics.
9. Unknown runtime syscall codes fail with PC, code, and module context.

Current local coverage is in
`external/psp-recomp/tools/tests/interp_fallback_test.cpp`. It executes
synthetic guest instruction streams that cover delay-slot HLE calls, nested
guest calls, outer return-PC preservation, guest-export recursion, and a guest
callback into static code that reaches a patched import. It now also covers
nested native-table re-entry and VFPU compute/load/store continuation. An
unmapped runtime syscall code is rejected before HLE dispatch. A separate
process-level assertion for the final abort diagnostic remains useful but is
not required for the continuation semantics.

### Scheduler tests

1. Module-start thread uses the supplied GP.
2. A thread created by module code inherits that module GP.
3. Entry-thread UID and next UID can differ.
4. Callback-enabled vblank waits execute notified callbacks.

### Packaging tests

Run the executable from a working directory unrelated to the build tree and
verify that:

- VFPU tables load;
- both PGF fonts load; and
- configuration still writes beside the executable.

## Changes that should remain game-specific

Do not upstream these as generic defaults:

- ULUS-10006 hashes and file paths;
- `0x08804000` / `0x0880432c`;
- the EBOOT path argument;
- Metal Gear Acid's computed callback entry `0x08919f10`;
- Metal Gear Acid's raw-LBN overlay paths, hashes, load bases, and 56-target
  front-end allowlist;
- module base expectations;
- frame-count smoke-test content; or
- a blanket rule that every `sce*` module is HLE-replaced.

The framework should expose mechanisms for these choices; the root project
should provide the values.
