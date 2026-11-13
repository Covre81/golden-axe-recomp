/*
 * goldenaxe_spec.c — instantiates the GameSpec for Golden Axe
 * (Sega Genesis/Mega Drive, 1990, W REV01).
 *
 * Identity, recompiled trampolines, and a minimal frame-record packer.
 * Addresses verified against the disassembly and the ROM
 * vector table:
 *
 *   $04 -> $000ABE  EntryPoint (initial PC)
 *   $70 -> $000CE6  HBlank (IRQ4)
 *   $78 -> $000CF6  VBlank (IRQ6)
 *   GameLoop        $000C76  (outer mode dispatcher + per-frame loop)
 *
 * Deliberately NULL/minimal for bring-up:
 *   - save_resume_pc      — no per-mode loop tops mapped yet; falls back to
 *                           resume_main_loop_pc (GameLoop). Map Title/Level/
 *                           Duel loop tops from ga.lst later.
 *   - call_periodic       — no PLC-style periodic hook wired (plc_pending=0).
 *   - z80_step            — no Z80 static recompilation; superzazu
 *                           interpreter path stays the default.
 *
 */
#include "game_spec.h"
#include "game_layout.h"
#include "genesis_runtime.h"
#include "goldenaxe_video.h"
#include "goldenaxe_options.h"
#include "video/genesis_machine.h"

#include <stdint.h>
#include <stddef.h>   /* NULL */
#include <string.h>   /* memset */

/* ---- 68K RAM shadow (defined in glue.c) ---- */
extern uint8_t g_ram[0x10000];
extern uint8_t g_rom[0x400000];

/* ---- Recompiled entry trampolines ---- */
/* Routed through recomp_call_addr so the tail-call trampoline frame
 * is set up before the recompiled function runs. */
static void ga_call_entry_point(void) { recomp_call_addr(0x000ABEu); }

/* The VDP's pending control-port command belongs to the interrupted code:
 * the game can prime a command and take an interrupt before its data
 * writes, and the handler's own VDP work would otherwise redirect them. */
typedef struct {
    uint8_t  control_pending, code, address_hi, dma_fill_pending;
    uint16_t address;
} GaVdpCommand;

static GaVdpCommand ga_vdp_command_save(void)
{
    const GVDP *v = &g_machine.vdp;
    GaVdpCommand s = { v->control_pending, v->code, v->address_hi,
                       v->dma_fill_pending, v->address };
    return s;
}

static void ga_vdp_command_restore(const GaVdpCommand *s)
{
    GVDP *v = &g_machine.vdp;
    v->control_pending  = s->control_pending;
    v->code             = s->code;
    v->address_hi       = s->address_hi;
    v->dma_fill_pending = s->dma_fill_pending;
    v->address          = s->address;
}

static void ga_call_hblank(void)
{
    GaVdpCommand command = ga_vdp_command_save();
    recomp_call_addr(0x000CE6u);
    ga_vdp_command_restore(&command);
}

