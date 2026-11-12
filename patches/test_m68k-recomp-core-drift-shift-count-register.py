#!/usr/bin/env python3
"""cycle_drift_correction: o deslocamento com contagem em registrador lê o registrador da CONTAGEM.

    lsl.w d1,d0    (E368)   contagem em d1, dado em d0
    lsr.l d3,d5    (E6AD)   contagem em d3, dado em d5

No MC68000 a contagem fica nos bits 11-9 da palavra de instrução e o registrador
deslocado nos bits 2-0. O motor (emit_cycle_drift_correction, code_generator.c) usava
`w0 & 7`, ou seja, o registrador do DADO: somava 2*((Dn & 63) - 4) com Dn qualquer,
em média cerca de +55 ciclos por deslocamento. No Golden Axe isso fazia cada carga
de gráficos (descompressor Nemesis) demorar mais quadros que no console.

Sem ROM: monta uma ROM sintética com cycle_drift_correction = true, roda o recompilador
e confere o C gerado. Falha no motor f92e278 e passa com
patches/m68k-recomp-core-drift-shift-count-register.patch.

    python patches/test_m68k-recomp-core-drift-shift-count-register.py --recompiler <GenesisRecomp.exe>
"""
import argparse
import re
import subprocess
import tempfile
from pathlib import Path

CONFIG = """[game]
output_prefix = "sh"
cycle_drift_correction = true
[functions]
extra = [0x200]
[ram_layout]
game_mode = 0
vint_runcount = 0
vint_routine = 0
plc_pending = 0
initial_ssp = 0xFFFE00
vbla_stack = 0
intr_stack = 0
player_object = 0
level_modes = []
"""

# $200: lsl.w d1,d0 / lsr.l d3,d5 / lsl.w #2,d0 (contagem imediata: sem correção) / rts
CODE = bytes.fromhex("e368 e6ad e548 4e75")


def build_rom() -> bytes:
    rom = bytearray(b"\xff" * 0x400)
    rom[0:8] = bytes.fromhex("00fffe00 00000200")
    rom[0x100:0x200] = b" " * 256
    rom[0x100:0x104] = b"SEGA"
    rom[0x200:0x200 + len(CODE)] = CODE
    return bytes(rom)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--recompiler", type=Path, required=True)
    args = ap.parse_args()
    with tempfile.TemporaryDirectory(prefix="ga-shift-reg-") as temp:
        td = Path(temp)
        (td / "game.toml").write_text(CONFIG)
        (td / "test.bin").write_bytes(build_rom())
        p = subprocess.run([str(args.recompiler.resolve()), "test.bin", "--game", "game.toml",
                            "--output-dir", "generated"], cwd=td, capture_output=True, text=True)
        if p.returncode:
            raise RuntimeError(f"recompilador falhou ({p.returncode})\n{p.stdout}\n{p.stderr}")
        code = "\n".join(f.read_text() for f in sorted((td / "generated").glob("sh_part*.c")))
        used = [int(n) for n in re.findall(r"2\*\(\(int\)\(g_cpu\.D\[(\d)\] & 63u\) - 4\)\)", code)]
        assert sorted(used) == [1, 3], (
            f"a correção deveria ler a contagem (d1 e d3), leu d{sorted(used)}.\n"
            "Causa provável: `w0 & 7` em vez de `(w0 >> 9) & 7` em emit_cycle_drift_correction.")
    print("PASS: a correção de ciclos de deslocamento lê o registrador da contagem (d1, d3)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
