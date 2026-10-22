# Project completion plan

This plan defines how Metal Gear Acid progresses from the current bootable
hybrid recompilation to a reproducible, validated Windows release.

Execution is tracked in [TODO.md](TODO.md). Technical facts belong in
[FINDINGS.md](FINDINGS.md), framework work in [UPSTREAM.md](UPSTREAM.md), and
commands and measurable checks in [REPRODUCTION.md](REPRODUCTION.md).

## Current baseline

As of 2026-10-22:

- the supported ULUS-10006 v1.00 disc is pinned and extracted reproducibly;
- the `mgp_main` PRX generates 9,914 functions with zero trapping stubs;
- a release clang-cl Windows executable builds successfully;
- plaintext runtime modules load, relocate, link, start, and unload;
- private KJFS, ZLIB, sound, and stage exports execute through interpreter
  fallback;
- hybrid callbacks from interpreted modules into static main code work;
- software GE, XAudio2, VFPU tables, PGF fonts, and input initialize;
- deterministic runs navigate the title menu and enter the new-game opening;
- empty, removed, and existing-save memory-stick states are validated; and
- KJFS, ZLIB, sound, init, title, prologue, st00, and st01 have generated
  native tables;
- post-load-patched overlay functions use a reviewed, module-qualified hybrid
  allowlist rather than whole-module interpretation; and
- an opt-in window-title counter reports rolling FPS/frame time on every
  renderer;
- optimized software rendering remains pixel-exact at the four title gates,
  and D3D12 passes the same functional front-end acceptance route; and
- D3D12 scales 1x-8x pass the front-end gate, while 1x/2x/4x/8x also load the
  selected post-Forest STAGE01 route with low measured GPU cost; and
- runtime-JAL-aware live verification keeps linker-adjusted calls native while
  genuine code mismatches retain module-qualified fallback; and
- native STAGE01 reduces matched route interpreter work by 85.51% with exact
  frame parity; and
- gameplay, card PMFs, save creation, broader D3D12 scaling/golden coverage,
  campaign performance, and full-game stability are not yet validated.

## Definition of done

The project is release-ready when all of the following are true:

1. **Reproducible source-only build**
   - A clean recursive clone plus a user-supplied supported ISO can extract,
     generate, configure, build, and run using documented commands.
   - No game executable, generated game C, disc data, save, trace, memory dump,
     or frame capture is committed or packaged.
2. **Complete single-player behavior**
   - Boot, logos, intro, title, menus, options, new game, load game, tutorial,
     every campaign stage, cutscenes, ending, and credits complete.
   - Suspend/resume and normal PSP-compatible save/load behavior work.
3. **Platform behavior**
   - Keyboard and SDL gamepad input are usable and configurable.
   - Audio, ATRAC/SAS, and MPEG/PMF playback are synchronized and stable.
   - Windowing, fullscreen, focus, and clean exit work on Windows 10/11 x64.
4. **Rendering correctness**
   - The software renderer matches PPSSPP reference checkpoints closely enough
     to diagnose semantic differences.
   - The primary hardware renderer matches approved software golden frames at
     native resolution and supported scaling factors.
5. **Performance and stability**
   - Performance meets or exceeds the original PSP pacing on the supported
     baseline PC without sustained interpreter bottlenecks.
   - No unbounded memory growth, deadlock, host crash, or unreviewed permissive
     HLE path occurs in long runs.
6. **Dispatch and HLE accountability**
   - Every observed import and computed target is implemented, statically
     compiled, or present on an explicit reviewed fallback allowlist.
   - Release validation runs with permissive fallback disabled.
7. **Framework quality**
   - Generic improvements are tested with synthetic fixtures and integrated
     into the maintained `psp-recomp` fork.
   - Game-specific policy remains in this parent project.
8. **Release engineering**
   - CI, content audit, licenses, credits, documentation, clean-clone testing,
     and a source-only release checklist pass.

Original online infrastructure and PSP ad-hoc multiplayer are not release
requirements unless scope is explicitly expanded later. They must fail
clearly rather than appear to work.

## Guiding principles

1. Use PPSSPP interpreter behavior as the oracle before optimizing.
2. Prove behavior in the software renderer before debugging hardware output.
3. Fix root causes in the generic fork when evidence is not title-specific.
4. Keep title hashes, addresses, module policy, and validation scripts in this
   project.
5. Do not return fake success for unsupported behavior in release mode.
6. Prefer deterministic captures, scripts, and thresholds over visual
   impressions.
7. Preserve a working checkpoint while replacing interpreter paths with
   generated native modules.
8. Update the TODO and affected documentation in the same change as the code.

## Milestones

