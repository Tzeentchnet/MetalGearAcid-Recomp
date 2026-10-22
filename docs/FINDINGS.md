# Findings

Project milestones are defined in [PLAN.md](PLAN.md), and work derived from
these findings is tracked internally.

Validated through 2026-10-22 against:

- Metal Gear Acid USA, `ULUS-10006`, disc version `1.00`;
- PPSSPP `v1.20.4`, interpreter mode;
- the `Tzeentchnet/psp-recomp` `kzl` branch based on the sal063 toolkit;
- Windows x64, clang-cl 19.1.5, CMake, and Ninja.

## Disc and executable

### MGA-F-001 - The supported disc is pinned exactly

The supported ISO is:

| Property | Value |
|---|---|
| Disc ID | `ULUS10006` |
| Disc version | `1.00` |
| Size | `201,392,128` bytes |
| SHA-1 | `d29eaba896be28c2575ead246bdaa3a9712929d4` |

The build and extraction tools reject a different image unless verification is
explicitly disabled for analysis. File-level hashes are recorded in
[../config/mga.toml](../config/mga.toml).

### MGA-F-002 - `program.prx` and `BOOT.BIN` are the same plaintext PRX

`PSP_GAME/USRDIR/program.prx` and `PSP_GAME/SYSDIR/BOOT.BIN` are byte-identical:

| Property | Value |
|---|---|
| Size | `1,715,950` bytes |
| SHA-1 | `5c6fe2caa1d100c9956388c5d2137edc2f77a7be` |
| Magic | ELF |

`EBOOT.BIN` is the encrypted `~PSP` form:

| Property | Value |
|---|---|
| Size | `1,716,288` bytes |
| SHA-1 | `3649b68e30375f50f6f0c3bfa927f32867f95d2f` |

No PPSSPP decryption step is required for the main module because the disc
already contains the plaintext PRX.

### MGA-F-003 - Main-module layout is stable and codegen-complete

The main PRX has:

| Property | Value |
|---|---|
| Module name | `mgp_main` |
| Module version | `1.1` |
| Load base | `0x08804000` |
| Entry / `module_start` | `0x0880432c` |
| GP | `0x0894dc70` |
| Text address | `0x08804040` |
| Text size | `0x12f734` |
| Relocated image size | `0x1e1800` |
| Module info | `0x08933c7c` |
| Type-A relocations | `46,628` |
| Discovered functions | `9,913` |
| Import stubs | `117` |
| Import libraries | `19` |

After the VFPU7 additions in MGA-F-010, the analyzer still discovers `9,913`
functions. Codegen emits `9,914` native entries with zero trapping stubs after
adding the verified computed callback entry from MGA-F-034.

## Standalone boot

### MGA-F-004 - The PPSSPP entry-state contract is measurable

A one-instruction PPSSPP interpreter trace at `0x0880432c` produced:

| State | Oracle value |
|---|---|
| `a0` / argument length | `0x21` |
| `a1` / argument pointer | `0x09fffed0` |
| Argument bytes | `disc0:/PSP_GAME/SYSDIR/EBOOT.BIN\0` |
| `k0` | `0x09ffff00` |
| `sp` | `0x09fffe90` |
| `ra` | `0x08000030` |
| Stack block | `0x09fc0000-0x0a000000` |
| Current thread UID | `0x113` |
| Kernel next UID | `0x114` |
| Next GE list ID | `0` |

The `0x40000` start stack is the PSP default when the PRX does not export a
`module_start_thread_parameter`.

The framework needed compile-time game boot configuration for the argument,
next UID, priority, stack size, attributes, title, and initial GE list ID.

The standalone scheduler now accepts the existing entry-thread UID separately
from the next allocatable UID. A protected smoke run matches the oracle's
initial sequence:

```text
module_start = 0x113
user_main    = 0x114
Main         = 0x115
```

Later UIDs still drift because PPSSPP allocates internal objects that the native
runtime does not model; see MGA-F-025.

### MGA-F-005 - Boot enters two game-created threads before `Main`

The observed native sequence is:

1. `module_start`;
2. `user_main` at `0x08804128`, priority `0x20`;
3. `Main` at `0x0880449c`, priority `0x30`.

The standalone scheduler must preserve PSP stack filling, the 256-byte `k0`
block, aligned argument copying, the thread-return stub, priority preemption,
and per-thread GP state.

## Runtime module architecture

### MGA-F-006 - Metal Gear Acid is not a single-module game

Extraction found:

- 71 additional plaintext PRXs under `USRDIR/modules` and `USRDIR/stage`;
- 8 encrypted `~PSP` PRXs that should be handled by HLE or decryption;
- a small statically recompiled main module that dynamically loads services and
  stage overlays.

Faking `sceKernelLoadModule` is therefore not a viable compatibility path for
this game.

### MGA-F-007 - Initial modules occupy deterministic first-fit addresses

With the measured call and allocation order, the important boot modules are:

| Module | Base | Allocation | Entry | GP | Execution |
|---|---:|---:|---:|---:|---|
| `KCEJ_FS` | `0x09af5800` | `0x0000fa00` | `0x09af6544` | `0x09b09e60` | Guest |
| `ZLIB` | `0x09b05200` | `0x00004100` | `0x09b0687c` | `0x09b112d0` | Guest |
| `sceATRAC3plus_Library` | `0x09b09300` | `0x00003f00` | - | `0x09b14c20` | HLE replaced |
| `sceMpeg_library` | `0x09b0d200` | `0x00007e00` | - | `0x09b1cda0` | HLE replaced |
| `KCEJ_SOUND` | `0x09b15000` | `0x0002ec00` | `0x09b15760` | `0x09b32bf0` | Guest |
| First `mgp_stage` | `0x09b43c00` | `0x0000f500` | `0x09b43c34` | `0x09b5af20` | Guest |

Later stage overlays unload and reuse `0x09b43c00`. A subsequent observed
overlay used a `0x1c100` allocation and GP `0x09b67b20`.

This validates a runtime module manager backed by the PSP first-fit block
allocator rather than host `malloc` addresses or arbitrary fixed bases.

### MGA-F-008 - The game primarily uses `sceKernelLoadModuleByID`

The main game opens each PRX through `sceIoOpen`, then calls
`sceKernelLoadModuleByID(fd, ...)`. A path-only loader is insufficient.

The runtime loader must:

1. read either ISO-backed or host-backed descriptors without corrupting their
   current PSP offset;
2. allocate the complete PT_LOAD memory range;
3. copy segments and zero BSS;
4. apply PSP type-A relocations;
5. parse module info, imports, exports, and start-thread parameters;
6. patch import stubs;
7. register named guest exports;
8. create a module-start thread with the module GP; and
9. release exports and memory on unload.

### MGA-F-009 - Guest exports need a second dispatch tier

The main module imports private libraries:

- `kjfs` - 7 functions;
- `zlibdec` - 3 functions;
- `sound` - 2 functions.

These NIDs are not host HLE calls. Once their modules load, the NIDs must map
to guest addresses. The current bring-up uses:

- built-in HLE first;
- active guest exports second;
- explicit unimplemented-NID failure last.

Guest exports currently execute in the interpreter. This is correct enough for
bring-up but is the main performance limitation.

### MGA-F-010 - Four VFPU7 packed conversion operations were missing

