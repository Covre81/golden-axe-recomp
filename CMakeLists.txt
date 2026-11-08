cmake_minimum_required(VERSION 3.16)
project(GoldenAxeRecomp C CXX)

# O runner usa _Static_assert (C11); o MSVC sem isso compila como C90.
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

set(RECOMP_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/external/segagenesisrecomp")
set(GAME_DIR "${CMAKE_CURRENT_SOURCE_DIR}/game")
set(GA_ROM golden_axe.bin)   # dump próprio, World Rev A (REV01) CRC32 665D7DF9; nunca versionado

foreach(f "${GA_ROM}" game.toml golden_axe_spec.c)
    if(NOT EXISTS "${GAME_DIR}/${f}")
        message(FATAL_ERROR "Falta game/${f}. A ROM vem do seu cartucho; "
            "game.toml e golden_axe_spec.c precisam dos vetores lidos dela.")
    endif()
endforeach()

include("${RECOMP_ROOT}/cmake/GenesisRecompGenerated.cmake")
include("${RECOMP_ROOT}/cmake/GenesisRecompRunner.cmake")

# SDL2 que já vem dentro do motor (Windows/MSVC)
set(SDL2_BUNDLED "${RECOMP_ROOT}/runner/external/SDL2/SDL2-2.28.5")
find_package(SDL2 CONFIG REQUIRED PATHS "${SDL2_BUNDLED}/cmake" NO_DEFAULT_PATH)

genesisrecomp_add_generated_sources(GA_GEN goldenaxe "${GAME_DIR}" ${GA_ROM})
genesisrecomp_runner_sources(RUNNER_SOURCES TRACE ON)

add_executable(GoldenAxeRecomp ${RUNNER_SOURCES} ${GA_GEN} "${GAME_DIR}/golden_axe_spec.c")
add_dependencies(GoldenAxeRecomp ${GA_GEN_TARGET})
genesisrecomp_runner_target(GoldenAxeRecomp)

target_include_directories(GoldenAxeRecomp PRIVATE
    "${RECOMP_ROOT}/runner"
    "${RECOMP_ROOT}/runner/include"
    "${RECOMP_ROOT}/runner/video"
    "${RECOMP_ROOT}/runner/external/ymfm/src"
    "${RECOMP_ROOT}/runner/external/superzazu"
    "${RECOMP_ROOT}/runner/external/clowncommon"
    "${RECOMP_ROOT}/recompiler/src"
    "${GA_GEN_DIR}"
    "${GAME_DIR}")
target_compile_definitions(GoldenAxeRecomp PRIVATE
    INCLUDE_GENERATED_CODE=1 ENABLE_RECOMPILED_CODE=1 OWN_BACKEND=1 DEFAULT_DEBUG_PORT=4380)
# SDL.h renomeia main -> SDL_main no Windows; SDL2main fornece o main real.
target_link_libraries(GoldenAxeRecomp PRIVATE SDL2::SDL2main SDL2::SDL2)

if(MSVC)
    target_compile_options(GoldenAxeRecomp PRIVATE /W3 /WX- /utf-8 /wd4102 /wd4996 /wd4013 /bigobj)
    add_custom_command(TARGET GoldenAxeRecomp POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            "${SDL2_BUNDLED}/lib/x64/SDL2.dll" "$<TARGET_FILE_DIR:GoldenAxeRecomp>")
endif()