/* ---- Player1 scripted-state stale-velocity AND input-lockout fix ----
 *
 * Dispatch entries 14, 16, 18, 19, 21, 22, 24, 26 (loc_8162, loc_7DF4,
 * loc_7E3A, loc_7E94, loc_80F2, loc_8116, loc_8648-family, loc_8238) are
 * the "idle / walk-to-NPC-position / dialog-wait / scripted cutscene
 * walk-in" family. Entry 13 (loc_79DE, dash attack) removed 2026-11-12
 * because the ROM keeps its landing momentum on purpose. None of them read
 * joypad input -- only entry 0 (loc_6FE0) does.
 *
 * Two things this family can leave behind that entry 0 depends on being
 * clean, and that only SOME of the family's many exit paths reset:
 *
 * 1. $2C(a0), the X-velocity register. Several members (e.g. loc_8238,
 *    loc_7E94) write a SCRIPTED, non-player value here while active.
 *    loc_B68C (the unconditional per-frame physics integrator) keeps
 *    adding whatever is in $2C(a0) to X every frame regardless of
 *    dispatch state. In entry 0 a leftover $2C cannot persist: with no
 *    direction held loc_70E0 -> loc_7092 decays it by $8000 per frame
 *    (also when bit 5 is set, via loc_7028), a wall clears it (loc_C2C2),
 *    and jump/attack/magic clear it (loc_72F0, loc_8A9E); so $2C is left
 *    to the ROM.
 *
 * 2. Bit 5 of $3(a0), the terrain-height-transition hold flag (set by
 *    loc_74E0, cleared by loc_750A as part of this same state family's
 *    own normal operation). loc_6FE0 (entry 0's own body) tests this bit FIRST,
 *    before any of its jump/attack/directional-input branches:
 *        btst #5, $3(a0)
 *        bne.s loc_7028      ; skip jump/attack/magic (decay still runs)
 *    Bit 5 blocks jump, attack, magic, and up/down (ga.asm 7707-7708,
 *    7728-7729). If this bit is still set the instant control hands back
 *    to entry 0, input is *completely* dead -- not just movement, but jump,
 *    attack, and magic too, matching the exact symptom reported ("only
 *    pause works"). This is a better fit for total lockout than (1) alone,
 *    which would only explain movement being wrong.
 *
 * Both (1) and (2) stem from the SAME handoff: whichever of this family's
 * exit paths actually runs, only some of them (e.g. loc_750A's own bit5
 * clear, loc_7F38's $2C(a0) clear) reset either piece of state; the
 * natural-timeout / other exits (e.g. loc_8238's loc_82D2) reset neither.
 *
 * Fix: rather than patch each individual missing clear() one at a time
 * (risking missing others), detect ANY transition where the PREVIOUS
 * frame's dispatch entry was one of this scripted family and the CURRENT
 * frame's entry is 0 (real player control), and clear $3(a0) bit 5 there
 * (bit 5 blocks jump, attack, magic, and up/down; that is why the hook
 * still clears bit 5; $2C(a0) is left to the ROM; see point 1 and the
 * last paragraph).
 * Combat/movement states (running, jump, attacks, hit-reaction, etc.) are
 * NOT in this set, so real player-driven momentum or an in-progress
 * terrain hold from actual gameplay is never touched -- only entries
 * confirmed (via this doc's disasm reading) to never read input and only
 * ever carry scripted, not player-intended, state. Scoped to Player1
 * ($FFFFD000) only -- the only address this investigation's live captures
 * ever observed hitting these entries.
 *
 * The $2C(a0) clear was removed (2026-11-12) because entry 0 decays $2C
 * itself every frame with no direction held (loc_70E0 -> loc_7092: +/-$8000
 * per frame toward 0, cleared on wall contact via loc_C2C2), so a leftover
 * walk-in value cannot persist (bit 5 or not); zeroing it here desynced
 * the attract demo and every stage intro vs BlastEm (ROM: $10000 -> $8000 ->
 * 0, X fraction $80). */
#define GA_P1_BASE    0x00FFD000u
#define GA_P1_STATE42 (GA_P1_BASE + 0x42u)
#define GA_P1_FLAGS3  (GA_P1_BASE + 0x3u)
#define GA_FLAGS3_TERRAIN_HOLD_BIT 0x20u

static int ga_is_scripted_noinput_entry(uint16_t state42)
{
    if (state42 == 0u) return 0;
    int entry = ((state42 >> 8) & 0x7Fu) / 4;
    switch (entry) {
        case 14: case 16: case 18: case 19:
        case 21: case 22: case 24: case 26:
            return 1;
        default:
            return 0;
    }
}

/* ---- Global "freeze non-cutscene objects" flag (bit 3 of $FFFFC104) ----
 *
 * Shared dispatcher (loc_6DCC/loc_6EF0 / loc_6F26): btst #3,$FFC104; if set,
 * skip the object's whole per-frame update unless move.b $42(a0),d0;
 * andi.b #$7F,d0; cmpi.b #$3C,d0 passes (magic spell state).
 *
 * loc_7330 sets bit 3 at magic start (state $3C); loc_8E60 / loc_8DFC clear
 * it when the spell ends. BlastEm (2P, P2 casts magic): freeze lasts ~248
 * frames and both enemies take damage. In 2P, P2 casting while P1 is in
 * state 0 is legitimate -- bit 3 must stay set until the spell finishes.
 *
 * Recomp hook: each VBlank, if Player1 state42==0 and bit 3 is still set,
 * clear bit 3 (corrects a stuck flag after some scripted paths). Skip that
 * clear while Player 2 is in magic state (active slot: $FFD080 bit 7, and
 * ($FFD0C2&$7F)==$3C). Otherwise 2P P2 magic is cancelled after one frame. */
