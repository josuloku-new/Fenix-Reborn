# gow2 - ReXGlue Recompiled Project
#
# SDK boilerplate lives in generated/rexglue.cmake.

cmake_minimum_required(VERSION 3.25)
project(gow2 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(generated/rexglue.cmake)

# Sources
set(GOW2_SOURCES
    src/main.cpp
    src/roundevenf.cpp
    src/gow2_mnk.cpp
    src/gow2_direct_mouse.cpp
    src/gow2_input.cpp
    src/gow2_mods.cpp
    src/input_guard.cpp
    src/gow2_overlay.cpp
    src/gow2_settings_overlay.cpp
)

if(WIN32)
    add_executable(gow2 WIN32 ${GOW2_SOURCES})
else()
    add_executable(gow2 ${GOW2_SOURCES})
endif()

rexglue_setup_target(gow2 GPU_PLUGINS xenos)
if(MSVC)
    target_compile_options(gow2 PRIVATE /utf-8)
endif()

# ReXGlue omits five shared tails from callers; fix after codegen, before compile.
if(TARGET gow2_recomp)
    find_package(Python3 REQUIRED COMPONENTS Interpreter)
    add_custom_target(gow2_fix_codegen_tails
        COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/fix_codegen_tails.py"
                "${CMAKE_CURRENT_SOURCE_DIR}/generated/default"
        COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/apply_compatible_mods.py"
                "${CMAKE_CURRENT_SOURCE_DIR}/generated/default"
        DEPENDS gow2_codegen
        VERBATIM)
    add_dependencies(gow2_recomp gow2_fix_codegen_tails)
endif()

add_executable(gow2_input_check EXCLUDE_FROM_ALL src/mouse_filter_check.cpp)
add_executable(gow2_input_stress EXCLUDE_FROM_ALL src/input_stress_check.cpp src/input_guard.cpp)
target_link_libraries(gow2_input_stress PRIVATE rex::runtime)
add_executable(gow2_overlay_check EXCLUDE_FROM_ALL src/overlay_check.cpp src/gow2_overlay.cpp src/gow2_settings_overlay.cpp src/gow2_mods.cpp)
target_link_libraries(gow2_overlay_check PRIVATE rex::runtime)
if(MSVC)
    target_compile_options(gow2_overlay_check PRIVATE /utf-8)
endif()