| Milestone | Status | Exit gate |
|---|---|---|
| M0 - Reproducible boot baseline | Done | Verified build reaches visible game content with zero main-module stubs. |
| M1 - Framework hardening | Active | Module/codegen/scheduler changes have synthetic tests and are organized for upstream integration. |
| M2 - Deterministic front end | Done | Three scripted native runs reproduce the same title/menu/new-game checkpoints with no unknown HLE, crash, watchdog, or permissive fallback. |
| M3 - Native runtime modules | Done | Boot-critical services and all deterministic front-end overlays activate generated tables; patched-function fallback is module-qualified and exact-allowlisted. |
| M4 - Playable vertical slice | Active | New game through tutorial or first mission is playable, savable, reloadable, and repeatable. |
| M5 - Full single-player validation | Pending | All campaign stages, movies, saves, transitions, ending, and credits pass. |
| M6 - Renderer/performance parity | Pending | Hardware rendering, scaling, frame pacing, audio timing, and soak gates pass. |
| M7 - Source release | Pending | CI, content audit, clean clone, documentation, licensing, and release checklist pass. |

## Phase 0 - Reproducible boot baseline

Status: complete.

Delivered:

- disc and file identity configuration;
- extraction of the main and plaintext runtime PRXs;
- main-module relocation, imports, function inventory, and split codegen;
- Windows clang-cl build and runtime resource packaging;
- PPSSPP entry-state capture;
- dynamic PRX loading and guest-export dispatch;
- hybrid callback import patching;
- the required VFPU7 conversions and callback-aware vblank HLE;
- frame 60 and frame 300 smoke checks; and
- initial findings, upstream, and reproduction documentation.

Gate evidence is recorded in [FINDINGS.md](FINDINGS.md) and
[REPRODUCTION.md](REPRODUCTION.md).

## Phase 1 - Harden and upstream the framework

Goal: convert the successful game-driven prototype into maintainable generic
framework behavior.

Work:

1. Organize changes into focused commits in the `psp-recomp` fork.
2. Add synthetic PRX tests for loader validation, relocation, import patching,
   export activation, module start, unload, and overlay base reuse.
3. Add direct interpreter/HLE tests for delay-slot syscalls, nested return
   targets, hybrid callbacks, and unknown runtime syscall codes.
4. Replace the `sce*` HLE-replacement heuristic with explicit per-title module
   policy.
5. Make entry-thread UID and next allocatable UID independent.
6. Audit UID drift and decide which internal kernel objects need modeling.
7. Implement variable-import handling or explicit load-time rejection.
8. Carry `(library, NID)` through static and runtime dispatch.
9. Run all generic tests plus protected Metal Gear Acid and Killzone smoke
   checks before moving the parent submodule pin.

Exit gate:

- every local P0 framework change in [UPSTREAM.md](UPSTREAM.md) has a synthetic
  regression test;
- no framework test relies on copyrighted game data;
- both known game projects retain their measured smoke checkpoints; and
- the parent repository pins a reviewed fork commit rather than depending on
  uncommitted submodule changes.

## Phase 2 - Reach a deterministic front end

Goal: boot through logos and intro into an idle, controllable title/menu state.

Status: complete.

Delivered:

- inserted, removed, empty-save, and existing-save memory-stick coverage;
- a corrected START/DOWN/UP/CIRCLE title-menu route;
- nested interpreted-to-native dispatch and interpreted VFPU coverage needed
  by the title and new-game overlays;
- exact presentation captures and title selector acceptance metrics;
- a real-time XAudio2 functional gate; and
- three consecutive deterministic runs with identical checkpoint images.

The expected "intro PMF" is not present on this route. Both the PPSSPP title
oracle and a native 20,000-presentation new-game opening run make zero MPEG
calls. Card/campaign PMFs remain in Phase 5 and audio/video synchronization
remains in Phase 6.

Work:

1. Create a deterministic PPSSPP pad script and matching native input script.
2. Use isolated, known-empty memstick roots for new-user and existing-save
   cases.
3. Record PPSSPP call traces, frame checkpoints, module transitions, and
   protected logs through title idle.
4. Run native boot without `SR_FBDUMP` forced exit and fix the first concrete
   HLE, scheduler, module, audio, or GE divergence each iteration.
5. Classify GE commands `0xf0-0xf9` using PPSSPP behavior before implementing
   them.
6. Validate memory-stick dialogs, logo timing, input acceptance, menu
   navigation, and clean exit.
7. Validate any intro PMF path for video, audio, skip input, and teardown.

Exit gate:

- at least three consecutive clean runs reach the same idle title/menu state;
- no unimplemented NID, host crash, watchdog hang, or unbounded fallback
  occurs;
