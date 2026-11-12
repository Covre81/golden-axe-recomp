"""Teste de load de save, escondido (sem janela, sem foco, sem som).
Uso: set T_EXE_DIR=<copia do Release com debug.ini> & set T_PORT=<porta>
     python save_load_check.py <save.bin> <pasta_saida>
Carrega o save pela porta de debug, tira prints em +30/+150/+400 quadros,
anda 120 quadros para a direita e mostra C172/Y/X/fase. Se aparecer janela
visivel do jogo, mata o proprio processo (so o PID que ele abriu).
Rode sempre numa COPIA do Release (fora do repo), nunca na pasta do Bruno.
"""
import socket, subprocess, sys, time, json, os, ctypes
from ctypes import wintypes
from PIL import Image, ImageStat
EXE_DIR = os.environ.get('T_EXE_DIR', r'C:\tmp\savefix_test')
PORT = int(os.environ.get('T_PORT','4395'))
save, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
env = dict(os.environ, LNG_SCRIPT='1', LNG_TEST_HIDDEN='1', SDL_AUDIODRIVER='dummy')
args = [os.path.join(EXE_DIR, 'GoldenAxeRecomp.exe'), 'goldenaxe.bin', '--no-launcher', '--port', str(PORT),         '--max-frames', '400000', '--input-script', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wave_load.input'), '--mem-write-log', '0xFFC172-0xFFC173,0xFFD018-0xFFD01D@400000'] + (['--turbo'] if os.environ.get('T_TURBO') else [])
CREATE_NO_WINDOW = 0x08000000
proc = subprocess.Popen(args, cwd=EXE_DIR, env=env, creationflags=CREATE_NO_WINDOW,
                        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=open(os.path.join(out, 'run.err'), 'w'))
open(os.path.join(out, 'game.pid'), 'w').write(str(proc.pid))
log = open(os.path.join(out, 'test.log'), 'w')
def L(*a):
    s = ' '.join(str(x) for x in a); log.write(s + '\n'); log.flush(); print(s, flush=True)
u32 = ctypes.windll.user32
def visible_windows(pid):
    res = []
    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(h, l):
        p = wintypes.DWORD(); u32.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid and u32.IsWindowVisible(h): res.append(h)
        return True
    u32.EnumWindows(cb, 0); return res
def guard():
    v = visible_windows(proc.pid)
    if v:
        L('VISIBLE WINDOW -> kill', v); proc.kill(); sys.exit(3)
sock = None; t0 = time.time()
while time.time() - t0 < 30:
    guard()
    try: sock = socket.create_connection(('127.0.0.1', PORT), timeout=2); break
    except OSError: time.sleep(0.2)
if not sock: L('no tcp'); proc.kill(); sys.exit(2)
sock.settimeout(15); buf = b''; nid = [0]
def cmd(**kw):
    global buf
    nid[0] += 1; kw['id'] = nid[0]
    sock.sendall((json.dumps(kw) + '\n').encode())
    while True:
        while b'\n' in buf:
            line, buf = buf.split(b'\n', 1)
            try: r = json.loads(line)
            except Exception: continue
            if r.get('id') == nid[0]: return r
        d = sock.recv(65536)
        if not d: raise EOFError
        buf += d
def rd(a, n): return bytes.fromhex(cmd(cmd='read_memory', addr=hex(a), size=n)['hex'])
def shot(name):
    p = os.path.join(out, name); cmd(cmd='screenshot', path=p); time.sleep(0.3)
    try:
        im = Image.open(p).convert('L'); st = ImageStat.Stat(im)
        return p, round(st.mean[0], 1), im.getextrema()
    except Exception as e: return p, 'ERR', str(e)
def state():
    g = rd(0xFFC172, 2); return g.hex(), rd(0xFFD018, 2).hex(), rd(0xFFD01C, 2).hex(), rd(0xFFFE2D, 1)[0]
try:
    while cmd(cmd='ping')['frame'] < 120: guard(); time.sleep(0.1)
    guard()
    r = cmd(cmd='load_state', path=save); L('load_state', save, r); L('immediately after load: frame', cmd(cmd='ping')['frame'], 'C172', rd(0xFFC172,2).hex(), 'regs', cmd(cmd='get_registers'))
    for _k in range(12): L('  early f', cmd(cmd='ping')['frame'], 'C172', rd(0xFFC172,2).hex(), 'D018', rd(0xFFD018,6).hex()); time.sleep(0.03)
    f0 = cmd(cmd='ping')['frame']; L('f0', f0, 'C172/y/x/stage', state())
    marks = {30: 's030.png', 150: 's150.png', 400: 's400.png'}
    moved_phase = False; xs = []
    while True:
        guard()
        fr = cmd(cmd='ping')['frame']; d = fr - f0
        for k in sorted(marks):
            if d >= k: L('frame+%d' % d, 'C172/y/x/stage', state(), 'shot', shot(marks.pop(k)))
        if d >= 400 and not moved_phase:
            moved_phase = True; xa = state()[2]; cmd(cmd='set_input', keys='8'); fm = fr
        if moved_phase and fr - fm >= 120:
            cmd(cmd='set_input', keys='0'); xb = state()[2]
            L('walk right 120f: x', xa, '->', xb, 'state', state(), 'shot', shot('s_walk.png')); break
        if time.time() - t0 > 240: L('TIMEOUT'); break
        time.sleep(0.02)
finally:
    try: cmd(cmd='quit')
    except Exception: pass
    for _ in range(30):
        if proc.poll() is not None: break
        time.sleep(0.2)
    if proc.poll() is None: L('kill own pid', proc.pid); proc.kill()
    L('exit', proc.returncode)


