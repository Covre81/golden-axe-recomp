import glob,os
def comp(ram):
    o=0xD000; p=ram[o:o+0x500]; sl=p[0x100:]
    en=' '.join('%d:%02x,%s,%s,%s,%02x'%(i,sl[i*0x80]&0x7F,sl[i*0x80+0x1C:i*0x80+0x1E].hex(),sl[i*0x80+0x20:i*0x80+0x22].hex(),sl[i*0x80+0x42:i*0x80+0x44].hex(),sl[i*0x80+0x64]) for i in range(4) if sl[i*0x80]&0x80)
    return 'P %s,%s,%s,%s,%02x | %s'%(p[0x1C:0x1E].hex(),p[0x18:0x1A].hex(),p[0x20:0x22].hex(),p[0x42:0x44].hex(),p[3],en)
bl={}
for l in open(r'atk_bl\bot.log'):
    if l.startswith('r '): k,rest=l[2:].split(' ',1); bl[int(k)]=rest.strip()
for f in sorted(glob.glob(r'atk_rc\ram_*.bin')):
    t=int(os.path.basename(f)[4:8]); c=comp(open(f,'rb').read())
    match=[k for k in range(t-4,t+5) if bl.get(k)==c]
    print(t,'RC',c); print('   BL',bl.get(t),'match at',match)
# HP do inimigo 0 e 1 ao longo do tempo no BlastEm
prev=None
for k in sorted(bl):
    hp=bl[k].split('| ')[1]
    if prev and hp.count(',')==prev.count(','):
        a=[x.split(',')[-1] for x in prev.split()]; b=[x.split(',')[-1] for x in hp.split()]
        if a!=b: print('BL hp change t',k,hp)
    prev=hp
