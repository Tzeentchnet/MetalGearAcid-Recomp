# Project status

Last updated: 2026-10-24

Milestone definitions and release gates are maintained in [PLAN.md](PLAN.md).
Ready and blocked work is tracked internally.

## Current status

- The supported ISO is pinned by size and SHA-1.
- The plaintext `mgp_main` PRX is extracted reproducibly.
- The main module relocates at `0x08804000`, enters at `0x0880432c`, and
  contains 9,914 generated entry points with no trapping stubs.
- PPSSPP oracle capture confirms the initial argument, 256 KiB start-thread
  stack, next UID, and initial GE list ID.
- Plaintext runtime PRXs are loaded, relocated, linked to HLE, and executed
  through interpreter fallback. This covers `kjfs`, `zlibdec`, `sound`, and
  stage overlays; Sony media modules use the fork's native HLE replacements.
- Native software rendering, XAudio2, VFPU tables, fonts, mixed
  interpreted/native callbacks, keyboard input, and gamepad mappings are
  active.
- Three deterministic runs navigate NEW GAME/LOAD GAME, return to NEW GAME,
  and enter the opening story overlay with identical software-renderer
  checkpoints and no crash, watchdog, unknown HLE, or permissive fallback.
- Empty, removed, and existing-save memory-stick states are validated. Card
  PMFs, save creation, and the full campaign are not yet validated. Verified
  completion and post-Forest ULUS-10006 fixtures provide direct gameplay
  routes without replaying the scripted opening.
- KJFS, ZLIB, sound, init, title, prologue, st00, and st01 activate generated
  native dispatch tables. STAGE01 adds 1,351 generated entries. Functions
  genuinely changed by the game's post-load overlay linker fall back with
  module-qualified identity; runtime-JAL target changes remain native and
  dispatch through the live guest word.
- Native conversion reduced the matched present-600 wall/CPU benchmark by
  about 45%. Pixel-exact software-renderer optimizations raise the measured
  menu/prologue route from 39.2 to 46.4 FPS, while the accepted D3D12 route
  reaches about 162.6 FPS host presentation throughput on the validation PC.
- Every D3D12 scale from 1x through 8x passes the front-end gate, and
  1x/2x/4x/8x load the selected post-Forest STAGE01 route.
- The default executable exposes the same graphics controls as the MGA2
  recomp: Automatic/D3D12/software/Vulkan selection, D3D12 1x-8x internal
  resolution, 1x-5x xBRZ texture scaling on both hardware backends,
  Balanced/Full-resolution D3D12 shading, and F11 desktop fullscreen.
- The Win32 GDI baseline, Vulkan presenter with software GE, and full Vulkan
  GE backend all pass the deterministic front-end functional/audio/fallback
  gate. The Vulkan presenter preserves software captures exactly.
- D3D12 and Vulkan use PSP-quantized nearest/bilinear sampling by default.
  Integer texture-function/fog math and native-format D3D12 logical captures
  reduce title pixels above delta 8 to 0.28-0.33% on D3D12 and 1.97-2.03% on
  Vulkan. At least 99.7% of those remaining pixels are adjacent to
  software-reference edges, isolating the residual to hardware
  coverage/interpolation rather than broad interior color errors.
- Failed live-code wrappers remain in the interpreter, eliminating the
  post-prologue host stack overflow; the 50,000-presentation regression route
  exits cleanly.
- Fixed-rate XAudio2 output retains real guest audio across load gaps; the
  accepted route reports zero underruns/drops and one preservation-silence
  transition.
- PSP scratchpad support and a bounded, scheduler-aware interpreter carry the
  deterministic route into st00 through present 30,000.
- A Circle-only new-game profile completes initial default-deck setup. Two
  empty-fixture runs produce identical checkpoints through the playable
  six-card prologue hand and exit without a runtime failure marker.
- Native STAGE01 reduces the matched post-Forest route's interpreted
  instructions by 85.51% and median wall time by 64.74%, with byte-identical
  checkpoints and unchanged save fixtures.

The next gameplay milestone is deliberate movement, camera, card/action,
pause, and cancel/confirm validation from the six-card prologue state,
followed by combat, stage transitions, and native save/reload. Feature-class
D3D12/Vulkan goldens, movies, full-stage pacing, campaign validation, and
long soaks also remain. The next ranked renderer experiment is replacing
unsafe serialized pipeline libraries with validated per-PSO persistence.
