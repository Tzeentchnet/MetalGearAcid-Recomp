#include "recomp.h"

#include <stddef.h>

extern const SrDispatchTable mga_kjfs_dispatch_table;
extern const SrDispatchTable mga_zlib_dispatch_table;
extern const SrDispatchTable mga_sound_dispatch_table;
extern const SrDispatchTable mga_stage_init_dispatch_table;
extern const SrDispatchTable mga_stage_title_dispatch_table;
extern const SrDispatchTable mga_stage_prologue_dispatch_table;
extern const SrDispatchTable mga_stage_st00_dispatch_table;
extern const SrDispatchTable mga_stage_st01_dispatch_table;

static const SrModulePolicyEntry s_mga_modules[] = {
    {
        "disc0:/PSP_GAME/USRDIR/modules/kjfs.prx",
        "KCEJ_FS",
        "78e4d6c569be06ecb25b5a88caf230709c575ead",
        SR_MODULE_GUEST,
        0x09af5800u,
        &mga_kjfs_dispatch_table,
    },
    {
        "disc0:/PSP_GAME/USRDIR/modules/zlibdec.prx",
        "ZLIB",
        "e6b33fae3f3579745aec806fb8bcc3cd2cd7ced4",
        SR_MODULE_GUEST,
        0x09b05200u,
        &mga_zlib_dispatch_table,
    },
    {
        "disc0:/PSP_GAME/USRDIR/modules/sound.prx",
        "KCEJ_SOUND",
        "32af84c6ebd301864c9d41be2ecc0cebd879e109",
        SR_MODULE_GUEST,
        0x09b15000u,
        &mga_sound_dispatch_table,
    },
    {
        "disc0:/PSP_GAME/USRDIR/modules/videocodec.prx",
        "*",
        "65756d91587792f6d5e024f31afdba3eadab3a62",
        SR_MODULE_HLE,
        0,
        NULL,
    },
    {
        "disc0:/PSP_GAME/USRDIR/modules/audiocodec.prx",
        "*",
        "8dc31685adf1ad9432083cd4ffd7ed0df7fce33d",
        SR_MODULE_HLE,
        0,
        NULL,
    },
    {
        "disc0:/PSP_GAME/USRDIR/modules/sc_sascore.prx",
        "*",
        "7cbc68acd56620e9af5f280f88f2e2a06e78e026",
        SR_MODULE_HLE,
        0,
        NULL,
    },
    {
        "disc0:/PSP_GAME/USRDIR/modules/libatrac3plus.prx",
        "sceATRAC3plus_Library",
        "96d91d0925fc0c2cad8066830abe9d34b1f3c6da",
        SR_MODULE_HLE,
        0,
        NULL,
    },
    {
        "disc0:/PSP_GAME/USRDIR/modules/mpegbase.prx",
        "*",
        "4ba5f5e09ed323e426138e8ce20507bbf2919a87",
        SR_MODULE_HLE,
        0,
        NULL,
    },
    {
        "disc0:/PSP_GAME/USRDIR/modules/mpeg.prx",
        "sceMpeg_library",
        "33a4fd4f725d3b48417c6745b5edd95a6ca9fda5",
        SR_MODULE_HLE,
        0,
        NULL,
    },
    {
        "disc0:/sce_lbn0x10b80_size0x144a6",
        "mgp_stage",
        "21cc9fd6cc74551db23f59cc34cad3e0a9585cb4",
        SR_MODULE_GUEST,
        0x09b43c00u,
        &mga_stage_init_dispatch_table,
    },
    {
        "disc0:/sce_lbn0x17810_size0x24189",
        "mgp_stage",
        "c280a20e8cfc43c659bf85a3b5ccea6c40c088df",
        SR_MODULE_GUEST,
        0x09b43c00u,
        &mga_stage_title_dispatch_table,
    },
    {
        "disc0:/sce_lbn0x11780_size0x22f8e",
        "mgp_stage",
        "c99a55c0dadfd673dc3b5c878aee4e852615138a",
        SR_MODULE_GUEST,
        0x09b43c00u,
        &mga_stage_prologue_dispatch_table,
    },
    {
        "disc0:/sce_lbn0x11ad0_size0x1fb51",
        "mgp_stage",
        "7899000a805ae773838b6c11741e62af46d14338",
        SR_MODULE_GUEST,
        0x09b43c00u,
        &mga_stage_st00_dispatch_table,
    },
    {
        "disc0:/sce_lbn0x11e50_size0x2c138",
        "mgp_stage",
        "9dfc231f933ef0d508ad7763f74fb6d857581e66",
        SR_MODULE_GUEST,
        0x09b6c600u,
        &mga_stage_st01_dispatch_table,
    },
};

void sr_mga_register_module_policy(void) {
    sr_module_set_policy(
        s_mga_modules,
        (uint32_t)(sizeof(s_mga_modules) / sizeof(s_mga_modules[0])));
}
