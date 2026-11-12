import glob, os
def line(ram):
    p = ram[0xD000:0xD060]
    return 'x %s y %s z %s g24 %s st42 %s f3 %02x lv %s cam %s' % (p[0x1C:0x1E].hex(), p[0x18:0x1A].hex(), p[0x20:0x22].hex(), p[0x24:0x26].hex(), p[0x42:0x44].hex(), p[3], ram[0xFE7C:0xFE7D].hex(), ram[0xC20C:0xC212].hex())
rc = {int(os.path.basename(f)[4:8]): line(open(f, 'rb').read()) for f in glob.glob(r'pit_rc2\ram_*.bin')}
bl = {}
for l in open(r'pit_bl2\bot.log'):
    if l.startswith('r '): k, rest = l[2:].split(' ', 1); bl[int(k)] = rest.strip()
best = max(range(-3, 4), key=lambda o: sum(1 for k in rc if bl.get(k + o) == rc[k]))
same = sum(1 for k in rc if bl.get(k + best) == rc[k])
print('offset', best, 'identical', same, 'of', len(rc))
# eventos: mudancas de vidas e de estado do jogador
def events(d, tag):
    prev = None
    for k in sorted(d):
        v = d[k]; f = dict(zip(v.split()[0::2], v.split()[1::2]))
        key = (f['lv'], f['st42'][:2])
        if key != prev: print(tag, k, v); prev = key
events(rc, 'RC'); events(bl, 'BL')
diff = [k for k in sorted(rc) if bl.get(k + best) != rc[k]]
print('first diffs', diff[:10])
for k in diff[:3]: print(k, 'RC', rc[k]); print(k + best, 'BL', bl.get(k + best))
