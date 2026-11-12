# Fase 1, continuação (2026-11-12, manhã): correção do motor aplicada, testes, itens 3 a 5

Marcas: [CONFIRMADO] medido ou lido no código; [PROVÁVEL] bem indicado, não provado; [INFERIDO] dedução.
Feito por outro agente (Grok Bot) a pedido do Bruno. Nada foi commitado.

## 1. Correção do deslocamento aplicada (só na cópia local)

- `patches/m68k-recomp-core-drift-shift-count-register.patch` aplicado com `git apply` em
  `segagenesisrecomp/external/m68k-recomp-core` (`profiles/genesis/code_generator.c:2121`, `w0 & 7` -> `(w0 >> 9) & 7`).
  **Sem commit** no submódulo nem no repo. Para desfazer:
  `git -C segagenesisrecomp/external/m68k-recomp-core checkout -- profiles/genesis/code_generator.c` e recompilar.
- Backup do exe antigo: `build\game\Release\GoldenAxeRecomp.prefix.exe` (hash `1EDFC8D9…`).
- Build: `cmake --build build\game --config Release` (a árvore real é `build\game`; `build\` sozinho não tem projeto). OK, 0 erros.
  Exe novo `36EA36E3…`. O C gerado mudou nos 7 deslocamentos (agora lê `D1`/`D7`, os registradores da contagem) [CONFIRMADO].
- Teste do patch (`patches/test_m68k-recomp-core-drift-shift-count-register.py --recompiler build\game\Release\GenesisRecomp.exe`): **PASS** contra o arquivo aplicado de verdade [CONFIRMADO].

## 2. Testes com o exe corrigido

| Teste | Resultado |
|---|---|
| GO! (paleta RAM = CRAM, dourado) | 27 GO!s do boot ao final + 11 + 6 nas rodadas de vida real: **todos dourados, paleta = CRAM**; `check_go.py` verde em todos [CONFIRMADO] |
| Rodada completa boot -> final (modo deus, `C:\tmp\shiftfix_full2`) | Chegou ao final (estado `$24`, quadro 63.382). Sem travamento, sem crash, controle sempre respondeu [CONFIRMADO]. O "POSSIBLE FREEZE" da fase 6 é a cena do rei e da princesa (diálogo, controle desligado de propósito), conferido por tela [CONFIRMADO] |
| Tempo do som contra o BlastEm (`audio_lag.py`, 7.800 quadros, 2 vezes) | Antes: VERMELHO, degrau máximo 13,8 quadros, deriva +43,8 quadros em 116 s. Depois: **VERDE, degrau máximo 2,4, deriva −16,2**. As duas rodadas deram WAV idêntico (md5 `DAFC1903…`) e hashes de quadro idênticos [CONFIRMADO] |

O WAV do exe novo é idêntico ao do build de teste do Claude (`fixshift_long.wav`), ou seja, o patch aplicado se comporta igual ao que foi medido ontem [CONFIRMADO].

## 3. (A) Rodada com vida e vidas de verdade

Ferramenta nova: `tools/probe/wave_driver_v7.py --real-hp` (não escreve vidas/HP; inimigos e chefes continuam morrendo pela RAM, pelo caminho de morte do próprio jogo).

| Trecho | Resultado |
|---|---|
| Boot, fases 1 e 2 (3 vidas) | Passou inteiro com dano real, chefes inclusos. Morreu 3 vezes em ~600 quadros no começo da fase 3, game over, voltou ao título normalmente [CONFIRMADO] |
| Fase 2 a partir de save (9 vidas) | Passou a fase 2 inteira; na fase 3 morreu 9 vezes seguidas, game over normal |
| Fase 4 a partir de save | Passou a fase 4 inteira; na fase 5 morreu 9 vezes, game over normal |
| Fase 6 a partir de save | Passou a fase 6 inteira (com a cena do rei); na fase 7 morreu 9 vezes, game over normal |
| Fase 7 a partir de save | Morreu logo no começo (escadas/beiradas do castelo, por tela), game over normal |
| Fase 8 | **Não coberta com vida real**: o save de 600 quadros já caiu no fim do chefe, então só rodou o final (5 telas do final, sem erro) |

As mortes nas fases 3, 5 e 7 acontecem quase sempre **sem inimigo por perto**: o robô cai da beirada (as duas fases têm precipício) quando a navegação dele tenta ir para cima/baixo [PROVÁVEL]. É limitação do robô, não do jogo: no original cair também mata. O ciclo morte -> renascer -> game over -> título funcionou sempre [CONFIRMADO].

**Só o Bruno pode julgar:** sensação do controle (atraso de entrada, pulo, golpe), dificuldade e se algo "parece errado".

### Achado: save tirado no 1º quadro da fase não volta

O driver salvava `stageN_start.bin` no primeiro quadro de gameplay da fase. Da fase 2 em diante esses saves carregam com `ok: True`, mas a tela fica preta e o jogador não aparece (x=`00B0`, y=`0000`) [CONFIRMADO: fases 2, 3, 4, 5 no exe novo; também no exe antigo com um save antigo do mesmo tipo]. O mesmo ponto salvo 600 quadros depois carrega e joga normal [CONFIRMADO: fases 2, 4, 6, 7, 8]. O save da fase 1 sempre funcionou. Não é causado pelo patch [CONFIRMADO: o exe antigo faz o mesmo].
- O "save de um build não serve no outro" anotado antes pode ser em parte este mesmo efeito [INFERIDO].
- Impacto para o Bruno: só se ele fizer um save rápido exatamente no início de uma fase [INFERIDO]. Vale avisar o Garland (é defeito do save state do motor).

## 4. (B) O adiantamento de ~0,24% depois do patch

### MULU/MULS/DIVU/DIVS: descartado (sinal errado) [CONFIRMADO, lido]
- O custo fixo do motor (`m68k-recomp-core/common/m68k_timing.c:340`) é MULU/MULS = 38+2·8+ea = 54+ea (média) e DIVU = 140+ea (quase o pior caso).
- O Golden Axe tem só 31 dessas instruções (`ga.asm`), quase todas com operando imediato pequeno (`#3`, `#$C`, `#$12`, `#$18`, `#$64`) ou quadrado de distância pequena. O custo real do MULU com `#3` é 38+2·2 = 42: o motor **cobra a mais** (~12 ciclos). DIVU real ≤ 140: também cobra a mais ou igual.
- Cobrar a mais deixa o recomp mais **lento**, e ele está **adiantado**. Então cobrir MUL/DIV aumentaria o adiantamento. Não é a causa.
- Não existe comando no servidor TCP que conte instruções por opcode; a contagem por quadro não foi medida em execução (só leitura do código e da ROM).

### Causa parcial achada: o quadro de áudio é de 59,94 Hz, o console é 59,92 Hz [CONFIRMADO]
- `runner/sim_step.c:16`: `GENESIS_SIM_WALL_FRAME_MASTER_CYCLES 895780u`. O quadro NTSC real é 262 × 3420 = **896.040** ciclos mestre (59,9227 Hz). O Z80 e o 68000 andam as 262 linhas inteiras, mas o som de cada quadro sai 260 ciclos mestre mais curto.
- Medido: o WAV tem exatamente **3.732,0 amostras por quadro** (29.109.600 em 7.800 quadros); o hardware dá 3.733,5. Diferença −0,040%.
- Isso explica só ~3 dos 16,2 quadros. Simulação (WAV re-rotulado para o tempo real do quadro): deriva −16,2 -> **−13,2** [INFERIDO, modelo].
- O valor veio de propósito para casar com o ritmo do host em 59,94 fps (`main.c:3255`, `60000/1001`).
- Patch **escrito, NÃO aplicado**: `patches/segagenesisrecomp-ntsc-frame-audio.patch` (muda `sim_step.c` para 896040, o fps padrão do pacer para 53693175/896040 e o teste `tests/runtime/sim_step_test.c`). Aplica limpo (`git apply --check`). Teste: `patches/test_segagenesisrecomp-ntsc-frame-audio.py` falha no motor atual e passa na cópia corrigida (checagem sem ROM); com `--exe` confere amostras por quadro (≥ 3733).
- Risco: o jogo passa a rodar a 59,92 fps no PC em vez de 59,94 (imperceptível). Vai para o Garland como sugestão.

### O resto (~13 quadros) continua aberto [PROVÁVEL a forma, causa não achada]
- A deriva **não é contínua**: o atraso fica parado em 4–20 s, 28–44 s e 56–68 s (a música anda na velocidade certa) e muda em **degraus de 1 a 2 quadros nas trocas de tela**, mais um desvio de −7 quadros que já existe aos 4 s (boot). Ou seja, o recomp ainda termina algumas cargas/o boot mais cedo que o console.
- O orçamento de 68000 por quadro é 262 × 488 = 127.856 ciclos (real 128.005,7). Isso deixaria o recomp mais lento, não mais rápido: não explica.
- Candidatos: espera da FIFO da porta de dados do VDP não modelada (o status sempre diz "FIFO vazia", `video/genesis_vdp.c:432`) [INFERIDO]; esperas de barramento do Z80/BUSREQ [INFERIDO]. Próximo passo: medir em que quadro cada carga termina no BlastEm (depurador) e comparar.

### `--pacing`: contradição só de comentário [CONFIRMADO, lido]
`glue.h` diz que `accurate` é o padrão; `glue.c:155` define `GLUE_PACING_FIBER_FULL`, e o comentário do próprio `glue.c` explica que `accurate` ficou opcional. O valor que vale é `FIBER_FULL`. Como o Claude mediu, trocar o modo não muda nada no Golden Axe.

## 5. (C) Som

- **Volume −2,4 dB**: é ganho puro, igual em todas as faixas de 100 Hz a 8 kHz, em música, história e luta [CONFIRMADO]. Bate com `YM_GAIN 195/256` = −2,37 dB (`runner/audio/ym2612_ymfm.cpp:55`), escolhido para igualar o clownmdemu; o BlastEm fica no nível sem esse ganho [PROVÁVEL]. Não é defeito, é referência diferente.
- **"Falta de agudo"**: com o exe corrigido, até 8 kHz não há perda extra além dos −2,4 dB (≤ 0,5 dB). Acima de 8–12 kHz há −1 a −4 dB extras. Os 5 a 10 dB de ontem (~100–101,5 s) eram em grande parte desalinhamento causado pelo atraso antigo: em 112 s o mesmo cálculo varia ±6 dB só de deslocar a janela 20 ms [PROVÁVEL].
  - Filtros: o recomp usa passa-baixa de 1ª ordem com corte ~2,84 kHz (coeficientes do clownmdemu, FM e PSG); o BlastEm usa `lowpass_cutoff 3390` (`default.cfg`). Diferença prevista 1 a 1,5 dB acima de 5 kHz [INFERIDO, conta].
  - O resto acima de 12 kHz é compatível com a FM a 53 kHz repetida por amostra até 223 kHz (retenção) [INFERIDO]. Pouco audível.
- **Som em gameplay**: o BlastEm não tem script de entrada, então não deu para comparar o mesmo trecho de gameplay. Feito no lugar: WAV de 150 s do recomp (fase 2 inteira com chefe + começo da fase 3): sem clipping (pico 9.797 de 32.767), nenhuma janela muda de 100 ms, nenhum salto de amostra [CONFIRMADO]. Vozes/magia contra o BlastEm continuam **não comparadas**; precisa de alguém jogando o mesmo trecho no BlastEm, ou de entrada automática no BlastEm.

## Arquivos desta sessão

- Modificado (submódulo, sem commit): `segagenesisrecomp/external/m68k-recomp-core/profiles/genesis/code_generator.c` (o patch de 1 linha).
- Novos: `patches/segagenesisrecomp-ntsc-frame-audio.patch`, `patches/test_segagenesisrecomp-ntsc-frame-audio.py`, `tools/probe/wave_driver_v7.py`, esta nota.
- Modificado: `tools/probe/README.md` (v7 e aviso do save).
- Fora do git: `build\game\Release\GoldenAxeRecomp.prefix.exe` (backup), saídas em `C:\tmp\shiftfix_*`, `C:\tmp\realhp*`, `C:\tmp\shiftfix_lag`, `C:\tmp\oldexe` (cópia do exe antigo para teste).
- Saves bons (exe novo, tirados 600 quadros após o início da fase): `C:\tmp\shiftfix_full2\stage1..8_start.bin`.

## 6. Correção do save no primeiro quadro da fase (resolvido em 2026-11-12, tarde)

- Problema: um save feito no primeiro quadro da fase 2 (ou de qualquer fase) abria com tela preta [CONFIRMADO]. O jogo marca o modo "fase" como já iniciado (bit 7 de `$FFC172`) antes de terminar de montar a fase; ao carregar, ele pulava a montagem.
- A ideia do Claude estava certa: no load, se a pilha mostra que o jogo estava dentro da montagem (`loc_12DC`, retorno `$12EC` em `$FFFCF8`), limpar o bit 7 para a montagem rodar de novo [CONFIRMADO].
- Por que parecia não funcionar: o código novo estava certo, mas o exe continuava rodando a versão **antiga** do gancho [CONFIRMADO]. O MSVC compila com otimização do programa inteiro (LTCG incremental) e copiou para dentro de `main.c` (`runner_load_state_file`) uma cópia antiga de `ga_on_state_loaded`; recompilar só `goldenaxe_spec.c` não atualizava essa cópia. Prova: com um print de depuração só no `goldenaxe_spec.c` nada aparecia; quando `main.c` também foi recompilado, o print apareceu (`A7=00FFFCB8 C172=800C ret=000012EC init=1`) e a fase carregou [CONFIRMADO]. A causa exata dentro do compilador é [PROVÁVEL].
- Regra prática: depois de mexer em um gancho do `goldenaxe_spec.c`, encoste em `segagenesisrecomp/runner/main.c` (salvar sem mudar) ou faça build limpo. Quem clona do zero não é afetado.
- Teste (escondido, cópia do exe fora do repo) [CONFIRMADO]:
  - save do primeiro quadro da fase 2: carrega, personagem aparece e anda (x `00C2`→`012E`);
  - save do primeiro quadro da fase 1 e save 600 quadros dentro da fase 1: carregam e andam;
  - save com o bit 7 limpo à mão (controle): igual ao corrigido.
  - Prints em `C:\Users\covre\ga_savefix_evidence\08_..12_*.png`.
- Ferramenta: `tools/probe/save_load_check.py`.
- Limite: só o modo fase (`$0C`). Outros modos têm a mesma fraqueza na teoria; a solução geral seria no motor (adiar o save até o jogo voltar ao GameLoop) [INFERIDO].

## 7. Chefes travados na fase 3 (Bad Brothers) — atualizado à tarde

Testado escondido com os dois saves do Bruno (fase 3, jogador parado, 2.400–3.600 quadros). Provas em `C:\Users\covre\ga_savefix_evidence\boss\`.

- Save 1: um irmão (`$FFD180`) fica no estado `$0C` esperando ser tocado; o outro (`$FFD100`) fica no laço `$04`→`$08`→`$04` (golpeia o ar a cada 30 quadros) [CONFIRMADO].
- Save 2: `$FFD180` igual (estado `$0C`); `$FFD100` fica no estado `$00` parado, porque o jogador está 38 px longe na "profundidade" (`+$20`) [CONFIRMADO].
- O irmão do estado `$0C` só sai quando o jogador bate nele (`loc_10782`). Isso bate com o que o Bruno viu ("só destravou depois que eu ataquei") e é do jogo original [PROVÁVEL].

### Descoberta nova: o jogador fica imune a golpes quando está parado ou andando [CONFIRMADO]

- Com o vigia ligado, os irmãos chegam perto e o golpe acerta: o jogo marca o bit 6 de `$FFD003` ("levei golpe", `loc_BFCC`). Mas o jogador nunca perde vida.
- O log de escrita de memória mostra quem apaga esse bit: o código do próprio port, em `ga_call_vblank` (`game/goldenaxe_spec.c`, a correção antiga `GA_FLAGS3_CUTSCENE_RETRIGGER_BIT`). Ela apaga o bit 6 de `$3` e o bit 2 de `$2` do jogador em todo quadro em que o estado `$42` do jogador é 0 (parado/andando).
- Esse código veio no projeto original (commit `fd8b7f7`). O comentário dele diz que o bit "aparecia andando, sem NPC por perto" e travava o controle. Muito provavelmente eram golpes de inimigos [PROVÁVEL].
- Teste: com esse apagamento desligado (só no exe de teste), o primeiro golpe do irmão no save 1 acerta (vida 32→16) e o laço de "golpear o ar" some [CONFIRMADO].
- Efeito no jogo: o jogador parado ou andando não leva dano, e a IA de alguns inimigos fica repetindo o ataque. Isso explica pelo menos um dos dois chefes travados [PROVÁVEL].
- **Corrigido no código** (12/11, fim da tarde): o apagamento do bit 6 / bit 2 saiu de `ga_call_vblank` [CONFIRMADO].
- O Cursor leu o `ga.asm` e concluiu que o "travamento de controle" antigo era causado pela própria correção: ela apagava o bit 2 (trava de um quadro do golpe) e o jogo repetia o começo do "levei golpe" todo quadro [PROVÁVEL].
- Testes escondidos depois da correção [CONFIRMADO]:
  - save 1 do Bruno: o irmão acerta no primeiro golpe (vida 32→16), sem laço de golpe no ar;
  - partida inteira automática (modo deus) até o final do jogo, sem travar o controle (a única "parada" foi na fase 6, igual às partidas antigas, e é o robô de teste que se perde no caminho);
  - partida com vida de verdade a partir da fase 2: chegou à fase 5. O exe antigo deu game over na fase 3. As mortes por queda no precipício foram nos mesmos quadros nos dois; o jogador agora leva mais golpes (17 contra 9), como no jogo original;
  - saves (primeiro quadro da fase 2 e meio da fase 1) continuam carregando.
- Efeito para o Bruno: o jogo fica um pouco mais difícil, igual ao original. Ficar parado agora tira vida.
- Continua sendo do jogo original [PROVÁVEL]: o irmão no estado `$0C` só sai quando é atacado, e o irmão no estado `$00` não se aproxima se o jogador está em outra "faixa" de profundidade (save 2).

### Vigia opcional da IA (versão 2, não aplicada)

- `patches/proposal-boss-ai-watchdog.patch` foi refeito: olha os 8 espaços de inimigo, aceita `$C0`/`$C1` com script `$40262`, e só escreve estados múltiplos de 4. Regras: `$0C` parado por 120 quadros → `$04`; `$00` parado por 180 quadros → `$04`; laço de golpe no ar → aproxima 4 px.
- Desligado: comportamento igual ao exe sem patch, mesmos números nos dois saves [CONFIRMADO].
- Ligado: o irmão do `$0C` sai em 119 quadros e o do `$00` passa a atacar [CONFIRMADO]. Mas os golpes continuam sem tirar vida, por causa da imunidade acima. Por isso **não entrou no código**.
- Conferido no `ga.asm`: o tipo fica no byte `+$00` (bit 7 = ativo, `$C0` → `loc_10250`, `$C1` → `loc_1028A`), `+$1C` = X, `+$18` = Y, `+$20` = profundidade, `+$4C` = estado da IA (tabela `loc_102FE`, passos de 4) [CONFIRMADO].

## 8. Tela preta do launcher (AMD)

- O fundo do menu é `#0A0D16`, quase preto [CONFIRMADO].
- Causa mais provável: retorno cedo da escala HiDPI em `apply_logical_display` (`launcher_imgui.cpp:271`), ou a janela maximizada no desktop de 2987x724 [PROVÁVEL].
- Contorno atual: `skip_launcher = 1` em `settings.ini` na seção `[launcher]`, ou abrir com `--no-launcher`.
- Proposta (não aplicada): `patches/proposal-launcher-amd-black.patch`. Em 12/11 à tarde ela foi aplicada só para compilar e **compila sem erro** [CONFIRMADO]; depois foi desfeita. Não dá para testar sem abrir a janela na tela do Bruno, então continua só como patch.
