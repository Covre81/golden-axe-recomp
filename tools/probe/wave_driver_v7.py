"""Driver TCP v7 = v6 + modo --real-hp (vida e vidas de verdade, sem modo deus).
Uso: python -I wave_driver_v7.py <exe_dir> <out_dir> <port> <timeout_s> [--real-hp] [flags do jogo] [LOAD=<save.bin>]
--keep-lives: com --real-hp, HP de verdade mas vidas voltam a 9 (testa golpes/mortes sem game over por queda).
--shot-every=N: tira um print a cada N quadros em <saida>\shots (para medir cenas/dialogos).
--save-delay=N: salva o stageN_start.bin N quadros depois do 1o quadro de gameplay da fase (padrao 0 = como no v6).
Com --real-hp o driver NAO escreve $FFFE7C/$FFFE7E; registra cada perda de vida/HP (deaths) e game over.
Inimigos e chefes continuam sendo mortos pela RAM (mesmo caminho de morte do v6).
Inimigo: HP=0 + Y=$0300 (o jogo remove fora da tela, loc_B44A). Chefe: HP=0 + $4C=$18 (morte do chefe, $12080).
Nao escreva $401A em +$42: so vale para quem tem o estado $40 na tabela; nos outros o jmp cai no meio de
uma instrucao ($AA8C, $12944, $12E0E, $12128 = tabela + $40). Ver README.md.
"""
import socket, subprocess, sys, time, json, os, shutil
exe_dir, out, port, timeout = sys.argv[1], sys.argv[2], int(sys.argv[3]), float(sys.argv[4])
REAL_HP = '--real-hp' in sys.argv[5:]
KEEP_LIVES = '--keep-lives' in sys.argv[5:]  # com --real-hp: HP de verdade, mas vidas sempre 9 (o robo cai em buracos)
SHOT_EVERY = int(([a.split('=',1)[1] for a in sys.argv[5:] if a.startswith('--shot-every=')] or ['0'])[0])  # print a cada N quadros (0 = desligado)
SAVE_DELAY = int(([a.split('=',1)[1] for a in sys.argv[5:] if a.startswith('--save-delay=')] or ['0'])[0])
extra = [a for a in sys.argv[5:] if not a.startswith('LOAD=') and a not in ('--real-hp', '--keep-lives') and not a.startswith('--save-delay=') and not a.startswith('--shot-every=')]
load = ([a[5:] for a in sys.argv[5:] if a.startswith('LOAD=')] or [None])[0]
os.makedirs(out, exist_ok=True)
here = os.path.dirname(os.path.abspath(__file__))
args = [os.path.join(exe_dir, 'GoldenAxeRecomp.exe'), 'goldenaxe.bin', '--port', str(port),
        '--max-frames', '400000', '--input-script', os.path.join(here, 'wave_load.input' if load else 'wave_full.input'),
        '--mem-write-log', '0xFFC2A2-0xFFC2A5,0xFFC17C,0xFFC0B8-0xFFC0BF@400000'] + extra
proc = subprocess.Popen(args, cwd=exe_dir, stderr=open(os.path.join(out, 'run.err'), 'w'), stdout=subprocess.DEVNULL)
log = open(os.path.join(out, 'driver.log'), 'w')
def L(*a):
    log.write(' '.join(str(x) for x in a) + '\n'); log.flush()
t0 = time.time(); sock = None
while time.time() - t0 < 30:
    try: sock = socket.create_connection(('127.0.0.1', port), timeout=2); break
    except OSError: time.sleep(0.3)
if not sock: L('no tcp'); proc.kill(); sys.exit(2)
sock.settimeout(10); buf = b''; nid = [0]
PID_FILE = os.path.join(out, 'game.pid'); open(PID_FILE, 'w').write(str(proc.pid))
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
def wr(a, d): cmd(cmd='write_memory', addr=hex(a), hex=d.hex())
RIGHT, LEFT, B, START = 0x08, 0x04, 0x10, 0x80
if load:
    while cmd(cmd='ping')['frame'] < 120: time.sleep(0.2)
    r = cmd(cmd='load_state', path=load); L('load_state', load, r)
