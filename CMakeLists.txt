cmake_minimum_required(VERSION 3.25)
project(MGARecomp LANGUAGES C CXX)

set(MGA_GEN_DIR "${CMAKE_SOURCE_DIR}/build/mga/gen" CACHE PATH
    "Directory written by tools/mga/gen.py")
set(PSP_RECOMP_DIR "${CMAKE_SOURCE_DIR}/external/psp-recomp" CACHE PATH
    "PSP recompiler/runtime fork")

option(MGA_ENABLE_D3D12 "Build the SDL3/D3D12 renderer" OFF)
option(MGA_RUNTIME_ONLY "Compile the runtime without generated game code" OFF)
option(MGA_ENABLE_INSTRUCTION_TRACE "Keep instruction trace hooks" OFF)

if(MGA_RUNTIME_ONLY AND MGA_ENABLE_D3D12)
  message(FATAL_ERROR "MGA_RUNTIME_ONLY does not include the SDL3 backend")
endif()
if(MGA_ENABLE_D3D12)
  if(NOT WIN32)
    message(FATAL_ERROR "MGA_ENABLE_D3D12 requires Windows")
  endif()
  find_package(SDL3 CONFIG REQUIRED COMPONENTS SDL3-shared)
endif()
if(NOT MGA_RUNTIME_ONLY AND CMAKE_C_COMPILER_ID STREQUAL "MSVC")
  message(FATAL_ERROR "Generated GNU C requires clang-cl, not MSVC cl")
endif()
if(CMAKE_C_SIMULATE_ID STREQUAL "MSVC")
  get_filename_component(MGA_CLANG_BIN_DIR "${CMAKE_C_COMPILER}" DIRECTORY)
  set(MGA_LLVM_LIB "${MGA_CLANG_BIN_DIR}/llvm-lib.exe")
  if(NOT EXISTS "${MGA_LLVM_LIB}")
    message(FATAL_ERROR "llvm-lib.exe was not found beside clang-cl")
  endif()
  set(CMAKE_AR "${MGA_LLVM_LIB}")
  set(MGA_FP_FLAGS /fp:precise /clang:-ffp-contract=off
                   /clang:-fno-strict-aliasing)
else()
  set(MGA_FP_FLAGS -ffp-contract=off -fno-strict-aliasing)
endif()

if(NOT MGA_RUNTIME_ONLY)
  file(GLOB MGA_GEN_SRCS CONFIGURE_DEPENDS
       "${MGA_GEN_DIR}/mga_recomp_[0-9][0-9][0-9].c")
  set(MGA_REGISTER_SRC "${MGA_GEN_DIR}/mga_recomp_register.c")
  if(NOT EXISTS "${MGA_REGISTER_SRC}" OR NOT MGA_GEN_SRCS)
    message(FATAL_ERROR
      "No generated code in ${MGA_GEN_DIR}. Run extraction and generation first.")
  endif()
  list(APPEND MGA_GEN_SRCS "${MGA_REGISTER_SRC}")
  list(LENGTH MGA_GEN_SRCS MGA_GEN_COUNT)
  message(STATUS "MGA generated translation units: ${MGA_GEN_COUNT}")

  add_library(mga_game STATIC ${MGA_GEN_SRCS})
  target_include_directories(mga_game PRIVATE
    "${PSP_RECOMP_DIR}/src/rt" "${MGA_GEN_DIR}")
  target_compile_definitions(mga_game PRIVATE
    "SR_ENABLE_INSTRUCTION_TRACE=$<BOOL:${MGA_ENABLE_INSTRUCTION_TRACE}>")
  if(CMAKE_C_SIMULATE_ID STREQUAL "MSVC")
    target_compile_options(mga_game PRIVATE /W3 ${MGA_FP_FLAGS}
      "$<$<CONFIG:Release>:/O1>")
  else()
    target_compile_options(mga_game PRIVATE -Wall -Wno-unused-label
      ${MGA_FP_FLAGS} "$<$<CONFIG:Release>:-O1>")
  endif()
endif()

set(RT "${PSP_RECOMP_DIR}/src/rt")
set(AT3 "${PSP_RECOMP_DIR}/third_party/at3_standalone")
set(MGA_AT3_SRCS
  ${AT3}/atrac.cpp
  ${AT3}/atrac3.cpp
  ${AT3}/atrac3plus.cpp
  ${AT3}/atrac3plusdec.cpp
  ${AT3}/atrac3plusdsp.cpp
  ${AT3}/get_bits.cpp
  ${AT3}/compat.cpp
  ${AT3}/fft.cpp
  ${AT3}/mem.cpp
  ${RT}/atrac_decode.cpp)
