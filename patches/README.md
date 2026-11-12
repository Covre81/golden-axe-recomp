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

## `proposal-boss-ai-watchdog.patch`

Version 2, compiled and tested hidden, **not applied**. Optional AI watchdog
for the stage 3 Bad Brothers, off by default (`boss_ai_watchdog=1` in
`goldenaxe-video.ini`). Off: identical behaviour. On: a brother parked in
state `$0C` or `$00` is moved to `$04`, and a brother whiffing forever is
nudged toward the player. Not merged: the real cause of the endless
swinging was the player hit-flag clear in `ga_call_vblank`, now removed (see
"Already in the tree"). The watchdog was tested only before that fix.

## `proposal-launcher-amd-black.patch`

Not applied. Compiles cleanly (checked 2026-11-12) but was never run: it
can only be verified by opening the launcher window. Attempt to fix the black
launcher on AMD (HiDPI early-return in `apply_logical_display`, maximize
across a wide virtual desktop). Current workaround: `skip_launcher = 1` under
`[launcher]` in `settings.ini`, or `--no-launcher`.

## Already in the tree

Player hit-flag fix (2026-11-12): `ga_call_vblank` no longer clears player 1
`$3` bit 6 / `$2` bit 2 while `$42 == 0`. That clear erased enemy hits
(`loc_BFCC`), so an idle or walking player took no damage and enemies such as
the stage 3 Bad Brothers swung at the air forever. Tested hidden: boss save
(first swing hits, loop gone), full GOD-mode run to the ending with no control
lock, and a real-HP run from stage 2 (reached stage 5; same pit deaths as
before, no hang).

The first-frame save fix (rerun the stage init on load) is now in
`game/goldenaxe_spec.c`; the old `WIP-save-fix-level-init.patch` was removed.
After changing a hook in that file, touch `segagenesisrecomp/runner/main.c`
or do a clean build: MSVC incremental LTCG can keep an old inlined copy.


`m68k-recomp-core-dma-wait-yield.patch` (and its test) were added in an
earlier commit. See git history.
