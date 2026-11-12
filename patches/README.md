# Patches

Proposed and work-in-progress patches for this fork. Unless a note says
otherwise, they are **not applied** in the committed tree.

The engine drift fix lives only as a patch file here (the `segagenesisrecomp`
submodule pointer is unchanged). Apply it locally as shown below.

## `m68k-recomp-core-drift-shift-count-register.patch`

Engine fix: `cycle_drift_correction` took the register-count shift's count
from `w0 & 7` instead of `(w0 >> 9) & 7`. With this applied, all GO! arrows
are gold and timing drift vs BlastEm drops a lot.

Apply from the repository root:

```
cd segagenesisrecomp/external/m68k-recomp-core
git apply ../../../patches/m68k-recomp-core-drift-shift-count-register.patch
```

Equivalent one-liner (same path: three levels up from the submodule to the
repo root):

```
git -C segagenesisrecomp/external/m68k-recomp-core apply ../../../patches/m68k-recomp-core-drift-shift-count-register.patch
```

ROM-free test: `patches/test_m68k-recomp-core-drift-shift-count-register.py`
(pass `--recompiler` pointing at `GenesisRecomp.exe`).

## `segagenesisrecomp-ntsc-frame-audio.patch`

Experimental, not applied. Changes the NTSC audio frame length from 895780
to 896040 master cycles (hardware 59.92 Hz). Test:
`patches/test_segagenesisrecomp-ntsc-frame-audio.py`.

## `WIP-save-fix-level-init.patch`

Does not work yet. Attempt to fix a black screen when a save is taken on the
first frame of a stage (clears bit 7 of `$FFC172` on load if the CPU was
inside `loc_12DC`). Hand-editing that bit in the save file does fix it; the
hook does not appear to run at load time. See
`notes/fase1-continuacao-2026-11-12.md`.

## `proposal-boss-ai-watchdog.patch`

Untested, not compiled, not applied. Optional AI watchdog for the stage 3
Bad Brothers softlock, off by default (`boss_ai_watchdog=1` in
`goldenaxe-video.ini`). Generated C matches `ga.asm`; this is likely original
game behaviour.

## `proposal-launcher-amd-black.patch`

Untested, not compiled, not applied. Attempt to fix the black launcher on
AMD (HiDPI early-return in `apply_logical_display`, maximize across a wide
virtual desktop). Current workaround: `skip_launcher = 1` under `[launcher]`
in `settings.ini`, or `--no-launcher`.

## Already in the tree

`m68k-recomp-core-dma-wait-yield.patch` (and its test) were added in an
earlier commit. See git history.