add_library(mga_at3 STATIC ${MGA_AT3_SRCS})
target_include_directories(mga_at3 PRIVATE "${AT3}" "${RT}")
target_compile_features(mga_at3 PRIVATE cxx_std_17)
target_compile_options(mga_at3 PRIVATE ${MGA_FP_FLAGS})

set(SAVEDATA_CRYPTO "${PSP_RECOMP_DIR}/third_party/ppsspp_savedata")
add_library(mga_savedata_crypto STATIC
  ${SAVEDATA_CRYPTO}/AES.c
  ${SAVEDATA_CRYPTO}/SHA1.c
  ${SAVEDATA_CRYPTO}/bn.c
  ${SAVEDATA_CRYPTO}/ec.c
  ${SAVEDATA_CRYPTO}/kirk_engine.c
  ${SAVEDATA_CRYPTO}/chnnlsv.cpp
  ${RT}/savedata_crypto.cpp)
target_include_directories(mga_savedata_crypto PRIVATE
  "${SAVEDATA_CRYPTO}" "${RT}")
target_compile_features(mga_savedata_crypto PRIVATE cxx_std_17)
if(MSVC)
  target_compile_options(mga_savedata_crypto PRIVATE /W1)
else()
  target_compile_options(mga_savedata_crypto PRIVATE
    -Wno-unused-parameter -Wno-unused-const-variable)
endif()

set(MGA_RUNTIME_SRCS
  ${RT}/recomp.c
  ${RT}/dispatch_table.c
  ${RT}/fpu_mode.c
  ${RT}/interp_runtime.cpp
  ${PSP_RECOMP_DIR}/src/ref/interp.cpp
  ${RT}/module.c
  ${RT}/vfpu_interp.c
  ${RT}/vfpu_asin.c
  ${RT}/hle.c
  ${RT}/net.c
  ${RT}/kmem.c
  ${RT}/intr.c
  ${RT}/gelist.c
  ${RT}/callback.c
  ${RT}/sched.c
  ${RT}/iso.c
  ${RT}/mpeg.c
  ${RT}/pgf.c
  ${RT}/gui.c
  ${RT}/settings_path.c
  ${RT}/graphics_config.c
  ${RT}/graphics_settings.c
  ${RT}/input_config.c
  ${RT}/input_settings.c
  ${RT}/kzl_twinstick.c
  ${RT}/startup_check.c
  ${RT}/audio_mixer.c
  ${RT}/audio_xaudio2.cpp
  ${RT}/sas_reverb.c
  ${RT}/h264_mf.c
  ${RT}/savedata.c
  ${RT}/osk_win.c
  ${RT}/ge.c)
if(MGA_ENABLE_D3D12)
  list(APPEND MGA_RUNTIME_SRCS
    ${RT}/gpu_d3d12/device.cpp
    ${RT}/gpu_d3d12/framebuffer.cpp
    ${RT}/gpu_d3d12/framebuffer_key.cpp
    ${RT}/gpu_d3d12/pipeline.cpp
    ${RT}/gpu_d3d12/pipeline_key.cpp
    ${RT}/gpu_d3d12/present.cpp
    ${RT}/gpu_d3d12/present_layout.cpp
    ${RT}/gpu_d3d12/shader_state.cpp
    ${RT}/gpu_d3d12/texture.cpp
    ${RT}/gpu_d3d12/texture_key.cpp
    ${RT}/gpu_d3d12/vertex.cpp)
endif()

if(MGA_RUNTIME_ONLY)
  add_library(mga_runtime_compile STATIC ${MGA_RUNTIME_SRCS})
  add_dependencies(mga_runtime_compile mga_at3 mga_savedata_crypto)
  target_include_directories(mga_runtime_compile PRIVATE "${RT}")
  target_compile_definitions(mga_runtime_compile PRIVATE
    _CRT_SECURE_NO_WARNINGS SR_GAME_TITLE="Metal Gear Acid")
  target_compile_features(mga_runtime_compile PRIVATE cxx_std_17)
  target_compile_options(mga_runtime_compile PRIVATE ${MGA_FP_FLAGS})
  if(CMAKE_C_SIMULATE_ID STREQUAL "MSVC")
    target_compile_options(mga_runtime_compile PRIVATE
      /clang:-Wno-macro-redefined)
  endif()
  return()
endif()

add_executable(mga_driver
  ${RT}/driver.c
  tools/mga/module_policy.c
  ${MGA_RUNTIME_SRCS})
