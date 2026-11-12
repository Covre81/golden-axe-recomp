# Draft for Garland — NOT SENT

Context: your GoldenAxeRecomp at engine f92e278, Rev A ROM (CRC32 665D7DF9). I built two variants, `cycle_drift_correction = true` (your default) and `false`, and ran both from boot to the ending with a TCP driver (god mode through RAM writes).

**What works.** Both builds reach the ending (stages 1–8, Death Adder, Death Bringer, king's text). No crash, no hang, control never locks after the first dialog.

## 1. `cycle_drift_correction` and the GO! colours

The `game.toml` comment says the first GO! of a level can show wrong colours without it. I could not reproduce that on f92e278: 27 natural GO! prompts per build, all gold, palette RAM equal to CRAM on every read, with the correction on and off. A GO! forced through RAM (`$FFC2A2 = $81`) is also gold in both.

- Did another change fix it since you wrote that comment? Is there a specific spot or input where you still see it?

## 2. Timing against BlastEm (first 130 s from boot, no input)

Music pitch and timbre match BlastEm (peaks within 1 Hz, bands within ~1 dB; level is a constant 2.4 dB lower). Timing does not:

- **Correction on:** in sync until ~20 s, then falls behind in steps at screen transitions: +5 frames at ~21 s, +13 at ~27 s, about 43 frames (0.71 s) late after 2 minutes. Between steps the lag is flat.
- **Correction off:** runs ahead instead, 7 frames by 4 s and 13 frames by 48 s.

So the correction fixes the "too fast" drift but seems to overcharge during loads (graphics decompression, I assume). Is that expected? Would per-site data help you (frame numbers, functions running at each step)?

Some demo sound effects have 5–10 dB less energy above 5 kHz than BlastEm (around 100–101.5 s); others match. Not isolated per channel yet, so treat it as a lead, not a bug report.

## 3. One real discovery gap: `$001CEC`

`floor_coverage.toml` reports `$001CEC` from frame 1451 on. It is entry 0 of the `loc_1D2C` ladder (`bra.w loc_1CEC`, the empty-slot handler of the event queue): a lone `rts` inside `loc_1CD2`. The dispatch is `jsr loc_1D2C(pc,d0.w)` at `$1D1C`, so the floor runs it 4 times per frame. It cannot go in `[functions].extra` because it is an interior label. `function_finder.c` enumerates `bra` ladders for `jmp (d8,PC,Xn)` but not for `jsr`. Is that something you would want handled in the engine?

## 4. Retraction: the three interior-label misses were my driver

`$00AA8C`, `$012E0E`, `$012944` (and `$012128` in floor coverage) are **not** engine gaps. Each is a state table base plus `$40`: `$AA4C`, `$12DCE`, `$12904`, `$120E8`. My driver wrote `$401A` to `+$42` on every enemy, and those entity types have no state `$40`, so the `jmp table(pc,d0.w)` landed mid-instruction. Real hardware would run garbage there. The driver no longer does that. Small note: the `in_func` field in `interior_label_misses.toml` is the function that made the jump, not the one containing the address, which misled me at first.

## 5. Tests and CI

I have ROM-free tests (the four wait-loop hooks, `game.toml` addresses checked against the disassembly) and a Windows CI job. Would you take a PR with those?
