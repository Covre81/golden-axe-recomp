# script do recomp para o exp p2mag do bot.py (t=0 no quadro do LOAD_STATE)
lines = ['WAIT 200', r'LOAD_STATE C:\tmp\ga_tests\p2\p2_met.bin', 'PLAYER 1', 'HOLD LEFT']
for t in range(0, 600):
    if t == 150: lines += ['PLAYER 1', 'RELEASE LEFT']
    if t == 20: lines += ['PLAYER 2', 'HOLD A']
    if t == 24: lines += ['PLAYER 2', 'RELEASE A']
    if t in (0, 1): lines.append('WRITE_RAM8 0xFFFE90 0x03')
    if t % 60 == 0: lines += ['WRITE_RAM8 0xFFFE7E 0x30', 'WRITE_RAM8 0xFFFE8E 0x30']
    lines.append(r'DUMP_RAM C:\tmp\ga_tests\bl\mag_rc\ram_%04d.bin' % t)
    lines.append('WAIT 1')
lines.append('EXIT 0')
open(r'C:\tmp\ga_tests\bl\p2mag.input', 'w').write('\n'.join(lines) + '\n'); print(len(lines))