target_include_directories(mga_driver PRIVATE "${RT}")
target_compile_features(mga_driver PRIVATE cxx_std_17)
target_compile_options(mga_driver PRIVATE ${MGA_FP_FLAGS})
target_compile_definitions(mga_driver PRIVATE
  _CRT_SECURE_NO_WARNINGS
  SR_GAME_TITLE="Metal Gear Acid"
  SR_EXPECTED_ISO_SIZE=201392128
  SR_EXPECTED_ISO_SHA1="d29eaba896be28c2575ead246bdaa3a9712929d4"
  SR_BOOT_ARG="disc0:/PSP_GAME/SYSDIR/EBOOT.BIN"
  SR_BOOT_NEXT_UID=0x114u
  SR_MODULE_START_UID=0x113u
  SR_MODULE_START_PRIORITY=0x20u
  SR_MODULE_START_STACK_SIZE=0x40000u
  SR_MODULE_START_ATTR=0u
  SR_MODULE_POLICY_INIT=sr_mga_register_module_policy
  SR_INTERP_DEFAULT_MAX_STEPS=100000000ULL
  SR_INITIAL_GE_LIST_ID=0)
if(CMAKE_C_SIMULATE_ID STREQUAL "MSVC")
  target_compile_options(mga_driver PRIVATE /clang:-Wno-macro-redefined)
endif()
target_link_libraries(mga_driver PRIVATE
  mga_game mga_at3 mga_savedata_crypto
  mfplat mfuuid gdi32 user32 dinput8 dxguid ole32 winmm xaudio2 bcrypt)
if(MGA_ENABLE_D3D12)
  target_compile_definitions(mga_driver PRIVATE SR_D3D12)
  target_link_libraries(mga_driver PRIVATE SDL3::SDL3 d3d12 dxgi)
  add_custom_command(TARGET mga_driver POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
            $<TARGET_FILE:SDL3::SDL3-shared>
            $<TARGET_FILE_DIR:mga_driver>)
endif()
set_target_properties(mga_driver PROPERTIES OUTPUT_NAME mga)
add_custom_command(TARGET mga_driver POST_BUILD
  COMMAND ${CMAKE_COMMAND} -E copy_directory
          "${PSP_RECOMP_DIR}/assets"
          "$<TARGET_FILE_DIR:mga_driver>/assets"
  COMMAND ${CMAKE_COMMAND} -E copy_directory
          "${PSP_RECOMP_DIR}/font"
          "$<TARGET_FILE_DIR:mga_driver>/font")

include(CTest)
if(BUILD_TESTING)
  add_executable(mga_module_loader_tests EXCLUDE_FROM_ALL
    ${PSP_RECOMP_DIR}/tools/tests/module_loader_test.c
    ${SAVEDATA_CRYPTO}/SHA1.c)
  target_include_directories(mga_module_loader_tests PRIVATE "${RT}")
  target_compile_definitions(mga_module_loader_tests PRIVATE
    _CRT_SECURE_NO_WARNINGS)
  target_compile_options(mga_module_loader_tests PRIVATE ${MGA_FP_FLAGS})
  if(CMAKE_C_SIMULATE_ID STREQUAL "MSVC")
    target_compile_options(mga_module_loader_tests PRIVATE
      /W3 /clang:-Wno-macro-redefined)
  else()
    target_compile_options(mga_module_loader_tests PRIVATE -Wall -Wextra)
  endif()
  add_test(NAME mga_module_loader COMMAND mga_module_loader_tests)

  add_executable(mga_interp_tests EXCLUDE_FROM_ALL
    ${PSP_RECOMP_DIR}/tools/tests/interp_fallback_test.cpp
    ${RT}/recomp.c
    ${RT}/dispatch_table.c
    ${RT}/fpu_mode.c
    ${RT}/interp_runtime.cpp
    ${PSP_RECOMP_DIR}/src/ref/interp.cpp
    ${RT}/settings_path.c)
  target_include_directories(mga_interp_tests PRIVATE
    "${RT}" "${PSP_RECOMP_DIR}/src/ref")
  target_compile_definitions(mga_interp_tests PRIVATE
    _CRT_SECURE_NO_WARNINGS)
  target_compile_features(mga_interp_tests PRIVATE cxx_std_17)
  target_compile_options(mga_interp_tests PRIVATE ${MGA_FP_FLAGS})
  if(CMAKE_C_SIMULATE_ID STREQUAL "MSVC")
    target_compile_options(mga_interp_tests PRIVATE
      /W3 /clang:-Wno-macro-redefined)
  else()
    target_compile_options(mga_interp_tests PRIVATE -Wall -Wextra)
  endif()
  add_test(NAME mga_interpreter_fallback COMMAND mga_interp_tests)
endif()