- scripted input can enter and leave the principal menus; and
- software-renderer checkpoints and timing tolerances are recorded in
  [REPRODUCTION.md](REPRODUCTION.md).

## Phase 3 - Native runtime modules and overlays

Goal: remove interpreter cost from normal boot and gameplay.

Status: complete for the deterministic front-end route.

Delivered:

- unique generated symbols and immutable dispatch descriptors per PRX;
- collision-checked activation/deactivation tied to exact module identity and
  expected load base;
- native KJFS (527 entries), ZLIB (121), and sound (904);
- native init (636), title (997), and prologue (1,091) overlays;
- live-code verification for title-owned post-load relocations, with only
  mutated functions falling back;
- a reviewed exact allowlist of 56 module-qualified overlay targets;
- same-base init/title/prologue activation coverage; and
- restored one-million-instruction fallback cap plus before/after wall, CPU,
  and real-time pacing benchmarks.

Matched present-600 runs reduced wall time from 20.281s to 11.222s and host
CPU time from 19.156s to 10.531s. Seven real-time menu windows improved from
34.54 to 39.22 FPS average, while the worst transition interval fell from
2.188s to 0.271s.

Work:

1. Give generated modules unique symbol/registration prefixes.
2. Support multiple immutable dispatch tables.
3. Activate a generated table only when module path, hash, base, and policy
   match.
4. Deactivate overlay tables on unload and support a different module at the
   same guest address.
5. Generate and link KJFS, ZLIB, sound, the initial stage, title stage, and
   every subsequently observed overlay.
6. Retain interpreter fallback for discovery, with logging and a reviewed
   allowlist.
7. Measure boot time, fallback targets, and host CPU time before and after each
   module conversion.

Exit gate:

- boot to title performs no sustained whole-module interpretation;
- every expected module load selects the correct generated table;
- overlay unload/reload is deterministic; and
- performance is adequate for real-time front-end validation on the baseline
  machine.

## Phase 4 - Playable vertical slice

Goal: prove the complete game loop through a bounded section of play.

Scope:

- title and new-game flow;
- tutorial or first mission;
- cards/deck setup needed by that flow;
- movement, camera, selection, menus, pause, and combat;
- audio, stage loading, transitions, and cutscenes encountered;
- save, exit, restart, and reload.

Work:

1. Define a deterministic input route and PPSSPP reference save.
2. Capture checkpoints at scene transitions and representative gameplay.
3. Audit computed dispatch and HLE coverage for the entire route.
4. Validate save data compatibility in both directions with PPSSPP.
5. Run a 30-minute stability session with diagnostics disabled except explicit
   error reporting.

Exit gate:

- the route completes three times from a clean memstick;
- save/reload resumes at the expected state;
- no unknown dispatch, permissive HLE, deadlock, or host crash occurs; and
- visible/audio differences are documented and triaged.

## Phase 5 - Full single-player validation

Goal: validate every supported game path.

Work:

1. Build a stage/overlay inventory from the extracted stage tree.
2. Track each campaign stage, intermission, ending, epilogue, suspend-save, and
   title overlay in [TODO.md](TODO.md).
3. Validate all mandatory movies and audio paths.
4. Validate deck/card progression, settings, load/save slots, suspend data,
   game over/retry, and ending/credits.
5. Test a new save, mid-game saves, completed save, and corrupted/missing save
   behavior.
6. Record any unreachable legacy network action and provide an explicit
   offline result.

Exit gate:

- every single-player stage and mandatory transition is checked;
- the ending and credits complete;
- no release-blocking item remains in the phase checklist; and
- a full campaign save can be loaded by PPSSPP.

## Phase 6 - Renderer, audio, performance, and soak

Goal: turn functional correctness into a stable native PC experience.

Progress: the opt-in FPS counter works on every presenter, the software
front-end remains pixel-exact while improving from 39.22 to 46.35 FPS, and the
dedicated D3D12 preset passes the deterministic title/menu/prologue route at
1x with 162.55 FPS host presentation throughput. All configured scales 1x-8x
now pass that functional route; 1x/2x/4x/8x load STAGE01, and GPU timestamp
work remains at or below 2.06 ms on the measured routes. Native STAGE01 now
removes 85.51% of the matched route's interpreted instructions.
PSP-quantized hardware sampling, movies, broader gameplay/audio
synchronization, and soak coverage remain.

Work:

1. Establish software-renderer golden checkpoints for each rendering feature
   class.
2. Enable and validate the preferred D3D12 path for Metal Gear Acid.
3. Compare color, depth, blending, stencil, texture, framebuffer-feedback, and
   presentation behavior at native resolution.
4. Validate supported internal scaling without changing PSP-visible
   framebuffer semantics.
