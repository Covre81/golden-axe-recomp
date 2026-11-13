#!/usr/bin/env python3
"""Gera o zip de release do Golden Axe Recomp (Windows).

    python tools/make_release.py            # compila em build-release/ e empacota
    python tools/make_release.py --no-build # so empacota o que ja esta la

Precisa da ROM em game/goldenaxe.bin: o codigo do jogo e gerado a partir dela na
compilacao, por isso nao da para fazer isto no GitHub Actions. A ROM NAO entra
no zip: quem monta o zip e o empacotador do motor
(segagenesisrecomp/tools/package_release.py), que usa lista de permitidos e
recusa ROM, saves e logs. Regras em segagenesisrecomp/RELEASING.md.

Saida: release/GoldenAxeRecomp-v<versao>-win64.zip
"""
import argparse
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / "segagenesisrecomp"
BUILD = ROOT / "build-release"
OUT_DIR = BUILD / "Release"
# Producao: sem servidor de depuracao nem aneis de diagnostico (RELEASING.md item 5).
PROD_FLAGS = ["-DGEN_ENABLE_TRACE=OFF", "-DSONIC_REVERSE_DEBUG=OFF", "-DGEN_DEV_TRACE=OFF"]


def run(*cmd):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], cwd=ROOT, check=True)


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, check=True,
                          capture_output=True, text=True).stdout.strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--no-build", action="store_true", help="nao recompila; so empacota")
    args = ap.parse_args()

    if not (ROOT / "game" / "goldenaxe.bin").is_file():
        sys.exit("ERRO: falta a ROM em game/goldenaxe.bin")

    # O zip deve corresponder a um commit. Mudanca local fora do commit vira aviso.
    dirty = git("status", "--porcelain")
    if dirty:
        print("AVISO: ha mudancas fora do commit; o zip nao corresponde exatamente "
              "ao que esta no GitHub:\n" + dirty, flush=True)

    if not args.no_build:
        run("cmake", "-S", ".", "-B", BUILD, "-G", "Visual Studio 17 2022", "-A", "x64",
            *PROD_FLAGS)
        run("cmake", "--build", BUILD, "--config", "Release",
            "--target", "GoldenAxeRecomp", "--parallel")

    info_path = OUT_DIR / "build-info.json"
    info = json.loads(info_path.read_text(encoding="utf-8"))
    bad = [k for k in ("trace", "reverse_debug", "dev_trace") if info[k] != "OFF"]
    if bad:
        sys.exit(f"ERRO: build nao e de producao ({', '.join(bad)} ligado em {info_path})")
    head = git("rev-parse", "HEAD")
    if info["source_commit"] != head:
        sys.exit(f"ERRO: o exe e do commit {info['source_commit'][:7]}, o repo esta em "
                 f"{head[:7]}; rode sem --no-build")

    out = ROOT / "release" / f"GoldenAxeRecomp-v{info['version']}-win64.zip"
    run(sys.executable, "-I", ENGINE / "tools" / "package_release.py",
        "--exe", OUT_DIR / "GoldenAxeRecomp.exe",
        "--extra", OUT_DIR / "SDL2.dll", info_path,
        "--asset-dir", OUT_DIR / "assets",
        "--license", ROOT / "LICENSE.md",
        "--notices", ENGINE / "THIRD-PARTY-LICENSES.md",
        "--readme", ROOT / "release" / "README.txt",
        "--out", out)

    with zipfile.ZipFile(out) as z:
        names = z.namelist()
    print(f"\nOK: {out} ({out.stat().st_size / 1e6:.1f} MB, {len(names)} arquivos)")
    for n in names:
        print("  ", n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
