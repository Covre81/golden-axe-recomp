# Golden Axe (World Rev A, CRC32 665D7DF9): mapa de memória e plano de cheats

Pesquisa feita em 2026-10-26, só com fontes locais. A rede não foi usada.

**Fontes:**

| Sigla | O que é | Onde está |
|---|---|---|
| **JV** | Clone do projeto jvisser (Golden Axe MD) | scratchpad, `jvisser/` |
| **GA** | Disassembly lory1990 | scratchpad, `lory_x/ga.asm`. Somente leitura. Os números citados são linhas do arquivo. Nenhum trecho foi copiado. |
| **ENG** | Motor | `external/segagenesisrecomp`, commit `252535d` |

O jvisser usa a mesma ROM que este projeto. O SHA256 em `jvisser/README.md:9` é igual ao do README daqui [CONFIRMADO]. Por isso os endereços de JV valem sem ajuste.

Convenções do documento:
- Todo endereço é de 68000 (`$FFxxxx`). Ele corresponde a `g_ram[addr & 0xFFFF]`.
- A RAM é big-endian. Uma `.w` em `FE2C` tem o byte alto em `FE2C` e o baixo em `FE2D`. Isso está confirmado pelo `ram16` em `sonicthehedgehog/sonic1_video.c:28-32` [CONFIRMADO].

---

## (a) Endereços de RAM úteis

### Máquina de estados do jogo

| Endereço | Tam. | Significado | Fonte |
|---|---|---|---|
| FFC170 | .w | `requested_game_state`. `FFFF` quer dizer "nada pendente". Escrever um estado aqui pede a troca. | JV `goldenaxe.h`; GA GameLoop ~713-725 [CONFIRMADO] |
| FFC172 | .w | `current_game_state`. A tabela é despachada por `C172 & 0x7C`. O bit 15 indica que o handler já foi inicializado. | JV; GA ~713-760 [CONFIRMADO] |
| | | Valores: 00 Sega, 04 Title, 08 Player select, **0C Gameplay**, 10 Demo, 14 Profile, 18 Intermission, 1C Camp, 20 Result, 24 End, 28 Beginner end, 2C Cast, 30 Credits, 34 VS, 38 Duel, 3C Next duel, 40 Game over | JV `goldenaxe.h` [CONFIRMADO] |
| FFC104 | .b | `game_mode_flags`. Bit 1 = duel, bit 2 = beginner. O bit 3 aborta os eventos em loc_2520. | JV `var.md`; GA 2549-2578 [CONFIRMADO] |
| FFC105 | .b | Jogadores ativos. Bit 0 = modo 2P, bit 1 = P1 ativo, bit 4 = P2 ativo. | GA init loc_4222/4252 [PROVÁVEL] |
| FFC106 | .w | Timer de continue. Recebe `$0A00` quando as vidas chegam a 0. | GA loc_7D1A..7D82 [PROVÁVEL] |
| FFFE2C | .w | `current_level`. O índice efetivo é o byte baixo **FE2D**, de 0 a 7, aplicado com `&7`. | JV; GA loc_12A8 [CONFIRMADO] |
| FFFE08 | .w | `demo_index` | JV [CONFIRMADO] |
| FFFE34 | .b | Créditos. O padrão é 4 ou 6 conforme a região (bit 7 de FE00). Cada continue faz FE34--. O código `$66` no player select grava 9. | GA loc_230A, loc_41BE [PROVÁVEL] |
| FFFE35 | .b | Opção de barras de vida, de 0 a 2 (3, 4 ou 5 barras). A vida máxima é `FE35*16 + $30`. | GA ~4505-4525, loc_42BE [PROVÁVEL] |

### Status do jogador

A struct tem 16 bytes. P1 fica em `FFFE7C` e P2 em `FFFE8C`.

