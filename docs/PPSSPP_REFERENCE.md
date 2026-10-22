# PPSSPP deterministic front-end reference

This document records non-game metadata from a protected PPSSPP v1.20.4
interpreter run.

The protected inputs were:

- the verified ULUS-10006 v1.00 ISO;
- a newly generated empty PPSSPP memstick fixture;
- [../config/mga_boot.pad](../config/mga_boot.pad); and
- a 20-second headless timeout with software rendering and call-edge capture.

The full log, call trace, memstick, and any captures remain local and ignored.
The reduced machine-readable report is
[reference/ppsspp_frontend.json](reference/ppsspp_frontend.json).
The corresponding native report is
[reference/native_frontend.json](reference/native_frontend.json).
The deterministic native menu report is
[reference/native_frontend_menu.json](reference/native_frontend_menu.json).

## Stage checkpoints

| Stage | UID | Base | Allocation | GP | Hcount | Vblank | Presents |
|---|---:|---:|---:|---:|---:|---:|---:|
| `init` | `0x174` | `0x09b43c00` | `0xf500` | `0x09b5af20` | `24027` | `84` | `42` |
| `title` | `0x17c` | `0x09b43c00` | `0x1c100` | `0x09b67b20` | `47765` | `167` | `167` |

The allocation sizes identify the overlays:

- `stage/init/init.prx` relocates to `0xf430`, rounded to `0xf500`;
- `stage/title/title.prx` relocates to `0x1c030`, rounded to `0x1c100`.

No later stage module started during the capture. This is the initial
deterministic title/front-end reference gate.

## Native comparison

The native runtime used the matching empty fixture and boot profile, with
`SR_EXIT_AFTER_PRESENT=600` and no framebuffer-capture exit.

| Stage | PPSSPP UID | Native UID | Base | Allocation | GP |
|---|---:|---:|---:|---:|---:|
| `init` | `0x174` | `0x174` | `0x09b43c00` | `0xf500` | `0x09b5af20` |
| `title` | `0x17c` | `0x17b` | `0x09b43c00` | `0x1c100` | `0x09b67b20` |

The native run reaches present 600 with:

- zero unimplemented HLE calls;
- zero host crashes;
- zero watchdogs;
- zero interpreter stops; and
- 82 module-qualified overlay fallback targets at present 600.

The remaining one-UID title discrepancy occurs after the aligned first-stage
load and requires a follow-up object-allocation audit. It does not prevent the
current title gate.

KJFS, ZLIB, sound, init, and title now activate generated native tables before
this gate. The fallback count is higher than the old address-only count because
the v2 log preserves overlay identity and records nested live-code-verification
fallbacks rather than collapsing overlapping addresses.

## Call and HLE coverage

| Metric | Value |
|---|---:|
| Unique call edges | `2,333` |
| Direct `jal` edges | `2,160` |
| Runtime `jalr` edges | `173` |
| Unique targets | `1,119` |
| HLE calls | `420,234` |
| Unique HLE functions | `61` |
| Controller reads | `6,729` |

The high HLE totals reflect the unthrottled headless interpreter during the
20-second wall-clock capture. They are coverage evidence, not expected native
real-time counts.

Selected media/audio counts:

| Call | Count |
|---|---:|
| `sceAudioOutputBlocking` | `22,215` |
| `sceAudioOutputPannedBlocking` | `43,525` |
| `sceMpegRingbufferPut` | `0` |
| `sceMpegGetAvcAu` | `0` |
| `sceMpegAvcDecode` | `0` |
| `sceMpegAtracDecode` | `0` |

This route does not exercise MPEG before or during the captured title state.
An extended native route through 20,000 presentations of the new-game opening
also makes zero MPEG calls, confirming that the expected front-end "intro PMF"
is not part of this title path. Campaign/card PMF validation remains separate.

## Diagnostics

The log contains:

- 11 expected missing-save-slot warnings for
  `ULUS10006000` through `ULUS10006010`;
- one expected `sceIoAssign` warning; and
- one host-environment error for missing `lang/.ini` beside the locally built
  PPSSPPHeadless executable.

There are no other warnings or errors in the reduced classification. The
missing language asset is a PPSSPP host setup issue, not guest behavior.

## Reproduction

Use the empty-fixture and pad-script commands in
[REPRODUCTION.md](REPRODUCTION.md), run PPSSPP with `-i -l
--graphics=software --timeout=20`, and set:

```powershell
$env:PSPRECOMP_PADSCRIPT = "$PWD\config\mga_boot.pad"
$env:PSPRECOMP_CALLTRACE = "$PWD\build\mga\reference\calls.txt"
$env:PSPRECOMP_CALLTRACE_START = "0880432c"
```

Reduce the protected outputs:

```powershell
python tools\mga\ppsspp_summary.py `
  build\mga\reference\ppsspp.log `
  --calls build\mga\reference\calls.txt `
  --timeout 20 `
  --padscript config\mga_boot.pad `
  --out docs\reference\ppsspp_frontend.json
```

Regenerate the committed JSON only when the PPSSPP build, input profile,
fixture profile, timeout, or measured behavior intentionally changes.

Reduce a native run:

```powershell
python tools\mga\native_summary.py `
  build\mga\native-title\stderr.log `
  --misses build\mga\native-title\dispatch-misses.txt `
  --present-limit 600 `
  --padscript config\mga_boot.pad `
  --out docs\reference\native_frontend.json
```
