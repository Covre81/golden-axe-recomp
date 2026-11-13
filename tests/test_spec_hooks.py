#!/usr/bin/env python3
"""Travas de regressão dos ganchos de `game/goldenaxe_spec.c` (só código-fonte, sem ROM).

Cada item foi um bug do port, achado comparando com o BlastEm (notas em
`notes/bughunt-2026-11-12*.md`). O comportamento em jogo só se confere com a
ROM (`tools/probe/blastem_dual`); aqui fica o que dá para travar no CI:

1. Hook A não escreve a velocidade X `$2C(a0)` do jogador 1 (dessincronizava
   a demonstração e a entrada de cada fase).
2. O golpe de corrida (entrada 13) não está na família "roteirizada".
3. O gancho não limpa o bit 6 de `$3(a0)` nem o bit 2 de `$2(a0)` (deixava o
   jogador 1 imune parado ou andando).
4. O bit 3 de `$FFC104` só é limpo se o jogador 2 não estiver em magia.
5. `ga_on_state_loaded` zera `s_prev_p1_state42`, que fica fora do save.

    python tests/test_spec_hooks.py
"""
import argparse
import re
import sys
from pathlib import Path

SPEC = Path(__file__).resolve().parent.parent / "game" / "goldenaxe_spec.c"


def body(src: str, signature: str) -> str:
    m = re.search(re.escape(signature) + r"\s*\{(.*?)\n\}", src, re.S)
    if not m:
        sys.exit(f"FAIL: não achei {signature}")
    return re.sub(r"/\*.*?\*/", "", m.group(1), flags=re.S)  # sem comentários


def main() -> int:
    argparse.ArgumentParser().parse_known_args()  # aceita --recompiler (contrato do run_all)
    src = SPEC.read_text(encoding="utf-8")
    vblank = body(src, "static void ga_call_vblank(void)")
    family = body(src, "static int ga_is_scripted_noinput_entry(uint16_t state42)")
    loaded = body(src, "static void ga_on_state_loaded(void)")
    checks = [
        ("Hook A não escreve $2C(a0)",
         not re.search(r"XVEL|0x2C", vblank) and "m68k_write32" not in vblank),
        ("entrada 13 (golpe de corrida) fora da família roteirizada",
         not re.search(r"case\s+13\s*:", family) and re.search(r"case\s+14\s*:", family)),
        ("gancho não limpa $3 bit 6 nem $2 bit 2",
         "CUTSCENE_RETRIGGER" not in vblank and "ONESHOT_LATCH" not in vblank),
        ("congelamento só é limpo fora da magia do jogador 2",
         re.search(r"GA_FREEZE_NONCUTSCENE_BIT\)\s*&&\s*!ga_p2_casting_magic\(\)", vblank)),
        ("load zera a memória do Hook A",
         re.search(r"s_prev_p1_state42\s*=\s*0xFFFFu\s*;", loaded)),
    ]
    bad = [name for name, ok in checks if not ok]
    for name in bad:
        print("FAIL:", name)
    if not bad:
        print(f"PASS: {len(checks)} travas dos ganchos do spec")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