#define GA_GLOBAL_FREEZE_FLAGS 0x00FFC104u
#define GA_FREEZE_NONCUTSCENE_BIT 0x08u
#define GA_P2_BASE    0x00FFD080u
#define GA_P2_STATE42 (GA_P2_BASE + 0x42u)

static int ga_p2_casting_magic(void)
{
    uint8_t id = m68k_read8(GA_P2_BASE);

    if (!(id & 0x80u))
        return 0;
    return (m68k_read8(GA_P2_STATE42) & 0x7Fu) == 0x3Cu;
}

/* ---- Player1 "cutscene-retrigger" bit silently blocking entry-0 dispatch
 * (bit 6 of $3(a0)) ----
 *
 * loc_6DCC (the very top of the shared per-object dispatcher, run before
 * the loc_6F68 state-table jump) has a second gate beyond the freeze flag
 * above:
 *     bclr #1, $3(a0)
 *     bne.w loc_6ED8            ; one-shot "start cutscene" trigger (spawn-time only)
 *     btst #6, $3(a0)
 *     beq.w loc_6EF0            ; bit6 clear -> normal dispatch, reaches loc_6F3E
 *     bset #2, $2(a0)
 *     bne.w loc_6EF0            ; bit2 of $2(a0) already set -> also normal dispatch
 *     ... heavy "linked-NPC allow-list" logic, ends by overwriting $42(a0) ...
 * Live dispatch-tracing this session (instrumenting recomp_dispatch_once
 * directly, watching every tail-call address reached) found bit6 getting
 * set during ordinary walking -- no dialog, no NPC nearby -- and once set,
 * func_006FE0 (entry 0, the player-control state) *permanently* stops
 * being tail-called every subsequent frame, even though $42(a0) itself
 * keeps reading back as 0x0000 on every external check. This is because
 * the "bset #2,$2(a0) / bne.w loc_6EF0" short-circuit apparently isn't
 * sticking frame-to-frame here (bit2 doesn't stay set), so the heavy
 * branch re-fires every frame, each time overwriting $42(a0) and forcing
 * it back through a different (non-entry-0) code path before the object's
 * own logic settles $42(a0) back to 0 by the time anything reads it --
 * entry 0's own code (movement input, animation ticking, everything)
 * simply never runs that frame. Confirmed via the exact same
 * frame-by-frame trace: at the frame this bit turns on, func_006FE0 drops
 * out of the dispatch trace entirely while the outer func_006DB0 dispatch
 * keeps firing every frame as normal -- and confirmed the reverse too:
 * forcibly clearing bits 5/6 of $3(a0) and bit 2 of $2(a0) on every
 * dispatch restores func_006FE0 running every frame again.
 *
 * This is a different, independent symptom from the terrain-hold
 * ($2C(a0)/bit5) and freeze-flag bugs above, but the same style of fix
 * applies: whenever entry 0 is genuinely, currently active (state42==0),
 * bit6 being set is never legitimate (entry 0's own dispatch wouldn't be
 * reachable to observe state42==0 in the first place if the heavy branch
 * had actually taken over that frame) -- so clearing it here is a pure
 * no-op in the healthy case and only ever corrects the stuck/re-arming
 * bit. Bit 2 of $2(a0) is cleared alongside it so the one-shot latch
 * starts from a known state rather than possibly re-arming the same
 * frame it's observed already-set. NOT yet root-caused *why* bit6 gets
 * set here in the first place (no dialog/NPC trigger was present in the
 * repro) -- this addresses the dispatch-blocking symptom, not the
 * upstream cause. */
