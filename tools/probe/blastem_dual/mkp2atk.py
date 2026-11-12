# script do recomp para o exp p2atk do bot.py (t=0 no quadro do LOAD_STATE)
import sys
IDLE = len(sys.argv) > 1 and sys.argv[1] == 'idle'
OUT = 'p2i_rc' if IDLE else 'p2_rc'
lines = ['WAIT 200', r'LOAD_STATE C:\tmp\ga_tests\p2\p2_met.bin']
def m1(t): return {'LEFT'} if t < 150 else set()
def m2(t):
    if t < 30: return {'RIGHT'}
    s = set()
    if IDLE: return s
    if t % 12 < 3: s.add('B')
    if t % 60 < 4: s.add('RIGHT')
    return s
held = {1: set(), 2: set()}
for t in range(0, 1200):
    for pn, fn in ((1, m1), (2, m2)):
        want = fn(t)
        if want != held[pn]:
            lines.append('PLAYER %d' % pn)
            for b in sorted(held[pn] - want): lines.append('RELEASE ' + b)
            for b in sorted(want - held[pn]): lines.append('HOLD ' + b)
            held[pn] = want
    if t % 60 == 0:
        lines += ['WRITE_RAM8 0xFFFE7E 0x30', 'WRITE_RAM8 0xFFFE8E 0x30', 'WRITE_RAM8 0xFFFE7C 0x03', 'WRITE_RAM8 0xFFFE8C 0x03']
    if t % 2 == 0: lines.append(r'DUMP_RAM C:\tmp\ga_tests\bl\%s\ram_%04d.bin' % (OUT, t))
    lines.append('WAIT 1')
lines.append('EXIT 0')
assert len(lines) <= 4096, len(lines)
open(r'C:\tmp\ga_tests\bl\%s.input' % ('p2idle' if IDLE else 'p2atk'), 'w').write('\n'.join(lines) + '\n'); print(len(lines))
