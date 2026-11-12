# script do recomp para o buraco da fase 7 (igual ao exp pit7 do bot.py; t=0 no quadro do LOAD_STATE)
lines = ['WAIT 200', r'LOAD_STATE C:\tmp\ga_tests\s7\stage7_start.bin', 'HOLD RIGHT']
for t in range(0, 1300):
    if t == 1100: lines.append('RELEASE RIGHT')
    if t % 60 == 0: lines.append('WRITE_RAM8 0xFFFE7C 0x09')
    if t % 2 == 0: lines.append(r'DUMP_RAM C:\tmp\ga_tests\bl\pit7_rc\ram_%04d.bin' % t)
    lines.append('WAIT 1')
lines.append('EXIT 0')
open(r'C:\tmp\ga_tests\bl\pit7.input', 'w').write('\n'.join(lines) + '\n'); print(len(lines))