| Endereço P1 / P2 | Tam. | Significado | Fonte |
|---|---|---|---|
| FE7C / FE8C | .b | Vidas. A init grava `.w $0300`, ou seja 3 vidas. | GA loc_4252; morte `subq.b #1,0(a2)` em loc_7D1A..7D82 [CONFIRMADO no código, nome INFERIDO] |
| FE7E / FE8E | .b | Vida (energia). O máximo é `FE35*16+$30`. O dano desconta com piso 0 (loc_6EBE). | GA loc_42BE, loc_6EBE [PROVÁVEL] |
| FE80 / FE90 | .b | Frascos de magia. A init grava `.w $0100`, ou seja 1 frasco. Usar a magia zera o valor (0x7C5C `clr.b (a3)`). | GA loc_4252, ~8689-8703; JV `cheat.s` [CONFIRMADO] |
| FE83 / FE93 | .b | Personagem (+7): 0 Ax, 1 Tyris, 2 Gilius. | GA loc_42D2 [PROVÁVEL] |
| ROM 0x00A944 | 3 .b | Tabela com o máximo de frascos por personagem: {6 Ax, 9 Tyris, 4 Gilius}. | GA loc_A918..A964 [PROVÁVEL] |
| FE76 / FE7A | ? | Contadores que sobem no fim da animação de morte. Significado desconhecido. | GA loc_7D1A [INFERIDO] |

### Seleção de fase, eventos e entrada

| Endereço | Tam. | Significado | Fonte |
|---|---|---|---|
| FFC1B0 | .w | Flag de seleção de fase. O código de entrada `$96` no player select grava 1. Com ela ligada, a entrada em C177 incrementa ou decrementa FE2C (`&7`). | GA loc_41BE, loc_4440/4448; JV `cheat.s` (0x4444) [CONFIRMADO] |
| FFC1A5 / FFC1AD | .b | Personagem escolhido, P1 e P2 (`-1` antes de chegar a +7). | GA loc_42D2 [PROVÁVEL] |
| FFC2A2 | .b | Evento pendente de fim de fase. Os gatilhos de mapa só gravam quando ele vale 0. Valores: `$21` próxima fase, `$41` camp, `$11` fim, `$81` especial. O bit 0 arma o evento. | GA ~1928-1945, 2549-2578 [CONFIRMADO] |
| FFC26C | .w | `ActiveEnemyCount`. O evento só dispara com valor 0. | JV `var.md`; GA loc_2520 [CONFIRMADO] |
| FFC272 | .w | Slots de entidade pendentes. Também precisa valer 0. | JV; GA loc_2520 [CONFIRMADO] |
| FFC22A | .w | `next_event_trigger` (gatilhos de mapa) | JV `map.h` [CONFIRMADO] |
| FFC176 / C177 | .b | Controle P1, estado atual e "mudou neste frame". O bitfield é SACBRLDU. | JV [CONFIRMADO]; o layout dos bits é [INFERIDO] |
| FFC178 / C179 | .b | Controle P2, mesmos campos. | JV [CONFIRMADO] |

### Entidades

São 64 slots de 0x80 bytes a partir de `FFD000`.

| Endereço / offset | Tam. | Significado | Fonte |
|---|---|---|---|
| FFD000, FFD080 | 0x80 | Jogadores 1 e 2 | JV `entity.h` [CONFIRMADO] |
| FFD100..FFD4FF | 8×0x80 | Slots instanciados pelo mapa (inimigos e chefes) | JV `entity.md` [CONFIRMADO] |
| FFD500.. | | Slots secundários. D500 é o slot da magia. | JV [CONFIRMADO] |
| +0x00 | .b | id. O bit 7 indica que a entidade já foi inicializada. | JV [CONFIRMADO] |
| +0x02 | .b | flags02. O bit 7 esconde o sprite. | JV [CONFIRMADO] |
| +0x03 | .b | Bit 1 knockdown, bit 2 montado, bit 6 recebeu dano, bit 7 causou dano. | JV [CONFIRMADO] |
| +0x18, +0x1C, +0x20, +0x24 | .l 16:16 | Posição: y, x, baseY e altura. | JV [CONFIRMADO] |
| +0x3C | | mount | JV |
| +0x42, +0x44, +0x4C | | state, flags44, state_main | JV |
| **+0x64** | .b | **HP** | JV `cheat.s`, `entity.md`; GA loc_D3D2 (linha 15234) [CONFIRMADO] |
| | | IDs de chefe (`id & 0x7F`): Bad Brother 3F/40/41, Death Adder 4A, Death Bringer 4B, Death Adder Jr 4C | JV `entity.md` [CONFIRMADO] |

### Rotinas da ROM úteis como pontos de hook

