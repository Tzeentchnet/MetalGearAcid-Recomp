# Findings

Project milestones are defined in [PLAN.md](PLAN.md), and work derived from
these findings is tracked in [TODO.md](TODO.md).

Validated on 2026-10-21 against:

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

After the VFPU7 additions in MGA-F-010, codegen emits all `9,913` functions
with zero trapping stubs.

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
  CROSS probes.

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
interpreter stop. The dispatch-miss log contains 48 unique expected dynamic
module targets.

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
