#!/usr/bin/env python3
"""Os 4 loops de espera do Golden Axe cedem a vez por gancho do spec.

O motor não cede a vez em `move/btst/bne` (só em `tst/bcc`). O spec do
Garland resolve com `game_hook` no `bne` de cada loop; o `ga_instruction_hook`
chama glue_yield_for_interrupt_poll() quando o desvio vai ser tomado.
Endereços conferidos no ga.asm (Rev A):

    $DB4   loc_DA8   move.b $C183.w,d0 / bne        espera o VBlank
    $2C4A  loc_2C00  move.w (a5),d4 / btst #1 / bne  DMA do VDP (bug de controle)
    $2CE4  loc_2CDE  move.w (a5),d4 / btst #1 / bne  DMA do VDP
    $903C  loc_9032  move.w $C00004,d4 / btst / bne  DMA do VDP

Parte 1 (sem nada): game.toml e spec listam exatamente esses 4.
Parte 2 (--recompiler): game_hook num bne gera a chamada antes do desvio e
entra na tabela que o interpretador tier-3 consulta. Sem ROM.

    python tests/test_wait_loop_hooks.py [--recompiler <GenesisRecomp.exe>]
"""
import argparse
import re
import subprocess
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WAIT_SITES = {0x000DB4, 0x002C4A, 0x002CE4, 0x00903C}


def check_config() -> None:
    toml = tomllib.loads((ROOT / "game/game.toml").read_text(encoding="utf-8"))
    hooks = {s["addr"] for s in toml.get("widescreen_site", []) if s["kind"] == "game_hook"}
    assert WAIT_SITES <= hooks, f"game.toml sem game_hook em {sorted(map(hex, WAIT_SITES - hooks))}"

    spec = (ROOT / "game/goldenaxe_spec.c").read_text(encoding="utf-8")
    m = re.search(r"ga_instruction_hook\(uint32_t pc\)\s*\{\s*if \(([^{]*)\)\s*\{", spec)
    assert m, "ga_instruction_hook não encontrado no spec"
    in_spec = {int(x, 16) for x in re.findall(r"pc == 0x([0-9A-Fa-f]+)u", m.group(1))}
    assert in_spec == WAIT_SITES, f"spec cede em {sorted(map(hex, in_spec))}, esperado {sorted(map(hex, WAIT_SITES))}"


CONFIG = """[game]
output_prefix = "hk"
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
[[widescreen_site]]
addr = 0x000206
kind = "game_hook"
"""
# $200: move.w (a5),d4 / btst #1,d4 / bne.s $200 / rts  (mesma forma de loc_2CDE)
POLL = bytes.fromhex("3815 08040001 66f8 4e75")


def build_rom() -> bytes:
    rom = bytearray(b"\xff" * 0x400)
    rom[0:8] = bytes.fromhex("00fffe00 00000200")
    rom[0x100:0x200] = b" " * 256
    rom[0x100:0x104] = b"SEGA"
    rom[0x200:0x200 + len(POLL)] = POLL
    return bytes(rom)


def check_codegen(recompiler: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="ga-wait-hook-") as temp:
        td = Path(temp)
        (td / "game.toml").write_text(CONFIG)
        (td / "test.bin").write_bytes(build_rom())
        p = subprocess.run([str(recompiler.resolve()), "test.bin", "--game", "game.toml",
                            "--output-dir", "generated"], cwd=td, capture_output=True, text=True)
        if p.returncode:
            raise RuntimeError(f"recompilador falhou ({p.returncode})\n{p.stdout}\n{p.stderr}")
        gen = td / "generated"
        code = "\n".join(f.read_text() for f in sorted(gen.glob("hk_part*.c")))
        # O gancho tem que vir no bne, antes do desvio de volta ao topo do loop.
        assert re.search(r"/\* \$000206 \*/\s*if \(genesis_game_instruction_hook\(0x000206u\)\) return;"
                         r"[^$]*?goto label_000200;", code), "gancho não emitido antes do bne:\n" + code
        dispatch = (gen / "hk_dispatch.c").read_text()
        assert re.search(r"s_game_hook_sites\[\] = \{ 0x000206u", dispatch), \
            "site ausente da tabela do interpretador tier-3"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--recompiler", type=Path)
    args = ap.parse_args()
    check_config()
    print("PASS: game.toml e spec cedem nos 4 loops de espera")
    if args.recompiler:
        check_codegen(args.recompiler)
        print("PASS: game_hook no bne é emitido antes do desvio e vai para a tabela tier-3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
