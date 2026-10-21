# Upstream framework improvements

This document converts [FINDINGS.md](FINDINGS.md) into work for the upstream
`psp-recomp` fork. Implementation status and dependencies are tracked in
[TODO.md](TODO.md), primarily Phase 1 and Phase 3.

Status values:

- **Local** - implemented in this worktree but not yet upstreamed.
- **Fork commit** - committed on the local maintained fork branch, but not yet
  pushed, reviewed, or accepted upstream.
- **Proposed** - design or fidelity work still required.
- **Game config** - should remain title-specific rather than generic runtime
  behavior.

## Priority matrix

| Priority | Work item | Findings | Status | Required upstream result |
|---|---|---|---|---|
| P0 | Import-map stubs outside `.sceStub.text` | MGA-F-011 | Fork commit `1225147` | Codegen treats every parsed import address as an import stub. |
| P0 | Patch imports in the loaded static image | MGA-F-012 | Fork commits `51aa462`, `1225147` | Interpreted callbacks into static modules reach HLE instead of raw no-op stubs. |
| P0 | Runtime PRX loader and module registry | MGA-F-006 through MGA-F-009 | Fork commit `51aa462` + synthetic tests | Load-by-path and load-by-fd, relocation, imports, exports, start, unload, and explicit failures. |
| P0 | Interpreter syscall continuation | MGA-F-013 | Fork commit `51aa462` + synthetic tests | Runtime PRX syscalls execute HLE and resume with the original outer return target. |
| P0 | Per-thread GP | MGA-F-014 | Fork commit `51aa462` | Module-created threads run with their module GP. |
| P0 | VFPU7 packed conversions | MGA-F-010 | Fork commits `1225147`, `7980eb7` | `vi2uc`, `vi2c`, `vi2us`, and `vi2s` codegen semantics with executable vectors. |
| P0 | Executable-relative resources | MGA-F-020 | Fork commit `51aa462` | VFPU tables and fonts work from any process working directory. |
| P1 | Explicit module replacement policy | MGA-F-015 | Fork commit `abad642` + synthetic tests | Per-title policy selects guest, HLE, or reject by path/name/hash; decryption remains future work. |
| P1 | Static recompilation of runtime modules | MGA-F-021 | Proposed | Multiple generated module tables can be activated/deactivated at runtime. |
| P1 | Variable import binding | MGA-F-016 | Fork commit `abad642` explicit rejection | Bind supported variable imports in the future; current load-time rejection prevents silent misuse. |
| P1 | UID-fidelity model | MGA-F-004, MGA-F-025 | Fork commit `abad642`; audited through first stage | Separate current entry UID from next UID and account for PSP file-node objects. |
| P1 | Library-qualified import identity | MGA-F-031 | Fork commits `abad642`, `7980eb7` | Preserve `(library, NID)` through generated imports, runtime bindings, guest exports, and diagnostics. |
| P1 | Callback-aware vblank HLE | MGA-F-018 | Fork commit `51aa462` | Register `sceDisplayWaitVblankStartCB` with callback-enabled waiting. |
| P1 | Module unload/base reuse | MGA-F-007, MGA-F-026 | Fork commit `51aa462` + synthetic tests | Unload invalidates exports, frees memory, and allows deterministic overlay reuse. |
| P1 | Interpreter budget policy | MGA-F-021 | Proposed | Per-module budgets and progress diagnostics replace one global cap. |
| P2 | Generic diagnostic switches | MGA-F-024 through MGA-F-026 | Fork commit `51aa462` | UID, event, module, and watchdog-RAM logs are opt-in and title-neutral. |
| P2 | Multi-buffer capture | MGA-F-023 | Proposed | Capture displayed buffer and best render/content buffer with metadata. |
| P2 | GE `0xf0-0xf9` classification | MGA-F-022 | Fork commit `abad642` | Store immediate-vertex state and explicitly report nonzero unsupported VAP draws. |
| P2 | Gate all title patches | MGA-F-019 | Fork commit `51aa462` | Killzone-specific data mutations require an explicit build flag. |
| P2 | Shared dual-clock pad scripts | MGA-F-027 | Fork commit `abad642` + parent profiles | Header-only scripts are neutral and v3 profiles drive PPSSPP vblanks plus native presents. |
| P2 | Capture-free presentation limit | MGA-F-030 | Fork commit `abad642` | `SR_EXIT_AFTER_PRESENT` logs the terminal present and exits cleanly without a game-derived capture. |
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

Current local coverage is in
`external/psp-recomp/tools/tests/module_loader_test.c`. Its synthetic PRX has
two PT_LOAD segments, explicit BSS, module start parameters, a named import and
export, and a type-A relocation section. It currently covers items 1-6 and
same-base reload. The two-simultaneously-described-overlay dispatch case in
item 7 remains part of T-3.9 because it depends on multi-table native dispatch.

### Interpreter/HLE tests

1. `jr ra; syscall` executes the delay-slot syscall and resumes at `ra`.
2. Two nested syscalls do not replace the outer return target.
3. A guest export called through a static import returns without HLE register
   poisoning.
4. An interpreted callback into static code reaches a patched static import.
5. Unknown runtime syscall codes fail with PC, code, and module context.

Current local coverage is in
`external/psp-recomp/tools/tests/interp_fallback_test.cpp`. It executes
synthetic guest instruction streams that cover delay-slot HLE calls, nested
guest calls, outer return-PC preservation, guest-export recursion, and a guest
callback into static code that reaches a patched import. It also verifies that
an unmapped runtime syscall code is rejected before HLE dispatch. A separate
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
- Metal Gear Acid's 100-million-step bring-up cap;
- module base expectations;
- frame-count smoke-test content; or
- a blanket rule that every `sce*` module is HLE-replaced.

The framework should expose mechanisms for these choices; the root project
should provide the values.
