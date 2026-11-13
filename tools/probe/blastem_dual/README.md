# blastem_dual: mesmo teste no BlastEm (referencia) e no recomp, quadro a quadro

Ferramentas da rodada 3b (2026-11-12). Os caminhos estao fixos em `C:\tmp\ga_tests` (copie a ROM para `C:\tmp\ga_tests\bl\ga.bin` e o Release para `C:\tmp\ga_tests\exe_r`/`exe_r2`).

- `gdbc.py`: cliente minimo do stub GDB do BlastEm (`blastem.exe ROM -D`, porta 1234). Le no maximo 255 bytes por pacote `m`.
- `bot.py blastem|recomp <exp> <saida> [save.bin|ram]`: liga o BlastEm (janela visivel) ou o recomp (oculto), chega ao gameplay e roda o experimento.
  - Entrada no BlastEm: breakpoint em `$344A` (`not.w d0` da leitura do controle, `loc_33FC`), troca D0 por `~mascara`. Uma parada por quadro para o P1, exata.
  - Transplante: no BlastEm para em `$DB4` (espera do VBlank) e grava os 64 KB da RAM, menos a pilha (`$FFFB00-$FFFCFF`). Do save do recomp a RAM sai do offset `0x66`.
  - Experimentos: `boot`, `snap` (RAM no 1o contato com inimigos), `replay`, `atk` (borda esquerda batendo), `pit2` (buraco da fase 3), `pit7` (buraco da fase 7), `p2atk` (2 jogadores, P2 batendo; `P2_IDLE=1` deixa o P2 parado apanhando), `p2mag` (magia do P2 com o P1 parado), `demo` (demonstracao sem entrada, sem boot).
  - Entrada do P2 (`step2`): no mesmo breakpoint, segunda parada com `a0 = $FFC178`.
  - Scripts do recomp: `mkpit7.py`, `mkp2atk.py [idle]`, `mkp2mag.py`, `mkdemo.py`; `cmppit7.py` compara a fase 7. A escrita na RAM no mesmo quadro do `LOAD_STATE` se perde no recomp: escreva tambem no quadro seguinte.
- No recomp o teste exato usa script de entrada (`mkatk.py`, `mkpit2.py`: `LOAD_STATE` + `HOLD`/`RELEASE` por quadro + `DUMP_RAM`); `cmpatk.py`/`cmppit.py` comparam com o log do BlastEm.
- Limite do runner: 4096 diretivas por script.
- Rodada 5: `bot.py blastem demoram` (RAM `$FFC000-$FFFFFF` por leitura do controle durante a demo, `DEMO_N` quadros), `mkdemo2.py A B` (DUMP_RAM por quadro no recomp, ate ~2000 quadros por script) e `cmpdemo.py` (compara as demos alinhando por `$FFC17A`). Ver `notes/bughunt-2026-11-12-r5.md`.