#define GA_FLAGS3_CUTSCENE_RETRIGGER_BIT 0x40u
#define GA_FLAGS2_ONESHOT_LATCH_BIT      0x04u

/* ---- Optional Bad Brothers ($C0/$C1) AI watchdog, OFF by default ----
 * Enable with "boss_ai_watchdog=1" in goldenaxe-video.ini.
 * Mitigates original-ROM boss AI stalls (ga.asm); not a recompilation bug.
 * Post-VBlank, for each of eight enemy slots at $FFD100+i*$80: only if ID is
 * $C0/$C1 with anim script $00040262, then (1) loc_10782 "wait for contact":
 * state $0C, $4E bit 6, no $03 bits 6/1 -- after 120 frames clear $4E bit 6 and
 * set $4C=$04; (2) loc_1034C idle probe: state $00 with $4C bit 7 -- after 180
 * frames set $4C=$04; (3) $04->$08 whiff loop -- after 6 entries into $08 with
 * no $03 bit 6, if |P1 X - brother X|>16 nudge brother X 4 px toward P1.
 * AI state bytes written to $4C are always multiples of 4 (ROM jump table). */
#define GA_BB_SLOT_BASE     0x00FFD100u
#define GA_BB_SLOT_STRIDE   0x80u
#define GA_BB_SLOT_COUNT    8u
#define GA_BB_ANIM_SCRIPT   0x00040262u
#define GA_BB_WAIT_FRAMES   120u
#define GA_BB_IDLE_FRAMES   180u
#define GA_BB_ATK_STREAK    6u
#define GA_BB_NUDGE_GAP     16u

typedef struct {
    uint16_t wait_contact;
    uint16_t idle_probe;
    uint8_t atk_streak;
    uint8_t prev_st;
} GaBbWd;

static int ga_bb_is_brother(uint32_t b)
{
    uint8_t id = m68k_read8(b);
    uint8_t kind = (uint8_t)(id & 0x7Fu);

    if (kind != 0x40u && kind != 0x41u)
        return 0;
    if (!(id & 0x80u))
        return 0;
    return m68k_read32(b + 0x6Cu) == GA_BB_ANIM_SCRIPT;
}

static void ga_bb_watchdog_one(uint32_t b, GaBbWd *s)
{
    uint8_t st4c;
    uint8_t st;
    uint8_t f3;
    uint8_t f4e;

    if (!ga_bb_is_brother(b)) {
        s->wait_contact = 0;
        s->idle_probe = 0;
        s->atk_streak = 0;
        s->prev_st = 0xFFu;
        return;
    }
    st4c = m68k_read8(b + 0x4Cu);
    st = (uint8_t)(st4c & 0x7Fu);
    f3 = m68k_read8(b + 0x03u);
    f4e = m68k_read8(b + 0x4Eu);

    if (st == 0x0Cu && (f4e & 0x40u) && !(f3 & 0x42u)) {
        if (++s->wait_contact >= GA_BB_WAIT_FRAMES) {
            m68k_write8(b + 0x4Eu, (uint8_t)(f4e & ~0x40u));
            m68k_write8(b + 0x4Cu, 0x04u);
            s->wait_contact = 0;
        }
    } else {
        s->wait_contact = 0;
    }

    if (st == 0x00u && (st4c & 0x80u)) {
        if (++s->idle_probe >= GA_BB_IDLE_FRAMES) {
            m68k_write8(b + 0x4Cu, 0x04u);
            s->idle_probe = 0;
        }
    } else {
        s->idle_probe = 0;
    }

    if (st == 0x08u && s->prev_st != 0x08u) {
        if (++s->atk_streak >= GA_BB_ATK_STREAK) {
            uint16_t bx = m68k_read16(b + 0x1Cu);
            uint16_t px = m68k_read16(0x00FFD01Cu);
            int gap = (int)px - (int)bx;

            if (gap < 0)
                gap = -gap;
            if ((unsigned)gap > GA_BB_NUDGE_GAP)
                m68k_write16(b + 0x1Cu,
                             (uint16_t)(px > bx ? bx + 4u : bx - 4u));
            s->atk_streak = 0;
        }
    } else if ((f3 & 0x40u) || (st != 0x04u && st != 0x08u)) {
        s->atk_streak = 0;
    }
    s->prev_st = st;
}