saved_stages = set(); block_shots = 0
hp0 = {}
BOSSES = {0x3F, 0x40, 0x41, 0x4A, 0x4B, 0x4C}
NAV = [RIGHT if False else 0x08, 0x09, 0x0A, 0x01, 0x02, 0x05, 0x06, 'JUMP', 0x04]
wx = [None, 0, 0, 0]; seen = {}; killed = {}; despawned = {}; last_px = None; px_change = 0; freeze_flagged = False; last_fr = -1; same_fr_since = time.time(); stderr_flags = 0; gos = []; cur = None; tick = 0; started = False
last_gameplay = 0; prev_a3 = 0; result = 'timeout'; last_stage = None; armed_logged = False
stage_first = {}; last_lives = None; last_hp = None; deaths = 0; hp_hits = 0; min_hp = 999; max_stage = 0
last_shot = [-1]
L('mode', 'REAL_HP' if REAL_HP else 'GOD')
try:
    while time.time() - t0 < timeout:
        if proc.poll() is not None: result = 'exe exited %s' % proc.returncode; break
        fr = cmd(cmd='ping')['frame']
        g = rd(0xFFC172, 2); state = int.from_bytes(g, 'big') & 0x7C
        st = rd(0xFFC26C, 8); c26c = int.from_bytes(st[0:2], 'big'); c272 = int.from_bytes(st[6:8], 'big')
        c2a2 = rd(0xFFC2A2, 4); stage = rd(0xFFFE2D, 1)[0]
        tick += 1
        if stage != last_stage: L('stage idx', stage, 'at', fr, 'state', hex(state)); last_stage = stage
        if started and stage < max_stage and state != 0x24: L('STAGE WENT BACK (game over/restart?)', max_stage, '->', stage, 'at', fr); cmd(cmd='screenshot', path=os.path.join(out, 'back_%06d.png' % fr)); result = 'GAME OVER/RESTART at frame %d (max stage idx %d)' % (fr, max_stage); break
        max_stage = max(max_stage, stage)
        if REAL_HP and started:
            lv = rd(0xFFFE7C, 1)[0]; hpv = rd(0xFFFE7E, 1)[0]
            if last_lives is not None and lv < last_lives:
                deaths += 1; L('DEATH', deaths, 'lives', last_lives, '->', lv, 'at', fr, 'stage', stage); cmd(cmd='screenshot', path=os.path.join(out, 'death_%06d.png' % fr))
            if last_hp is not None and hpv < last_hp and state == 0x0C: hp_hits += 1
            if state == 0x0C: min_hp = min(min_hp, hpv)
            last_lives = lv; last_hp = hpv
        if load and not started: started = True; L('started from load at', fr)
        if not started:
            if rd(0xFFD042, 2) == b'\x00\x00' and fr > 2600: started = True; L('control at', fr)
            time.sleep(0.03); continue
        if fr != last_fr: last_fr = fr; same_fr_since = time.time()
        if SHOT_EVERY and fr // SHOT_EVERY != last_shot[0]:
            last_shot[0] = fr // SHOT_EVERY; os.makedirs(os.path.join(out, 'shots'), exist_ok=True); cmd(cmd='screenshot', path=os.path.join(out, 'shots', 's_%06d.png' % fr))
        elif time.time() - same_fr_since > 15: result = 'HANG: frame stuck at %d' % fr; cmd(cmd='screenshot', path=os.path.join(out, 'hang_%06d.png' % fr)); break
        if state == 0x0C and cur is None:
            px = rd(0xFFD000 + 0x1C, 2) + rd(0xFFD000 + 0x18, 2)
            if px != last_px: last_px = px; px_change = fr
            elif fr - px_change > 1800 and not freeze_flagged:
                freeze_flagged = True; L('POSSIBLE FREEZE: player pos unchanged since', px_change, 'now', fr, 'stage', stage)
                cmd(cmd='screenshot', path=os.path.join(out, 'freeze_%06d.png' % fr))
            elif fr - px_change > 5400: result = 'FREEZE: no player movement for 5400 frames at %d' % fr; break
            if fr - px_change < 60: freeze_flagged = False
        # GO! capture (C2A3 bit7 rising = loc_274C started the GO! flash)
        a3 = c2a2[1]
        if (a3 & 0x80) and not (prev_a3 & 0x80):
            cur = {'n': len(gos) + 1, 'start': fr, 'stage': stage, 'shots': 0, 'eq': True, 'gold': False}
            gos.append(cur); os.makedirs(os.path.join(out, 'go%d' % cur['n']), exist_ok=True)
            L('GO#%d start' % cur['n'], 'frame', fr, 'stage', stage, 'C2A2', c2a2.hex())
            cmd(cmd='set_input', keys='0')
        prev_a3 = a3
        if cur is not None:
            blk = rd(0xFFC080, 0x80).hex(); cram = cmd(cmd='read_cram')['hex'].lower()
            eq = blk == cram; cur['eq'] &= eq
            if blk[112:128] == '00000088' + '00cc0eee': cur['gold'] = True
            L('cap GO#%d f' % cur['n'], fr, 'C2A2', c2a2.hex(), 'pal==cram', eq, 'palL1', blk[64:128], 'cramL1', cram[64:128])
            if cur['shots'] < 14:
                cmd(cmd='screenshot', path=os.path.join(out, 'go%d' % cur['n'], 'go_%06d.png' % fr)); cur['shots'] += 1
            if fr - cur['start'] > 90: L('GO#%d end' % cur['n'], cur); cur = None
            time.sleep(0.005); continue
        if state == 0x0C:
            last_gameplay = fr
            stage_first.setdefault(stage, fr)
            if stage not in saved_stages and fr - stage_first[stage] >= SAVE_DELAY:
                saved_stages.add(stage); p_ = os.path.join(out, 'stage%d_start.bin' % (stage + 1)); L('save_state', p_, cmd(cmd='save_state', path=p_), 'at', fr)
            if REAL_HP and KEEP_LIVES and rd(0xFFFE7C, 1)[0] < 3:
                wr(0xFFFE7C, bytes([9])); last_lives = 9
            if not REAL_HP:
                mx = rd(0xFFFE35, 1)[0] * 16 + 0x30
                wr(0xFFFE7C, bytes([9])); wr(0xFFFE7E, bytes([mx]))
            slots = rd(0xFFD100, 0x400)
            for kk in list(killed):
                if not (slots[kk[0]*0x80] & 0x80) or (slots[kk[0]*0x80] & 0x7F) != kk[1]:
                    killed.pop(kk); seen.pop(kk, None); despawned.pop(kk, None); hp0.pop(kk, None)
            alive = []
            for i in range(8):
                s = slots[i*0x80:(i+1)*0x80]
                if s[0] & 0x80:
                    key = (i, s[0] & 0x7F)
                    if hp0.get(key, 1) != 0: alive.append(key)
                    first = seen.setdefault(key, fr); k = killed.get(key)
                    if key not in hp0 and fr == first: hp0[key] = s[0x64]
                    if hp0.get(key, 1) == 0:
                        continue  # entidade sem HP ao nascer (cena/porta/objeto): nao mexer
                    if (k is None and fr - first > 60) or (k is not None and fr - k[0] > 400):
                        if key[1] in BOSSES:
                            # chefe: HP=0 e flag "recebeu dano" (+3 bit6); o codigo do chefe vai para o estado $0C (golpe)
                            wr(0xFFD100 + i*0x80 + 0x64, b'\x00'); wr(0xFFD100 + i*0x80 + 0x4C, b'\x18')  # estado $18 = morte do chefe (loc_12080: subq C26C)
                        else:
                            wr(0xFFD100 + i*0x80 + 0x64, b'\x00'); wr(0xFFD100 + i*0x80 + 0x18, b'\x03\x00')
                        killed[key] = (fr, (k[1] + 1) if k else 1)
                        L('kill', key, 'at', fr, 'try', killed[key][1])
            if (c2a2[0] & 0x80) and not armed_logged: L('armed', c2a2.hex(), 'at', fr, 'C26C', c26c); armed_logged = True
            if not (c2a2[0] & 0x80): armed_logged = False
            if tick % 40 == 0: L('f', fr, 'stage', stage, 'C26C', c26c, 'C272', c272, 'C2A2', c2a2.hex(), 'alive', alive)
            if False:
                pass
            elif not alive and c26c == 0:
                xw = rd(0xFFD000 + 0x1C, 2)
                if xw != wx[0]: wx[0] = xw; wx[1] = fr
                if fr - wx[1] > 120 and fr - wx[2] > 200:
                    wx[3] = (wx[3] + 1) % len(NAV); wx[2] = fr
                    yv = rd(0xFFD000 + 0x18, 2)
                    L('walk blocked at', fr, 'x', xw.hex(), 'y', yv.hex(), 'nav ->', NAV[wx[3]])
                    if block_shots < 12:
                        cmd(cmd='screenshot', path=os.path.join(out, 'blocked_%06d.png' % fr)); block_shots += 1
                vert = 0
                nav = NAV[wx[3]]
                keys = nav if nav != 'JUMP' else (RIGHT | (0x20 if tick % 8 < 2 else 0))
                if nav != 'JUMP' and (tick // 15) % 4 == 3: keys = 0
            else:
                d = RIGHT if (tick // 25) % 2 == 0 else LEFT
                keys = (B if tick % 2 == 0 else 0) | (d if tick % 6 < 2 else 0)
            cmd(cmd='set_input', keys='%X' % keys)
        else:
            if tick % 40 == 0: L('nongame f', fr, 'state', hex(state), 'stage', stage)
            # fora do gameplay ha muito tempo (mapa/dialogo/descanso): pulso de START
            if state == 0x24 and tick % 60 == 0: cmd(cmd='screenshot', path=os.path.join(out, 'ending_%06d.png' % fr))
            if state != 0x24 and fr - last_gameplay > 900 and tick % 30 == 0:
                cmd(cmd='set_input', keys='80'); cmd(cmd='set_input', keys='0'); L('START pulse at', fr, 'state', hex(state))
            else:
                cmd(cmd='set_input', keys='0')
        time.sleep(0.015)
finally:
    L('result', result, 'gos', [(x['n'], x['start'], x['stage'], x['eq'], x['gold']) for x in gos])
    L('summary mode', 'REAL_HP' if REAL_HP else 'GOD', 'deaths', deaths, 'hp_hits', hp_hits, 'min_hp', min_hp, 'max_stage_idx', max_stage)
    try: cmd(cmd='quit')
    except Exception: pass
    time.sleep(2)
    if proc.poll() is None: proc.kill()
    try: shutil.copy(os.path.join(exe_dir, 'mem_write_log_native.log'), os.path.join(out, 'mem_write_log.log'))
    except Exception as e: L('copy log failed', e)
print(result, [(x['n'], x['start'], x['stage'], x['eq'], x['gold']) for x in gos])