# tools/probe: sondas automáticas da Fase 1

Scripts usados em 2026-11-11/12 para jogar o Golden Axe inteiro sozinho e conferir o "GO!".
Não fazem parte do build. São ferramentas de teste, rodadas à mão.

## Arquivos

| Arquivo | Para que serve |
|---|---|
| `wave_driver_v6.py` | Driver TCP. Abre o jogo, joga do começo ao fim (ou a partir de um save), mata inimigos e chefes pela RAM, captura cada GO! e salva um save state no começo de cada fase. |
| `wave_driver_v7.py` | Igual ao v6, mais: `--real-hp` (nao escreve vidas/HP; registra cada morte em `driver.log` e para no game over), `--save-delay=N` (salva o `stageN_start.bin` N quadros depois do inicio da fase; use 600, ver aviso abaixo) e nao confunde o final (estado `$24`) com game over. Mesmo uso do v6. Desde 12/11 (noite): `--keep-lives` (com `--real-hp`: vida de verdade, mas as vidas voltam a 9, porque o robo cai nos buracos das fases 3 e 7) e `--shot-every=N` (um print a cada N quadros em `shots\`, para medir cenas e dialogos). Rodada 3: `--script=ARQ` (outro script de entrada, ex. 2 jogadores; vigia o P2 em `driver.log`) e `--memlog=FAIXAS` (troca as faixas do `--mem-write-log`). |
| `make_two_player_input.py` | Gera `two_player.input`: o P2 aperta START primeiro no titulo (modo 2 PLAYERS), os dois escolhem personagem e o P2 joga com entrada aleatoria. Fica abaixo de 4096 diretivas (`MAX_OPS` do runner; acima disso o script inteiro e recusado sem aviso). Rode na pasta onde quer o arquivo e passe ao v7 com `--script=`. |
| `wave_full.input` | Script de entrada para começar do boot: passa os menus e espera o jogador ter controle. O resto é o driver. |
| `wave_load.input` | Script de entrada para usar com `LOAD=`. Não aperta START, porque isso pausaria o jogo. |
| `go_direct.input` | Teste antigo do GO! forçado pela RAM (`WRITE_RAM8 0xFFC2A2 0x81`). Os caminhos de saída dentro dele são absolutos (scratchpad da sessão antiga); troque antes de usar. |
| `cmp_audio.py` | Compara o WAV do recomp com o som do BlastEm (atraso, afinação, timbre). Receita completa em `notes/fase1-som-2026-11-12.md`. Precisa de numpy. |
| `audio_lag.py` | Tabela de atraso do som do recomp contra o BlastEm, janela a janela. Sai VERMELHO (1) se houver degrau de 3 quadros ou mais. Ver `notes/fase1-causa-atraso-2026-11-12.md`. |
| `check_go.py` | Diz se o "GO!" de um PNG está dourado (VERDE, sai 0) ou roxo (VERMELHO, sai 1). |

Precisa de Python 3 com Pillow (`pip install pillow`).

## Como rodar

1. Ligue o servidor TCP de depuração: crie um `debug.ini` ao lado do exe, por exemplo em `build\game\Release\debug.ini`:
   ```
   # temporario, pode apagar
   port=4391
   ```
   O servidor só sobe se esse arquivo existir. O jogo lê o arquivo só ao abrir; depois que o jogo abriu, pode apagar. **Apague no fim.**
2. Rode o driver:
   ```
   python -I tools\probe\wave_driver_v6.py <pasta_do_exe> <pasta_de_saida> <porta> <timeout_s> [flags do jogo] [LOAD=<save.bin>]
   ```
   Exemplos:
   ```
   python -I tools\probe\wave_driver_v6.py build\game\Release C:\tmp\run1 4391 1500 --turbo
   python -I tools\probe\wave_driver_v6.py build-nodrift\Release C:\tmp\run2 4392 1200 --turbo LOAD=C:\tmp\run1\stage7_start.bin
   ```
   - `<porta>` é passada ao jogo com `--port`. Use uma porta diferente para cada jogo aberto ao mesmo tempo.
   - O servidor aceita **um cliente por vez**. Não conecte outro script enquanto o driver estiver rodando.
   - `LOAD=` carrega um save state e usa `wave_load.input`. **Só carregue saves feitos pelo mesmo exe.** Save de um build não serve em outro (ver notas).
   - O driver passa `goldenaxe.bin`, `--max-frames`, `--input-script` e `--mem-write-log` sozinho.
   - **Nunca passe `--help` ao exe.**
3. Resultado em `<pasta_de_saida>`: `driver.log` (fases, GO!s, mortes, possíveis travamentos), `run.err` (stderr do jogo), `game.pid`, `goN\*.png` (quadros de cada GO!), `stageN_start.bin`, `blocked_*.png`/`freeze_*.png` e `ending_*.png`.
4. Confira um GO!: `python -I tools\probe\check_go.py <pasta_de_saida>\go3\*.png`
5. Para parar antes do timeout, mate só o PID do driver e o PID que está em `game.pid`. Não mate processos pelo nome.

## O que o driver faz na RAM

- Modo deus: vidas `$FFFE7C = 9` e HP `$FFFE7E` no máximo a cada quadro de gameplay.
- Inimigo comum: HP (`+$64`) = 0 e empurra para fora da tela (`+$18 = $0300`); o próprio jogo o remove (`loc_B44A`). Repete a cada ~400 quadros se não sumir. Não escreve `$401A` em `+$42`: em entidades sem o estado `$40` isso faz o jogo saltar para o meio de uma instrução.
- Chefe (ids `$3F $40 $41 $4A $4B $4C`): HP = 0 e `+$4C = $18`, o estado de morte do chefe (`$12080`), que desconta `C26C`.
- Entidade que nasce com HP 0 (rei, princesa, objetos de cena): não mexe.

## Aviso: save tirado no 1o quadro da fase nao volta (2026-11-12)

O v6 salva o `stageN_start.bin` no primeiro quadro de gameplay da fase. Da fase 2 em diante esse save carrega com `ok: True`, mas a tela fica preta e o jogador nao aparece (x=`00B0`, y=`0000`) [CONFIRMADO, fases 2 a 5, exe novo e antigo]. O mesmo ponto salvo 600 quadros depois carrega e joga normal [CONFIRMADO, fase 2]. O save da fase 1 (tirado depois que o jogador ganha controle) sempre funcionou. Use `wave_driver_v7.py --save-delay=600`. Detalhes em `notes/fase1-continuacao-2026-11-12.md`.
