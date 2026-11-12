"""Tabela de atraso do áudio do recomp contra o BlastEm, janela a janela (só o essencial de cmp_audio.py).

Uso: python -I audio_lag.py <recomp.wav> <blastem.raw> [t_ini=4] [t_fim=48] [janela_s=2]
Imprime o atraso do recomp (em quadros de 1/59,94 s; + = recomp atrasado, - = adiantado) por janela e
o tamanho de cada degrau. O .raw é float32 estéreo 48 kHz (SDL_AUDIODRIVER=disk no BlastEm).
Aviso: o atraso vem do envelope do som, não de eventos do 68000. Serve para comparar builds entre si.
"""
import sys, wave
import numpy as np

SR, ENV, FPS = 48000, 100, 59.94


def load_wav(p):
    w = wave.open(p, "rb")
    sr, ch = w.getframerate(), w.getnchannels()
    x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").reshape(-1, ch).mean(1) / 32768.0
    k = max(1, int(sr / SR))
    x = np.convolve(x, np.ones(k) / k, mode="same")
    t = np.arange(int(len(x) * SR / sr)) * (sr / SR)
    return np.interp(t, np.arange(len(x)), x)


def env(x):
    n = SR // ENV
    m = len(x) // n
    return np.sqrt((x[: m * n].reshape(m, n) ** 2).mean(1))


def main(wav, raw, t0=4, t1=48, win=2):
    er = env(load_wav(wav))
    ef = env(np.fromfile(raw, dtype="<f4").reshape(-1, 2).mean(1).astype(np.float64))
    W, rows, prev, worst = int(win * ENV), [], None, 0.0
    for s0 in range(int(t0 * ENV), min(len(er), int(t1 * ENV)) - W, W):
        a = er[s0:s0 + W]
        best = (0, -2.0)
        for d in range(-150, 151):
            b0 = s0 + d
            if b0 < 0 or b0 + W > len(ef):
                continue
            b = ef[b0:b0 + W]
            if a.std() < 1e-9 or b.std() < 1e-9:
                continue
            c = np.corrcoef(a, b)[0, 1]
            if c > best[1]:
                best = (d, c)
        lag = -best[0] / ENV
        step = "" if prev is None else f"  degrau {(lag - prev) * FPS:+.1f} q" if abs(lag - prev) * FPS >= 2 else ""
        if prev is not None and best[1] > 0.8:
            worst = max(worst, abs(lag - prev) * FPS)
        rows.append((s0 / ENV, lag, best[1]))
        print(f"t={s0/ENV:5.0f}s  atraso {lag:+.2f}s ({lag*FPS:+5.1f} q)  corr {best[1]:.2f}{step}")
        prev = lag if best[1] > 0.8 else prev
    good = [r for r in rows if r[2] > 0.8]
    if good:
        print(f"resumo: primeiro {good[0][1]*FPS:+.1f} q -> ultimo {good[-1][1]*FPS:+.1f} q "
              f"(variacao {(good[-1][1]-good[0][1])*FPS:+.1f} quadros em {good[-1][0]-good[0][0]:.0f} s)")
    ok = worst < 3.0
    print(("VERDE" if ok else "VERMELHO") + f": maior degrau entre janelas {worst:.1f} quadros (limite 3)")
    return 0 if ok else 1


if __name__ == "__main__":
    a = sys.argv[1:]
    sys.exit(main(a[0], a[1], *(float(x) for x in a[2:])))