static void ga_bb_watchdog_tick(void)
{
    static GaBbWd wd[GA_BB_SLOT_COUNT];
    static int wd_ready;
    uint32_t i;

    if (!goldenaxe_boss_ai_watchdog_enabled())
        return;
    if (!wd_ready) {
        for (i = 0; i < GA_BB_SLOT_COUNT; i++)
            wd[i].prev_st = 0xFFu;
        wd_ready = 1;
    }
    for (i = 0; i < GA_BB_SLOT_COUNT; i++)
        ga_bb_watchdog_one(GA_BB_SLOT_BASE + i * GA_BB_SLOT_STRIDE, &wd[i]);
}

static void ga_call_vblank(void)
{
    static uint16_t s_prev_p1_state42 = 0xFFFFu;  /* sentinel: no prior frame yet */

    GaVdpCommand command = ga_vdp_command_save();
    recomp_call_addr(0x000CF6u);
    ga_vdp_command_restore(&command);

    uint16_t cur = m68k_read16(GA_P1_STATE42);
    if (ga_is_scripted_noinput_entry(s_prev_p1_state42) && cur == 0x0000u) {
        uint8_t flags3 = m68k_read8(GA_P1_FLAGS3);
        if (flags3 & GA_FLAGS3_TERRAIN_HOLD_BIT)
            m68k_write8(GA_P1_FLAGS3,
                        (uint8_t)(flags3 & ~GA_FLAGS3_TERRAIN_HOLD_BIT));
    }
    s_prev_p1_state42 = cur;

    if (cur == 0x0000u) {
        uint8_t freeze = m68k_read8(GA_GLOBAL_FREEZE_FLAGS);
        if ((freeze & GA_FREEZE_NONCUTSCENE_BIT) && !ga_p2_casting_magic())
            m68k_write8(GA_GLOBAL_FREEZE_FLAGS, (uint8_t)(freeze & ~GA_FREEZE_NONCUTSCENE_BIT));

        /* $3 bit 6 / $2 bit 2 are no longer cleared here: bit 6 is the
         * "got hit" flag that loc_BFCC sets when an enemy swing lands, so
         * clearing it every idle/walking frame made player 1 immune and left
         * enemies (e.g. the stage 3 Bad Brothers) swinging forever. */
    }

    ga_bb_watchdog_tick();
}

/* ---- Frame-record packer ---- */

/* WRAM offsets (low 16 bits of $FFxxxx), from ga.asm + golden-axe-7.wch. */
#define GA_GAME_MODE   0xC172   /* word: mode | $80 transition flag   */
#define GA_VINT_COUNT  0xC2AE   /* longword: +4 per VBlank            */
#define GA_PLAYER_X    0xD01C   /* word (wch + ga.asm:1434)           */
#define GA_PLAYER_Y    0xD018   /* word (wch + ga.asm:1433)           */
#define GA_HEALTH      0xFE7E   /* byte (wch + ga.asm:1765,4919,5776) */
#define GA_MAGIC       0xFE80   /* byte (wch + ga.asm:1782,5770)      */

/* v1 layout of the 256-byte game_data tail. Bump GA_GAME_DATA_VERSION on
 * any shape change so frame-ring consumers can detect stale captures. */
#define GA_GAME_DATA_VERSION 1

typedef struct {
    uint16_t version;
    uint16_t game_mode;      /* raw C172 word incl. transition bit */
    uint32_t vint_count;     /* /4 = serviced VBlanks              */
    uint16_t player_x;
    uint16_t player_y;
    uint8_t  health;
    uint8_t  magic;
} GoldenAxeGameData;

static uint16_t ga_rd16(uint32_t off) {
    return (uint16_t)(((uint16_t)g_ram[off] << 8) | g_ram[off + 1]);
}

static uint32_t ga_rd32(uint32_t off) {
    return ((uint32_t)ga_rd16(off) << 16) | (uint32_t)ga_rd16(off + 2);
}

