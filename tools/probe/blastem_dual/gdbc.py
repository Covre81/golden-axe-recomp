import socket, subprocess, time, sys, os
class GDB:
    def __init__(s, port=1234):
        t0=time.time()
        while True:
            try: s.s=socket.create_connection(('127.0.0.1',port),timeout=10); break
            except OSError:
                if time.time()-t0>20: raise
                time.sleep(0.3)
        s.buf=b''
    def _recv_pkt(s):
        while True:
            i=s.buf.find(b'$')
            if i>=0:
                j=s.buf.find(b'#',i)
                if j>=0 and len(s.buf)>=j+3:
                    data=s.buf[i+1:j]; s.buf=s.buf[j+3:]; s.s.sendall(b'+'); return data.decode(errors='replace')
            d=s.s.recv(65536)
            if not d: raise EOFError
            s.buf+=d
    def send(s, cmd, wait=True):
        pkt=b'$'+cmd.encode()+b'#'+('%02x'%(sum(cmd.encode())&0xFF)).encode()
        s.s.sendall(pkt)
        return s._recv_pkt() if wait else None
    def rd(s,a,n):
        r=s.send('m%x,%x'%(a&0xFFFFFF,n)); return bytes.fromhex(r)
    def wr(s,a,data): return s.send('M%x,%x:%s'%(a&0xFFFFFF,len(data),data.hex()))
