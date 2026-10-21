# Credits and provenance

This project builds on:

- **sal063** — original
  [PSP-recompilation-project](https://github.com/sal063/PSP-recompilation-project)
  static recompiler and native runtime.
- **Tzeentchnet** — the
  [Killzone: Liberation runtime fork](https://github.com/Tzeentchnet/psp-recomp)
  used here, including standalone boot, interpreter fallback, D3D12, audio,
  media, input, and extensive HLE work.
- **PPSSPP contributors** — PSP behavior, verification, system fonts, and
  portions of the runtime modeled on or ported from PPSSPP.
- **SDL contributors** — SDL3 window and input support used by the optional
  renderer.

The bundled runtime has additional third-party components and license notices.
See `external/psp-recomp/CREDITS.md` after initializing the submodule.