static void goldenaxe_fill_frame_record(uint8_t game_data[256]) {
    GoldenAxeGameData *ga = (GoldenAxeGameData *)game_data;
    memset(ga, 0, sizeof(*ga));
    ga->version    = GA_GAME_DATA_VERSION;
    ga->game_mode  = ga_rd16(GA_GAME_MODE);
    ga->vint_count = ga_rd32(GA_VINT_COUNT);
    ga->player_x   = ga_rd16(GA_PLAYER_X);
    ga->player_y   = ga_rd16(GA_PLAYER_Y);
    ga->health     = g_ram[GA_HEALTH];
    ga->magic      = g_ram[GA_MAGIC];
}

/* ---- Dispatch override ---- */
/*
 * 1) Nemesis DMA primitive aliases (see long comment below).
 *
 * 2) Object-state trampoline table $BA72..$BC71 (ga.asm loc_BA72): the four
 *    object dispatchers jump to ENTRIES (bra.w opcodes at base+4*k,
 *    k = routine&$7F), but discovery emits the bra DESTINATIONS (handlers),
 *    not the entries — so every state dispatch missed. Decode the entry's
 *    bra.w from ROM bytes and call the true handler: target = entry + 2 +
 *    disp16 (PC-relative to the extension word). Entries may chain through
 *    further bra.w's (e.g. entry 31 -> loc_BA70 rts trampoline).
 */
static inline uint16_t ga_rom16(uint32_t off)
{
    return (uint16_t)(((uint16_t)g_rom[off] << 8) | g_rom[off + 1]);
}

#define GA_STATE_TABLE_LO 0x00BA72u
#define GA_STATE_TABLE_HI 0x00BBFAu   /* table ends where real code begins */
#define GA_MODE_TABLE_LO  0x000CA2u
#define GA_MODE_TABLE_HI  0x000D0Au   /* 17 mode entries (ga.asm loc_CA2) */

/* Decode a bra.w trampoline entry from ROM and return its true target.
 * Entries may chain (bra -> bra); bounded follow. Returns false when the
 * word at `addr` is not a bra.w (caller then falls through to the miss
 * logger so the failure stays loud). */
static int ga_bra_target(uint32_t addr, uint32_t *out_tgt)
{
    uint16_t op = ga_rom16(addr);
    int guard = 0;
    while ((op & 0xFF00u) == 0x6000u && guard++ < 8) {
        int16_t disp = (int16_t)ga_rom16(addr + 2u);
        uint32_t tgt = addr + 2u + (uint32_t)disp;
        op = ga_rom16(tgt);
        if (!((op & 0xFF00u) == 0x6000u)) { *out_tgt = tgt; return 1; }
        addr = tgt;
    }
    *out_tgt = addr;
    return ((op & 0xFF00u) != 0x6000u);
}

#define GA_ROM_SIZE 0x80000u   /* matches expected_rom_size below */

