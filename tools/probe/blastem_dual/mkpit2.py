lines = ['WAIT 200', r'LOAD_STATE C:\tmp\ga_tests\godr\stage3_start.bin', 'HOLD UP', 'HOLD LEFT']
for t in range(0, 1300):
    if t == 240: lines += ['RELEASE UP', 'HOLD DOWN']
    if t == 640: lines += ['RELEASE DOWN', 'RELEASE LEFT']
    if t % 2 == 0: lines.append(r'DUMP_RAM C:\tmp\ga_tests\bl\pit_rc2\ram_%04d.bin' % t)
    lines.append('WAIT 1')
lines.append('EXIT 0')
open(r'C:\tmp\ga_tests\bl\pit2.input', 'w').write('\n'.join(lines) + '\n'); print(len(lines))
