# recomp: demonstracao sem entrada, DUMP_RAM a cada 2 quadros dos quadros 3000 a 6000 (igual ao exp demo do bot.py)
lines = ['WAIT 3000']
for t in range(3000, 6000, 2):
    lines.append(r'DUMP_RAM C:\tmp\ga_tests\bl\demo_rc\ram_%04d.bin' % t); lines.append('WAIT 2')
lines.append('EXIT 0')
open(r'C:\tmp\ga_tests\bl\demo.input', 'w').write('\n'.join(lines) + '\n'); print(len(lines))