Initial main-module codegen emitted two trapping functions:

| Function | Instruction address | Word | Operation |
|---|---:|---:|---|
| `0x08885e4c` | `0x08885e54` | `0xd03c8484` | `vi2uc` |
| `0x08886c8c` | `0x08886d6c` | `0xd03f88cc` | `vi2s` |

The VFPU4 jump index `1` selects the VFPU7 table. Framework support was needed
for:

- `vi2uc`;
- `vi2c`;
- `vi2us`;
- `vi2s`.

The implementation must apply source prefixes before interpreting lane bits,
pack bytes or halfwords with the PSP shifts and signed clamping behavior, then
apply the destination prefix to the packed result.

The executable semantic harness now validates these operations rather than
only checking emitted C text. It covers negative clamp, byte/halfword
extraction, odd vector sizes, source swizzle, destination saturation, and
destination write masks; all 207 current VFPU/codegen vectors pass.

### MGA-F-011 - Import-table membership is authoritative, not section name

Metal Gear Acid places private-library import stubs in `.text`, including:

| Stub | Library | NID |
|---:|---|---:|
| `0x08926750` | `sound` | `0x531b15d1` |
| `0x08926760` | `kjfs` | `0x93e9297f` |
| `0x08926768` | `kjfs` | `0x1ecf095d` |

The original codegen only emitted HLE calls for addresses in sections named
`.sceStub.text*`. Those `.text` stubs compiled as `jr ra; nop`, silently
dropping every custom-module call.

Codegen must treat every address returned by the parsed PRX import map as an
import stub, regardless of its section.

### MGA-F-012 - Hybrid callbacks require patching the static image too

Interpreted module code can call a function pointer into the statically
recompiled main module. The interpreter then follows guest instructions in the
main image.

The failure sequence was:

1. main queued a sound-file request and waited on a completion semaphore;
2. the interpreted `sdfile.c` worker consumed the request;
3. the worker called a main-module completion callback;
4. the callback reached an unpatched raw main import stub;
5. `sceKernelSignalSema` became `jr ra; nop`;
6. the main thread waited forever.

It is not enough for generated native import functions to call `sr_syscall`.
Codegen must also emit a table that patches the corresponding stubs in the
loaded guest image. This lets interpreted callbacks execute the same HLE calls.

A synthetic hybrid-callback test now locks this path: interpreted module code
calls a main-image callback, which reaches a patched main import and executes
the expected HLE syscall before returning through both guest frames.

### MGA-F-013 - Interpreter syscall continuation must preserve the outer return

Runtime-loaded import stubs use `jr ra; syscall` and a runtime-assigned
20-bit syscall code mapped to the full NID.

When the reference interpreter stops on a syscall in the branch delay slot:

- the branch target has already become the resumed PC;
- HLE must run against the exported CPU state;
- interpretation must continue at that PC;
- the original top-level return PC must remain unchanged across all nested
  syscalls.

Re-reading `ra` as the top-level return after every syscall is incorrect
because nested guest calls legitimately change it.

Synthetic nested-call coverage now verifies that delay-slot syscalls resume at
the local guest return while the original outer dispatch return remains
unchanged.

### MGA-F-014 - Thread GP inheritance is module-specific

Threads created by an interpreted PRX must inherit the current module's GP, not
the main executable's global GP.

The scheduler therefore needs a GP per TCB:

- capture the current CPU GP at `sceKernelCreateThread`;
- permit the module manager to set the module-start thread GP;
- restore that GP in the PSP start context; and
- report it through thread status.

Without this, service and stage threads address the wrong small-data region.

### MGA-F-015 - Encrypted and HLE-replaced modules use explicit policy

Encrypted Sony modules such as codec and SAS PRXs cannot be executed by the
plaintext loader. The runtime creates an HLE-only module object only when the parent policy
selects it.

Some plaintext Sony modules, notably ATRAC and MPEG, still need their PSP
allocation footprint but should use native HLE behavior instead of starting
their guest implementation.

The `sce*` name-prefix heuristic has been removed. The parent now registers a
table keyed by exact guest path and SHA-1, with an expected plaintext module
name where available. Each entry explicitly chooses:

- guest execution;
- native HLE replacement;
- decrypt and execute; or
- unsupported with an error.

Policy behavior:

- configured encrypted modules must select HLE;
- unlisted encrypted modules fail;
- configured plaintext module names must match after relocation;
- explicit reject entries fail before execution; and
- unlisted plaintext modules default to guest execution, allowing stage
  overlays without a 40-entry table.

Synthetic tests cover HLE selection, hash/path miss, module-name mismatch, and
unlisted encrypted rejection. The protected title gate verifies the MGA table.

### MGA-F-016 - Variable imports are explicitly unsupported

The loader records function imports and exports. It observes variable counts
but does not currently relocate or bind imported variables.

Boot through the title gate does not require a variable import. A module with
any imported variable now fails during load with its module, library, and
count, and the loader removes partial exports, UID state, and allocation.
Silent variable-import success is therefore no longer possible.

## HLE, rendering, and packaging

### MGA-F-017 - `sceIoAssign` is a required no-state compatibility call

Boot calls:

```text
sceIoAssign("disc0:", "umd0:", "isofs:", 1, NULL, 0)
```

PPSSPP validates the strings, logs the request, and returns success without
changing a mount table. The runtime can do the same because its ISO VFS already
implements `disc0:`.

### MGA-F-018 - Callback-aware vblank wait is required

The game reaches NID `0x46f186c3`, `sceDisplayWaitVblankStartCB`.

It uses the same vblank wait as `sceDisplayWaitVblankStart`, but the scheduler
must mark the wait callback-enabled so notified PSP callbacks can execute.

### MGA-F-019 - Killzone-specific file mutation must be opt-in

The Liberation fork patches a retired online-menu payload while reading files.
Applying that transformation to all titles risks modifying unrelated game
data.

The call is now gated by `SR_KZL_PATCHES`. Game-specific byte rewriting must
never be enabled by default in the generic runtime.

### MGA-F-020 - Runtime resources must resolve relative to the executable

Deep stage initialization reached a VFPU reciprocal and aborted because the
runtime tried to open:

```text
assets/vfpu/vfpu_rcp_lut.dat
```

relative to the process working directory.

Portable builds need to:

1. copy `assets/` and `font/` beside the executable; and
2. resolve their default paths relative to the executable, while retaining
   environment overrides.

This applies to VFPU lookup tables and PGF fonts.

### MGA-F-021 - The one-million-step fallback limit is too small for ZLIB

Interpreted ZLIB decompression exceeded the generic one-million-instruction
limit around `0x09b079f4`.

A 100-million-step per-call cap allowed boot to continue through module and
stage initialization. This is a bring-up setting, not a performance solution.

Resolved for the deterministic front end in MGA-F-041: native ZLIB and sound
now pass at the framework's one-million-step default. Per-module policy remains
useful for future uncompiled campaign overlays.

Upstream should support:

- per-module or per-call budgets;
- progress-aware diagnostics;
- hot-module static recompilation; and
- a lower bounded limit for unknown targets.

### MGA-F-022 - GE commands `0xf0-0xf9` are immediate-vertex state

PPSSPP defines:

| Opcode | State |
|---:|---|
| `0xf0-0xf2` | Immediate screen X/Y/Z |
| `0xf3-0xf5` | Immediate texture S/T/Q |
| `0xf6` | Immediate primary RGB |
| `0xf7` | Immediate alpha and primitive submission (`VAP`) |
| `0xf8` | Immediate fog coefficient |
| `0xf9` | Immediate secondary RGB |

The runtime now stores all ten state words. Metal Gear Acid writes only zero
initialization values on the validated boot/title route, and the present-600
gate no longer reports them as unknown. A nonzero `VAP` still reports an
explicit unsupported immediate draw until full immediate-primitive assembly is
implemented.

### MGA-F-023 - Frame capture must distinguish displayed and rendered buffers

At frame 300, the displayed buffer capture was black while a content-buffer
capture contained the KONAMI logo. Metal Gear Acid uses multiple buffers and
can present during a transition.

Validation tools should retain:

- the PSP display buffer;
- the active GE render target or best non-empty content buffer; and
- the full eDRAM dump for protected local analysis.

## Validation and remaining fidelity

### MGA-F-024 - Native boot reaches visible game content

Measured software-renderer checkpoints:

| Frame | Visible content | GE pixels | Texture samples | Nonzero texture samples |
|---:|---|---:|---:|---:|
| 60 | `Checking Memory Stick Duo` | `3,584,196` | `1,880,400` | `186,680` |
| 300 | KONAMI logo in content buffer | `62,871,776` | `209,395,936` | `76,569,425` |

The captures were local and removed after inspection.

This proves:

- verified standalone boot;
- static main-module execution;
- runtime PRX load/relocation/link/start/unload;
- guest exports and hybrid callbacks;
- ISO file access and decompression;
- XAudio2 and sound threads;
- GE signal/finish callbacks;
- VFPU tables and PGF packaging; and
- stage-overlay reuse.

It does not prove title-screen completion, input correctness, saves, movies,
missions, or full-game stability.

### MGA-F-025 - File nodes account for the observed UID drift

The entry-thread split in MGA-F-004 fixed the first three handles, but dynamic
module and stage UIDs initially remained low.

A paired PPSSPP/native audit found that every successful `sceIoOpen` consumes a
kernel UID for PPSSPP's hidden file node even though the game receives a small
integer file descriptor. This includes:

- each PRX opened before `sceKernelLoadModuleByID`; and
- the raw-sector KFS archive opened before the `KFS_Arc` FPL.

Associating one UID with each native `Fd` and releasing its registry entry on
close aligns the audited sequence:

| Object | PPSSPP | Native |
|---|---:|---:|
| Entry thread | `0x113` | `0x113` |
| `user_main` | `0x114` | `0x114` |
| `Main` | `0x115` | `0x115` |
| KJFS module | `0x119` | `0x119` |
| ZLIB module | `0x11f` | `0x11f` |
| Sound module | `0x12e` | `0x12e` |
| `KFS_Arc` FPL | `0x172` | `0x172` |
| First stage module | `0x174` | `0x174` |

The raw UID diagnostic now logs untyped allocations as well as later type
registration, making future drift attributable instead of invisible.

### MGA-F-026 - `sr_ba_free` returns one on success

The block allocator's free function returns `1` on success and `0` on failure.
The first module-unload implementation tested the result in the opposite
direction and printed a false failure even though the stage memory was
released and reused.

Module unload regression coverage must assert both:

- success return interpretation; and
- exact base reuse by the next overlay.

A synthetic two-segment PRX test now exercises this contract together with BSS,
all supported type-A relocation forms, malformed cleanup, imports, exports,
module-start parameters, and HLE-only modules.

### MGA-F-027 - One v3 pad profile can drive both timing domains

The patched PPSSPP input hook advances events by PPSSPP vblank count. The
native runtime can advance the same logical event by presentation count.

The shared v3 format records both:

```text
<ppsspp-vblank> <runtime-present> <hex-mask> <ppsspp-width> <runtime-width>
```

Three source-only profiles now exist:

- `mga_neutral.pad` - no scripted input;
- `mga_boot.pad` - bounded START pulses for logo/title advancement; and
- `mga_menu_probe.pad` - the boot pulses followed by START, DOWN, UP, and
  CIRCLE probes.

A header-only script must be authoritative. Previously the native parser saw
zero events and fell through to its automatic START pulse, so "neutral" was
not neutral. Script presence now suppresses automatic input even with zero
events.

The profiles contain only timing and PSP button masks. They contain no game
data. Their exact title/menu calibration remains part of the deterministic
front-end reference work.

### MGA-F-028 - PPSSPP and native memstick roots require different layouts

The patched PPSSPP override expects:

```text
<root>/PSP/SAVEDATA/
```

The native `SR_FSDIR` VFS preserves the PSP device name and expects:

```text
<root>/ms0/PSP/SAVEDATA/
```

The source-only fixture tool creates either layout, or clones a protected
existing-save template into a new path. It writes a local manifest containing
only backend/profile metadata and a sorted relative-path, size, and SHA-256
inventory. It never records the protected template's absolute path.

Both generated empty layouts boot successfully with the shared neutral input
profile. Save payloads and fixture manifests remain under ignored `build/` or
another protected local directory.

### MGA-F-029 - The deterministic PPSSPP route reaches the title overlay

A 20-second PPSSPP interpreter run with an empty memstick and
`mga_boot.pad` reaches:

| Stage | UID | Allocation | Vblank | Presents |
|---|---:|---:|---:|---:|
| `init` | `0x174` | `0xf500` | `84` | `42` |
| `title` | `0x17c` | `0x1c100` | `167` | `167` |

The title allocation and GP identify `stage/title/title.prx`. No later stage
starts during the capture.

The call trace contains 2,333 unique edges and 1,119 targets. The route reaches
61 HLE functions and active audio output but no MPEG calls. This is the
protected oracle gate for native title-front-end work; detailed reduced
metadata is in `PPSSPP_REFERENCE.md` and
`reference/ppsspp_frontend.json`.

### MGA-F-030 - Native reaches a stable title gate without capture exit

Using the empty native fixture, `mga_boot.pad`, and
`SR_EXIT_AFTER_PRESENT=600`, the native runtime loads:

| Stage | UID | Allocation | GP |
|---|---:|---:|---:|
| `init` | `0x174` | `0xf500` | `0x09b5af20` |
| `title` | `0x17b` | `0x1c100` | `0x09b67b20` |

It exits at present 600 with no unimplemented HLE, host crash, watchdog, or
interpreter stop. After Phase 3 conversion, the present-600 log contains 82
module-qualified overlay fallback targets and no service-module fallback.

PPSSPP gives the title module UID `0x17c`; native is one lower after the
correctly aligned first stage. This narrows the next UID audit to object
creation between init unload and title load.

### MGA-F-031 - Import identity must retain the library name

PSP linkage is `(library, NID)`, not NID alone. The initial runtime preserved
the library while patching a stub, then discarded it when resolving the
runtime syscall and guest export.

The dispatch path now retains the pair through:

- generated static import calls;
- runtime syscall-code bindings;
- guest export lookup;
- NID logs; and
- unknown/permissive diagnostics.

Guest export lookup rejects the same NID under a different library. Built-in
HLE registration remains a global NID table for compatibility; generated and
runtime calls still carry the requested library so that registry can be
namespaced later without another codegen format change.

Regeneration confirms examples such as:

```text
sr_syscall_lib(s, "kjfs", 0x93e9297f)
sr_syscall_lib(s, "IoFileMgrForUser", 0x810c4bc3)
```

The library-qualified build retains the capture-free present-600 title gate.

### MGA-F-032 - Memory-stick presence is separate from host-path existence

Pointing `SR_FSDIR` at a nonexistent directory did not model a removed card.
The old runtime always returned inserted/assigned values from `sceIoDevctl`,
so an absent host root behaved exactly like an inserted empty stick.

`SR_MEMSTICK_STATE=removed` now matches PPSSPP v1.20.4:

| Query | Inserted | Removed |
|---|---:|---:|
| Driver status `0x02025801` | `4` | `1` |
| Device state `0x02025806` | `1` | `2` |
| FAT state `0x02425823` | `1` | `0` |
| Capacity/write-protect query | success | `0x80010013` |

Insert/FAT callbacks are registered but are not notified immediately while
removed. A synthetic state test covers the default, inserted, removed, and
invalid-value paths.

Metal Gear Acid polls device state on the initial memory-stick screen. In the
removed state it remains on `Checking Memory Stick Duo`, performs no save-slot
`Getstat`, and reaches the bounded presentation exit without a crash or
permissive fallback.

### MGA-F-033 - A valid existing save adds one title-route UID

A protected North American `ULUS10006001` fixture contains `PARAM.SFO`,
`ICON0.PNG`, and encrypted `00000000.000`. Native savedata decrypts and loads
the payload, then reaches title without mutating the fixture inventory.

The observed title UIDs are:

| Fixture | Title UID | Dispatch misses |
|---|---:|---:|
| Inserted, no save | `0x17b` | `50` |
| Inserted, valid slot `001` | `0x17c` | `53` |

The existing-save path therefore accounts for one additional game-visible
kernel object and happens to align the title UID with the empty-memstick PPSSPP
oracle. It does not explain the one-UID difference in the empty native route.

### MGA-F-034 - Interpreted call chains must re-enter native dispatch

The title overlay calls the main-module target `0x08919f10` from inside an
already-running interpreted call chain. Adding that verified computed target
to the generated dispatch table was necessary but not sufficient: the outer
dispatcher was not consulted again while the interpreter followed nested
guest calls.

The interpreter now stops at any nested target present in the active native
table. The runtime executes that generated function, restores the guest return
PC from `$ra`, and resumes the original interpreted call chain without
replacing its outer return target.

The next new-game overlay then exercised VFPU compute opcode `0xd0038087`.
Reference fallback now:

- reuses the tested `sr_vfpu_interp` compute/prefix engine;
- implements `lv.s`, `sv.s`, `lv.q`, and `sv.q` memory forms; and
- implements VFPU data/control transfers through COP2.

Synthetic interpreter coverage locks both an interpreted-to-native nested call
and VFPU compute/load/store continuation. The previously fatal title-menu
transition now completes without an interpreter stop.

### MGA-F-035 - CIRCLE confirms the North American title menu

The initial menu profile assumed CROSS (`0x4000`) confirmed NEW GAME. Exact
presentation captures showed that DOWN and UP moved the selector, but CROSS
left NEW GAME unchanged. CIRCLE (`0x2000`) enters the opening overlay.

The deterministic route is:

| Presentation | State |
|---:|---|
| `3000` | NEW GAME selected |
| `3120` | LOAD GAME selected after DOWN |
| `3240` | NEW GAME reselected after UP |
| `3360` | title fading after CIRCLE |

The opening overlay has UID `0x183`, allocation `0x1c600`, and GP
`0x09b67860`. A live Win32 keyboard run produced the same DOWN, UP, and CIRCLE
PSP masks and reached that overlay while an attached gamepad remained
enumerated. The public input test covers the equivalent keyboard and gamepad
bindings.

### MGA-F-036 - The deterministic front end has no intro PMF

The PPSSPP title oracle reports zero MPEG calls. Native runs likewise report
zero MPEG calls through title and through 20,000 presentations of the
new-game opening. The main image contains only the PMF references
`cdmv%02d.pmf` and `no_data.pmf`; the former addresses card/campaign movies,
not a pre-title intro.

The Phase 2 "intro PMF" premise is therefore not applicable to this route.
Actual PMF playback, skip, teardown, audio/video synchronization, and campaign
coverage remain Phase 5/6 work.

### MGA-F-037 - The title-menu acceptance route is byte-repeatable

`frontend_acceptance.py` checks the route, pad masks, the exact reviewed
fallback allowlist, zero failure/permissive markers, XAudio2 startup/shutdown,
nonzero playback, zero dropped blocks, and title-specific selector regions.

Three consecutive present-4200 runs passed. Captures at presentations 3000,
3120, 3240, and 3360 had one SHA-256 value per checkpoint across all three
runs. XAudio2 played between 347,392 and 349,696 frames with zero dropped
blocks. Underruns remain nonzero and are tracked by the Phase 6 audio/performance
work rather than hidden by the functional Phase 2 gate.

### MGA-F-038 - Generated modules use identity-bound immutable tables

Codegen now accepts a C symbol prefix and emits:

- prefixed function names;
- one sorted immutable `SrDispatchTable`;
- a prefixed registration symbol; and
- no conflicting `sr_register_all` symbol.

The runtime can activate up to 32 tables. Activation validates descriptor
shape, ordering, alignment, and address collisions. Module policy activates a
table only after exact path/SHA-1, module name, expected base, and
table-address-range checks. Unload deactivates it before releasing guest
memory.

The deterministic route uses:

| Module | Base | Native entries | Stubs |
|---|---:|---:|---:|
| KJFS | `0x09af5800` | `527` | `0` |
| ZLIB | `0x09b05200` | `121` | `0` |
| KCEJ_SOUND | `0x09b15000` | `904` | `0` |
| init | `0x09b43c00` | `636` | `0` |
| title | `0x09b43c00` | `997` | `0` |
| prologue | `0x09b43c00` | `1,091` | `0` |

Init, title, and prologue use distinct raw-LBN paths and hashes at the same
guest base. Public tests reject simultaneous overlap, deactivate the first
table, then activate a second table at `0x09b43c00`.

### MGA-F-039 - Main applies a second relocation pass to stage code

Activating a stage table generated directly from the extracted PRX produced a
black loop. Instruction watching showed main rewriting stage code after module
start. For example, the halfword at `0x09b45ad8` changed while main executed
`0x08804f80`.

A captured init link pass contains 675 relocation records and changes 680
words. Mutations include:

- 547 JAL instructions;
- 53 LUI immediates;
- 67 load/store/add-immediate operands; and
- eight words whose opcode changes from NOP/SPECIAL to J.

These are title-owned links to main-module code/data, not the standard PRX
relocations already applied by the generic loader. Generated overlays
therefore verify each function's live guest instructions on every wrapper
entry. Runtime JALs require the same opcode and dispatch their live target;
other changed instructions enter explicit interpreter fallback against the
patched guest image. Unchanged functions execute natively.

This preserves rendering and menu behavior without silently executing stale
constants. A future title-specific offline linker could convert more of these
verified fallbacks to native code.

### MGA-F-040 - Overlapping overlay fallbacks require module identity

An address-only miss log collapsed different overlay functions at the shared
`0x09b43c00` base. Version 2 miss logs retain `(module prefix, address)`.

