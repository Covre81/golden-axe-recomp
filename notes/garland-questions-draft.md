# Draft for Garland — NOT SENT

Context: your GoldenAxeRecomp at engine f92e278, Rev A ROM (CRC32 665D7DF9). I built two variants, `cycle_drift_correction = true` (your default) and `false`, and ran both from boot to the ending with a TCP driver (god mode through RAM writes).

**What works.** Both builds reach the ending (stages 1–8, Death Adder, Death Bringer, king's text). No crash, no hang, control never locks after the first dialog.

## 1. `cycle_drift_correction` and the GO! colours

The `game.toml` comment says the first GO! of a level can show wrong colours without it. I could not reproduce that on f92e278: 27 natural GO! prompts per build, all gold, palette RAM equal to CRAM on every read, with the correction on and off. A GO! forced through RAM (`$FFC2A2 = $81`) is also gold in both.

With the fixed correction (section 2) I repeated it: 27 GO! prompts from boot to the ending plus 17 in real-HP runs, all gold, palette RAM equal to CRAM.

- Did another change fix it since you wrote that comment? Is there a specific spot or input where you still see it?

## 2. Timing against BlastEm (first 130 s from boot, no input)

Music pitch and timbre match BlastEm (peaks within 1 Hz, bands within ~1 dB; level is a constant 2.4 dB lower). Timing does not:

- **Correction on:** in sync until ~20 s, then falls behind in steps at screen transitions: +5 frames at ~21 s, +13 at ~27 s, about 43 frames (0.71 s) late after 2 minutes. Between steps the lag is flat.
- **Correction off:** runs ahead instead, 7 frames by 4 s and 13 frames by 48 s.

**Found the cause of the steps — a one-line bug in the engine's correction.** In `emit_cycle_drift_correction` (`m68k-recomp-core/profiles/genesis/code_generator.c:2121`), register-count shifts (`lsl.w d1,d0`) take the count register from `w0 & 7`, which is the *shifted* register. The count is in bits 11–9. The correction adds `2*((Dn & 63) - 4)` with the wrong `Dn` (my estimate: roughly +55 cycles per shift, assuming uniform low bits). All 7 register-count shifts in the whole ROM are affected, and they all sit in the graphics-decompression routines at `$30BE`–`$33AE`, which run with VBlank masked. With `(w0 >> 9) & 7`: mode `$10` is reached at frame 1261 instead of 1267 (same as no correction), the audio lag has no steps any more (largest step 2.4 frames vs 13.8), and over 2 minutes the lag goes from +43.8 frames (steps) to −16.2 frames (no large steps, recomp *ahead*). Patch and a ROM-free test (synthetic ROM, fails before / passes after) are ready: `patches/m68k-recomp-core-drift-shift-count-register.*`.

What is left after the fix (recomp ~16 frames *ahead* of BlastEm after 116 s):
- It is not continuous. The lag is flat for long stretches (4–20 s, 28–44 s, 56–68 s) and moves in steps of 1–2 frames at screen changes, plus a 7-frame offset already there at 4 s (boot). So some loads still finish early.
- MULU/MULS/DIVU/DIVS are ruled out: Golden Axe has 31 of them, almost all with small immediates, and the engine's fixed cost over-charges them. That would make the recomp slower, not faster.
- About 3 of the 16 frames are the audio frame length (section 3).
- My remaining suspects are un-modelled bus waits: the VDP data-port FIFO (status always reads "empty", `video/genesis_vdp.c:432`) and Z80 BUSREQ. Not measured. Is bus-stall modelling something you plan, or would you take a patch?
- Caveat on my reference: it is BlastEm's *audio*, not frame numbers of game events, so part of the offset may live in the Z80/YM path rather than the 68000.
- Side note: `glue.h` says `--pacing accurate` is the default, but `glue.c:155` sets `FIBER_FULL`. The two modes produced byte-identical write logs in my 1800-frame runs.

Some demo sound effects have 5–10 dB less energy above 5 kHz than BlastEm (around 100–101.5 s); others match. Not isolated per channel yet, so treat it as a lead, not a bug report.

## 3. Audio frame is 59.94 Hz, the console is 59.92 Hz

`runner/sim_step.c:16` drains the audio chips by 895780 master cycles per frame and `main.c` paces at 60000/1001. A real NTSC frame is 262 × 3420 = 896040 master cycles (59.9227 Hz). The 68000 and Z80 run the full 262 lines, so each frame's audio is 260 master cycles short: the WAV has exactly 3732.0 samples per frame (29,109,600 in 7800 frames) against 3733.5 on hardware, −0.040%. My model says this is ~3 of the 16 frames of drift.

Patch written, **not applied and not measured in a build**: `patches/segagenesisrecomp-ntsc-frame-audio.patch` (896040 in `sim_step.c`, default pacer 53693175/896040, `sim_step_test.c` updated) with a ROM-free test. The host would run at 59.92 fps instead of 59.94. Did you pick 59.94 on purpose to match displays? If so I will drop it.

## 4. Save states taken mid-init load to a black screen

A state saved on the first gameplay frame of stage 2+ loads with `ok` but the screen stays black and the player never spawns. Cause: the save happens while the game fiber is still inside the level-mode init (`loc_12DC`: art decompression, spawn, fade, several frames). Bit 7 of `$FFC172` ("mode initialised") is set *before* that init runs, the native stack is not part of the state, and load restarts the fiber at `resume_main_loop_pc` (`$C76`), so the rest of the init is skipped. Same class as the opening-dialog case you already special-case with `save_resume_pc`.

Game-side fix, in my fork: `on_state_loaded` clears bit 7 when the mode is `$0C` and the first return address under GameLoop's (`initial_ssp − 8`) is inside `$12E0..$13AE`, so the init runs again. Tested on first-frame saves of stages 1 and 2 and on mid-stage saves.

It only covers level mode. 15 of the 17 mode handlers use the same `bset #7 / beq init` pattern, and four of them (`$04`, `$14`, `$28`, `$2C`) end the init with a tail-jump into the fade, which a return-address check cannot see. An engine-side fix would cover all games: defer a save request until the game fiber is back at `resume_main_loop_pc`. Would you take that?

Build note: with MSVC incremental LTCG, rebuilding only `goldenaxe_spec.c` kept an old inlined copy of `on_state_loaded` inside `runner_load_state_file` (`main.c`). Touching `main.c` or a clean build fixes it.

## 5. Three bugs in the `ga_call_vblank` hooks

Found by comparing against BlastEm frame by frame (GDB remote, `tools/probe/blastem_dual`). All fixed in my fork:

- **Player 1 could not be hit while idle or walking.** The hook cleared `$3(a0)` bit 6 and `$2(a0)` bit 2 on every frame with `$42 == 0`. Bit 6 is the "got hit" flag set by `loc_BFCC`, so enemy hits were erased and the stage 3 Bad Brothers swung at the air forever. Removed both clears; a full run to the ending shows no control lock without them.
- **Attract demo and every stage intro desynced.** On the scripted walk-in → state 0 transition the hook zeroed X velocity `$2C(a0)`. The ROM leaves `$10000` and decays it itself (`loc_70E0` → `loc_7092`, `$8000` per frame). The recomp ended half a pixel behind and the demo diverged from vblank `$100` on. The hook now only clears bit 5 of `$3(a0)`. Both demos match BlastEm end to end. Entry 13 (dash attack, `loc_79DE`) was also taken out of the scripted family: the ROM keeps its landing momentum.
- **Player 2 magic was cancelled after one frame in 2-player games.** The "stuck freeze flag" clear (bit 3 of `$FFC104` while player 1 is in state 0) also fired while player 2 was casting. It now skips while player 2 is in state `$3C`. BlastEm: the freeze lasts ~248 frames.

Question: do you remember which symptom made you add the bit 3 clear and the bit 6 / bit 2 clears? Bit 3 is set only at `loc_7330` and cleared only at `loc_8E60`, so in a faithful run it should never stick. If an older engine bug caused it, the bit 3 hook may be removable too.

Small one: `s_prev_p1_state42` is a function-static outside the save state, so it survived a load or rewind. I reset it in `on_state_loaded`.

## 6. One real discovery gap: `$001CEC`

`floor_coverage.toml` reports `$001CEC` from frame 1451 on. It is entry 0 of the `loc_1D2C` ladder (`bra.w loc_1CEC`, the empty-slot handler of the event queue): a lone `rts` inside `loc_1CD2`. The dispatch is `jsr loc_1D2C(pc,d0.w)` at `$1D1C`, so the floor runs it 4 times per frame. It cannot go in `[functions].extra` because it is an interior label. `function_finder.c` enumerates `bra` ladders for `jmp (d8,PC,Xn)` but not for `jsr`. Is that something you would want handled in the engine?

## 7. Retraction: the three interior-label misses were my driver

`$00AA8C`, `$012E0E`, `$012944` (and `$012128` in floor coverage) are **not** engine gaps. Each is a state table base plus `$40`: `$AA4C`, `$12DCE`, `$12904`, `$120E8`. My driver wrote `$401A` to `+$42` on every enemy, and those entity types have no state `$40`, so the `jmp table(pc,d0.w)` landed mid-instruction. Real hardware would run garbage there. The driver no longer does that. Small note: the `in_func` field in `interior_label_misses.toml` is the function that made the jump, not the one containing the address, which misled me at first.

## 8. Tests and CI

I have ROM-free tests (the four wait-loop hooks, `game.toml` addresses checked against the disassembly, source-level guards for the hook fixes in section 5) and a Windows CI job. Would you take a PR with those?
