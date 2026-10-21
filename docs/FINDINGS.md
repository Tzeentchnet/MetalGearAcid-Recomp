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

Remaining fidelity issue: the generic standalone scheduler allocates its entry
thread from the next-UID counter, while the oracle distinguishes the existing
entry-thread UID (`0x113`) from the next allocatable UID (`0x114`). These values
should be independently configurable upstream.

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

### MGA-F-015 - Encrypted and HLE-replaced modules need an explicit policy

Encrypted Sony modules such as codec and SAS PRXs cannot be executed by the
plaintext loader. The current local policy creates an HLE-only module object.

Some plaintext Sony modules, notably ATRAC and MPEG, still need their PSP
allocation footprint but should use native HLE behavior instead of starting
their guest implementation.

The current name-prefix heuristic (`sce*`) is suitable for bring-up, but the
upstream design should use a per-title module policy keyed by path, module
name, and hash. It should explicitly choose:

- guest execution;
- native HLE replacement;
- decrypt and execute; or
- unsupported with an error.

### MGA-F-016 - Variable imports remain unimplemented

The loader records function imports and exports. It observes variable counts
but does not currently relocate or bind imported variables.

Boot through the KONAMI logo did not require a variable import, but this is a
known module-manager gap and must fail explicitly if a title reaches one.

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

### MGA-F-022 - GE commands `0xf0-0xf9` remain unhandled but are not the first blocker

The software GE path reports commands `0xf0` through `0xf9` once each. Despite
that, the game renders its memory-stick message and KONAMI logo.

These commands require semantic classification before being implemented. They
must not be treated as the explanation for every later visual issue merely
because they appear in the log.

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

### MGA-F-025 - UID allocation is observably different from PPSSPP

Examples:

| Object | PPSSPP | Current native run |
|---|---:|---:|
| Entry thread | `0x113` | `0x114` |
| ZLIB module | `0x11f` | `0x11e` |
| First stage module | `0x174` | `0x16a` |

PPSSPP consumes UIDs for internal module, IO, and helper objects that the
native runtime does not yet model. Metal Gear Acid still reaches visible
content, but UID drift can break titles that index their own tables by UID or
compare handles.

The framework needs a deliberate UID-fidelity policy rather than incidental
matching.

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