The final deterministic route contains 56 reviewed targets:

| Module | Targets |
|---|---:|
| `mga_stage_init` | `6` |
| `mga_stage_title` | `13` |
| `mga_stage_prologue` | `37` |

`config/mga_frontend_fallbacks.toml` records exact module hashes and target
sets. Both `fallback_report.py` and `frontend_acceptance.py` fail on a missing
or unexpected target. Three consecutive runs matched all 56 entries and the
four established frame hashes exactly. The earlier exact 266-target set was
reduced by MGA-F-057's runtime-JAL-aware verification, not by relaxing the
allowlist.

### MGA-F-041 - Native services materially reduce front-end cost

Matched present-600 runs on the same build measured:

| Mode | Wall time | Host CPU time | Fallback cap |
|---|---:|---:|---:|
| All configured modules disabled | `20,281 ms` | `19,156.25 ms` | `100,000,000` |
| Native services/verified overlays | `11,222 ms` | `10,531.25 ms` | `1,000,000` |

The native route is about 1.81x faster and removes the parent project's
100-million-step bring-up override.

Across seven real-time 120-present menu windows:

| Mode | Mean FPS | Mean p95 frame | Worst frame |
|---|---:|---:|---:|
| All interpreted | `34.54` | `156.19 ms` | `2,187.80 ms` |
| Native/hybrid | `39.22` | `153.09 ms` | `271.16 ms` |

Software rendering and the remaining verified overlay fallbacks still prevent
stable 60 FPS. That is Phase 6 work; the conversion nonetheless removes the
largest transition stall and materially reduces CPU cost.

### MGA-F-042 - Window-title FPS diagnostics work on every presenter

`SR_FPS_COUNTER=1` updates the app window title every 500 ms with rolling
presentation rate and average frame time:

```text
Metal Gear Acid | 46.4 FPS | 21.55 ms
```

The counter uses a tested, renderer-independent QPC accumulator. GDI calls
`SetWindowText`; Vulkan and D3D12 update their SDL3 windows. It is opt-in and
does not change guest timing or rendering.

### MGA-F-043 - Exact software sampling optimizations improve the front end

GE profiling showed software rasterization consuming 94-96% of menu/prologue
window time, while the window blit itself remained below 1 ms.

Three pixel-exact changes remove redundant work:

1. bilinear sampling reads one texel when both weights are zero and two when
   either axis weight is zero;
2. through-mode triangles no longer interpolate reciprocal-W, fog, or unused
   depth values; and
3. each software primitive caches decoded texels, reusing neighbors across
   bilinear samples.

All four established software checkpoint SHA-256 values remain unchanged and
the exact front-end acceptance gate passes. Real-time seven-window pacing
improved from:

| Metric | Before | Optimized |
|---|---:|---:|
| Mean FPS | `39.22` | `46.35` |
| Mean frame time | `25.73 ms` | `21.73 ms` |
| Mean p95 frame | `153.09 ms` | `127.54 ms` |
| Worst frame | `271.16 ms` | `247.42 ms` |

The complete accepted route fell from about 108.6s to 83.0s on the validation
machine.

### MGA-F-044 - D3D12 is the practical front-end performance path

The dedicated `clang-cl-d3d12` preset builds against an SDL3 development
package without replacing the software-reference build. At 1x native
resolution on an RTX 5070, the same deterministic route measured:

| Metric | Optimized software | D3D12 |
|---|---:|---:|
| Route wall time | `83.0 s` | `14.1 s` |
| Mean host presentation FPS | `46.35` | `162.55` |
| Mean frame time | `21.73 ms` | `6.37 ms` |
| Mean p95 frame | `127.54 ms` | `21.41 ms` |

D3D12 menu and prologue captures are visually correct and pass the functional
acceptance metrics. Native-resolution title captures are not pixel-identical
to software: 13.5-13.6% of title pixels exceed channel delta 8, with maximum
delta 18-25; the fade frame has 0.61% above delta 8 and maximum delta 9.
Those small color differences require the explicit tolerance review in
T-6.3, but they do not block D3D12 as the recommended diagnostic/playability
renderer.

### MGA-F-045 - Configuration captions must use the compiled title

The explicit `--configure` and `--configure-input` paths already used
`SR_GAME_TITLE`, but the automatic first-run graphics/controller dialogs and
native message-box caption still said `Killzone: Liberation`.

All GUI entry points now use the same compile-time title with a generic
`PSP Recomp` fallback. Fresh-process validation reports:

```text
Metal Gear Acid Graphics
Metal Gear Acid Controller
```

Killzone builds retain their own caption through their existing
`SR_GAME_TITLE` definition.

### MGA-F-046 - Failed live-code wrappers must become interpreter-only

An interactive D3D12 run crashed after the prologue with Windows exception
`0xc00000fd` (stack overflow). The fault itself was in `__chkstk`; a protected
stack scan showed repeating `sr_interpret_direct_module` and
`sr_interpret_fallback` frames while the guest stack pointer stayed
unchanged.

The recursion was host-only. After a generated overlay function failed its
live-code check, the wrapper entered the interpreter but remained visible in
the active native dispatch table. When interpreted control reached that
address again, it handed control back to the same wrapper, which immediately
re-entered the interpreter.

Codegen now marks the exact failed generated function pointer as
interpreter-only before tail-entering live guest code. Dispatch suppresses
that pointer while retaining the active table's module identity. A
replacement overlay at the same guest address remains native because it has
a different function pointer; the public dispatch-table test covers this
case.

The exact D3D12 init/title/prologue route now reaches the configured
50,000-presentation limit in 108.8s with no host crash, interpreter stop, or
permissive fallback.

### MGA-F-047 - Blocking audio must not drain the host device

The FPS counter could report 150 or more presentations per second while
audio still stuttered. Historical real-time logs confirmed 145-177 XAudio2
underruns in roughly eight seconds, so presentation throughput was not a
valid audio-health proxy.

Normal `sceAudioOutput*Blocking` channels waited until their queued depth
reached zero. That wakes the producer only after XAudio2 consumes the final
submitted block, guaranteeing a gap at each guest audio buffer.

The accepted policy now:

1. retains three guest buffers or two complete host-device queues of real
   audio before blocking;
2. submits device-only preservation silence without advancing the guest
   mixer timeline or discarding late samples;
3. fades across real/silence boundaries;
4. after a load gap, accumulates 4,096 real frames before resuming, with a
   500 ms fallback for short effects; and
5. keeps playback fixed at 44.1 kHz without adaptive speed/pitch changes.

The accepted D3D12 route now reports:

```text
played=242944 frames (5508.93 ms)
clock_drift=-44.80 ms
device_buffers=6..8
dropped=0
resynced=3072
silent_blocks=2
underruns=0
padding_blocks=7
padding_transitions=1
```

`frontend_acceptance.py` now rejects any device underrun in addition to
dropped guest frames.

The Forest-save mission transition is a harsher load case. The original
full-queue padding path produced roughly 93-293 real/silence transitions and
audible static bursts. The final path completed the same manually driven
transition with 8 transitions and 67,456 resynced frames; the user reported
that transitions were "much better" and mission audio remained clean.

### MGA-F-048 - The first post-prologue overlay requires PSP scratchpad RAM

The first live run beyond the prologue loaded another `mgp_stage` module:

| Property | Value |
|---|---|
| Disc file | `PSP_GAME/USRDIR/stage/st00/st00.prx` |
| Raw path | `disc0:/sce_lbn0x11ad0_size0x1fb51` |
| SHA-1 | `7899000a805ae773838b6c11741e62af46d14338` |
| Base | `0x09b43c00` |
| Allocation | `0x19200` |
| Generated entries | 1,000 |
| Trapping stubs | 0 |

Before st00 had an active table, its computed callback entries were reported
as unqualified fallbacks. After native integration, execution reached a store
at `0x00013fe0`. This is not a wild pointer: st00 uses the PSP's 16 KiB
scratchpad at `0x00010000-0x00013fff` for transient mission data.

The runtime now maps scratchpad separately from VRAM and user RAM, including
the PSP physical aliases used by guest code. Native memory macros and runtime
interpreter spans share the mapping. The public interpreter test covers
native/aliased reads plus an interpreted write at the final valid word.

### MGA-F-049 - Hybrid handoff depth must be bounded at long-lived loops

Live-code verification creates legitimate interpreter/native crossings, but
long-lived stage loops can retain those host continuations across scheduler
fiber switches. st00 reached handoff depth 1,024 in a deterministic 37-second
fast-forward run and eventually exhausted the 64 MiB fiber stack.

The runtime now:

1. caps native handoff depth at 256;
2. executes deeper calls in the interpreter without another host call frame;
3. exports interpreter state to the scheduler every 256 instructions;
4. treats the one-million-step limit as a scheduler-mode chunk boundary while
   preserving strict failure in standalone tests; and
5. implements the fallback instructions reached by the deeper path:
   `vnop`, all `vf2i` modes, `vi2f`, all VFPU7 packed conversions, and
   `bvf`/`bvt` plus likely variants.

The cleaned D3D12 broad-button route reaches init, title, prologue, and st00,
logs the depth cap once, and exits normally at present 30,000 after 152.8s.
There are no host crashes, memory faults, unimplemented instructions,
interpreter stops, or permissive fallbacks.

### MGA-F-050 - Verified public saves bypass the scripted opening

Two North American `ULUS-10006` saves are preserved only in ignored local
build storage:

| Source | Folder | Progress | SHA-256 / status |
|---|---|---|---|
| GameFAQs #10243 | `ULUS10006001` | Completion data, Normal, 32:04:46, one clear | Existing protected fixture; byte-identical after native load |
| GameFAQs #8725 | `ULUS10006002` | After Forest/tutorial, Normal, third playthrough | ZIP `fab05c1a904144dea3395734b2db00a27b6d8ae91ac3bf405fb357ce728c1de2` |

The #8725 ZIP contains only `00000000.000`, `ICON0.PNG`, and `PARAM.SFO`;
its paths were validated before extraction. The folder name must remain
`ULUS10006002`. It appears under LOAD GAME rather than initial CONTINUE.

A disposable native fixture loads the save, reaches the `0x18a00` and
`0x23200` post-save overlays, exits normally, and remains byte-identical.
This provides a repeatable gameplay/audio route without replaying the long
scripted prologue.

This fixture and `config/mga_load_save_probe.pad` are now the Phase 4
reference route. A fresh 2026-10-22 D3D12 1x run followed LOAD GAME to the
map, selected `Lobito Laboratory - Outside Gate`, confirmed STAGE01 and its
delayed prompt, activated native `st01` at `0x09b6c600`, and exited cleanly at
present 10,000. It reported zero audio drops or underruns and no runtime
failure marker; post-run fixture verification remained byte-identical. This
establishes the deterministic route, not gameplay, combat, or save-creation
coverage.

### MGA-F-051 - Structured timing separates host, submission, and GPU cost

Opt-in diagnostics now write every measured presentation to a stable CSV and
record D3D12 timestamp-query results after the owning frame fence completes.
The existing human-readable windows now include p50, p95, p99, over-budget
count, and GPU average/maximum. Bounded runs shut the frontend down cleanly, so
pipeline, texture, and framebuffer summaries are no longer lost to `_Exit`.

Three accepted front-end runs at each representative scale measured:

| Internal scale | Median host present FPS | Median p95 | Median p99 | Median GPU work |
|---:|---:|---:|---:|---:|
| 1x | `157.83` | `23.50 ms` | `32.44 ms` | `0.10 ms` |
| 2x | `153.62` | `23.44 ms` | `32.39 ms` | `0.18 ms` |
| 4x | `158.45` | `22.72 ms` | `32.35 ms` | `0.42 ms` |
| 8x | `157.60` | `15.17 ms` | `32.59 ms` | `1.75 ms` |

The corrected post-Forest/STAGE01 route produced median host presentation
throughput of `178.07`, `175.44`, `175.26`, and `171.98` FPS at 1x, 2x, 4x,
and 8x. Median GPU work was `0.11`, `0.20`, `0.44`, and `2.06` ms.

These are host presentation-call rates, not the PSP's game FPS. They do show
that the validated routes remain CPU/runtime-bound even at 8x. Disabling
variable-rate shading at 2x, 4x, and 8x changed median throughput by less than
the observed run variance and produced byte-identical logical and
full-resolution title captures. VRS is not a release-critical optimization on
this workload.

### MGA-F-052 - Every supported scale passes, but point captures bias even scales

The exact front-end acceptance route passed at every integer D3D12 scale from
1x through 8x with:

- the then-current 266-target fallback set, subsequently reduced to 56 by
  MGA-F-057 without changing checkpoint pixels;
- all four semantic frame checks;
- zero unknown HLE, permissive fallback, crash, watchdog, or interpreter stop;
- zero audio drops or underruns; and
- no D3D12 validation or device-removal failure.

The post-Forest route also loaded the selected `0x23200` STAGE01 overlay and
preserved its save fixture at 1x, 2x, 4x, and 8x.

The old logical capture selects one internal pixel at `scale / 2`. Odd scales
therefore reproduce the 1x title delta exactly, while even scales report
misleadingly large point-sample deltas:

| Scale | Pixels above delta 8, old point sample | Maximum delta |
|---:|---:|---:|
| 1x | `13.61%` | `18` |
| 2x | `39.20%` | `98` |
| 4x | `28.83%` | `57` |
| 6x | `24.04%` | `41` |
| 8x | `21.28%` | `34` |

Full-internal-resolution captures prove that this is primarily a diagnostic
sampling artifact rather than an even-scale rendering failure. Box-averaging
each internal logical-pixel block brings 2x, 3x, 4x, and 8x back to
`12.66-13.53%` above delta 8, matching the 1x distribution. The full images
retain real subpixel information: `77.28-85.15%` of logical blocks contain
more than one internal color.

The runtime retains the established 480x272 point capture by default for
compatibility and adds an explicit `SR_D3D12_CAPTURE_INTERNAL=1` path.
`tools/mga/scaling_capture.py` analyzes every subpixel offset and a box-filtered
logical result without changing existing goldens.

### MGA-F-053 - The remaining title delta is common texture-stage behavior

At 1x, the three textured title frames retain `13.54-13.62%` of pixels above
delta 8 and maximum channel deltas of 18-25. The mostly untextured fade has
only `0.61%` above delta 8 and maximum delta 9.

Two controlled D3D12 experiments produced byte-identical captures to the
default path:

1. disabling the direct hardware-blend path; and
2. selecting the legacy pixel shader.

D3D12 capture reads the display texture before final window presentation, so
the linear presentation sampler is also excluded. The common shader path uses
hardware floating-point texture filtering, while the software oracle
quantizes bilinear weights to 8 bits and truncates each interpolation stage.
The evidence therefore localizes the dominant difference to texture
sampling/interpolation quantization before destination blending. A manual
PSP-quantized GPU sampler is implemented and measured in MGA-F-059;
broadening the existing whole-frame tolerance is not a substitute for the
remaining feature-class analysis.

### MGA-F-054 - Interpreter cost is concentrated in a few overlay entries

`SR_INTERP_PROFILE=<path>` now records calls, guest instructions, syscalls,
native handoffs, chunk limits, returns, and failures separately from the
stable v2 fallback allowlist. The parent report tool aggregates multiple runs
and ranks targets by actual work rather than unique address count.

The accepted front-end route executes `2,055,263` interpreted instructions.
Two entries account for about 56%:

| Module/target | Calls | Instructions | Share |
|---|---:|---:|---:|
| `mga_stage_title/0x09b4665c` | `7,018` | `779,343` | `37.92%` |
| `mga_stage_prologue/0x09b4d7dc` | `127` | `371,063` | `18.05%` |

The corrected post-Forest route executes `26,931,234` interpreted
instructions. Its selected mission overlay is:

| Property | Value |
|---|---|
| Disc file | `PSP_GAME/USRDIR/stage/st01/st01.prx` |
| Raw path | `disc0:/sce_lbn0x11e50_size0x2c138` |
| SHA-1 | `9dfc231f933ef0d508ad7763f74fb6d857581e66` |
| Runtime base | `0x09b6c600` |
| Allocation | `0x23200` |

Target `0x09b6effc` alone executes `21,855,537` instructions (`81.15%`);
`0x09b7b218` adds `1,553,717` (`5.77%`). Generating and activating a verified
native STAGE01 table is therefore the highest-confidence performance
improvement. MGA-F-057 records its implementation and measured result.
Generic compiler optimization is not a substitute for removing this
interpreted workload.

### MGA-F-055 - Whole-program O2 is below the action threshold

A separate clang-cl build compiled every generated main and native-module
translation unit with `/O2` instead of the reviewed `/O1` default. Three exact
front-end acceptance runs measured:

| Build | Median host present FPS | Median p95 | Run spread |
|---|---:|---:|---:|
| `/O1` | `157.83` | `23.50 ms` | `1.42%` |
| `/O2` | `159.34` | `23.58 ms` | `4.42%` |

The `0.96%` median difference is below the 5% action threshold and smaller
than run variance. `/O1` remains the default; no new production option or
larger generated objects are justified by this route.

### MGA-F-056 - Serialized D3D12 pipeline libraries are unsafe on the validation driver

An explicit cold/warm `SR_D3D12_PSO_CACHE` experiment wrote five route PSOs
successfully. The second process loaded the `52,060`-byte library, then
`LoadGraphicsPipeline` returned `DXGI_ERROR_DEVICE_REMOVED`; the device reason
was `DXGI_ERROR_DRIVER_INTERNAL_ERROR`, and the run exited before the front
end.

The normal in-memory asynchronous PSO cache is unaffected. Disk persistence
remains disabled by default and now requires the additional
`SR_D3D12_UNSAFE_PSO_CACHE=1` diagnostic acknowledgement, preventing an
ordinary opt-in from removing the device. Replacing pipeline-library
serialization with individually validated cached-PSO blobs is preferable to
silently accepting this driver-specific failure.

### MGA-F-057 - Runtime-JAL-aware native STAGE01 removes the dominant hot spot

`stage/st01/st01.prx` generates 1,351/1,351 functions with zero trapping
stubs. The parent binds its exact raw path, SHA-1, runtime base, and immutable
dispatch table through the existing module policy.

The first direct integration exposed an important generic verifier issue.
Overlay functions cached a successful live-code comparison forever, while the
game can patch code after a function's first invocation. In addition, exact
comparison rejected linker-adjusted JAL target bits even though
`--runtime-jal` already reads and dispatches the live JAL word.

Fork commit `06e7010` changes verified overlays to:

1. recheck non-JAL live instructions on every wrapper entry until a mismatch
   disables that wrapper;
2. require runtime JALs to remain JAL opcodes while allowing their live target
   bits to differ; and
3. continue using the existing module-qualified interpreter-only suppression
   for genuine code mismatches.

This preserves safety while allowing the post-load linker changes that the
generated code explicitly supports.

Three matched present-10,000 post-Forest runs measured:

| Metric | Interpreted STAGE01 | Native/hybrid STAGE01 | Change |
|---|---:|---:|---:|
| Median route wall time | `53,278 ms` | `18,786 ms` | `-64.74%` |
| Interpreted instructions/run | `25,835,871` | `3,743,963` | `-85.51%` |
| Interpreter calls/run | `28,883` | `16,400` | `-43.22%` |
| Distinct fallback targets | `139` | `110` | `-20.86%` |
| Median steady host present FPS | `163.30` | `179.92` | `+10.18%` |

The interpreted control had high host wall-time variance (`19.2-84.4 s`);
instruction counts and the native route were stable, with native wall times
of `18.6-18.9 s`. Both captured checkpoints are byte-identical between
control and native runs. Three native runs preserve the save fixture and
report zero unknown HLE, crash, watchdog, interpreter stop, permissive
fallback, audio drop, or underrun.

The same verifier change reduces the exact deterministic front-end allowlist
from 266 to 56 targets (6 init, 13 title, 37 prologue) with byte-identical
software and D3D12 captures. Median front-end host presentation throughput
remains within variance, moving from `157.83` to `159.50` FPS.

### MGA-F-058 - GDI and Vulkan pass the deterministic front end

The parent now exposes a dedicated `clang-cl-vulkan` preset using the
runtime's existing SDL3/Vulkan backend. Three renderer configurations completed
the exact present-4,200 route with the reviewed 56-target fallback set, zero
unknown HLE/crash/watchdog/interpreter stop/permissive fallback, and zero audio
drops or underruns:

| Configuration | GE renderer | Presenter | Result |
|---|---|---|---|
| `clang-cl`, `SR_GPU=sw`, `SR_VIDEO=gdi` | Software | Win32 GDI | Pass |
| `clang-cl-vulkan`, `SR_GPU=sw` | Software | SDL3/Vulkan | Pass |
| `clang-cl-vulkan`, `SR_GPU=vk` | Vulkan | SDL3/Vulkan | Pass |

The Vulkan presenter with software GE produces all four captures
byte-identically to GDI, isolating presentation/window behavior from
rasterization.

The full Vulkan GE backend is functionally correct on the route but is not
pixel-identical to the software oracle:

| Checkpoint class | Different pixels | Pixels above delta 8 | Maximum delta |
|---|---:|---:|---:|
| Three title frames | `24.25-24.63%` | `5.81-5.88%` | `17` |
| Title fade | `11.18%` | `0.42%` | `9` |

These differences are smaller than the measured D3D12 title distribution but
still require feature-class review before Vulkan can share a release golden
tolerance.

One diagnostic run per configuration measured:

| Configuration | Host present FPS | p95 interval | Backend average |
|---|---:|---:|---:|
| GDI + software GE | `114.26` | `50.70 ms` | `0.28 ms` |
| Vulkan presenter + software GE | `112.84` | `50.60 ms` | `0.39 ms` |
| Vulkan GE | `158.25` | `21.12 ms` | `0.25 ms` |

The software-renderer configurations remain CPU-raster bound, so replacing
GDI presentation alone does not improve throughput. Vulkan GE submitted
1,240,103 triangles and 3,314 sprites across 21,278 submissions, with 3,683
GPU-owned and five CPU presentations. These single-run timing values are
diagnostic rather than release thresholds.

### MGA-F-059 - PSP-quantized GPU sampling materially improves parity

Fork commit `2584d53` adds a shared sampling policy to D3D12 and Vulkan for
non-mipmapped textures:

1. nearest coordinates follow the software renderer's shifted integer rule;
2. bilinear weights are truncated to 8-bit fractions;
3. horizontal and vertical interpolation use the same ordered signed
   `>> 8` operations; and
4. wrap/clamp coordinates are resolved explicitly before texel fetch.

The path is enabled by default. `SR_GPU_PSP_SAMPLER=0` restores host hardware
filtering for A/B diagnostics. Mipmapped D3D12 textures retain the hardware
path until PSP LOD selection is modeled explicitly.

Against the software oracle:

| Renderer | Sampler | Title pixels above delta 8 | Title maximum delta | Fade above delta 8 |
|---|---|---:|---:|---:|
| D3D12 | Hardware | `13.54-13.62%` | `18-25` | `0.61%` |
| D3D12 | PSP-quantized | `1.02-1.04%` | `17` | `0.03%` |
| Vulkan | Hardware | `5.81-5.88%` | `17` | `0.42%` |
| Vulkan | PSP-quantized | `3.58-3.63%` | `17` | `0.45%` |

D3D12's large-delta title population falls by more than 92%; Vulkan's falls
by about 38%. The quantized path also reduces the number of any-difference
pixels from about 70% to 63% on D3D12 and from about 24% to 13% on Vulkan.
The remaining maximum deltas show that sampler quantization is not the only
source of raster divergence.

Both default quantized renderers pass the exact front-end functional, input,
audio, module, and fallback gates. D3D12 and Vulkan also complete the native
STAGE01 route with unchanged save fixtures and no runtime failure marker.
Single-run timing and D3D12 GPU timestamps show no measurable cost on these
routes; dedicated repeated performance thresholds remain future work.

### MGA-F-060 - Remaining large deltas are hardware edge behavior

Fork commit `41c8cb4` ports the software renderer's integer texture-function
and fog formulas to both GPU shaders. It also canonicalizes logical D3D12
golden captures through the active PSP framebuffer format; full internal-scale
captures remain raw.

The capture conversion is diagnostic, not a rendering shortcut. D3D12 keeps
full-range RGBA internally for blending and framebuffer feedback, then packs
logical goldens as 5650/5551/4444 exactly as the software capture path does.
This removes expansion bias from the comparison.

Final front-end results against the software oracle:

| Renderer | Title pixels above delta 8 | Title maximum delta | Fade above delta 8 |
|---|---:|---:|---:|
| D3D12 | `0.28-0.33%` | `15-16` | one pixel |
| Vulkan | `1.97-2.03%` | `17` | `0.45%` |

Integer texture-function math reduces Vulkan's title population from
`3.58-3.63%` to `1.97-2.03%`. D3D12's source-color population was already
dominated by its capture representation; native-format canonicalization
reduces it from `1.02-1.04%` to `0.28-0.33%`.

`tools/mga/frame_delta_report.py` classifies each above-threshold pixel against
the software-reference neighborhood:

| Renderer | Edge-adjacent share | Neighbor-resolved share | Interior pixels/frame |
|---|---:|---:|---:|
| D3D12 title | `99.73-99.77%` | `24.59-27.64%` | `1` |
| Vulkan title | `99.81-100%` | `49.28-50.09%` | `0-5` |

The remaining large deltas are therefore isolated to hardware triangle
coverage/interpolation at reference edges. They are not evidence of a broad
texture decode, texture-function, fog, presentation, or interior color error.
Achieving exact edge parity would require a dedicated PSP coverage strategy,
not a wider whole-frame color tolerance.

Default D3D12 and Vulkan front-end routes, plus both native STAGE01 routes,
pass with unchanged fixtures and clean failure/audio markers. Parent tests
cover the edge classifier; D3D12 tests cover logical capture
canonicalization.

### MGA-F-061 - Circle-only input completes the initial default-deck setup

The broad `0xf3f9` briefing pulses used for the first st00 discovery mixed
directional, shoulder, face, START, and SELECT inputs, so they could not prove
which control advanced the new-game flow. The new deterministic
`mga_new_game_setup.pad` retains the established boot/title timing, selects
NEW GAME, then sends only CIRCLE edges through present 18,000.

Two D3D12 1x runs from separate empty memstick fixtures loaded native init,
title, and prologue overlays and produced byte-identical captures at presents
18,000, 21,000, 24,000, 27,000, and 29,900. The route advances from Teliko's
opening dialogue through the card-effect tutorial and initial battlefield.
At present 29,900 it is waiting on a playable six-card hand with `18/30`
remaining from the default 30-card deck.

Both runs exited normally at present 30,000, contained no runtime failure
marker, and left their empty fixtures unchanged. This establishes NEW GAME
entry and initial default-deck setup. It does not yet validate deliberate
movement, camera, card selection, action execution, pause, cancel/confirm,
combat, or saving.

## Ranked improvement opportunities

| Rank | Priority | Opportunity | Evidence | Confidence | Disposition |
|---:|---|---|---|---:|---|
| Done | P1 | Generate, live-verify, and activate native `st01` | 85.51% fewer interpreted instructions with exact frame parity | 10/10 | Completed in MGA-F-057 |
| Done | P1 | Implement PSP-quantized hardware sampling | D3D12 title pixels above delta 8 fall from ~13.6% to ~1.0%; Vulkan also improves | 10/10 | Completed in MGA-F-059 |
| Done | P1 | Build feature-class D3D12/Vulkan goldens and isolate remaining deltas | 99.7-100% of residual large pixels are edge-adjacent | 10/10 | Completed in MGA-F-060 |
| 1 | P1 | Replace serialized pipeline libraries with safe per-PSO persistence | Reusing the current disk cache removes the D3D12 device | 10/10 | Keep gated until redesigned |
| 2 | P1 | Continue CMake/CTest integration for existing graphics/runtime tests | Relevant tests existed but were not reachable from the parent CTest surface | 9/10 | Incremental maintenance |
| 3 | P2 | Investigate exact PSP edge coverage if later scenes require it | Current title residuals are almost exclusively hardware edge pixels | 9/10 | Defer pending broader goldens |
| 4 | P2 | Profile the remaining front-end and STAGE01 fallback entries | The revised exact sets contain 56 and 110 targets respectively | 9/10 | Re-rank after broader gameplay |
| - | Reject | Switch all generated code to `/O2` | 0.96% median gain, below variance/action threshold | 9/10 | Keep `/O1` |
| - | Defer | Tune VRS for the current routes | No measurable throughput or capture difference | 9/10 | Revisit on heavier scenes |
