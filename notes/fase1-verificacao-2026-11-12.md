# Fase 1: verificação automática (2026-11-11 e 2026-11-12)

Rodadas feitas por um driver TCP (`tools/probe/wave_driver_v6.py`) que joga sozinho, com modo deus pela RAM.
Builds testados:

- **drift**: `build\game\Release`, `cycle_drift_correction = true` (o padrão do `game.toml`). Exe `f2c593ef`.
- **no-drift**: `build-nodrift\Release`, compilado com `cycle_drift_correction = false`. Exe `18b72d10`. Não está no git.

Marcas: [CONFIRMADO] visto em log, tela ou código; [PROVÁVEL] bem indicado, mas não provado; [INFERIDO] dedução sem teste direto.

## O que funciona

- O jogo vai do boot ao final nos dois builds: fases 1 a 8, Death Adder, Death Bringer e o texto final do rei ("THANK YOU GALLANT ONE!"... "WE PRAISE YOUR ACTS OF BRAVERY AND DEEDS OF COURAGE.") [CONFIRMADO].
- O controle não travou em nenhum ponto, inclusive depois do primeiro diálogo [CONFIRMADO]. Toda parada longa do jogador era cena com controle desligado de propósito: o diálogo do rei depois do Death Adder (~3.600 quadros) e o final [CONFIRMADO, por tela].
- Nenhum crash, nenhum travamento de quadro e nenhum aviso de fallback no stderr [CONFIRMADO].
- Todos os "GO!" saíram dourados nos dois builds. A paleta na RAM bateu com a CRAM em todos os quadros capturados [CONFIRMADO].

## Resultados

### GO! por fase (GO!s naturais, por morte de onda)

| Fase | drift | no-drift |
|---|---|---|
| 1 | 5 dourados | 5 dourados |
| 2 | 6 | 6 |
| 3 | 5 | 5 |
| 4 | 5 | 5 |
| 5 | 2 | 2 |
| 6 | 1 | 1 |
| 7 | 3 | 3 |
| 8 | 0 (fase sem GO!) | 0 |
| **Total** | **27, 0 roxos** | **27, 0 roxos** |

O `check_go.py` deu VERDE em todos. O GO! forçado pela RAM (`go_direct.input`) também deu dourado nos dois builds.

### Até onde cada rodada chegou

| Rodada | Build | Início | Fases | Fim |
|---|---|---|---|---|
| `v2_drift` | drift | boot | 1 a 6 | parou no Death Adder (driver antigo não sabia matar chefe) |
| `v4_drift_s6` | drift | save fase 6 | 6, 7, 8 | parou no Death Bringer |
| `v5`/`v6_drift_end` | drift | save fase 8 | 8 | **final alcançado** |
| `v6_nodrift_boot` | no-drift | boot | 1 a 7 | parado por tempo no começo da 7 |
| `v6_nodrift_s7` | no-drift | save fase 7 (do próprio no-drift) | 7, 8 | **final alcançado** |

Começo de cada fase no no-drift desde o boot (quadro): 1 = 20, 2 = 11.840, 3 = 24.567, 4 = 35.554, 5 = 46.189, 6 = 54.717, 7 = 61.555. No save da fase 7: fase 8 = 17.914, final = 18.195 + ~560.

Na fase 7 há trechos longos sem inimigos (~3.900 a ~6.800 quadros) nos dois builds. O jogador continua andando (o driver não acusou parada). É trecho de caminhada da fase, não trava [PROVÁVEL].

## Descobertas