| PC | Papel |
|---|---|
| 0x1228 | Handler de gameplay (estado 0C), chamado uma vez por frame pelo GameLoop. Na primeira vez faz `bset #7,C172` e desvia para a init loc_12DC. GA linhas 1203-1237 [CONFIRMADO]; a frequência de uma vez por frame é [PROVÁVEL]. |
| 0x12A8 | Avanço de fase. Faz fade de música, `C170=$0C`, `FE2C++ &7` e a transição para o escuro. GA linhas 1238-1249 [CONFIRMADO] |
| 0x1282 | Pede o camp (estado 1C) [CONFIRMADO] |
| 0x2520 | Processa os eventos de C2A2 [CONFIRMADO] |
| 0x41BE | Player select (estado 08) [CONFIRMADO] |
| 0x4444 | O `bne.s` depois de `tst.w C1B0`. O jvisser troca por `nop nop` para liberar a seleção de fase. [CONFIRMADO] |
| 0x6EBE | Desconto de dano na vida do jogador [CONFIRMADO] |
| 0x7C5C | Zera os frascos ao usar a magia [CONFIRMADO] |
| 0x7D5C | Decremento de vidas. O comentário do jvisser fala em "Fall death", mas a instrução é o `subq` de vidas. [CONFIRMADO] |
| 0xD3D2 | Ajuste de HP do inimigo depois da init. No modo beginner divide o HP por 2. Termina em `rts`. GA 15234 [CONFIRMADO] |
| 0xB954 | `update_active_entities` [CONFIRMADO] |
| 0x35E8 / 0x361C / 0x36D8 | play_music / play_sound_effect / screen_transition_to_dark [CONFIRMADO] |

---

## (b) Cheat por cheat: o que escrever e quando

Há dois tipos de cheat:
- **Contínuos:** reescritos a cada frame enquanto o jogo está no estado de gameplay, com gate `(peek16(C172) & 0x7C) == 0x0C`. São idempotentes.
- **Disparados:** escritos uma única vez, na borda de um comando ou tecla. Se fossem reescritos a cada frame, entrariam em cascata.

O ponto de execução "por frame" está descrito na seção (c). Hoje ele é um `game_hook` em 0x1228 que retorna 0, porque o `on_frame_post` não está ligado no runner. Os cheats disparados seguem o mesmo caminho: o comando só arma uma flag do host, e o hook em 0x1228 a consome uma vez, já com o gate de gameplay garantido. Assim a escrita acontece num ponto determinístico do frame, e não entre frames com o fiber do jogo suspenso.

| Cheat | Tipo | Escrita | Quando |
|---|---|---|---|
| Vidas infinitas | contínuo | `poke8(0xFFFE7C, 9)`. Para P2, `poke8(0xFFFE8C, 9)` só se o bit 4 de C105 estiver ligado. | A cada frame em gameplay. Não use hook em 0x7D5C retornando 1 (motivo abaixo). |
| God mode (vida cheia) | contínuo | `poke8(0xFFFE7E, peek8(0xFFFE35)*16 + 0x30)` e o mesmo para FE8E | A cada frame em gameplay. Fica uma janela de 1 frame: se um golpe tirar mais que o máximo de uma vez, o jogador morre. As vidas infinitas cobrem isso. |
| Magia infinita | contínuo | `poke8(0xFFFE80, max)`, com `max = glue_peek8(0x00A944 + peek8(0xFFFE83))`; idem FE90/FE93 | A cada frame em gameplay. Para "usar sem gastar" basta reescrever no frame seguinte, porque a magia em curso já leu a contagem antes do `clr`. Esse último ponto é [INFERIDO]. |
| Seleção de fase | contínuo no estado 08 | `poke16(0xFFFFC1B0, 1)` | A cada frame com `(C172 & 0x7C) == 0x08`, via `game_hook` em 0x41BE retornando 0. O próprio jogo passa a ler C177 e mexer em FE2C. Alternativa sem hook: o jogador digita o código `$96` no player select. |
| Avançar fase (pular) | disparado | Caminho fiel: se `peek8(C2A2) == 0`, escrever `poke8(C2A2, 0x21)` ($21 = bit 5 "próxima fase" mais bit 0 "armado", GA ~1928), `poke16(C26C, 0)` e `poke16(C272, 0)` | Uma vez por comando, em gameplay. O loc_2520 do próprio jogo faz o fade, a música e o `FE2C++`. |
| | | Atalho: `poke16(FE2C, (peek16(FE2C)+1)&7)` e `poke16(C170, 0x0C)` | Pula o fade e a música. Os efeitos colaterais são [INFERIDO]. |
| Ir para fase N (teleporte) | disparado | **Só no player select** (estado 08): `poke16(FE2C, N-1)`, com N de 1 a 8. Em gameplay, não grave FE2C: use só o "avançar +1" via C2A2. | Uma vez por comando. Motivo: no handler 0x1228, loc_138FE (mapa) roda antes de loc_2520 no mesmo frame e leria a fase trocada; e as checagens FE2D==5/7 olham o valor antes do incremento [INFERIDO]. |
| Matar chefe (deixar com 1 HP) | contínuo | Varrer os slots `FFD100 + i*0x80` (i de 0 a 7). Se `(peek8(slot) & 0x80)` estiver ligado e `(id & 0x7F)` for um ID de chefe, fazer `poke8(slot+0x64, 1)`. | A cada frame em gameplay. Basta um golpe para matar. |
| Inimigos com 1 HP (fiel ao jvisser) | estrutural | `game_hook` em **0xD3D2**: `poke8(g_cpu.A[0] + 0x64, 1)` e `return 1` | Na init de cada inimigo. É o único site em que retornar 1 equivale exatamente ao patch, porque o patch também termina em `rts` (veja a nota abaixo). |

