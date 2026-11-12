lines = ["# 2 jogadores: P1 pelo driver TCP, P2 por este script (gerado por make_two_player_input.py)",
"# No titulo, quem aperta START primeiro decide: P2 primeiro = modo 2 PLAYERS (ga.asm loc_39DE/loc_3A10, $FFC104=$13).",
"WAIT 400","PLAYER 2","PRESS START 5","PLAYER 1",
"WAIT 60","PRESS START 5",      # menu: ARCADE
"WAIT 120","PRESS START 5",     # select: P1 confirma
"WAIT 120","PLAYER 2","PRESS START 5","PLAYER 1",  # select: P2 confirma
"WAIT 60","PRESS START 5",
"WAIT 1400","WAIT_RAM16 0xFFD042 0x0000","PLAYER 2"]
import random
# O runner aceita no maximo 4096 diretivas (MAX_OPS em input_script.c); passando disso o script
# inteiro e recusado e o jogo roda sem entrada. Segmentos longos cobrem ~50 mil quadros.
random.seed(7)
while len(lines) < 4000:
    d = random.choice(["RIGHT","RIGHT","RIGHT","LEFT","UP","DOWN"])
    n = random.randint(30, 120)
    lines += ["HOLD "+d, "WAIT %d" % n, "PRESS B 4", "WAIT 8", "PRESS B 4", "WAIT 8", "PRESS B 4", "RELEASE "+d]
    if random.random() < 0.08: lines += ["PRESS C 3", "WAIT 30"]
lines += ["EXIT 0"]
assert len(lines) <= 4096
open(r"two_player.input", "w").write("\n".join(lines) + "\n")
print(len(lines))