static int ga_dispatch_override(uint32_t addr)
{
    uint32_t tgt;
    /* Object-state table entries (kept as an explicit fast-path/comment
     * anchor; folded into the general case below, which subsumes it). */
    if (addr >= GA_STATE_TABLE_LO && addr < GA_STATE_TABLE_HI &&
        ((addr - GA_STATE_TABLE_LO) % 4u) == 0u &&
        ga_bra_target(addr, &tgt))
    {
        recomp_call_addr(tgt);
        return 1;
    }
    /* Mode-table override ($CA2 range) REMOVED after it produced
     * dispatch-recursion stack overflows: mode handlers re-enter dispatch
     * before returning, so native trampolining here cannot terminate.
     * Proper fix = emit loc_CA2's pc-indexed site as an in-function switch
     * at codegen time (see glue.c interior-label notes). Until then the
     * tier-3 floor carries these misses, exactly as it carried boot since
     * the first bring-up. Excluded below too, for the same reason. */

    /* General bra.w-trampoline miss handler. The $BA72 object-state table
     * (above) turned out to be one instance of a WIDESPREAD idiom: many
     * per-entity-type behavior/animation state machines dispatch through
     * their OWN small `bra.w` jump table, indexed by a per-object state
     * byte with `jmp table(pc,d0.w)` and no other static reference to the
     * table or its entries anywhere in the ROM. Nothing statically jumps
     * to these tables, so the disassembler classifies them (and the
     * `bra.w` entries themselves) as data — e.g. ga.asm:9911-9913 flags
     * `jmp loc_8C32(pc,d0.w)` "(Uncertain target!)" with the 6-entry
     * table right after it dumped as "Unknown data". Every such miss was
     * previously falling through to the tier-3 floor.
     *
     * A `bra.w` opcode ($60xx) at the EXACT missed address is unambiguous
     * — real data doesn't reliably decode as one, and this only fires for
     * addresses the game itself just computed a dispatch to. Handling it
     * here (native call) instead of the floor fixes both correctness
     * (floor decline on any unsupported opcode reachable from the target)
     * and timing (native cycle costs vs the floor's PRM estimate) for
     * every such table at once, without hand-registering each one.
     *
     * Excludes: the $CA2 mode table (recursion risk, see above).
     * Bounds-checked against ROM size before reading. */
    /* recomp_call_addr() below is a genuine nested native C call (unlike
     * the tail-call trampoline it sets up internally, which loops flat) —
     * each override that resolves this way adds a real C stack frame for
     * as long as the resolved target's own execution is still running.
     * The floor path this replaces never did that (m68k_interp_run_framed
     * interprets flat, with no further C-level dispatch recursion), so
     * blanket-enabling this for every miss address risked exactly what
     * PRINCIPLES already flagged for the $CA2 mode table: something deep
     * in boot recursed enough to overflow the native stack (silent crash,
     * no watchdog/crash-report — confirmed empirically, not theoretical).
     * Cap nesting and decline (falls through to the floor, same as
     * before) past a depth no legitimate single-hop entity/animation
     * state dispatch should ever reach. */
    static int s_bra_override_depth = 0;
    if (!(addr >= GA_MODE_TABLE_LO && addr < GA_MODE_TABLE_HI) &&
        addr < (GA_ROM_SIZE - 4u) && (addr & 1u) == 0u &&
        s_bra_override_depth < 8 &&
        ga_bra_target(addr, &tgt))
    {
        s_bra_override_depth++;
        recomp_call_addr(tgt);
        s_bra_override_depth--;
        return 1;
    }

    /* The WRAM copy of the Nemesis DMA routines ($FFF400/$FFF410) never
     * reaches this function: recomp_dispatch_ram_stub() runs it first. */
    return 0;
}

/* ---- Save-state resume ----
 * A loaded state restarts the game fiber at GameLoop, which is mid-mode
 * because each mode keeps its initialized bit in $FFC172. The exception is
 * the opening dialog: loc_55D6 blocks inside player state $68, and the map
 * restore and control handoff after it live in that call chain. A state saved
 * there re-enters at $826C, so the dialog reopens and exits normally. */
static int ga_in_opening_dialog(void)
{
    return g_ram[0xD042] == 0xE8u && g_ram[0xD040] == 0u;
}

static uint32_t ga_save_resume_pc(uint8_t game_mode)
{
    (void)game_mode;
    return ga_in_opening_dialog() ? 0x00826Cu : 0u;
}

/* A state saved while the level mode ($0C) is still inside its init routine
 * (loc_12DC: art loads, player spawn, fade-in; several frames) cannot resume
 * at GameLoop: the mode's "initialized" bit 7 of $FFC172 is set before the
 * init starts, so the rest of it would be skipped (black screen, no player).
 * The init makes all its blocking calls from its own top level, so the first
 * return address under GameLoop's ($12E0..$13AE) identifies it.
 * Note: with MSVC incremental LTCG a rebuild that touches only this file can
 * keep an old inlined copy of the hooks inside main.c (runner_load_state_file);
 * after changing a hook, touch runner/main.c or do a clean build.
 * Limitation: level mode only. The other modes share the weakness and four of
 * them end their init with a tail-jumped fade this cannot see; the general
 * fix is engine-side (defer the save until the game is back at GameLoop). */