**Por que não usar hook com retorno 1 em 0x6EBE, 0x7C5C ou 0x7D5C.**
- Retornar 1 de um `instruction_hook` funciona como um `rts`: abandona a rotina inteira, não só a instrução. Fonte: `m68k_interp.c:1303` (`PC = pop32()`), `:1384-1391` ("Implicit RTS") e `game_spec.h` ("returning 1 replaces this routine") [CONFIRMADO].
- Os patches do jvisser nesses três PCs são `nop`. Eles pulam uma instrução e seguem a rotina.
- Um hook com retorno 1 ali cortaria efeito, knockback, os bits de C105 e o timer de continue.
- Para esses três cheats, escreva na RAM; não use hook.

**Não reescrever o avanço de fase a cada frame.** Os gatilhos de mapa só gravam C2A2 quando ele vale 0. Se o cheat reescrever `$21` todo frame, as fases avançam em cascata.

---

## (c) Como injetar sem editar o C gerado

A regra do projeto é nunca editar o C gerado (`notes/genesis-recomp-research.md`). O motor oferece três superfícies, todas do lado do adaptador do jogo (`g_game_spec`, definido uma única vez num `.c` do jogo).

1. **`instruction_hook(pc)` com os sites declarados no `game.toml`.**
   - Formato: uma entrada `[[widescreen_site]]` com `addr = 0x1228` e `kind = "game_hook"`.
   - Parser: `recompiler/src/game_config.c:541`. Enum: `game_config.h:125` [CONFIRMADO]. Exemplos: `sonicthehedgehog/game.toml:196-312`, com a implementação em `sonic1_video.c:390` e o teste em `tests/runtime/sonic1_video_test.c` [CONFIRMADO].
   - O hook roda **antes** da instrução daquele PC. Retornar 0 continua o código normal; retornar 1 substitui a rotina, com `rts` implícito.
   - O interpretador Tier-3 respeita os mesmos sites (`m68k_interp.c:310-312`), e o `glue.c:46` delega para o spec [CONFIRMADO].
   - Os sites são fixados em tempo de compilação. Adicionar um site exige editar o `game.toml` e **rodar o recompilador de novo**. Isso não edita o C gerado: ele é regenerado.
   - Sites propostos:

     | Site | Retorno | Uso |
     |---|---|---|
     | 0x1228 | 0 | "Tick" de gameplay para todos os cheats contínuos |
     | 0x41BE | 0 | Seleção de fase |
     | 0xD3D2 | 1 | Inimigos com 1 HP |

2. **Acesso à RAM pelo host.**
   - Use `glue_peek8/16/32` e `glue_poke8/16/32` com o endereço completo `0xFFxxxx`.
   - Fonte: `runner/include/genesis_host_mem.h`. O texto diz explicitamente que esse é o caminho para "game-adapter features", sem efeito no scheduler [CONFIRMADO].
   - Não use `m68k_read/write`, que conta como acesso de barramento do guest.
   - `g_ram[]` cru também funciona (`genesis_runtime.h:27`), mas aí a ordem big-endian fica por sua conta.

