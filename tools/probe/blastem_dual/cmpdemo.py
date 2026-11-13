# compara a demonstracao: BlastEm (bot.py demoram -> demo_c000.bin, uma copia de $FFC000-$FFFFFF por leitura do controle)
# com o recomp (mkdemo2.py -> ram_NNNNN.bin, RAM inteira por quadro). Alinha pelo contador de VBlank $FFC17A dentro de
# cada trecho com modo $8010 (demo) e compara X/Y/estado/HP dos objetos $FFD000.. com tolerancia de +-2 quadros
# (o BlastEm le a RAM no meio do quadro, na leitura do controle). Divergencia real = 4+ quadros seguidos sem casar.
# Uso: python cmpdemo.py <demo_c000.bin> <pasta com ram_*.bin>
import glob, os, sys
import numpy as np
bl = np.fromfile(sys.argv[1], dtype=np.uint8).reshape(-1, 0x4000)
rcf = sorted(glob.glob(os.path.join(sys.argv[2], 'ram_*.bin')))
rc = np.stack([np.fromfile(f, dtype=np.uint8)[0xC000:0x10000] for f in rcf])
def w(r, a): return int(r[a - 0xC000]) << 8 | int(r[a - 0xC000 + 1])
def keys(r):
    o = [0xD000 + i * 0x80 for i in range(10)]
    return [w(r, b + 0x1C) for b in o] + [w(r, b + 0x18) for b in o] + [w(r, b + 0x42) >> 8 for b in o] + [r[b + 0x64 - 0xC000] for b in o]
def demo_segs(arr):
    segs, cur = [], None
    for j in range(len(arr)):
        if w(arr[j], 0xC172) == 0x8010:
            if cur is None: cur = {}
            cur.setdefault(w(arr[j], 0xC17A), j)
        elif cur is not None: segs.append(cur); cur = None
    if cur: segs.append(cur)
    return segs
sb, sr = demo_segs(bl), demo_segs(rc)
print('trechos de demo: BlastEm %d, recomp %d' % (len(sb), len(sr)))
for n, (mb, mr) in enumerate(zip(sb, sr)):
    common = sorted(set(mb) & set(mr)); bad = {}
    for vb in common:
        ka = keys(bl[mb[vb]]); cands = [keys(rc[mr[v]]) for v in range(vb - 2, vb + 3) if v in mr]
        miss = [i for i in range(len(ka)) if all(c[i] != ka[i] for c in cands)]
        if miss: bad[vb] = miss
    run, pers = 0, None
    for vb in common:
        run = run + 1 if vb in bad else 0
        if run >= 4 and pers is None: pers = vb - 3
    print('demo %d: vb %d..%d (%d quadros), fim BL vb %d / RC vb %d, desencontros isolados %d, divergencia persistente: %s'
          % (n + 1, common[0], common[-1], len(common), max(mb), max(mr), len(bad), 'nenhuma' if pers is None else 'a partir de vb %d' % pers))
