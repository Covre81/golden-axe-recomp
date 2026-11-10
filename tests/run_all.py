#!/usr/bin/env python3
"""Roda todos os tests/test_*.py. Não precisa de ROM.

Compila o GenesisRecomp em build/recompiler se ainda não existir (ou com
--rebuild) e passa --recompiler para cada teste. Contrato: todo test_*.py
aceita --recompiler e sai com código != 0 quando falha.

Com --engine, também compila e roda a suíte CTest do motor
(segagenesisrecomp/tests, ~130 testes de VDP, áudio, runtime e Sega CD).

    python tests/run_all.py [--rebuild] [--engine]
"""
import argparse
import os
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


ENGINE = ROOT / "segagenesisrecomp"
ENGINE_BUILD = ROOT / "build" / "engine-tests"
SDL2 = ENGINE / "runner" / "external" / "SDL2" / "SDL2-2.28.5"
# ponytail: falhas que o upstream já corrigiu depois da base do fork do Garland.
# Tirar daqui quando o submódulo segagenesisrecomp passar desses commits.
ENGINE_KNOWN_FAILURES = {
    "vdp_host_sprite": "mstan 76490c6 (2026-11-09) corrige a expectativa do teste",
    "vdp_host_sprite_batched": "mstan 76490c6 (2026-11-09) corrige a expectativa do teste",
}


def run_engine_tests(rebuild: bool) -> bool:
    if rebuild or not (ENGINE_BUILD / "CTestTestfile.cmake").exists():
        gen = (["-G", "Visual Studio 17 2022", "-A", "x64", f"-DSDL2_DIR={SDL2 / 'cmake'}"]
               if sys.platform == "win32" else ["-DCMAKE_BUILD_TYPE=Release"])
        subprocess.run([cmake(), "-S", str(ENGINE / "tests"), "-B", str(ENGINE_BUILD), *gen], check=True)
    subprocess.run([cmake(), "--build", str(ENGINE_BUILD), "--config", "Release", "--parallel"], check=True)

    env = dict(os.environ)
    if sys.platform == "win32":  # sem isso, os testes com SDL saem com 0xC0000135 (DLL ausente)
        env["PATH"] = str(SDL2 / "lib" / "x64") + os.pathsep + env["PATH"]
    ctest = str(Path(cmake()).with_name("ctest.exe" if sys.platform == "win32" else "ctest"))
    # Golden Axe é cartucho: os testes de Sega CD não dizem nada sobre ele, e dois
    # deles quebram na CI por caminho curto do Windows (RUNNER~1 vs runneradmin).
    skip = "^(segacd_.*|" + "|".join(ENGINE_KNOWN_FAILURES) + ")$"
    print(f"== motor: pulando Sega CD e {len(ENGINE_KNOWN_FAILURES)} falhas já corrigidas no upstream", flush=True)
    return subprocess.run([ctest, "--test-dir", str(ENGINE_BUILD), "-C", "Release", "-E", skip,
                           "--output-on-failure", "--timeout", "300", "-j4"], env=env).returncode == 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--engine", action="store_true", help="também roda a suíte CTest do motor")
    args = ap.parse_args()
    if args.rebuild or not EXE.exists():
        build_recompiler()

    failed = []
    if args.engine and not run_engine_tests(args.rebuild):
        failed.append("motor (ctest)")
    for test in sorted((ROOT / "tests").glob("test_*.py")):
        print(f"== {test.name}", flush=True)
        if subprocess.run([sys.executable, str(test), "--recompiler", str(EXE)]).returncode:
            failed.append(test.name)
    total = len(list((ROOT / "tests").glob("test_*.py"))) + args.engine
    if failed:
        print(f"FALHOU {len(failed)}/{total}: {', '.join(failed)}")
        return 1
    print(f"OK {total}/{total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