3. **Ligar e desligar os cheats.**
   - Superfícies disponíveis em `runner/game_spec.h` [CONFIRMADO]:

     | Campo | Função |
     |---|---|
     | `handle_arg` / `arg_usage` | Flags de CLI, por exemplo `--cheat-lives` |
     | `load_settings` | Configurações persistentes |
     | `mods(base)` | Provider de mods do launcher: "Game-owned additive features" |
     | `commands` | Comandos TCP de debug, `game_spec.h:231-236`. É o candidato natural aos cheats disparados (avançar fase, ir para fase N). O handler do comando apenas arma uma flag; quem escreve na RAM é o hook em 0x1228 (ou o 0x41BE, no player select). |

   - Não investiguei como uma hotkey no host chegaria ao adaptador [lacuna].
   - Guardas obrigatórias:
     - `netplay_allowed` deve retornar 0 com qualquer cheat ligado;
     - `state_unavailable_reason` é a alternativa se o estado do cheat tiver que entrar no snapshot. Os cheats contínuos não precisam disso, porque tudo vive na RAM do guest.

**Achado importante: `on_frame_pre`, `on_frame_post` e `on_post_reset` não são chamados pelo runner no checkout atual.**
- Eles estão declarados em `game_spec.h:180-185` e citados no `CLAUDE.md`.
- O grep em todo o repositório só encontra as declarações e os `= NULL` dos specs. O fim de frame real é `glue_service_vblank` (`glue.c:1202-1218`), que não chama nenhum deles. Isso vale para o checkout atual: os submódulos `m68k-recomp-core`, `z80-recomp-core`, `rbengine` e `recomp-net` estão vazios. [PROVÁVEL]
- Por isso o tick por frame da seção (b) é o `game_hook` em 0x1228, e não `on_frame_post`.
- Ligar `on_frame_post` em `glue_service_vblank` seria um patch de uma linha no motor. Isso é um fork do upstream, não do C gerado. Decisão do Bruno.

---

## (d) Riscos e lacunas

**1. A emissão do `game_hook` no C gerado não pôde ser verificada no código.**
- O `recompiler/src/code_generator.c` é um forward para `external/m68k-recomp-core/profiles/genesis/code_generator.c`.
- Esse submódulo não está no checkout. A pasta existe e está vazia; o `.gitmodules` aponta para `../m68k-recomp-core.git`.
- Que o C gerado chama `genesis_game_instruction_hook` nos sites é **[PROVÁVEL]**, por três evidências: o `game.toml` do Sonic, o teste runtime e a declaração "Generated table lookup" em `genesis_runtime.h:205-206`.
- Para confirmar: `git submodule update --init external/m68k-recomp-core`, depois de liberado, porque não instalei nada.

**2. O site 0x1228 só funciona se for um ponto de entrada traduzido.**
- 0x1228 é alvo de uma tabela de despacho (`loc_CA2`). Por isso deve ser raiz de função [PROVÁVEL]
- Se o recompilador fundir esse ponto no meio de outra função, o site pode cair num lugar não instrumentado. Valide com um log no hook.

**3. Riscos de cada cheat:**
- **God mode:** a janela de 1 frame continua (veja (b)). Se a queda no buraco for um caminho de morte separado, a vida cheia não impede a morte; as vidas infinitas compensam.
- **HP=1:** ainda precisa de um golpe. Gravar 0 direto pode não disparar a rotina de morte, nem o gatilho `NEXT_LEVEL_ON_ENEMY_DEFEAT` (map event 0x1C) [INFERIDO].
- **Avançar fase:**
  - com FE2D==5, loc_256E desvia para uma sequência especial (loc_257E, que checa os jogadores);
  - com FE2D==7, o bit 4 vai para o final (`C170=$24`).
  - Pular a partir dessas fases pode quebrar a progressão. O atalho por C170 pula o fade e a música [INFERIDO].
- **Modo beginner:** o jogo limita FE2C a no máximo 2 e trata o fim de jogo de outro jeito (estado 28). Desligue os cheats de fase quando o bit 2 de C104 estiver ligado.
- **Modo duel** (bit 1 de C104, estados 34/38/3C): a struct de status e os slots podem ter outra semântica. Desligue os cheats.

**4. Determinismo e netplay.** Toda escrita do host diverge do original. `netplay_allowed()` precisa retornar 0, e um save state feito com cheat carrega os valores alterados.

**5. HUD.** Barras de vida, frascos e vidas podem não redesenhar depois de um `poke` até o jogo atualizar por conta própria [INFERIDO]. Teste visual pendente.

**6. Itens não confirmados:**
- o significado de FE76/FE7A;
- o layout exato dos bits de C176;
- os nomes das 8 fases;
- a lista de chefes por fase (os IDs vêm do jvisser e não foram cruzados com as tabelas de spawn).

**7. Licença.** Este documento cita apenas endereços e descrições. Nenhum trecho de `ga.asm` ou dos blobs saiu do scratchpad.
