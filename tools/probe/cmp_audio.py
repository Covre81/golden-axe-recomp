"""Compara o WAV do recomp com o raw do BlastEm (float32 estéreo 48 kHz, via SDL_AUDIODRIVER=disk).
Uso: python -I cmp_audio.py <recomp.wav> <blastem.raw>
Mede: atraso e deriva de tempo (envelope), afinação (picos do espectro) e timbre (energia por oitava).
"""
import sys, wave
import numpy as np

SR = 48000
ENV = 100  # Hz do envelope


def load_wav(p):
    w = wave.open(p, "rb")
    sr, ch = w.getframerate(), w.getnchannels()
    x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").reshape(-1, ch).mean(1) / 32768.0
    # reamostra p/ 48 kHz: média móvel (passa-baixa simples) + interpolação linear
    k = max(1, int(sr / SR))
    x = np.convolve(x, np.ones(k) / k, mode="same")
    t = np.arange(int(len(x) * SR / sr)) * (sr / SR)
    return np.interp(t, np.arange(len(x)), x)


def load_raw(p):
    return np.fromfile(p, dtype="<f4").reshape(-1, 2).mean(1).astype(np.float64)


def env(x):
    n = SR // ENV
    m = len(x) // n
    return np.sqrt((x[: m * n].reshape(m, n) ** 2).mean(1))


def best_lag(a, b, maxlag):
    """lag (em amostras do envelope) que melhor casa b[i+lag] com a[i]; devolve (lag, correlação)."""
    a = (a - a.mean()) / (a.std() + 1e-12)
    b = (b - b.mean()) / (b.std() + 1e-12)
    best = (0, -2.0)
    for lag in range(-maxlag, maxlag + 1):
        if lag >= 0:
            n = min(len(a), len(b) - lag); c = (a[:n] * b[lag:lag + n]).mean() if n > 50 else -2
        else:
            n = min(len(a) + lag, len(b)); c = (a[-lag:-lag + n] * b[:n]).mean() if n > 50 else -2
        if c > best[1]:
            best = (lag, c)
    return best


def peaks(x, k=6):
    s = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    f = np.fft.rfftfreq(len(x), 1 / SR)
    out = []
    s = s.copy()
    for _ in range(k):
        i = int(s.argmax())
        if s[i] <= 0: break
        out.append((f[i], s[i]))
        lo, hi = max(0, i - 40), i + 40
        s[lo:hi] = 0
    return sorted(out)


rec, ref = load_wav(sys.argv[1]), load_raw(sys.argv[2])
print(f"recomp {len(rec)/SR:.1f}s rms={np.sqrt((rec**2).mean()):.4f} pico={abs(rec).max():.3f}")
print(f"blastem {len(ref)/SR:.1f}s rms={np.sqrt((ref**2).mean()):.4f} pico={abs(ref).max():.3f}")
er, ef = env(rec), env(ref)


def first_sound(e):
    i = np.nonzero(e > 0.02 * e.max())[0]
    return i[0] / ENV if len(i) else None


print(f"primeiro som: recomp {first_sound(er)}s, blastem {first_sound(ef)}s")
lag, c = best_lag(er, ef, 15 * ENV)
print(f"alinhamento global: blastem atrasado {lag/ENV:+.2f}s em relação ao recomp, correlação do envelope {c:.3f}")
# deriva: alinhamento por janelas de 10 s
print("deriva por janela de 10 s (atraso local, correlação):")
W = 10 * ENV
for s0 in range(0, len(er) - W + 1, W):
    b0 = s0 + lag
    if b0 < 0 or b0 + W > len(ef): continue
    l2, c2 = best_lag(er[s0:s0 + W], ef[max(0, b0 - 100):b0 + W + 100], 0)
    best = (0, -2)
    for d in range(-100, 101):
        if b0 + d < 0 or b0 + d + W > len(ef): continue
        a = er[s0:s0 + W]; b = ef[b0 + d:b0 + d + W]
        cc = np.corrcoef(a, b)[0, 1] if a.std() > 1e-9 and b.std() > 1e-9 else -2
        if cc > best[1]: best = (d, cc)
    print(f"  t={s0/ENV:5.0f}s  desvio {best[0]/ENV:+.2f}s  corr {best[1]:.3f}  rms rec {er[s0:s0+W].mean():.4f} ref {ef[b0:b0+W].mean():.4f}")
# afinação e timbre em janelas de 2 s alinhadas
off = int(lag / ENV * SR)
bands = [(2 ** i * 62.5, 2 ** (i + 1) * 62.5) for i in range(8)]
print("picos do espectro (Hz) e energia por oitava (dB recomp - blastem), janelas de 2 s:")
for t0 in range(0, int(len(rec) / SR) - 2, 6):
    a = rec[t0 * SR:(t0 + 2) * SR]
    b0 = t0 * SR + off
    if b0 < 0 or b0 + 2 * SR > len(ref): continue
    b = ref[b0:b0 + 2 * SR]
    if np.sqrt((a ** 2).mean()) < 1e-4 and np.sqrt((b ** 2).mean()) < 1e-4: continue
    pa, pb = peaks(a), peaks(b)
    sa, sb = np.abs(np.fft.rfft(a)) ** 2, np.abs(np.fft.rfft(b)) ** 2
    f = np.fft.rfftfreq(len(a), 1 / SR)
    g = 10 * np.log10(sa.sum() / (sb.sum() + 1e-20) + 1e-20)
    d = [10 * np.log10(sa[(f >= lo) & (f < hi)].sum() / (sb[(f >= lo) & (f < hi)].sum() + 1e-20) + 1e-20) - g for lo, hi in bands]
    print(f"  t={t0:3d}s nivel {g:+.1f} dB")
    print("     rec:", " ".join(f"{p[0]:.0f}" for p in pa))
    print("     ref:", " ".join(f"{p[0]:.0f}" for p in pb))
    print("     oitavas 62Hz..8kHz (relativo):", " ".join(f"{x:+.1f}" for x in d))
