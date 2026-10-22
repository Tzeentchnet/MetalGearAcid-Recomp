# Metal Gear Acid recompilation documentation

This directory records reproducible technical findings from bringing
**Metal Gear Acid (ULUS-10006 v1.00)** up on the PSP static recompilation
framework.

## Repositories

- Private parent:
  `https://github.com/Tzeentchnet/MetalGearAcid-Recomp`
- Public maintained runtime fork:
  `https://github.com/Tzeentchnet/psp-recomp`
- Pinned runtime commit: `40447fd`

The parent being private does not change the evidence policy below. Game data,
generated code, saves, logs, traces, dumps, and captures remain untracked.

## Documents

- [PLAN.md](PLAN.md) - milestone roadmap, definition of done, validation
  ladder, upstream workflow, risks, and documentation maintenance contract.
- [TODO.md](TODO.md) - live prioritized task list, current focus, completion
  evidence, and continuous documentation obligations.
- [FINDINGS.md](FINDINGS.md) - numbered, evidence-backed findings about the
  disc, executable, module layout, boot contract, runtime behavior, and
  framework gaps.
- [UPSTREAM.md](UPSTREAM.md) - changes that should be generalized in the
  `psp-recomp` fork, including priority, current local status, and required
  regression coverage.
- [REPRODUCTION.md](REPRODUCTION.md) - extraction, code generation, PPSSPP
  oracle capture, build, trace comparison, and rendering smoke-test commands.
- [PPSSPP_REFERENCE.md](PPSSPP_REFERENCE.md) - deterministic protected-oracle
  front-end checkpoints and reduced non-game metrics.

## Current validated checkpoint

Phases 2 and 3 are complete. Three native runs reproduce the same title-menu
selector states and transition into the new-game opening overlay while XAudio2
is active. KJFS, ZLIB, sound, init, title, and prologue use generated native
tables; remaining post-load-patched overlay functions are covered by an exact
module-qualified allowlist. Empty, removed, and existing-save memory-stick
paths pass. Gameplay, card/campaign PMFs, save creation, broader D3D12
golden/scaling coverage, and full-game stability remain later milestones.
The D3D12 build now passes
the deterministic front-end gate and is the recommended performance path;
software rendering remains the pixel-exact reference. Scales 1x-8x pass that
gate, 1x/2x/4x/8x also load the selected post-Forest STAGE01 route, and
structured profiling identifies native STAGE01 conversion as the dominant
next measured performance opportunity.

Reduced machine-readable evidence lives in
`reference/native_frontend.json`, `reference/native_frontend_menu.json`, and
`reference/ppsspp_frontend.json`; protected logs, saves, and captures remain
ignored.

## Evidence policy

Findings use the prefix `MGA-F-`. They may record addresses, sizes, hashes,
counts, API names, and observed behavior, but this repository must not contain
game executables, generated game C, disc files, memory dumps, frame captures,
or other game-derived payloads.

The following remain local and ignored:

- `build/mga/disc/`
- `build/mga/gen/`
- PPSSPP traces and logs
- Ghidra projects and exports containing decompiled code
- framebuffer, eDRAM, and RAM captures

Rendering observations in the documents describe local captures. The captures
themselves are intentionally not committed.

## Framework boundary

Game constants belong in [../config/mga.toml](../config/mga.toml) or the root
build. Generic behavior belongs in `external/psp-recomp`.

An upstreamable framework change should:

1. avoid hard-coded Metal Gear Acid or Killzone addresses;
2. fail explicitly on unsupported input instead of returning fake success;
3. have synthetic, non-game regression coverage where practical; and
4. preserve existing single-module static recompilation behavior.

Task state is maintained in [TODO.md](TODO.md). The mandatory mapping from a
code or behavior change to the documents that must change with it is defined in
[PLAN.md](PLAN.md#documentation-maintenance-contract).
