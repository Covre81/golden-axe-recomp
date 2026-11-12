"""Asserção do laço do GO!: o sprite "GO!" + espada deve aparecer dourado.

Uso: python -I check_go.py <png...>
Sai 0 (verde) se em pelo menos um PNG a região do GO! tem bastante amarelo
e nada de roxo/magenta; sai 1 (vermelho) caso contrário. Imprime as cores
dominantes da região para diagnóstico.
"""
import sys
from collections import Counter
from PIL import Image

# Região do GO! em 320x224 (medida em go_08.png): canto superior direito.
X0, X1, Y0, Y1 = 225, 305, 40, 85

def is_yellow(r, g, b):   # tons dourados $0088/$00CC/$0EEE no DAC
    return r > 150 and g > 120 and b < 110
def is_purple(r, g, b):   # "roxo" relatado: magenta/violeta
    return r > 100 and b > 100 and g < 90

def analyse(path):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    sx, sy = w / 320, h / 224
    box = (int(X0 * sx), int(Y0 * sy), int(X1 * sx), int(Y1 * sy))
    px = list(im.crop(box).getdata())
    yellow = sum(is_yellow(*p) for p in px)
    purple = sum(is_purple(*p) for p in px)
    top = Counter(px).most_common(6)
    return yellow, purple, top

def main(paths):
    best = None
    for p in paths:
        y, pu, top = analyse(p)
        print(f"{p}: amarelo={y} roxo={pu} top={[(c, n) for c, n in top]}")
        if best is None or y > best[1]:
            best = (p, y, pu)
    p, y, pu = best
    ok = y >= 60 and pu == 0
    print(("VERDE" if ok else "VERMELHO") + f": melhor quadro {p} amarelo={y} roxo={pu}")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
