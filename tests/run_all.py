#!/usr/bin/env python3
"""Roda todos os tests/test_*.py. Não precisa de ROM.

Compila o GenesisRecomp em build/recompiler se ainda não existir (ou com
--rebuild) e passa --recompiler para cada teste. Contrato: todo test_*.py
aceita --recompiler e sai com código != 0 quando falha.

    python tests/run_all.py [--rebuild]
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build" / "recompiler"
EXE = BUILD / "Release" / "GenesisRecomp.exe" if sys.platform == "win32" else BUILD / "GenesisRecomp"
# ponytail: caminho do VS Build Tools só como reserva quando o cmake não está no PATH
VS_CMAKE = Path(r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\IDE"
                r"\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe")


def cmake() -> str:
    found = shutil.which("cmake") or (str(VS_CMAKE) if VS_CMAKE.exists() else None)
    if not found:
        sys.exit("cmake não encontrado: instale o CMake ou o Visual Studio 2022 Build Tools")
    return found


def build_recompiler() -> None:
    src = ROOT / "segagenesisrecomp" / "recompiler"
    if not (src.parent / "external" / "m68k-recomp-core" / "profiles").exists():
        sys.exit("submódulos ausentes: veja o README (git submodule update --init ...)")
    gen = ["-G", "Visual Studio 17 2022", "-A", "x64"] if sys.platform == "win32" else ["-DCMAKE_BUILD_TYPE=Release"]
    subprocess.run([cmake(), "-S", str(src), "-B", str(BUILD), *gen], check=True)
    subprocess.run([cmake(), "--build", str(BUILD), "--config", "Release",
                    "--target", "GenesisRecomp", "--parallel"], check=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true")
    args = ap.parse_args()
    if args.rebuild or not EXE.exists():
        build_recompiler()

    failed = []
    for test in sorted((ROOT / "tests").glob("test_*.py")):
        print(f"== {test.name}", flush=True)
        if subprocess.run([sys.executable, str(test), "--recompiler", str(EXE)]).returncode:
            failed.append(test.name)
    total = len(list((ROOT / "tests").glob("test_*.py")))
    if failed:
        print(f"FALHOU {len(failed)}/{total}: {', '.join(failed)}")
        return 1
    print(f"OK {total}/{total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
