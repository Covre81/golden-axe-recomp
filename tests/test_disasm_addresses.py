#!/usr/bin/env python3
"""Confere endereços do game.toml e do spec contra o ga.asm (Rev A).

O ga.asm é conteúdo da Sega e nunca entra no repositório. Aponte para ele com
GA_ASM=<caminho>; sem isso o teste PULA (é o caso da CI). Não monta o ga.asm
(regra da Fase 0): só lê o texto.

1. Todo endereço de [functions].extra com rótulo loc_X começa numa instrução,
   não em dado (dc.*). Promover dado a função corrompe o codegen.
2. Endereço sem rótulo só passa se estiver em SEM_ROTULO, com o motivo. Um
   endereço novo sem rótulo (ex.: erro de digitação) faz o teste falhar.
3. Os 4 ganchos de espera caem no bne do loop: a sequência de instruções a
   partir do rótulo bate com a que deu o endereço (tamanhos somados à mão).

    GA_ASM=C:/caminho/ga.asm python tests/test_disasm_addresses.py
"""
import os
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Rotinas com nome (não loc_X) ou alvos internos sem rótulo; endereço vem do
# vetor/listagem do Garland, não dá para provar sem montar.
SEM_ROTULO = {
    0x000ABE: "EntryPoint (vetor de reset)",
    0x000C76: "GameLoop",
    0x000CE6: "HBlank (vetor IRQ4)",
    0x000CF6: "VBlank (vetor IRQ6)",
    0x0005A6: "alvo interno na ROM baixa, sem rótulo no ga.asm",
    0x0088C4: "alvo interno, sem rótulo no ga.asm",
}

# gancho: (rótulo do topo do loop, instruções até o bne inclusive, bytes até o bne)
GANCHOS = {
    0x000DB4: ("loc_DA8", [r"move\.b\s+d0, \$FFFFC183\.w", r"andi\s+#\$F8FF, sr",
                           r"move\.b\s+\$FFFFC183\.w, d0", r"bne\.s\s+-"], 4 + 4 + 4),
    0x002CE4: ("loc_2CDE", [r"move\.w\s+\(a5\), d4", r"btst\s+#1, d4", r"bne\.s\s+loc_2CDE"], 2 + 4),
    0x00903C: ("loc_9032", [r"move\.w\s+\$00C00004, d4", r"btst\s+#1, d4", r"bne\.s\s+loc_9032"], 6 + 4),
}
# $2C4A não tem rótulo próprio: é o bne final de loc_2C00, logo antes de loc_2C4E.
FIM_2C00 = [r"move\.w\s+\(a5\), d4", r"btst\s+#1, d4", r"bne\.s\s+-", r"rts", r"loc_2C4E:"]


def code_lines(asm: list[str], start: int) -> list[str]:
    """Linhas de código a partir de start, sem comentários, vazias e o rótulo anônimo '-'."""
    out = []
    for line in asm[start:start + 40]:
        s = line.split(";")[0].strip()
        if s and s != "-":
            out.append(re.sub(r"\s+", " ", s) if not s.endswith(":") else s)
    return out


def matches(lines: list[str], patterns: list[str]) -> bool:
    return len(lines) >= len(patterns) and all(re.fullmatch(p.replace(r"\s+", " "), l)
                                               for p, l in zip(patterns, lines))


def main() -> int:
    path = os.environ.get("GA_ASM")
    if not path or not Path(path).is_file():
        print("SKIP: defina GA_ASM com o caminho do ga.asm (Rev A) para rodar")
        return 0
    asm = Path(path).read_text(encoding="latin-1").splitlines()
    label_at = {m.group(1).upper(): i for i, l in enumerate(asm) if (m := re.match(r"loc_([0-9A-Fa-f]+):", l))}
    errors = []

    toml = tomllib.loads((ROOT / "game/game.toml").read_text(encoding="utf-8"))
    for addr in toml["functions"]["extra"]:
        i = label_at.get(f"{addr:X}")
        if i is None:
            if addr not in SEM_ROTULO:
                errors.append(f"${addr:06X}: sem rótulo loc_{addr:X} no ga.asm e fora de SEM_ROTULO")
            continue
        first = code_lines(asm, i + 1)[0]
        if first.startswith(("dc.", "even", "include", "binclude")) or first.endswith(":"):
            errors.append(f"${addr:06X}: loc_{addr:X} começa em '{first}', não numa instrução")
    for addr in SEM_ROTULO:
        if addr not in toml["functions"]["extra"]:
            errors.append(f"${addr:06X}: está em SEM_ROTULO mas saiu do game.toml (limpe a lista)")

    for addr, (label, seq, offset) in GANCHOS.items():
        i = label_at.get(label[4:].upper())
        if i is None or not matches(code_lines(asm, i + 1), seq):
            errors.append(f"gancho ${addr:06X}: {label} não tem a sequência esperada até o bne")
        elif int(label[4:], 16) + offset != addr:
            errors.append(f"gancho ${addr:06X}: {label}+{offset} = ${int(label[4:], 16) + offset:06X}")
    # $2C4A = loc_2C4E - rts(2) - bne.s(2)
    i = label_at.get("2C4E")
    tail = code_lines(asm[:i + 1], i - 8)[-5:] if i else []
    if not i or not matches(tail, FIM_2C00):
        errors.append("gancho $002C4A: fim de loc_2C00 não é move/btst/bne/rts antes de loc_2C4E")

    if errors:
        print("FALHOU:\n  " + "\n  ".join(errors))
        return 1
    n = len(toml["functions"]["extra"])
    print(f"PASS: {n - len(SEM_ROTULO)} funções com rótulo começam em instrução; "
          f"{len(SEM_ROTULO)} sem rótulo justificadas; 4 ganchos caem no bne")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())  # ignora --recompiler do run_all.py: não usa o recompilador
