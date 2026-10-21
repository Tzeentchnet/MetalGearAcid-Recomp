#include "recomp.h"

static const SrModulePolicyEntry s_mga_modules[] = {
    {
        "disc0:/PSP_GAME/USRDIR/modules/kjfs.prx",
        "KCEJ_FS",
        "78e4d6c569be06ecb25b5a88caf230709c575ead",
        SR_MODULE_GUEST,
    },
    {
        "disc0:/PSP_GAME/USRDIR/modules/zlibdec.prx",
        "ZLIB",
        "e6b33fae3f3579745aec806fb8bcc3cd2cd7ced4",
        SR_MODULE_GUEST,
    },
    {
        "disc0:/PSP_GAME/USRDIR/modules/sound.prx",
        "KCEJ_SOUND",
        "32af84c6ebd301864c9d41be2ecc0cebd879e109",
        SR_MODULE_GUEST,
    },
    {
        "disc0:/PSP_GAME/USRDIR/modules/videocodec.prx",
        "*",
        "65756d91587792f6d5e024f31afdba3eadab3a62",
        SR_MODULE_HLE,
    },
    {
        "disc0:/PSP_GAME/USRDIR/modules/audiocodec.prx",
        "*",
        "8dc31685adf1ad9432083cd4ffd7ed0df7fce33d",
        SR_MODULE_HLE,
    },
    {
        "disc0:/PSP_GAME/USRDIR/modules/sc_sascore.prx",
        "*",
        "7cbc68acd56620e9af5f280f88f2e2a06e78e026",
        SR_MODULE_HLE,
    },
    {
        "disc0:/PSP_GAME/USRDIR/modules/libatrac3plus.prx",
        "sceATRAC3plus_Library",
        "96d91d0925fc0c2cad8066830abe9d34b1f3c6da",
        SR_MODULE_HLE,
    },
    {
        "disc0:/PSP_GAME/USRDIR/modules/mpegbase.prx",
        "*",
        "4ba5f5e09ed323e426138e8ce20507bbf2919a87",
        SR_MODULE_HLE,
    },
    {
        "disc0:/PSP_GAME/USRDIR/modules/mpeg.prx",
        "sceMpeg_library",
        "33a4fd4f725d3b48417c6745b5edd95a6ca9fda5",
        SR_MODULE_HLE,
    },
};

void sr_mga_register_module_policy(void) {
    sr_module_set_policy(
        s_mga_modules,
        (uint32_t)(sizeof(s_mga_modules) / sizeof(s_mga_modules[0])));
}