- **Offsets de entidade** (slots de `$FFD100`, passo `$80`; jogador 1 em `$FFD000`): `+$00` id (bit 7 = já iniciado), `+$03` flags de golpe (bit 6 levou golpe, bit 1 magia), `+$18` Y, `+$1C` X, `+$42` animação/estado, `+$4C` estado do chefe, `+$64` HP [CONFIRMADO no ga.asm e na RAM].
- **RAM do jogo:** `$FFC26C` inimigos vivos; `$FFC2A2` evento da onda (`$81` = GO! armado, `$21` = fim de fase, `$11` = fim de jogo); `$FFFE2D` fase (0 a 7); `$FFC172` estado do jogo (`$0C` gameplay, `$24` final); `$FFFE7C` vidas; `$FFFE7E` HP do jogador [CONFIRMADO].
- **Morte de inimigo comum:** HP = 0 e `+$42 = $401A`, como em `loc_DCD0` [CONFIRMADO].
- **Morte de chefe:** Death Adder (`$4A`, `loc_11982`), Death Bringer (`$4B`, `loc_119BE`) e `$4C` usam a mesma máquina de estados em `+$4C` (tabela em `loc_11A3A`; no ga.asm é só `dc.b`, foi desmontada à parte). O estado `$18` (`$12080`) é a morte: desconta `C26C`, e no Death Bringer (`$CB`) espera 300 quadros e chama o final. Escrever HP = 0 e `+$4C = $18` usa esse caminho do próprio jogo [CONFIRMADO]. O `$401A` não vale para chefe [CONFIRMADO].
- **Truque de remoção fora da tela:** inimigo preso (ex.: Bizarrian) sai quando `+$18 = $0300`. O próprio jogo o remove e desconta `C26C` em `loc_B44A`/`loc_B472` [CONFIRMADO]. Não use em chefe nem em entidade de cena: quebrou a cena do rei numa rodada [CONFIRMADO].
- **Entidades de cena** (rei, princesa, portas) nascem com HP 0. O driver não mexe nelas [CONFIRMADO].
- **Save state é do build:** o formato GROWNS3 é struct cru, "private to a build" (`runner/main.c`). Save do drift carregado no no-drift abre sem erro, mas a tela fica preta e o jogador para [CONFIRMADO]. Use sempre save feito pelo mesmo exe.
- **Interior-label misses** iguais nos dois builds (`interior_label_misses.toml`): `$00AA8C` (dentro de `$00BF62`), `$012E0E` (dentro de `$012DC0`), `$012944` (dentro de `$0128F6`) [CONFIRMADO]. Não causaram erro visível [CONFIRMADO]. São lacunas de codegen do motor, não deste repo [INFERIDO].
- **Servidor TCP de depuração:** só sobe com `debug.ini` ao lado do exe; aceita um cliente por vez (`listen(s, 1)`, um `s_client` em `cmd_server.c`) [CONFIRMADO].
- Depois de um `load_state`, o stderr mostra `[fiber] restarted game fiber at $000C76`. É o reinício normal do load [PROVÁVEL].

## O que falhou e por quê

- **Reproduzir o GO! roxo:** não reproduz em nenhum dos 54 GO!s naturais nem no forçado, com ou sem `cycle_drift_correction` [CONFIRMADO]. Provável que outra mudança do Garland já tenha resolvido [INFERIDO].
- **Driver antigo travava no Death Adder:** usava a morte de inimigo comum (`$401A`), que chefe ignora. Resolvido com `+$4C = $18`.
- **Driver antigo quebrava a cena do rei:** matava e removia as entidades de cena. Resolvido ignorando quem nasce com HP 0.
- **Save do drift no no-drift:** não funciona (acima). O no-drift foi jogado do boot.
- **Morte forçando HP = 1 e atacando:** não matava com regularidade. Trocado pela escrita direta do estado de morte.

## Em aberto

- Partida manual do Bruno do começo ao fim. O driver usa modo deus e mata pela RAM, então não substitui uma partida real.
- Primeiro quadro capturado do final no drift (quadro 810 depois do load) saiu todo branco. No no-drift o quadro equivalente saiu normal, mas foi capturado ~120 quadros depois. Provável flash/fade da morte do Death Bringer [PROVÁVEL]. Conferir no BlastEm.
- Item 3: comparar o som com o BlastEm (DAC e timing do Z80).
- Item 4: gravar com `--input-script` e `--hash-frames` o primeiro diálogo e o GO!.
- Item 5: só depois, perguntar ao Garland se aceita PR com testes e CI.

## Onde estão os artefatos

- Scripts: `tools/probe/` (ver o README de lá).
- Logs, saves e capturas: `C:\Users\covre\AppData\Local\Temp\claude\71dec13997f65ab7\829e9c4a-4c1a-4004-90d6-1a2a29fd73ba\scratchpad\probe\` (pastas `wave\v2_drift`, `wave\v4_drift_s6`, `wave\v6_drift_end`, `wave\v6_nodrift_boot`, `wave\v6_nodrift_s7`). É pasta temporária; copie o que quiser guardar.
- Saves por fase: drift em `wave\v2_drift\stage1-6_start.bin` e `wave\v4_drift_s6\stage6-8_start.bin`; no-drift em `wave\v6_nodrift_boot\stage1-7_start.bin` e `wave\v6_nodrift_s7\stage7-8_start.bin`.
- Telas do final: `wave\v6_drift_end\ending_grid.png` e `wave\v6_nodrift_s7\ending_grid_nodrift.png`.
