# recomp: demonstracao sem entrada, DUMP_RAM em todo quadro de A a B (para comparar com o exp demoram do bot.py)
import sys
A = int(sys.argv[1]) if len(sys.argv) > 1 else 3500
B = int(sys.argv[2]) if len(sys.argv) > 2 else 4900
lines = ['WAIT %d' % A]
for t in range(A, B):
    lines.append(r'DUMP_RAM C:\tmp\ga_tests\bl\demo2_rc\ram_%05d.bin' % t); lines.append('WAIT 1')
lines.append('EXIT 0')
assert len(lines) <= 4096
open(r'C:\tmp\ga_tests\bl\demo2.input', 'w').write('\n'.join(lines) + '\n'); print(len(lines))
