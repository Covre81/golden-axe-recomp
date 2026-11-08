#include "game_spec.h"
#include "genesis_runtime.h"

/* Endereços: ver game.toml (rascunho, conferir com o dump). */
static void ga_call_entry_point(void) { recomp_call_addr(0x000ABEu); }
static void ga_call_vblank(void)      { recomp_call_addr(0x000CF6u); }
static void ga_call_hblank(void)      { recomp_call_addr(0x000CE6u); }

const GameSpec g_game_spec = {
    .display_name = "Golden Axe", .short_name = "GA",
    .expected_rom_crc32 = 0x665D7DF9u, .expected_rom_size = 0x80000u,
    .tier3_floor_default = 1,
    .call_entry_point = ga_call_entry_point,
    .call_vblank = ga_call_vblank, .call_hblank = ga_call_hblank,
};
