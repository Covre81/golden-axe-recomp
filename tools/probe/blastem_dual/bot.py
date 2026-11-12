"""Bot igual para BlastEm (GDB, quadro a quadro) e recomp (TCP). Uso:
python bot.py blastem|recomp <exp> <out_dir> [snapshot.ram]
exp: boot (chega no gameplay e salva RAM), pit (anda p/ direita matando inimigos), edge (fica na borda esquerda batendo)
"""
import sys, os, time, json, socket, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
emu, exp, out = sys.argv[1], sys.argv[2], sys.argv[3]
snap = sys.argv[4] if len(sys.argv) > 4 else None
os.makedirs(out, exist_ok=True)
LOG = open(os.path.join(out, 'bot.log'), 'w')
def L(*a):
    LOG.write(' '.join(str(x) for x in a) + '\n'); LOG.flush()
UP, DOWN, LEFT, RIGHT, B, C, A, START = 1, 2, 4, 8, 0x10, 0x20, 0x40, 0x80
SKIP_LO, SKIP_HI = 0xFFFB00, 0xFFFD00   # pilha: nao transplantar

class Blast:
    def __init__(s):
        from gdbc import GDB
        s.p = subprocess.Popen([r'C:\Dev\golden-axe-assets\blastem\blastem.exe', r'C:\tmp\ga_tests\bl\ga.bin', '-D'], cwd=r'C:\tmp\ga_tests\bl',
            stdout=open(os.path.join(out, 'blastem.out'), 'w'), stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
        open(os.path.join(out, 'blastem.pid'), 'w').write(str(s.p.pid))
        s.g = GDB(); s.g.send('Z0,344a,2'); s.frame = 0; s.mask = 0
    def step(s, mask):
        """roda ate a proxima leitura do P1 (1 quadro) aplicando mask no P1"""
        while True:
            r = s.g.send('c')
            a0 = int(s.g.send('p8'), 16)
            if (a0 & 0xFFFFFF) == 0xFFC176:
                s.g.send('P0=%08x' % ((~mask) & 0xFF)); s.frame += 1; return
    def rd(s, a, n):
        o = b''
        while n > 0:
            k = min(n, 0x100); d = s.g.rd(a, k)
            if not d: raise RuntimeError('gdb read %x' % a)
            o += d; a += len(d); n -= len(d)
        return o
    def wr(s, a, d): return s.g.wr(a, d)
    def transplant(s, ram):
        s.g.send('z0,344a,2'); s.g.send('Z0,db4,2'); s.g.send('c')
        a7 = int(s.g.send('p f'.replace(' ', '')), 16); L('transplant at db4, a7', hex(a7))
        for a in range(0, 0x10000, 0x80):
            addr = 0xFF0000 + a
            if SKIP_LO <= addr < SKIP_HI: continue
            s.g.wr(addr, ram[a:a+0x80])
        chk = s.rd(0xFFD000, 0x80); L('transplant check', chk == ram[0xD000:0xD080])
        s.g.send('z0,db4,2'); s.g.send('Z0,344a,2')
    def snap_db4(s):
        s.g.send('z0,344a,2'); s.g.send('Z0,db4,2'); s.g.send('c')
        ram = s.rd(0xFF0000, 0x10000)
        s.g.send('z0,db4,2'); s.g.send('Z0,344a,2'); return ram
    def shot(s, name): pass
    def close(s):
        try: s.g.send('z0,344a,2'); s.g.send('D')
        except Exception: pass
        time.sleep(0.5); s.p.kill()

class Recomp:
    def __init__(s, exe_dir=r'C:\tmp\ga_tests\exe_r', port=4415):
        open(os.path.join(exe_dir, 'debug.ini'), 'w').write('# temporario (executor)\nport=%d\n' % port)
        env = dict(os.environ, LNG_SCRIPT='1', LNG_TEST_HIDDEN='1', SDL_AUDIODRIVER='dummy')
        s.p = subprocess.Popen([os.path.join(exe_dir, 'GoldenAxeRecomp.exe'), 'goldenaxe.bin', '--no-launcher', '--port', str(port), '--max-frames', '400000'],
            cwd=exe_dir, env=env, creationflags=0x08000000, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=open(os.path.join(out, 'run.err'), 'w'))
        open(os.path.join(out, 'game.pid'), 'w').write(str(s.p.pid))
        t0 = time.time()
        while True:
            try: s.sock = socket.create_connection(('127.0.0.1', port), timeout=5); break
            except OSError:
                if time.time() - t0 > 30: raise
                time.sleep(0.3)
        s.buf = b''; s.nid = 0; s.last = s.ping(); s.frame = 0
    def cmd(s, **kw):
        s.nid += 1; kw['id'] = s.nid; s.sock.sendall((json.dumps(kw) + '\n').encode())
        while True:
            while b'\n' in s.buf:
                line, s.buf = s.buf.split(b'\n', 1)
                try: r = json.loads(line)
                except Exception: continue
                if r.get('id') == s.nid: return r
            d = s.sock.recv(65536)
            if not d: raise EOFError
            s.buf += d
    def ping(s): return s.cmd(cmd='ping')['frame']
    def step(s, mask):
        s.cmd(cmd='set_input', keys='%X' % mask)
        while True:
            f = s.ping()
            if f != s.last: s.frame += f - s.last; s.last = f; return
            time.sleep(0.002)
    def rd(s, a, n):
        out_ = b''
        while n > 0:
            k = min(n, 0x200); d = bytes.fromhex(s.cmd(cmd='read_memory', addr=hex(a), size=k)['hex']); assert d, hex(a); out_ += d; a += len(d); n -= len(d)
        return out_
    def wr(s, a, d): s.cmd(cmd='write_memory', addr=hex(a), hex=d.hex())
    def shot(s, name): s.cmd(cmd='screenshot', path=os.path.join(out, name))
    def close(s):
        try: s.cmd(cmd='quit')
        except Exception: pass
        time.sleep(2)
        if s.p.poll() is None: s.p.kill()

E = Blast() if emu == 'blastem' else Recomp(os.environ.get('BOT_EXE', r'C:\tmp\ga_tests\exe_r2'), int(os.environ.get('BOT_PORT', '4415')))

def state():
    m = E.rd(0xFFC172, 2); return (m[1] & 0x7C)

# ---- chegar ao gameplay (1 jogador, Ax) ----
def boot():
    f0 = E.frame; nextp = 380
    while True:
        st = state()
        p = E.rd(0xFFD000, 0x48)
        if st == 0x0C and not hasattr(E, '_fc'): E._fc = E.frame
        if st == 0x0C and (p[0] & 0x80) and p[0x42:0x44] == b'\0\0' and (E.rd(0xFFC104, 2)[1] & 2) and E.frame - E._fc > 300: break
        if E.frame // 120 != getattr(E, '_lb', -1): E._lb = E.frame // 120; L('boot f', E.frame, 'st', hex(st), 'C104', E.rd(0xFFC104, 2).hex(), 'D000', p[0:4].hex(), 'st42', p[0x42:0x44].hex())
        mask = 0
        if st != 0x0C and E.frame >= nextp:
            mask = START
            if E.frame >= nextp + 5: nextp = E.frame + 120
        E.step(mask)
        if E.frame - f0 > 9000: L('boot timeout'); return False
    L('gameplay at frame', E.frame); return True

def snapshot(path):
    ram = E.rd(0xFF0000, 0x10000); open(path, 'wb').write(ram); L('snapshot', path)

hp0 = {}; seen = {}
def kill_enemies(sl):
    for i in range(8):
        s = sl[i*0x80:(i+1)*0x80]
        if not (s[0] & 0x80): seen.pop(i, None); continue
        key = (i, s[0] & 0x7F)
        if key not in seen: seen[key] = E.frame; hp0[key] = s[0x64]
        if hp0.get(key, 1) == 0: continue
        if E.frame - seen[key] > 30 and s[0x64] != 0:
            E.wr(0xFFD100 + i*0x80 + 0x64, b'\x00'); E.wr(0xFFD100 + i*0x80 + 0x18, b'\x03\x00')
            L('kill', key, 'f', E.frame)

def rec(tag, p, extra=''):
    lv = E.rd(0xFFFE7C, 4)
    L(tag, 'f', E.frame, 'x', p[0x1C:0x1E].hex(), 'y', p[0x18:0x1A].hex(), 'z', p[0x20:0x22].hex(), 'g24', p[0x24:0x26].hex(), 'st42', p[0x42:0x44].hex(), 'f3', '%02x' % p[3], 'lives', lv.hex(), extra)

if not boot(): E.close(); sys.exit(1)
if exp == 'boot':
    snapshot(os.path.join(out, 'stage1_gameplay.ram')); E.close(); sys.exit(0)
if snap:
    ram = open(snap, 'rb').read()
    if snap.endswith('.bin'): ram = ram[0x66:0x66 + 0x10000]   # save do recomp: RAM no offset 0x66
    if emu == 'recomp' and snap.endswith('.bin'):
        L('load_state', E.cmd(cmd='load_state', path=snap)); E.last = E.ping()
    elif emu == 'blastem': E.transplant(ram)
    elif not snap.endswith('.bin'):
        for a in range(0, 0x10000, 0x400):
            if not (SKIP_LO <= 0xFF0000 + a < SKIP_HI): E.wr(0xFF0000 + a, ram[a:a+0x400])
    L('transplanted', snap, 'at', E.frame)
    if exp not in ('replay', 'atk', 'pit2'):
        for _ in range(30): E.step(0)
f_start = E.frame; prev = None; deaths = 0; lastlv = None
def compact(p):
    sl = p[0x100:]
    en = ' '.join('%d:%02x,%s,%s,%s,%02x' % (i, sl[i*0x80] & 0x7F, sl[i*0x80+0x1C:i*0x80+0x1E].hex(), sl[i*0x80+0x20:i*0x80+0x22].hex(), sl[i*0x80+0x42:i*0x80+0x44].hex(), sl[i*0x80+0x64]) for i in range(4) if sl[i*0x80] & 0x80)
    return 'P %s,%s,%s,%s,%02x | %s' % (p[0x1C:0x1E].hex(), p[0x18:0x1A].hex(), p[0x20:0x22].hex(), p[0x42:0x44].hex(), p[3], en)
if exp == 'snap':
    while True:
        p = E.rd(0xFFD000, 0x500); sl = p[0x100:]
        if any((sl[i*0x80] & 0x80) and sl[i*0x80+0x64] > 0 for i in range(8)): break
        E.step(RIGHT)
    for _ in range(20): E.step(0)
    ram = E.snap_db4() if emu == 'blastem' else E.rd(0xFF0000, 0x10000)
    open(os.path.join(out, 'met.ram'), 'wb').write(ram); L('snap met f', E.frame); E.close(); sys.exit(0)
def sched(t):
    if t < 600: return LEFT
    return (B if t % 12 < 3 else 0) | (LEFT if t % 60 < 4 else 0)
def psched(t):
    if t < 240: return UP | LEFT
    if t < 640: return DOWN | LEFT
    return 0
if exp == 'pit2':
    t = 0
    while t < 1300:
        p = E.rd(0xFFD000, 0x60); lv = E.rd(0xFFFE7C, 1); cam = E.rd(0xFFC20C, 6)
        L('r', t, 'x', p[0x1C:0x1E].hex(), 'y', p[0x18:0x1A].hex(), 'z', p[0x20:0x22].hex(), 'g24', p[0x24:0x26].hex(), 'st42', p[0x42:0x44].hex(), 'f3', '%02x' % p[3], 'lv', lv.hex(), 'cam', cam.hex())
        E.step(psched(t)); t += 1
    L('end'); E.close(); sys.exit(0)
if exp == 'atk':
    SHIFT = int(os.environ.get('ATK_SHIFT', '0'))
    t = 0
    while t < 1260:
        p = E.rd(0xFFD000, 0x500)
        L('r', t, compact(p))
        if t % 60 == 0: E.wr(0xFFFE7E, b'\x30')
        E.step(sched(t + SHIFT)); t += 1
    L('end'); E.close(); sys.exit(0)
if exp == 'replay':
    E.wr(0xFFFE7E, b'\x30')
    last = None; n = 0
    while E.frame - f_start < 900:
        p = E.rd(0xFFD000, 0x500)
        c = compact(p)
        L('r', E.frame - f_start, c)
        E.wr(0xFFFE7E, b'\x30'); E.wr(0xFFFE7C, b'\x09')
        E.step(LEFT)
if exp == 'pit':
    while E.frame - f_start < 3000 and deaths < 3:
        p = E.rd(0xFFD000, 0x500); sl = p[0x100:]
        kill_enemies(sl)
        lv = E.rd(0xFFFE7C, 1)[0]
        key = (p[0x1C:0x1E], p[0x42:0x44], p[0x24:0x26])
        if key != prev: rec('s', p); prev = key
        if lastlv is not None and lv < lastlv: deaths += 1; L('DEATH', deaths, 'f', E.frame)
        if lv < 3: E.wr(0xFFFE7C, b'\x09'); lv = 9
        lastlv = lv
        E.step(RIGHT if p[0x42:0x44] == b'\0\0' else 0)
elif exp == 'edge':
    # fica colado na borda esquerda, virado p/ esquerda, batendo; registra quem acerta quem
    lastf3 = 0; lasthp = {}
    while E.frame - f_start < 5400:
        p = E.rd(0xFFD000, 0x500); sl = p[0x100:]
        E.wr(0xFFFE7E, b'\x30'); E.wr(0xFFFE7C, b'\x09')
        if (p[3] & 0x40) and not (lastf3 & 0x40):
            ens = [(i, sl[i*0x80] & 0x7F, sl[i*0x80+0x1C:i*0x80+0x1E].hex(), sl[i*0x80+0x20:i*0x80+0x22].hex()) for i in range(8) if sl[i*0x80] & 0x80]
            L('P1 HIT f', E.frame, 'px', p[0x1C:0x1E].hex(), 'pz', p[0x20:0x22].hex(), 'enemies', ens)
        lastf3 = p[3]
        for i in range(8):
            s = sl[i*0x80:(i+1)*0x80]
            if not (s[0] & 0x80): lasthp.pop(i, None); continue
            hp = s[0x64]
            if i in lasthp and hp < lasthp[i]:
                L('ENEMY HIT f', E.frame, 'slot', i, 'id', '%02x' % (s[0] & 0x7F), 'ex', s[0x1C:0x1E].hex(), 'ez', s[0x20:0x22].hex(), 'hp', lasthp[i], '->', hp, 'px', p[0x1C:0x1E].hex())
            lasthp[i] = hp
        t = E.frame
        alive = [i for i in range(8) if (sl[i*0x80] & 0x80) and sl[i*0x80+0x64] > 0]
        if not hasattr(E, '_met'):
            if alive: E._met = t; L('enemies met f', t, 'px', p[0x1C:0x1E].hex())
            m = RIGHT
        elif p[0x1C:0x1E] > b'\x00\xb0' and t - E._met < 300: m = LEFT
        else: m = (B if t % 12 < 3 else 0) | (LEFT if t % 60 < 4 else 0)
        E.step(m)
L('end f', E.frame); E.close()