5. Profile remaining interpreted targets and HLE hot spots.
6. Validate audio latency, underruns, movie synchronization, focus behavior,
   controller hot-plug, and frame pacing.
7. Run menu idle, gameplay, repeated stage transition, save/load, and
   full-campaign soak tests.

Exit gate:

- hardware golden comparisons are within documented tolerances;
- no sustained audio underrun or frame-pacing regression remains;
- no leak or handle growth appears in soak runs; and
- performance meets the supported baseline target.

## Phase 7 - CI and source release

Goal: publish a legally clean, reproducible source release.

Work:

1. Add public tests that need no game data.
2. Add protected/self-hosted checks for extraction, generation, native build,
   trace checks, and frame metrics.
3. Audit tracked files and release archives for game-derived content.
4. Verify a clean recursive clone on a separate path or machine.
5. Pin reviewed submodule commits.
6. Complete license and provenance review.
7. Finalize user build, controller, troubleshooting, and known-limitations
   documentation.
8. Tag and build the source-only release artifact.

Exit gate:

- public and protected CI pass;
- clean-clone reproduction passes;
- content and license audits pass;
- all release-blocking TODO items are complete; and
- the [root README](../README.md), [FINDINGS.md](FINDINGS.md),
  [UPSTREAM.md](UPSTREAM.md), and [REPRODUCTION.md](REPRODUCTION.md) match the
  shipped behavior.

## Validation ladder

Use the smallest rung that proves a change, then advance only as needed:

1. Python/unit test.
2. Runtime compile-only target.
3. Full native build.
4. One-function PPSSPP/native trace.
5. Bounded call or scheduler trace.
6. Frame metric/capture checkpoint.
7. Scripted front-end route.
8. Playable vertical slice.
9. Full-stage route.
10. Soak or complete campaign.

Release-mode validation must not use:

- `SR_PERMISSIVE`;
- `SR_DISPATCH_PERMISSIVE`;
- success-shaped unknown-module handling; or
- ignored trapping stubs.

## Upstream workflow

For each generic framework improvement:

1. Reduce the game observation to a title-neutral requirement.
2. Add a synthetic failing test in the fork.
3. Implement the smallest generic fix.
4. Run the complete fork test suite.
5. Run the protected Metal Gear Acid smoke gate.
6. Run the corresponding Killzone regression gate.
7. Update [UPSTREAM.md](UPSTREAM.md) from `Local` or `Proposed` to the actual
   state.
8. Commit the fork change, then update the parent submodule pin.

Do not mix title addresses, hashes, or behavior patches into a generic fork
commit.

## Documentation maintenance contract

Documentation updates are part of task completion, not follow-up cleanup.

| Change | Required documents |
|---|---|
| New measured technical fact | `FINDINGS.md` |
| Framework design, priority, or upstream status | `UPSTREAM.md` |
| Command, environment variable, expected output, or threshold | `REPRODUCTION.md` |
| Milestone, scope, dependency, or release gate | `PLAN.md` |
| Task begins, completes, blocks, or changes priority | `TODO.md` |
| User-visible status, requirements, or run instructions | root `README.md` |
| Document added/removed or evidence policy changed | `docs/README.md` |
| Disc/module identity changes | `config/mga.toml`, `FINDINGS.md`, and `REPRODUCTION.md` |

Before marking any TODO item complete:

1. attach the validation command or evidence in its completion note;
2. update every applicable document from the table above;
3. verify relative Markdown links;
4. run `git diff --check`;
5. confirm no game-derived file became tracked; and
6. leave the next ready P0 item visible in the TODO's current-focus section.

At the end of every work session, [TODO.md](TODO.md) must reflect reality:

- active work is marked in progress;
- completed work is checked with date and evidence;
- blocked work names its blocker;
- newly discovered work is added with priority and dependency; and
- milestone status in this plan is updated if an exit gate changed.

## Principal risks

| Risk | Mitigation |
|---|---|
| Overlay modules reuse addresses | Activate dispatch by module identity and unload state, not address alone. |
| Interpreter hides performance issues | Measure fallback targets and convert hot modules before long validation. |
| UID drift changes game behavior | Compare oracle UID sequences and model required kernel objects explicitly. |
| Unknown GE commands are blamed prematurely | Use traces and isolated command tests before implementation. |
| HLE returns fake success | Keep permissive paths off in gates and surface unsupported behavior. |
| Renderer fixes regress another title | Maintain software goldens and run Killzone regression checks. |
| Save changes corrupt PSP data | Keep PPSSPP round-trip fixtures and back up local saves. |
| Copyrighted payload enters Git | Run tracked-content audits and keep all protected artifacts ignored. |
| Documentation becomes stale | Enforce the maintenance contract in every TODO completion and review. |
