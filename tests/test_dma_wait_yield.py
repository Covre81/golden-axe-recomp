#!/usr/bin/env python3
"""O loop de espera de DMA do Golden Axe (loc_2C00) precisa ceder a vez.

    move.w (a5),d4 / btst #1,d4 / bne.s <início>

Sem ceder, o código nativo gira para sempre: o status do VDP só muda quando o
runner avança o emulador. Sem ROM: monta uma ROM sintética, roda o recompilador
e confere o C gerado.

    python tests/test_dma_wait_yield.py --recompiler <GenesisRecomp.exe>
"""
import argparse
import re
import subprocess
import tempfile
from pathlib import Path

CONFIG = """[game]
output_prefix = "dma"
[functions]
extra = [0x200, 0x220]
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

# $200: move.w (a5),d4 / btst #1,d4 / bne.s $200 / rts   -> deve ceder
POLL_MEM = bytes.fromhex("3815 08040001 66f8 4e75")
# $220: move.w d3,d4 / btst #1,d4 / bne.s $220 / rts     -> NÃO deve ceder
# (origem é registrador: nada de hardware para esperar)
POLL_REG = bytes.fromhex("3803 08040001 66f8 4e75")


def build_rom() -> bytes:
    rom = bytearray(b"\xff" * 0x400)
    rom[0:8] = bytes.fromhex("00fffe00 00000200")
    rom[0x100:0x200] = b" " * 256
    rom[0x100:0x104] = b"SEGA"
    rom[0x200:0x200 + len(POLL_MEM)] = POLL_MEM
    rom[0x220:0x220 + len(POLL_REG)] = POLL_REG
    return bytes(rom)


def function_body(generated: Path, name: str) -> str:
    text = "\n".join(p.read_text() for p in sorted(generated.glob("dma_part*.c")))
    m = re.search(r"\n[^\n]*\b%s\s*\([^)]*\)\s*\{(.*?)\n\}" % name, text, re.S)
    if not m:
        raise AssertionError(f"{name} não foi gerada")
    return m.group(1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--recompiler", type=Path, required=True)
    args = ap.parse_args()
    with tempfile.TemporaryDirectory(prefix="ga-dma-wait-") as temp:
        td = Path(temp)
        (td / "game.toml").write_text(CONFIG)
        (td / "test.bin").write_bytes(build_rom())
        p = subprocess.run([str(args.recompiler.resolve()), "test.bin", "--game", "game.toml",
                            "--output-dir", "generated"], cwd=td, capture_output=True, text=True)
        if p.returncode:
            raise RuntimeError(f"recompilador falhou ({p.returncode})\n{p.stdout}\n{p.stderr}")
        gen = td / "generated"
        mem = function_body(gen, "func_000200")
        reg = function_body(gen, "func_000220")
        assert re.search(r"glue_yield_for_interrupt_poll\(\);\s*goto label_000200;", mem), \
            "loop move/btst/bne sobre memória não cede a vez:\n" + mem
        assert "glue_yield_for_interrupt_poll" not in reg, \
            "loop sobre registrador não deveria ceder:\n" + reg
    print("PASS: espera de DMA de 3 instruções cede; origem em registrador não")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
