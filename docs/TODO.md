# Project TODO

Last updated: 2026-10-22

This is the live execution list for [PLAN.md](PLAN.md). It must be updated in
the same change as implementation work.

## Status and priority

- `[ ]` - pending
- `[~]` - in progress
- `[x]` - complete
- `[!]` - blocked; the item must name the blocker
- **P0** - blocks the current milestone
- **P1** - required before release
- **P2** - useful enhancement or additional confidence

When completing an item:

1. change it to `[x]`;
2. add the completion date and concise evidence;
3. update every applicable document in the documentation matrix in
   [PLAN.md](PLAN.md#documentation-maintenance-contract);
4. add follow-up items discovered during validation; and
5. refresh **Current focus** so it lists ready work rather than completed work.

## Current focus

The next ready P0 work is:

1. **T-4.1** define the title-to-tutorial/first-mission reference route;
2. **T-4.2** enter a new game and complete initial deck/card setup;
3. **T-4.3** validate movement, camera, cards, actions, pause, and cancel;
4. **T-4.4** validate combat, enemy turns, failure, and retry;
5. **T-4.5** validate every module/stage transition on the route.

## Phase 0 - Reproducible boot baseline

- [x] **T-0.1 P0** Pin the ULUS-10006 v1.00 disc and required files by size
  and SHA-1.
  - Done 2026-10-21: identity is in `config/mga.toml`; extraction rejects a
    mismatch.
- [x] **T-0.2 P0** Extract the main module and all plaintext service/stage
  PRXs without committing them.
  - Done 2026-10-21: 71 additional plaintext PRXs extracted; 8 encrypted PRXs
    skipped.
- [x] **T-0.3 P0** Relocate and generate the main module with no trapping
  functions.
  - Done 2026-10-21: 46,628 relocations, 9,914/9,914 functions, zero stubs,
    including the verified computed callback entry at `0x08919f10`.
- [x] **T-0.4 P0** Build the native Windows executable with clang-cl.
  - Done 2026-10-21: release build links `mga.exe` and packages VFPU/font
    resources.
- [x] **T-0.5 P0** Capture the exact PPSSPP main-entry state.
  - Done 2026-10-21: argument, stack, registers, UID state, and GE ID recorded
    in MGA-F-004.
- [x] **T-0.6 P0** Load, relocate, link, start, and unload plaintext runtime
  PRXs.
  - Done 2026-10-21: KJFS, ZLIB, sound, and stage overlays execute through
    guest fallback.
- [x] **T-0.7 P0** Fix private imports in `.text` and hybrid callbacks into
  static main code.
  - Done 2026-10-21: parsed import-map addresses are authoritative and the
    loaded main image receives runtime syscall patches.
- [x] **T-0.8 P0** Add required VFPU7 and callback-aware vblank behavior.
  - Done 2026-10-21: zero main stubs and boot proceeds through stage rendering.
- [x] **T-0.9 P0** Establish visible native rendering checkpoints.
  - Done 2026-10-21: frame 60 reaches the memory-stick screen and frame 300
    reaches the KONAMI logo.
- [x] **T-0.10 P1** Document findings, reproduction steps, and upstream work.
  - Done 2026-10-21: `FINDINGS.md`, `UPSTREAM.md`, and `REPRODUCTION.md`.

## Phase 1 - Framework hardening and upstream integration

- [x] **T-1.1 P0** Split the modified `psp-recomp` worktree into reviewed,
  focused commits and pin the parent submodule to the resulting commit.
  - Dependency: T-1.2 is complete; T-1.3 should land with or before its
    implementation commit.
  - Done 2026-10-21: runtime/module work and native tests committed as
    `e2dbc91`; codegen/import/VFPU7 work committed as `9683b44`; the parent
    submodule was subsequently advanced to tested fidelity commits `245031c`
    and `96dd536`, then to native-overlay/audio/stability commit `3f7d48e` and
    renderer/profiling diagnostics commit `40447fd`, then live-overlay
    verification commit `06e7010`. The parent is pinned to `06e7010`. The
    fork branch is published at
    `Tzeentchnet/psp-recomp`; the parent is published privately at
    `Tzeentchnet/MetalGearAcid-Recomp`.
- [x] **T-1.2 P0** Add synthetic runtime PRX loader tests.
  - Cover PT_LOAD/BSS, every supported type-A relocation, malformed inputs,
    import patching, exports, start parameters, unload, and overlay base reuse.
  - Done 2026-10-21: `module_loader_test.c` builds a two-segment PRX entirely
    in memory and covers BSS, all supported relocation types, invalid input and
    cleanup, import patching/NID lookup, named exports, module-start
    parameters/GP/status, HLE-only modules, unload, and same-base reload.
    Passed through CMake/CTest and the fork's standalone Makefile target.
- [x] **T-1.3 P0** Add interpreter syscall and hybrid callback tests.
  - Cover delay-slot syscall resume, nested calls, original return-PC
    preservation, guest exports, callbacks into static code, and unknown codes.
  - Done 2026-10-21: `interp_fallback_test.cpp` now executes synthetic guest
    instruction streams for delay-slot HLE syscalls, nested guest calls,
    preserved outer returns, guest-export recursion, callbacks into patched
    static code, and rejection of unknown runtime syscall codes. Passed through
    CMake/CTest and the fork's standalone `test-interpreter` target.
- [x] **T-1.4 P1** Expand VFPU7 tests from emitted-text checks to executable
  semantic vectors.
  - Cover prefix behavior, clamping, odd vector sizes, packing, masks, and
    saturation.
  - Done 2026-10-21: the compile-and-run VFPU harness now covers all four
    packed conversions, negative unsigned clamp, signed byte/halfword
    extraction, pair/triple/quad packing, source swizzle, destination
    saturation, and destination write masks. All 207 semantic vectors pass
    with MinGW GCC.
- [x] **T-1.5 P1** Carry `(library, NID)` through generated imports, runtime
  syscall bindings, guest export lookup, and diagnostics.
  - Done 2026-10-21: generated static imports call `sr_syscall_lib`, runtime
    syscall bindings return the original library, guest export lookup requires
    an exact library when supplied, NID logs/unknown diagnostics retain the
    library, and compatibility wrappers remain for NID-only callers. Synthetic
    collision checks and the present-600 title gate pass.
- [x] **T-1.6 P0** Add separate standalone-boot fields for existing entry
  thread UID and next allocatable UID.
  - Oracle: current `0x113`, next `0x114`.
  - Done 2026-10-21: added `SR_MODULE_START_UID` independently from
    `SR_BOOT_NEXT_UID`; protected smoke now reports `module_start=0x113`,
    `user_main=0x114`, and `Main=0x115` while preserving the measured frame-60
    rendering checkpoint.
- [x] **T-1.7 P1** Audit PPSSPP/native UID sequences through first stage load
  and model kernel objects that affect game-visible handles.
  - Done 2026-10-21: PPSSPP allocates a hidden file-node UID for each
    `sceIoOpen`, including module files and the raw KFS archive. Associating
    that UID with the runtime `Fd` aligns every checked handle through the
    first stage: entry `0x113`, user main `0x114`, Main `0x115`, KJFS `0x119`,
    ZLIB `0x11f`, sound `0x12e`, KFS_Arc FPL `0x172`, and stage `0x174`.
    Frame-60 metrics remain unchanged.
- [x] **T-1.8 P1** Replace the `sce*` module-name heuristic with a per-title
  module policy keyed by path, name, and hash.
  - Done 2026-10-21: added a generic policy table API and an MGA-owned table
    with exact SHA-1/path/name modes. Configured encrypted modules require HLE,
    unlisted encrypted modules fail, explicit rejects fail, configured
    plaintext names are verified, and unlisted plaintext stage overlays
    default to guest execution. Synthetic mismatch/rejection tests and the
    present-600 title gate pass.
- [x] **T-1.9 P1** Implement variable imports or reject them during module load
  with library/NID/module context.
  - Done 2026-10-21: the loader rejects any nonzero imported-variable count
    with library, module, and count diagnostics; synthetic coverage verifies
    the partially registered module and allocation are cleaned up.
- [ ] **T-1.10 P1** Split PRX parsing/relocation from module-manager kernel
  policy.
- [ ] **T-1.11 P1** Add protected Metal Gear Acid and Killzone regression
  smoke tests for every upstream fork batch.
- [ ] **T-1.12 P1** Upstream accepted generic changes and update
  `UPSTREAM.md` status and parent submodule pin.
- [x] **T-1.13 P1** Make first-run, configuration, and native message dialogs
  use the compiled game title.
  - Done 2026-10-21: removed the remaining hardcoded Killzone captions from
    `gui.c`; verified `Metal Gear Acid Graphics` and
    `Metal Gear Acid Controller` in fresh processes.

## Phase 2 - Deterministic front end

- [x] **T-2.1 P0** Create deterministic PPSSPP and native input scripts for
  boot, logo skip where supported, title idle, and menu navigation.
  - Done 2026-10-21: added shared v3 neutral, boot-advance, and menu-probe
    profiles with independent PPSSPP-vblank and native-presentation timing;
    added a strict validator and five unit tests; verified the neutral profile
    is accepted by both backends and suppresses native automatic input while
    preserving the frame-60 checkpoint. Title validation later corrected the
    menu confirm action from CROSS to CIRCLE.
- [x] **T-2.2 P0** Define isolated empty and existing-save memstick fixtures.
  - Fixtures remain protected/local; commit only generators or metadata.
  - Done 2026-10-21: added a source-only fixture creator/verifier for PPSSPP
    (`PSP/SAVEDATA`) and native (`ms0/PSP/SAVEDATA`) roots, deterministic
    SHA-256 inventories, protected template cloning, and five unit tests.
    Both backends booted successfully with generated empty roots and the
    neutral pad profile; native retained the frame-60 checkpoint.
- [x] **T-2.3 P0** Record PPSSPP reference checkpoints from boot through title
  idle.
  - Include call traces, module timeline, frame metrics, audio/movie events,
    and expected wall/emulated timing.
  - Done 2026-10-21: a protected 20-second PPSSPP interpreter run with the
    empty fixture and boot profile reaches `init` at vblank 84/present 42 and
    `title` at vblank/present 167. Reduced metadata records 2,333 call edges,
    1,119 targets, 61 HLE functions, controller/audio counts, zero MPEG calls,
    and classified diagnostics; protected logs/traces remain ignored.
- [x] **T-2.4 P0** Run native boot without forced frame-capture exit and reach
  a stable title/menu state.
  - Done 2026-10-21: the empty native fixture plus `mga_boot.pad` reaches init
    and title overlays, remains stable through capture-free present 600, and
    exits through `SR_EXIT_AFTER_PRESENT` with code 0.
- [x] **T-2.5 P0** Fix every unimplemented HLE or dispatch failure encountered
  before title.
  - Done 2026-10-21: the present-600 gate reports zero unimplemented HLEs,
    host crashes, watchdogs, and interpreter stops. Fifty expected
    interpreter fallback targets remain for T-3 native-module conversion.
- [x] **T-2.6 P1** Classify GE commands `0xf0-0xf9` against PPSSPP and add
  focused tests for any required behavior.
  - Done 2026-10-21: PPSSPP identifies the range as immediate-vertex state
    (`VSCX` through `VSCV`), with `VAP` submitting a vertex. The runtime now
    stores all ten words and reports only nonzero unsupported `VAP` draws.
    Metal Gear Acid writes zero initialization values through present 600, so
    the title gate has no remaining `0xf0-0xf9` warnings.
- [x] **T-2.7 P1** Validate memory-stick message behavior for empty, present,
  missing, and existing-save states.
  - Done 2026-10-21: inserted/empty reaches title with eleven missing slots;
    `SR_MEMSTICK_STATE=removed` matches PPSSPP device/FAT values and remains
    on the memory-stick check without probing save paths; a protected valid
    `ULUS10006001` fixture decrypts and loads, remains byte-identical, and
    reaches title with UID `0x17c`.
- [x] **T-2.8 P1** Validate intro PMF video/audio, skip input, teardown, and
  transition to title.
  - Done 2026-10-21: the premise was disproved for the deterministic
    front-end route. PPSSPP reaches title with zero MPEG calls, and native
    reaches title plus 20,000 presentations of the new-game opening with no
    MPEG call. The main image references only card-movie `cdmv%02d.pmf` and
    `no_data.pmf`; mandatory PMF validation remains T-5.3/T-6.7.
- [x] **T-2.9 P1** Validate keyboard and gamepad control through all title
  menus.
  - Done 2026-10-21: START opens the principal menu, DOWN selects LOAD GAME,
    UP returns to NEW GAME, and CIRCLE enters the opening overlay. The same
    logical mappings pass the public keyboard/gamepad test; a live Win32
    keyboard run produced `0x0040`, `0x0010`, and `0x2000` edges while an
    attached gamepad remained enumerated.
- [x] **T-2.10 P1** Add title-idle and menu frame/audio acceptance checks to
  `REPRODUCTION.md`.
  - Done 2026-10-21: `frontend_acceptance.py` checks the three selector
    checkpoints, title fade, init/title/new-game overlay route, scripted
    inputs, exact fallback count, XAudio2 lifecycle, nonzero playback, and
    zero dropped frames, device underruns, and failure markers.
- [x] **T-2.11 P1** Complete three consecutive deterministic title/menu runs
  with no crash, watchdog, unknown HLE, or permissive fallback.
  - Done 2026-10-21: three present-4200 runs passed with 266 identical
    fallback targets and byte-identical captures at presents 3000, 3120,
    3240, and 3360. All used XAudio2, dropped zero blocks, and reported zero
    unimplemented HLEs, crashes, watchdogs, interpreter stops, or permissive
    fallbacks.
  - Revalidated 2026-10-22: runtime-JAL-aware live verification reduces the
    exact set to 56 targets while preserving all four checkpoint images and
    the zero-failure/audio gates across three runs.

## Phase 3 - Native service modules and overlays

- [x] **T-3.1 P0** Add a codegen module/symbol prefix so multiple generated
  PRXs can link into one executable.
  - Done 2026-10-21: `--symbol-prefix` namespaces every generated function,
    dispatch descriptor, and registration symbol; public codegen tests cover
    direct calls and table output.
- [x] **T-3.2 P0** Support multiple immutable dispatch tables with runtime
  activation and deactivation.
  - Done 2026-10-21: the runtime validates sorted immutable tables, rejects
    overlapping active addresses, supports idempotent activation, and removes
    tables explicitly on module unload.
- [x] **T-3.3 P0** Select generated tables by module path, hash, base, and
  active overlay identity.
  - Done 2026-10-21: module policy binds a table only after exact
    case-insensitive path/SHA-1, module name, expected base, and table-range
    checks. Raw-LBN paths distinguish overlays sharing `0x09b43c00`.
- [x] **T-3.4 P0** Generate and link KJFS.
  - Done 2026-10-21: 527/527 functions, zero stubs; KJFS activates at
    `0x09af5800` and removes ten present-600 fallback targets.
- [x] **T-3.5 P0** Generate and link ZLIB; measure decompression speedup and
  restore a conservative fallback step cap.
  - Done 2026-10-21: 121/121 functions, zero stubs; adding native ZLIB to
    native KJFS reduced the measured present-600 run from about 26.8s to
    11.3s. After sound conversion, the parent removed its 100-million override
    and passes at the framework's one-million-step default.
- [x] **T-3.6 P0** Generate and link KCEJ_SOUND and validate all worker
  threads/callbacks.
  - Done 2026-10-21: 904/904 functions, zero stubs; sound activates at
    `0x09b15000`, its worker/callback route reaches title, and present-600
    remains clean at the one-million-step cap.
- [x] **T-3.7 P0** Generate and link the initial and title stage overlays.
  - Done 2026-10-21: init emits 636/636 and title 997/997 functions with zero
    stubs. Live-code verification keeps post-load patched functions
    interpreted while unchanged functions run natively; both overlays render
    correctly and reuse `0x09b43c00`.
- [x] **T-3.8 P1** Generate every overlay observed in the deterministic
  front-end route.
  - Done 2026-10-21: prologue emits 1,091/1,091 functions with zero stubs and
    activates for raw path `disc0:/sce_lbn0x11780_size0x22f8e`.
- [x] **T-3.9 P1** Add overlay address-reuse tests with two modules sharing
  `0x09b43c00`.
  - Done 2026-10-21: public dispatch tests reject simultaneous overlap, then
    deactivate overlay A and activate overlay B at `0x09b43c00`.
- [x] **T-3.10 P1** Record and classify all remaining interpreter fallback
  targets.
  - Done 2026-10-21: module-qualified v2 logs record 266 route targets: 36
    init, 77 title, and 153 prologue.
  - Updated 2026-10-22: safely accepting linker-adjusted runtime JAL targets
    reduces the current set to 56: 6 init, 13 title, and 37 prologue.
- [x] **T-3.11 P1** Set a reviewed release fallback allowlist and fail on new
  targets.
  - Done 2026-10-21: `config/mga_frontend_fallbacks.toml` is checked exactly
    by `fallback_report.py` and `frontend_acceptance.py`; three consecutive
    runs passed with no missing or unexpected target.
  - Updated 2026-10-22: regenerated the exact allowlist from three identical
    56-target runs after live-verifier hardening.
- [x] **T-3.12 P1** Benchmark boot time, host CPU, frame pacing, and dispatch
  misses before and after conversion.
  - Done 2026-10-21: matched present-600 runs improved from
    20,281/19,156 ms wall/CPU to 11,222/10,531 ms. Seven real-time menu
    windows improved from 34.54 to 39.22 average FPS; the worst interval fell
    from 2,187.80 to 271.16 ms.

## Phase 4 - Playable vertical slice

- [ ] **T-4.1 P0** Define the reference route from title through tutorial or
  first mission.
  - Progress 2026-10-21: deterministic broad-button input crosses the
    prologue into `stage/st00/st00.prx`, the first mission overlay. Its exact
    hash/raw-LBN identity and 1,000-function native table are integrated. The
    route now passes 30,000 presentations; the dark briefing's intended
    advance/skip control remains. A verified post-Forest `ULUS10006002` save
    now provides a direct first-mission/gameplay route.
  - Progress 2026-10-22: corrected the load script to keep LOAD GAME selected,
    advance to the map, press UP to select `Lobito Laboratory - Outside Gate`,
    confirm STAGE01, and pass the delayed OK prompt. The route reproducibly
    loads the `0x23200` `st01` overlay at `0x09b6c600`.
- [ ] **T-4.2 P0** Enter a new game and complete initial deck/card setup.
- [ ] **T-4.3 P0** Validate movement, camera, card selection, action execution,
  pause, and cancel/confirm behavior.
- [ ] **T-4.4 P0** Validate combat, enemy turns, damage, failure, and retry on
  the reference route.
- [ ] **T-4.5 P0** Validate every module/stage transition on the route.
  - Progress 2026-10-21: init -> title -> prologue -> st00 is deterministic
    and crash-free through present 30,000.
  - Progress 2026-10-22: the protected post-Forest route adds
    init -> title -> load/map overlay -> st01 with an unchanged save fixture.
- [ ] **T-4.6 P0** Save, exit, restart, load, and resume the route.
  - Progress 2026-10-21: public completion and post-Forest saves decrypt and
    load natively from isolated fixtures. The Forest save reaches two later
    overlays and remains byte-identical; native save creation/resume remains.
- [ ] **T-4.7 P1** Verify the native save loads in PPSSPP and a PPSSPP save
  loads natively.
  - Progress 2026-10-21: GameFAQs #10243 and #8725 are region-verified
    ULUS-10006 fixtures. Cross-emulator save creation remains.
- [ ] **T-4.8 P1** Add representative software-renderer golden checkpoints.
- [ ] **T-4.9 P1** Audit imports, computed dispatch, and fallback coverage for
  the complete route.
  - Progress 2026-10-21: st00 has zero trapping stubs and the current extended
    route records 423 module-qualified interpreter targets. Review and exact
    allowlisting remain.
- [ ] **T-4.10 P1** Complete a 30-minute vertical-slice stability run.
- [ ] **T-4.11 P1** Repeat the clean-memstick route three times without an
  unknown HLE, host crash, deadlock, or permissive fallback.

## Phase 5 - Full single-player validation

- [ ] **T-5.1 P0** Create a checklist for every extracted stage, intermission,
  ending, epilogue, suspend-save, and title overlay.
- [ ] **T-5.2 P0** Validate every mandatory campaign stage and transition.
- [ ] **T-5.3 P0** Validate every mandatory cutscene and PMF sequence.
- [ ] **T-5.4 P0** Complete ending and credits.
- [ ] **T-5.5 P1** Validate card/deck progression, inventory, options, and
  unlock flows used by single player.
- [ ] **T-5.6 P1** Validate new, mid-game, completed, missing, and corrupted
  save behavior.
- [ ] **T-5.7 P1** Validate suspend-save creation, resume, and cleanup.
- [ ] **T-5.8 P1** Validate game-over, retry, quit-to-title, and repeated
  new-game/load cycles.
- [ ] **T-5.9 P1** Identify network/ad-hoc actions and provide explicit
  unsupported/offline behavior.
- [ ] **T-5.10 P1** Verify a completed native campaign save with PPSSPP.

## Phase 6 - Renderer, audio, performance, and soak

- [ ] **T-6.1 P0** Build software golden checkpoints covering geometry,
  blending, depth, stencil, texture formats, framebuffer effects, text, and
  movies.
- [x] **T-6.2 P0** Enable and validate the D3D12 renderer for Metal Gear Acid.
  - Done 2026-10-21: added the `clang-cl-d3d12` preset, validated the exact
    title/menu/prologue route at 1x, and passed the same functional frame,
    input, audio, module, and fallback acceptance gate.
- [ ] **T-6.3 P0** Compare D3D12 output against software goldens at native
  resolution.
  - Progress 2026-10-21: all four title checkpoints are visually correct and
    pass semantic metrics. They are not pixel-identical: title frames have
    maximum channel deltas of 18-25 with about 13.6% of pixels above delta 8;
    the transition has maximum delta 9.
- [x] **T-6.4 P1** Validate supported internal resolutions and presentation
  layouts.
  - Done 2026-10-22: every D3D12 scale from 1x through 8x passes the exact
    front-end functional gate. The selected STAGE01 route passes at 1x, 2x,
    4x, and 8x. Full-resolution capture, subpixel/box-filter analysis, VRS
    on/off comparisons, and native/letterbox/portrait layout tests are
    recorded in MGA-F-051 and MGA-F-052.
- [x] **T-6.5 P1** Resolve or document GE commands `0xf0-0xf9`.
  - Done 2026-10-21: MGA-F-022 classifies the range as immediate-vertex
    state; zero initialization is supported and nonzero VAP submission fails
    explicitly.
- [ ] **T-6.6 P1** Validate frame pacing through menus, movies, gameplay, and
  loading.
  - Progress 2026-10-21: the D3D12 title/prologue acceptance route completes
    in 13.9s with real-time pacing enabled for its final 900 presentations.
    Gameplay, PMF, and longer loading transitions remain.
  - Progress 2026-10-22: structured CSV timing now reports p50/p95/p99,
    over-budget intervals, backend cost, and fenced D3D12 GPU timestamps.
    Three-run front-end and STAGE01 matrices cover 1x, 2x, 4x, and 8x; GPU
    work remains at or below 2.06 ms on the measured routes. Movies and
    full-stage loading/steady-state pacing remain.
- [ ] **T-6.7 P1** Validate XAudio2 latency, SAS/ATRAC behavior, underruns, and
  movie synchronization.
  - Progress 2026-10-21: blocking output retains three guest buffers or two
    device queues. Device-only padding does not advance the mixer; load-gap
    resume prebuffers 4,096 real frames and fades boundaries at fixed
    44.1 kHz. Acceptance reports one transition, seven padding blocks,
    `resynced=3072`, `underruns=0`, and `dropped=0`. The Forest map-load
    transition is much improved and mission audio is clean. Campaign
    ATRAC/SAS and PMF synchronization remain.
- [ ] **T-6.8 P1** Profile and remove remaining release-critical interpreter
  and HLE hot spots.
  - Progress 2026-10-21: live-code-mismatched generated functions are marked
    interpreter-only by function identity, preventing recursive
    interpreter/native wrapper bounce. A 50,000-presentation
    init/title/prologue route exits cleanly with no host crash or interpreter
    stop. Native handoff depth is now capped at 256; deeper execution uses a
    scheduler-aware interpreter with chunked budgets, avoiding fiber-stack
    growth on the extended st00 route.
  - Progress 2026-10-22: aggregate interpreter profiles replace unique-target
    guesses with call/instruction counts. Two entries represent about 56% of
    front-end interpreted work. On the post-Forest route,
    `st01/0x09b6effc` represents 21,855,537 instructions, or 81.15% of the
    26,931,234 interpreted total. Whole-generated-code `/O2` was rejected at
    a 0.96% median gain.
  - Progress 2026-10-22: native STAGE01 plus runtime-JAL-aware live
    verification reduces the matched route from 25,835,871 to 3,743,963
    interpreted instructions per run (85.51%) and the median route wall time
    from 53,278 to 18,786 ms.
- [ ] **T-6.9 P1** Run repeated stage-transition and save/load soak tests.
  - Progress 2026-10-21: completion and post-Forest fixtures load without
    mutation; the Forest route reaches two later overlays and exits normally.
  - Progress 2026-10-22: twelve isolated post-Forest runs (three each at 1x,
    2x, 4x, and 8x) load STAGE01 and leave each fixture byte-identical. One
    2x timing sample contained a 52.2-second host scheduling outlier; the
    other runs and GPU timestamps did not reproduce it.
- [ ] **T-6.10 P1** Run a complete-campaign soak while monitoring memory,
  handles, callbacks, and thread count.
- [ ] **T-6.11 P2** Validate focus changes, minimize/restore, controller
  hot-plug, and multi-monitor behavior.
- [x] **T-6.12 P0** Add a live framerate diagnostic and remove
  front-end-critical software-renderer waste.
  - Done 2026-10-21: `SR_FPS_COUNTER=1` reports rolling FPS/frame time in GDI,
    Vulkan, and D3D12 titles. Exact bilinear fast paths, through-mode
    specialization, and a per-primitive decoded-texel cache keep all software
    checkpoint hashes unchanged while raising measured pacing from 39.22 to
    46.35 FPS. D3D12 reaches 162.55 FPS host presentation throughput.
- [x] **T-6.13 P1** Generate, live-verify, and activate the native STAGE01
  overlay.
  - Identity: `stage/st01/st01.prx`, SHA-1
    `9dfc231f933ef0d508ad7763f74fb6d857581e66`, runtime base `0x09b6c600`.
  - Acceptance: preserve the corrected route/captures and save fixture, retain
    explicit fallback identity for live-code mismatches, and materially reduce
    the 26.9-million-instruction interpreter total.
  - Done 2026-10-22: 1,351/1,351 functions generate with zero stubs and bind
    by exact path/hash/base. Three matched native runs preserve both captures
    byte-for-byte and leave each save fixture unchanged. Interpreted
    instructions fall by 85.51%, fallback targets from 139 to 110, and all
    failure/audio gates remain clean.
- [ ] **T-6.14 P2** Replace unsafe serialized D3D12 pipeline-library
  persistence with validated per-PSO caching or remove the experimental path.
  - `SR_D3D12_PSO_CACHE` reuse removed the validation GPU on the second
    process. Normal in-memory async PSOs remain active; disk reuse now requires
    `SR_D3D12_UNSAFE_PSO_CACHE=1`.

## Phase 7 - CI and source release

- [ ] **T-7.1 P0** Add public CI for Python tests, synthetic runtime tests,
  content audit, and runtime-only clang-cl build.
  - Progress 2026-10-22: parent CTest now exposes graphics-configuration and
    D3D12 vertex/state/layout tests in addition to the existing runtime set;
    structured-performance, interpreter-profile, and scaling-capture parent
    tools have unit coverage. CI wiring remains.
- [ ] **T-7.2 P0** Add protected CI for verified extraction, codegen, full
  native build, trace checks, and frame metrics.
- [ ] **T-7.3 P0** Run a clean recursive clone/build/run from a separate path.
- [ ] **T-7.4 P0** Audit tracked files and release archives for game-derived
  data.
- [ ] **T-7.5 P0** Pin reviewed parent and fork commits.
- [ ] **T-7.6 P1** Complete GPL and third-party provenance review.
- [ ] **T-7.7 P1** Finalize user build, controls, configuration,
  troubleshooting, and known-limitations documentation.
- [ ] **T-7.8 P1** Update every document in `docs/` to match release behavior.
- [ ] **T-7.9 P1** Produce and verify a deterministic source-only archive.
- [ ] **T-7.10 P1** Tag the release only after every milestone exit gate and
  release-blocking TODO item passes.

## Continuous maintenance

- [ ] **T-C.1 P0** At the end of every work session, update this file's
  statuses, evidence, blockers, priorities, and current focus.
- [ ] **T-C.2 P0** Update `FINDINGS.md` whenever evidence changes an
  understanding of game or framework behavior.
- [ ] **T-C.3 P0** Update `UPSTREAM.md` whenever a framework item changes
  design, priority, local status, commit, or upstream state.
- [ ] **T-C.4 P0** Update `REPRODUCTION.md` whenever commands, environment
  variables, expected output, metrics, or validation thresholds change.
- [ ] **T-C.5 P0** Update `PLAN.md` whenever scope, dependencies, milestones,
  or exit gates change.
- [ ] **T-C.6 P0** Update the root `README.md` and `docs/README.md` whenever
  user-visible status or the document set changes.
- [ ] **T-C.7 P0** Keep game-derived binaries, saves, traces, dumps, generated
  C, and captures ignored and out of release archives.
- [ ] **T-C.8 P1** Keep protected Metal Gear Acid checks and generic public
  framework tests distinct.
