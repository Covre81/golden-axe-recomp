#!/usr/bin/env python3
"""O quadro de audio do motor tem o tamanho do quadro NTSC real (896040 ciclos mestre).

Patch: patches/segagenesisrecomp-ntsc-frame-audio.patch (motor segagenesisrecomp f92e278).

1) Sem ROM (sempre): le runner/sim_step.c e runner/main.c e confere que
   GENESIS_SIM_WALL_FRAME_MASTER_CYCLES == 262*3420 e que o fps padrao do pacer e 53693175/896040.
2) Com --exe (precisa da ROM ao lado do exe): roda 600 quadros com --wav e confere
   que sai >= 3733 amostras PSG por quadro (hardware 3733,5; hoje sai 3732,0).

    python patches/test_segagenesisrecomp-ntsc-frame-audio.py [--engine segagenesisrecomp] [--exe build/game/Release/GoldenAxeRecomp.exe]
Nunca passe --help ao exe.
"""
import argparse, re, subprocess, tempfile, wave
from pathlib import Path

FRAMES = 600


def static_check(engine: Path) -> None:
    sim = (engine / "runner" / "sim_step.c").read_text(encoding="utf-8", errors="replace")
    m = re.search(r"#define\s+GENESIS_SIM_WALL_FRAME_MASTER_CYCLES\s+(\d+)u?", sim)
    assert m, "GENESIS_SIM_WALL_FRAME_MASTER_CYCLES nao encontrado em sim_step.c"
    assert int(m.group(1)) == 262 * 3420, (
        f"sim_step.c drena {m.group(1)} ciclos mestre por quadro; o NTSC real e {262*3420} (59,9227 Hz)")
    main = (engine / "runner" / "main.c").read_text(encoding="utf-8", errors="replace")
    assert "(53693175.0 / 896040.0)" in main, "main.c: fps padrao do pacer ainda nao e 53693175/896040"
    print("PASS (sem ROM): quadro de audio = 896040 ciclos mestre, pacer = 59,9227 fps")


def exe_check(exe: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="ga-ntsc-") as td:
        wav = Path(td) / "a.wav"
        p = subprocess.run([str(exe), "goldenaxe.bin", "--no-launcher", "--turbo", "--port", "4397",
                            "--max-frames", str(FRAMES), "--wav", str(wav)],
                           cwd=exe.parent, capture_output=True, text=True, timeout=600)
        w = wave.open(str(wav), "rb")
        n, sr = w.getnframes(), w.getframerate()
        w.close()
    spf = n / FRAMES
    hw = 53693175 / 240 / (53693175 / 896040)
    print(f"exe: {n} amostras em {FRAMES} quadros = {spf:.2f} por quadro (hardware {hw:.2f}, taxa {sr})")
    assert spf >= 3733.0, f"{spf:.2f} amostras por quadro: o audio do quadro ainda e o de 59,94 Hz (3732)"
    print("PASS (exe): amostras por quadro batem com o quadro NTSC real")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", type=Path, default=Path("segagenesisrecomp"))
    ap.add_argument("--exe", type=Path)
    a = ap.parse_args()
    static_check(a.engine)
    if a.exe:
        exe_check(a.exe.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())