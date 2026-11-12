# script do recomp quadro a quadro, igual ao sched() do bot (t=0 no quadro do LOAD_STATE)
LEFT, B = 'LEFT', 'B'
lines = ['WAIT 200', r'LOAD_STATE C:\tmp\ga_tests\bl\met_crafted.bin']
def sched(t):
    if t < 600: return {'LEFT'}
    m = set()
    if t % 12 < 3: m.add('B')
    if t % 60 < 4: m.add('LEFT')
    return m
held = set()
for t in range(0, 1260):
    want = sched(t)
    for b in sorted(held - want): lines.append('RELEASE ' + b)
    for b in sorted(want - held): lines.append('HOLD ' + b)
    held = want
    if t % 60 == 0: lines.append('WRITE_RAM8 0xFFFE7E 0x30')
    if t % 100 == 0 or t in (1259,): lines.append(r'DUMP_RAM C:\tmp\ga_tests\bl\atk_rc\ram_%04d.bin' % t)
    lines.append('WAIT 1')
lines.append('EXIT 0')
open(r'C:\tmp\ga_tests\bl\atk.input', 'w').write('\n'.join(lines) + '\n'); print(len(lines))
