import re
def load(p):
    d={}
    for l in open(p):
        if l.startswith('r '):
            k,rest=l[2:].split(' ',1); d[int(k)]=rest.strip()
    return d
bl=load(r'rep_bl2\bot.log'); rc=load(r'rep_rc2\bot.log')
def px(s): return int(s[2:6],16)
# melhor deslocamento pelo X do jogador nos primeiros 60 quadros
best=None
for off in range(-5,6):
    err=0;n=0
    for k,v in rc.items():
        if k>80: break
        if k+off in bl: err+=abs(px(bl[k+off])-px(v)); n+=1
    if n and (best is None or err/n<best[1]): best=(off,err/n)
print('offset',best)
off=best[0]; same=0; first=None
for k in sorted(rc):
    if k+off in bl:
        if bl[k+off]==rc[k]: same+=1
        elif first is None: first=k
print('identical samples',same,'of',len([k for k in rc if k+off in bl]),'first diff at rc frame',first)
for k in sorted(rc):
    if k+off in bl and (first is None or k>=first-14) and k<= (first or 0)+40:
        print(k,'RC',rc[k]); print(k+off,'BL',bl[k+off])
