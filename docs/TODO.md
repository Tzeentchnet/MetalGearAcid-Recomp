# Project TODO

Last updated: 2026-10-21

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

1. **T-1.6** separate entry-thread UID from next UID;
2. **T-2.1** create deterministic PPSSPP/native boot input scripts;
3. **T-1.4** expand VFPU7 coverage to executable semantic vectors;
4. **T-1.5** carry `(library, NID)` through all dispatch paths;
5. **T-1.7** audit PPSSPP/native UID allocation through first stage load.

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
  - Done 2026-10-21: 46,628 relocations, 9,913/9,913 functions, zero stubs.
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
    `51aa462`; codegen/import/VFPU7 work committed as `1225147`; the parent
    submodule is pinned to `1225147`.
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
- [ ] **T-1.4 P1** Expand VFPU7 tests from emitted-text checks to executable
  semantic vectors.
  - Cover prefix behavior, clamping, odd vector sizes, packing, masks, and
    saturation.
- [ ] **T-1.5 P1** Carry `(library, NID)` through generated imports, runtime
  syscall bindings, guest export lookup, and diagnostics.
- [ ] **T-1.6 P0** Add separate standalone-boot fields for existing entry
  thread UID and next allocatable UID.
  - Oracle: current `0x113`, next `0x114`.
- [ ] **T-1.7 P1** Audit PPSSPP/native UID sequences through first stage load
  and model kernel objects that affect game-visible handles.
- [ ] **T-1.8 P1** Replace the `sce*` module-name heuristic with a per-title
  module policy keyed by path, name, and hash.
- [ ] **T-1.9 P1** Implement variable imports or reject them during module load
  with library/NID/module context.
- [ ] **T-1.10 P1** Split PRX parsing/relocation from module-manager kernel
  policy.
- [ ] **T-1.11 P1** Add protected Metal Gear Acid and Killzone regression
  smoke tests for every upstream fork batch.
- [ ] **T-1.12 P1** Upstream accepted generic changes and update
  `UPSTREAM.md` status and parent submodule pin.

## Phase 2 - Deterministic front end

- [ ] **T-2.1 P0** Create deterministic PPSSPP and native input scripts for
  boot, logo skip where supported, title idle, and menu navigation.
- [ ] **T-2.2 P0** Define isolated empty and existing-save memstick fixtures.
  - Fixtures remain protected/local; commit only generators or metadata.
- [ ] **T-2.3 P0** Record PPSSPP reference checkpoints from boot through title
  idle.
  - Include call traces, module timeline, frame metrics, audio/movie events,
    and expected wall/emulated timing.
- [ ] **T-2.4 P0** Run native boot without forced frame-capture exit and reach
  a stable title/menu state.
- [ ] **T-2.5 P0** Fix every unimplemented HLE or dispatch failure encountered
  before title.
- [ ] **T-2.6 P1** Classify GE commands `0xf0-0xf9` against PPSSPP and add
  focused tests for any required behavior.
- [ ] **T-2.7 P1** Validate memory-stick message behavior for empty, present,
  missing, and existing-save states.
- [ ] **T-2.8 P1** Validate intro PMF video/audio, skip input, teardown, and
  transition to title.
- [ ] **T-2.9 P1** Validate keyboard and gamepad control through all title
  menus.
- [ ] **T-2.10 P1** Add title-idle and menu frame/audio acceptance checks to
  `REPRODUCTION.md`.
- [ ] **T-2.11 P1** Complete three consecutive deterministic title/menu runs
  with no crash, watchdog, unknown HLE, or permissive fallback.

## Phase 3 - Native service modules and overlays

- [ ] **T-3.1 P0** Add a codegen module/symbol prefix so multiple generated
  PRXs can link into one executable.
- [ ] **T-3.2 P0** Support multiple immutable dispatch tables with runtime
  activation and deactivation.
- [ ] **T-3.3 P0** Select generated tables by module path, hash, base, and
  active overlay identity.
- [ ] **T-3.4 P0** Generate and link KJFS.
- [ ] **T-3.5 P0** Generate and link ZLIB; measure decompression speedup and
  restore a conservative fallback step cap.
- [ ] **T-3.6 P0** Generate and link KCEJ_SOUND and validate all worker
  threads/callbacks.
- [ ] **T-3.7 P0** Generate and link the initial and title stage overlays.
- [ ] **T-3.8 P1** Generate every overlay observed in the deterministic
  front-end route.
- [ ] **T-3.9 P1** Add overlay address-reuse tests with two modules sharing
  `0x09b43c00`.
- [ ] **T-3.10 P1** Record and classify all remaining interpreter fallback
  targets.
- [ ] **T-3.11 P1** Set a reviewed release fallback allowlist and fail on new
  targets.
- [ ] **T-3.12 P1** Benchmark boot time, host CPU, frame pacing, and dispatch
  misses before and after conversion.

## Phase 4 - Playable vertical slice

- [ ] **T-4.1 P0** Define the reference route from title through tutorial or
  first mission.
- [ ] **T-4.2 P0** Enter a new game and complete initial deck/card setup.
- [ ] **T-4.3 P0** Validate movement, camera, card selection, action execution,
  pause, and cancel/confirm behavior.
- [ ] **T-4.4 P0** Validate combat, enemy turns, damage, failure, and retry on
  the reference route.
- [ ] **T-4.5 P0** Validate every module/stage transition on the route.
- [ ] **T-4.6 P0** Save, exit, restart, load, and resume the route.
- [ ] **T-4.7 P1** Verify the native save loads in PPSSPP and a PPSSPP save
  loads natively.
- [ ] **T-4.8 P1** Add representative software-renderer golden checkpoints.
- [ ] **T-4.9 P1** Audit imports, computed dispatch, and fallback coverage for
  the complete route.
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
- [ ] **T-6.2 P0** Enable and validate the D3D12 renderer for Metal Gear Acid.
- [ ] **T-6.3 P0** Compare D3D12 output against software goldens at native
  resolution.
- [ ] **T-6.4 P1** Validate supported internal resolutions and presentation
  layouts.
- [ ] **T-6.5 P1** Resolve or document GE commands `0xf0-0xf9`.
- [ ] **T-6.6 P1** Validate frame pacing through menus, movies, gameplay, and
  loading.
- [ ] **T-6.7 P1** Validate XAudio2 latency, SAS/ATRAC behavior, underruns, and
  movie synchronization.
- [ ] **T-6.8 P1** Profile and remove remaining release-critical interpreter
  and HLE hot spots.
- [ ] **T-6.9 P1** Run repeated stage-transition and save/load soak tests.
- [ ] **T-6.10 P1** Run a complete-campaign soak while monitoring memory,
  handles, callbacks, and thread count.
- [ ] **T-6.11 P2** Validate focus changes, minimize/restore, controller
  hot-plug, and multi-monitor behavior.

## Phase 7 - CI and source release

- [ ] **T-7.1 P0** Add public CI for Python tests, synthetic runtime tests,
  content audit, and runtime-only clang-cl build.
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