static int ga_in_level_init(void)
{
    uint32_t ssp = g_game_layout.initial_ssp;
    if ((g_ram[0xC173] & 0x7Cu) != 0x0Cu || g_cpu.A[7] > ssp - 8u) return 0;
    uint32_t ret = ga_rd32((ssp - 8u) & 0xFFFFu);
    return ret > 0x0012DCu && ret <= 0x0013AEu;
}

static void ga_on_state_loaded(void)
{
    goldenaxe_video_reset();
    if (ga_in_level_init()) g_ram[0xC172] &= 0x7Fu;   /* rerun the init */
    if (ga_in_opening_dialog()) g_cpu.A[0] = 0xFFFFD000u;
}

/* The VBlank-wait and VDP-DMA-busy polls ($DB4, $903C, $2C4A, $2CE4) need a
 * yield on the loop-back or the interrupt that ends them can never fire. */
static int ga_instruction_hook(uint32_t pc)
{
    if (pc == 0x000DB4u || pc == 0x00903Cu || pc == 0x002C4Au || pc == 0x002CE4u) {
        if (!(g_cpu.SR & 4u)) glue_yield_for_interrupt_poll();
        return 0;
    }
    return goldenaxe_video_hook(pc);
}

/* ---- The spec ---- */

static const GameDebugCommand ga_commands[] = {
    { "custom_video", goldenaxe_video_command },
};

const GameSpec g_game_spec = {
    .video                  = &goldenaxe_video,
    /* Fresh installs start in the original 4:3 view; a saved choice wins. */
    .video_default          = "off",
    .load_settings          = goldenaxe_load_settings,
    .mods                   = goldenaxe_mods,
    .netplay_config_image   = goldenaxe_config_image,
    .netplay_config_adopt   = goldenaxe_config_adopt,
    .instruction_hook       = ga_instruction_hook,
    .display_name           = "Golden Axe",
    .short_name             = "GoldenAxe",

    /* "Golden Axe (W) (REV01) [!]" — computed from the local ROM file */
    .expected_rom_crc32     = 0x665D7DF9u,
    .expected_rom_size      = 0x80000u,

    /* GA executes code the static pass cannot see:
     *   - a DMA/VRAM-flush routine copied to WRAM $FFFFF400 and jsr'd from
     *     VBlank every frame (ga.asm:762) — RAM code, no static func_ exists;
     *   - register-indirect jmp dispatchers around $303A/$0CEE (the 7
     *     unresolved-jumptable sites) and interior-label targets ($05A6,
     *     $305E, $3074) in disasm-unvisited low ROM.
     * Run the tier-3 miss fallback always-on like RKA: each miss executes
     * correctly on the interpreter capsule and feeds floor_coverage.toml as
     * [functions].extra leads for the next regen. */
    /* Tier-3 miss fallback ON: boot depends on it. The mode-0 dispatch at
     * frame ~46 ($C9E, inside the loc_CA2 mode table) only reaches its
     * handler via the interpreter capsule; with floor off the game
     * black-screens. Known cost: floor execution doesn't model VBlank-
     * spanning cycle accounting (see glue.c floor_enabled notes). */
    .tier3_floor_default    = 1,

    .call_entry_point       = ga_call_entry_point,
    .call_vblank            = ga_call_vblank,
    .call_hblank            = ga_call_hblank,

    /* GameLoop: reads the C170 mode mailbox, copies to C172, dispatches
     * jsr loc_CA2(pc,d0.w) — both the stable resume point AND the outer
     * mode dispatcher for this game. */
    .resume_main_loop_pc    = 0x000C76u,
    .save_resume_pc         = ga_save_resume_pc,
    .dispatch_main_loop_pc  = 0x000C76u,
    .call_periodic          = NULL,

    .on_state_loaded        = ga_on_state_loaded,
    .on_frame_pre           = NULL,
    .on_frame_post          = NULL,
    .on_hblank              = NULL,

    .dispatch_override      = ga_dispatch_override,

    .fill_frame_record      = goldenaxe_fill_frame_record,
    .frame_record_version   = GA_GAME_DATA_VERSION,

    .commands               = ga_commands,
    .command_count          = sizeof(ga_commands)/sizeof(ga_commands[0]),
};
