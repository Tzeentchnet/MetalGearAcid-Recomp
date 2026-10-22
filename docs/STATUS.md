# Project status and repository history

Last updated: 2026-10-22

Milestone definitions and release gates are maintained in [PLAN.md](PLAN.md).
Ready and blocked work is tracked in [TODO.md](TODO.md).

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
- KJFS, ZLIB, sound, init, title, and prologue activate generated native
  dispatch tables. The first mission overlay, st00, adds another 1,000 native
  entries. Functions changed by the game's post-load overlay linker fall back
  with module-qualified identity; unchanged functions remain native.
- Native conversion reduced the matched present-600 wall/CPU benchmark by
  about 45%. Pixel-exact software-renderer optimizations raise the measured
  menu/prologue route from 39.2 to 46.4 FPS, while the accepted D3D12 route
  reaches about 162.6 FPS host presentation throughput on the validation PC.
- Every D3D12 scale from 1x through 8x passes the front-end gate, and
  1x/2x/4x/8x load the selected post-Forest STAGE01 route.
- Failed live-code wrappers remain in the interpreter, eliminating the
  post-prologue host stack overflow; the 50,000-presentation regression route
  exits cleanly.
- Fixed-rate XAudio2 output retains real guest audio across load gaps; the
  accepted route reports zero underruns/drops and one preservation-silence
  transition.
- PSP scratchpad support and a bounded, scheduler-aware interpreter carry the
  deterministic route into st00 through present 30,000.
- Structured host/GPU/interpreter profiles identify native STAGE01 conversion
  as the highest-confidence performance work: one entry accounts for 81.15%
  of the measured post-Forest interpreted instructions.

The next gameplay milestone remains identifying the dark briefing's intended
advance control and completing a playable, savable new-game first-mission
route. Feature-class D3D12 goldens, movies, full-stage pacing, campaign
validation, and long soaks also remain.

## History and attribution

On 2026-10-22, the parent `master` history and the runtime fork's `kzl` and
`main` histories were rewritten to remove Copilot co-author trailers while
preserving the human author and committer identities. The cleaned runtime tips
are:

- runtime `kzl`: `40447fd`; and
- runtime `main`: `2a86b1f`.

The current parent tip is always `origin/master`.

Because those branches were force-pushed, an existing clone should preserve
any local work and rebase or cherry-pick it onto the cleaned history. A fresh
recursive clone is the simplest option when no local work must be retained.

Project policy prohibits adding AI tools as commit authors, committers, or
co-authors; see the tracked
[Copilot instructions](../.github/copilot-instructions.md).
