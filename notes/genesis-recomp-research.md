# Genesis Recomp: pesquisa para um port de Golden Axe

Pesquisa feita em 2026-10-25, só com fontes primárias: o repositório oficial, os repositórios dos jogos portados e as issues e releases do GitHub. Li tudo via `gh api` ou raw, sem clonar nada.

Legenda de certeza:
- `[CONFIRMADO]`: li no arquivo ou código citado.
- `[PROVÁVEL]`: a fonte indica, mas não diz com todas as letras.
- `[INFERIDO]`: é raciocínio meu, sem fonte primária.

Repositório principal: https://github.com/mstan/segagenesisrecomp. O branch padrão se chama **`master`**, não `main`, então links com `/blob/main/` dão 404.

---

## Resumo em 10 linhas

1. O Genesis Recomp lê a ROM de um jogo de Mega Drive e gera código C equivalente ao do processador 68000. Esse C é compilado num executável de PC. `[CONFIRMADO]`
2. O que o tradutor não acha, um interpretador executa como rede de segurança e anota num arquivo, para a próxima rodada de tradução. `[CONFIRMADO]`
3. Cada jogo precisa de um arquivo de configuração próprio (`game.toml`), de um "adaptador" em C e de muito trabalho de descoberta. A configuração de um jogo não serve para outro. `[CONFIRMADO]`
4. O projeto se declara **beta**. A licença é **PolyForm Noncommercial 1.0.0**, que proíbe uso comercial. `[CONFIRMADO]`
5. Os jogos oficialmente suportados são Sonic 1, 2, CD, 3/S&K e Rocket Knight Adventures. **Shinobi III e Gain Ground não estão na lista.** `[CONFIRMADO]`
6. O Shinobi III (roccocovs) usa o motor, mas copiado e modificado dentro do próprio repositório. O histórico do Git foi achatado num único commit, então **não dá para medir pelo Git quanto tempo levou**. A melhor medida de esforço é o Rocket Knight, do próprio autor: cerca de 4 meses do esqueleto até a v1.0. `[CONFIRMADO]`
7. O **Gain Ground (GeneralAtrox) não usa o Genesis Recomp**. É a versão de **fliperama System 24**, que tem dois 68000, e foi feita com um pipeline próprio em C++. `[CONFIRMADO]`
8. Os dois ports de terceiros declaram ter usado IA de forma pesada: Shinobi com Codex e ChatGPT, Gain Ground com agentes e um servidor MCP. `[CONFIRMADO]`
9. A ROM é conferida pelo tamanho e por um hash: CRC32 no motor oficial, SHA-256 no Shinobi. Se não bater, o jogo não abre. `[CONFIRMADO]`
10. Para o Golden Axe (Mega Drive, 1989), a arquitetura do motor encaixa. O custo real está em descobrir as rotinas do jogo e em acertar o som (Z80). `[INFERIDO]`

---

## 1. Como o pipeline funciona

### 1.1 A ideia geral

O Mega Drive tem dois processadores:
- o **68000**, que roda o jogo;
- o **Z80**, que normalmente cuida do som.

O Genesis Recomp **traduz o código do 68000 para C antes de rodar** (é isso que "recompilação estática" quer dizer). Ele não emula instrução por instrução enquanto o jogo roda. `[CONFIRMADO]` README: https://github.com/mstan/segagenesisrecomp/blob/master/README.md

A parte que entende o 68000 fica num submódulo compartilhado, `external/m68k-recomp-core`. Ele tem decodificador, validador, buscador de funções (`function_finder`), gerador de código e diagnóstico (`codegen_diag`). `[CONFIRMADO]` https://github.com/mstan/segagenesisrecomp/blob/master/.gitmodules

O comando básico é este:

```
GenesisRecomp.exe <rom> --game game.toml --output-dir generated
```

`[CONFIRMADO]` https://github.com/mstan/segagenesisrecomp/blob/master/docs/GETTING_STARTED.md

### 1.2 Descoberta de funções "guiada por evidência"

O tradutor só traduz o código que ele **sabe** que é código. Numa ROM, código e dados ficam misturados, e o 68000 pula muito para endereços calculados na hora. Por isso a descoberta junta três fontes:

1. **Análise estática**: o tradutor segue os saltos que consegue ver. `[CONFIRMADO]`
2. **Desmontagem anotada**: quando existe uma desmontagem comunitária (como a de Sonic 1), os rótulos dela viram "sementes". O `game.toml` aponta para arquivos como `annotations_from_disasm.csv` e `sonic1.disasm_seeds.toml`. A regra 16 do PRINCIPLES.md diz literalmente **"DISASM IS GROUND TRUTH"**: a desmontagem é a verdade de referência. `[CONFIRMADO]` https://github.com/mstan/segagenesisrecomp/blob/master/PRINCIPLES.md
3. **Evidência de execução**: quando o jogo roda e cai num endereço que não foi traduzido, isso fica registrado (ver 1.5). As regras deixam claro que isso é **último recurso**, não o método principal. `[CONFIRMADO]` PRINCIPLES.md

A própria documentação admite que a descoberta é **conservadora**: prefere deixar algo de fora a traduzir lixo. `[CONFIRMADO]` https://github.com/mstan/segagenesisrecomp/blob/master/COVERAGE.md

### 1.3 O arquivo `game.toml`: campos reais

Trecho resumido do `sonicthehedgehog/game.toml` (Sonic 1). Os valores abaixo foram copiados do arquivo e as listas foram cortadas:

```toml
# CRC32 (JUE REV00): 0xF9394E97

[game]
output_prefix   = "sonic"
annotations     = "annotations_from_disasm.csv"
discovery_files = ["sonic1.disasm_seeds.toml", "sonic1.disasm_subs.toml", "sonic1.disasm_jumptables.toml"]

[ram_layout]
game_mode      = 0xFFF600
vint_runcount  = 0xFFFE0C
vint_routine   = 0xFFF62A
plc_pending    = 0xFFF6F8
initial_ssp    = 0xFFFE00
player_object  = 0xFFD000
level_modes    = [0x08, 0x0C]

[widescreen]
capable         = true
max_extra_cells = 8

[[widescreen_site]]   # várias entradas: addr / kind / reg / shift
# kind pode ser: mask10, cull_left, subreg, subimm, addimm, game_hook

[functions]
extra     = [0x000B5E, ...]   # rotinas que a análise não achou sozinha (ex.: VBla_Music)
blacklist = [0x007E2A, 0x00A046, 0x014CA2]   # endereços que NÃO devem ser traduzidos
```

`[CONFIRMADO]` https://github.com/mstan/segagenesisrecomp/blob/master/sonicthehedgehog/game.toml

O `project/game/game.toml` do Shinobi III é mais revelador para um jogo **sem desmontagem pronta**. Ele tem 340 linhas e cerca de 121 endereços escritos à mão:

```toml
[game]
output_prefix = "shinobi3"
jump_table_autodiscovery = false

[ram_layout]          # tudo zerado: não mapearam a RAM como no Sonic
level_modes = []

[functions]
extra = [0x000320, 0x000522, ...]   # reset, VBlank, callbacks por fase (lista longa, manual)

[[functions.interior_alias]]        # ~9 entradas: ponto de entrada no meio de outra rotina
entry = 0x001F7E
owner = 0x001F68

[[jump_table]]                      # tabela de saltos declarada à mão
start  = 0x02A4D4
end    = 0x02A504
stride = 6
format = "bra_w"
```

O próprio arquivo traz este comentário: *"Reconstructed Shinobi III build inputs. The previous per-game project was deleted."* `[CONFIRMADO]` https://github.com/roccocovs/Shinobi3Recomp/blob/main/project/game/game.toml

Em resumo: além do `.toml`, cada jogo tem um arquivo C pequeno, o `*_spec.c`, que preenche uma estrutura `GameSpec`. Nela ficam o CRC esperado, o tamanho da ROM e os "ganchos" do jogo. O do Shinobi tem 124 linhas. `[CONFIRMADO]`
- https://github.com/mstan/segagenesisrecomp/blob/master/runner/game_spec.h
- https://github.com/roccocovs/Shinobi3Recomp/blob/main/project/game/shinobi3_spec.c

### 1.4 "Transforms" e ganchos

Não existe um sistema genérico de "transforms". Existem dois mecanismos:

- **`[[widescreen_site]]`**: manda o tradutor alterar instruções em pontos específicos para abrir a tela em widescreen. É opcional e muda de jogo para jogo. `[CONFIRMADO]`
- **Ganchos do jogo**: vivem no `*_spec.c` e no `[ram_layout]`. A regra é que dado específico de um jogo fica no spec e no layout, nunca espalhado pelo runner. `[CONFIRMADO]` PRINCIPLES.md

Há também uma regra fixa: **nunca editar à mão o C gerado**. Toda correção volta para a configuração ou para o tradutor, e o código é gerado de novo. `[CONFIRMADO]` PRINCIPLES.md e GETTING_STARTED.md

### 1.5 Interpretador de reserva ("Tier-3")

Quando o jogo salta para um endereço que não foi traduzido, quem executa é um **interpretador 68000 próprio**, escrito do zero. Esse endereço fica anotado em `dispatch_misses.toml`, ao lado do executável. Ele só cobre código do cartucho. `[CONFIRMADO]` README e PRINCIPLES.md

A regra 13a define um ciclo obrigatório:
1. olhar o `dispatch_misses.toml`;
2. conferir cada endereço na desmontagem;
3. gerar o C de novo;
4. compilar;
5. repetir até o arquivo ficar vazio.

`[CONFIRMADO]` PRINCIPLES.md

### 1.6 Runtime (o "console" em software)

| Peça | O que é | Fonte |
|---|---|---|
| VDP (vídeo) | implementação própria do projeto | `[CONFIRMADO]` README |
| YM2612 (som FM) | biblioteca **ymfm** (BSD-3) | `[CONFIRMADO]` [THIRD-PARTY-LICENSES.md](https://github.com/mstan/segagenesisrecomp/blob/master/THIRD-PARTY-LICENSES.md) |
| PSG SN76489 | implementação própria | `[CONFIRMADO]` README |
| Z80 (som) | **interpretado** por superzazu/z80 (MIT) | `[CONFIRMADO]` THIRD-PARTY-LICENSES.md |
| Z80 recompilado | opcional e experimental (`GENESIS_Z80_RECOMP=ON`), desligado no build normal. Deu resultado idêntico ao interpretador em Sonic 1/2/3/S3K e RKA | `[CONFIRMADO]` [docs/Z80_STATIC_RECOMP.md](https://github.com/mstan/segagenesisrecomp/blob/master/docs/Z80_STATIC_RECOMP.md) |
| Outros | SDL2 2.28.5 (vem no repo), minicoro (fibras), tomlc99, recomp-net (jogo online), rbengine (voltar no tempo) | `[CONFIRMADO]` .gitmodules e THIRD-PARTY-LICENSES.md |

---

## 2. Passo a passo real para portar um jogo novo

Este é o roteiro do [docs/GETTING_STARTED.md](https://github.com/mstan/segagenesisrecomp/blob/master/docs/GETTING_STARTED.md) `[CONFIRMADO]`, com o que é manual marcado em cada passo:

1. **Compilar o tradutor.** Comandos:
   ```
   git clone --recurse-submodules ...
   cmake -S recompiler -B build/recompiler -G "Visual Studio 17 2022" -A x64
   cmake --build build/recompiler --config Release --parallel
   ```
   Esse passo é mecânico.
2. **Criar um repositório separado para o jogo**, com o framework como submódulo. Os diretórios antigos (`sonicthehedgehog/`, `puyo/`, `rka/`) **não servem de modelo** para trabalho novo. `[CONFIRMADO]` README
3. **Escrever o `game.toml` do jogo.** Ele descreve a identidade da ROM, as rotinas, os despachos e o comportamento de bancos e dados. Este é o grosso do trabalho manual. O guia diz: *"A Sonic configuration does not automatically describe another 68000 game."*
4. **Escrever o CMake e o adaptador.** O adaptador liga o código gerado ao runner, define como roda um quadro, confere a ROM e integra com o runtime. Também é manual.
5. **Gerar, compilar e jogar.** Depois, repetir o ciclo do `dispatch_misses.toml` até ele ficar vazio.
6. **Validar o jogo original primeiro**, comparando com um emulador confiável num trecho curto e com o interpretador de reserva ligado. Widescreen e extras vêm só depois.

As regras também dizem que **quem verifica de ponta a ponta é o usuário, jogando**. Não existe CI na nuvem, porque o build precisa da ROM. `[CONFIRMADO]` PRINCIPLES.md

### Onde a IA entra

- O README do motor diz que ele funciona com *"command-line tools and source code, with no AI required"*. Ou seja, a IA não é necessária. `[CONFIRMADO]` README
- O repositório tem um `CLAUDE.md` e o rodapé cita o Discord "R.A.I.D. (Retro AI Development)". Isso indica que o autor trabalha com agentes de IA. `[PROVÁVEL]`
- O Shinobi III declara: *"developed with substantial assistance from OpenAI Codex and ChatGPT, including ROM analysis, code generation, debugging..."* `[CONFIRMADO]` https://github.com/roccocovs/Shinobi3Recomp
- `[INFERIDO]` A IA ajuda bem em três tarefas:
  - ler a desmontagem e propor endereços para o `game.toml`;
  - interpretar os registros de depuração;
  - escrever testes.

  O teste final continua sendo jogar.

### Ferramentas de depuração que existem

Todas confirmadas no [DEBUG.md](https://github.com/mstan/segagenesisrecomp/blob/master/DEBUG.md) e no [COSIM.md](https://github.com/mstan/segagenesisrecomp/blob/master/COSIM.md) `[CONFIRMADO]`:

- **Servidor de depuração TCP**: porta 4378. Aceita comandos JSON como `read_ram`, `vdp_state`, `z80_state`, `get_frame` e `crash_trail`.
- **Gravadores sempre ligados**: guardam os últimos 600 quadros, até 1 milhão de escritas na RAM (para "voltar no tempo"), um rastro de crash e a fila de eventos de áudio.
- **Co-simulação**: roda o código traduzido lado a lado com o interpretador para achar onde os dois divergem. `GENESIS_FORCE_INTERP=1` força tudo no interpretador. O emulador de referência clownmdemu foi removido em 2026-07-27.
- **Diagnóstico**: o `codegen_diag` com `--fail-on-unsupported` lista as instruções que o tradutor não suporta. O `boot_smoke.py` compara o boot com uma referência gravada.
- **Scripts Python em `tools/`**: `divergence_report`, `frame_wram_diff`, `chip_trace_analyze` e outros.

---

## 3. Esforço real: o que as datas mostram

| Projeto | Datas | O que dá para concluir |
|---|---|---|
| Motor (mstan) | 1º commit em 2026-03-24, cerca de 356 commits até 2026-10-23. Releases: v0.1.0 (2026-06-17), v0.1.1 (2026-10-18), v0.1.2 (2026-10-23) | Sete meses de trabalho contínuo **só no motor**, ainda em beta `[CONFIRMADO]` |
| Shinobi III | Repo criado em 2026-10-23. Um único "Initial commit" (41fa1f9), release v0.1.0 no mesmo dia | **Não dá para medir.** O histórico foi achatado, e o próprio `game.toml` diz que o projeto anterior foi apagado. O `docs/DEVELOPMENT-HISTORY.md` lista marcos sem datas `[CONFIRMADO]` |
| **Rocket Knight Adventures** (mstan) | É o primeiro jogo não-Sonic do motor, sem desmontagem pronta. Commit "scaffold ... (first non-Sonic bring-up)" em 2026-06-18. Repo do jogo com 1º commit em 2026-06-19 e cerca de 60 commits. Release v0.1.13 em 2026-10-05, **v1.0.0 em 2026-10-23** | **É a melhor medida disponível: cerca de 4 meses do esqueleto até a v1.0**, feitos pelo próprio autor do motor e com o motor sendo melhorado ao mesmo tempo. As releases anteriores à v0.1.13 não aparecem na API, então não sei a data do primeiro "jogável" `[CONFIRMADO]` para as datas, `[INFERIDO]` para a leitura |
| Gain Ground | 1º commit em 2026-09-13 ("Publish source-only native port", já jogável), 14 commits até 2026-10-17, 6 builds para Windows | Mede só a **manutenção pública** (cerca de 5 semanas). O trabalho anterior ao primeiro commit não aparece. E, de novo, **não é Genesis Recomp** `[CONFIRMADO]` |

Links:
- https://github.com/mstan/segagenesisrecomp/releases
- https://github.com/roccocovs/Shinobi3Recomp/commits/main
- https://github.com/GeneralAtrox/GainGround_ModernSourcePort/commits
- https://github.com/mstan/RocketKnightAdventuresRecomp e https://github.com/mstan/segagenesisrecomp/blob/master/rka/DEVELOPMENT.md

O diário do RKA mostra como é a descoberta sem desmontagem: `[CONFIRMADO]` rka/DEVELOPMENT.md
- No começo o jogo "desenhava o cenário mas não tinha gameplay", porque os objetos eram chamados por tabelas de salto que o tradutor não enxergava.
- Uma correção levou o número de funções de 934 para 4545 e zerou os "misses". Mas ela **quebrou a tela de título**, porque passou a traduzir dados como se fossem código. O autor chama isso de "falso cume": sem desmontagem, falta um "oráculo" que diga o que é código.

`[INFERIDO]` Nenhum dos ports de terceiros publica o tempo que levou "do zero até jogável". O Shinobi é a referência mais próxima entre eles, porque é Mega Drive e não tinha desmontagem pronta. Ele tem um sinal claro de esforço alto:
- cerca de 121 raízes de função descobertas à mão;
- cerca de 50 testes por fase;
- a correção do final do jogo exigiu mexer no runtime do Z80.

---

## 4. Build no Windows e licença

**Motor (oficial)** `[CONFIRMADO]` em GETTING_STARTED.md e README:
- Git for Windows.
- Visual Studio 2022 com a carga "Desktop development with C++" e as ferramentas de CMake.
- O build roda dentro do Developer PowerShell.
- O tradutor é escrito em C11. O build é por CMake, com MSVC ou Ninja.
- O SDL2 já vem no repositório. Não precisa instalar outras bibliotecas.
- Tamanho: o GitHub informa cerca de **91 MB** de repositório, contando o zip do SDL2. Os submódulos e a pasta de build somam mais. `[CONFIRMADO]` para o repositório, `[INFERIDO]` para o total em disco.
- Os testes rodam com `cmake -S tests -B build/tests` e depois `ctest`.

**Shinobi III** usa outra cadeia: CMake 3.24+, Ninja, Python 3 e **Zig 0.17.0** como compilador. Não usa VS. `[CONFIRMADO]` `build-windows.ps1` no repositório.

**Gain Ground** usa MSYS2 UCRT64 (g++), CMake 3.24+, Ninja e zlib. `[CONFIRMADO]`

**Licenças:**
- **Motor**: **PolyForm Noncommercial 1.0.0** (`LICENSE.md`, `LICENSE-recompiler`, "Copyright (c) 2026 Matthew Stan"). Pode usar e modificar **para fins não comerciais**. Vender ou monetizar o port não é permitido. `[CONFIRMADO]` https://github.com/mstan/segagenesisrecomp/blob/master/LICENSE.md
- **Dependências**: todas permissivas (BSD-3, MIT, ISC, zlib, Unlicense), sem nenhuma AGPL. `[CONFIRMADO]` THIRD-PARTY-LICENSES.md
- **Sobre a ROM**: o binário distribuído não pode conter a ROM. O C gerado é uma tradução de máquina do código da ROM. `[CONFIRMADO]` THIRD-PARTY-LICENSES.md. `[INFERIDO]` Por isso, publicar a pasta `generated/` é juridicamente delicado.
- **Gain Ground**: o repositório não tem licença declarada. `[CONFIRMADO]`

---

## 5. Limitações conhecidas

`[CONFIRMADO]` em COVERAGE.md e docs:
- Algumas formas de salto dinâmico (`JSR`/`JMP` com endereço calculado) **não são suportadas** pelo tradutor. Elas caem no interpretador.
- `ADDX`/`SUBX` com pré-decremento de memória é uma lacuna conhecida.
- A descoberta é conservadora, e os testes sintéticos não cobrem todas as combinações de instruções.
- O Z80 é **interpretado** por padrão. A versão recompilada é experimental.
- O Shinobi precisou corrigir o **aperto de mão entre 68000 e Z80** (bus request e mailbox) para o final do jogo funcionar. O teste dessa correção se chama `R7EndingZ80Handshake`. Ou seja, a sincronização entre os dois processadores **é um ponto frágil**. `[CONFIRMADO]` README do Shinobi3Recomp
- O Shinobi continua com interpretação "híbrida" em alguns caminhos dinâmicos e um aviso conhecido na fase de Mijin. `[CONFIRMADO]`
- Issues abertas no motor: #29 (SRAM de cartucho sempre mapeada), #23 (escala de saída em HiDPI) e #19 (VDP em lote, experimental). `[CONFIRMADO]` https://github.com/mstan/segagenesisrecomp/issues
- Sega CD fica num branch separado e não tem interpretador de reserva. `[CONFIRMADO]`
- Jogos com **dois 68000**, como o System 24 do Gain Ground arcade, estão **fora do escopo** do Genesis Recomp. `[INFERIDO]` O Mega Drive tem um só 68000, e o autor do Gain Ground criou outro pipeline.

**Isso afeta o Golden Axe (Mega Drive, 1989)?**
- **Dois processadores 68000**: não. A versão Mega Drive tem um 68000 e um Z80, igual ao Sonic. `[PROVÁVEL]` Isso é o hardware padrão do console, não verifiquei a ROM.
- **Driver de som no Z80**: é o ponto de risco. O jogo é de 1989, anterior ao Sonic, e pode usar um driver Z80 diferente dos já testados (Sonic, RKA). Se usar, pode exigir o mesmo tipo de ajuste de sincronização que o Shinobi precisou. Não verifiquei qual driver ele usa. `[INFERIDO]`
- **Truques de VDP**: em beat 'em up costumam ser rolagem por linha, muitos sprites e prioridades. O VDP do projeto roda Sonic 1/2/3, que usa bastante disso. Daí a expectativa de que funcione, mas ninguém testou. `[INFERIDO]`
- **Timing**: o projeto roda por quadro. Se o jogo depende de contagem fina de ciclos, isso aparece nos testes. `[INFERIDO]`

---

## 6. Revisão de ROM e como a verificação funciona

Aqui descrevo só o mecanismo. Não procurei nem referenciei ROMs.

- **Motor oficial**: o `GameSpec` de cada jogo traz dois campos, `expected_rom_crc32` e `expected_rom_size`. O `runner/main.c` calcula o CRC32 do arquivo e compara. Se não bater, o jogo não começa e aparece a mensagem *"ROM identity mismatch ... CRC32=..., expected=..."*. O launcher pede o arquivo de novo. O valor `0` desliga a checagem. `[CONFIRMADO]`
  - https://github.com/mstan/segagenesisrecomp/blob/master/runner/game_spec.h
  - https://github.com/mstan/segagenesisrecomp/blob/master/runner/main.c

  O Sonic 1 exige a revisão "JUE REV00" (CRC indicado no `game.toml` e no `sonic1_spec.c`). Isso importa porque **endereços do `game.toml` só valem para aquela revisão exata**. `[CONFIRMADO]` para o campo. `[INFERIDO]` para o motivo, mas é a consequência direta de usar endereços fixos.
- **Shinobi III**: exige o tamanho exato de 1 MiB e um **SHA-256** específico, conferido no script de build (`Get-FileHash`) e de novo ao abrir o jogo. `[CONFIRMADO]`
- **Gain Ground (arcade)**: confere o conjunto de arquivos do fliperama e o disco de dados, todos pela identidade. Depois guarda os dados extraídos em `%LOCALAPPDATA%\GainGround\`. `[CONFIRMADO]`

---

## O que isto significa para um port de Golden Axe

1. **É viável no papel.** O Golden Axe de Mega Drive tem o mesmo hardware que o motor já roda: um 68000, um Z80, VDP, YM2612 e PSG. Não é o caso do Gain Ground, que exigiu outro pipeline. `[PROVÁVEL]`
2. **O modelo a seguir é o Shinobi III, não o Sonic.** O Sonic tem desmontagem comunitária, mapa de RAM e rótulos, e o `game.toml` sai quase "pronto". Sem desmontagem equivalente, o trabalho vira o do Shinobi: achar à mão dezenas a centenas de pontos de entrada, tabelas de salto e callbacks, rodando o ciclo do `dispatch_misses.toml` muitas vezes. `[INFERIDO]` Não verifiquei se existe uma desmontagem pública do Golden Axe de Mega Drive. Isso é o primeiro item a checar.
3. **A primeira decisão é fixar a revisão da ROM.** Todo endereço no `game.toml` depende dela. Conferir com CRC32 ou SHA-256, como os projetos acima fazem. `[INFERIDO]` com base em 1.3 e 6.
4. **O risco técnico principal é o som (Z80) e a sincronização com o 68000.** Foi onde o Shinobi teve que corrigir o runtime. O VDP é um risco menor. `[INFERIDO]`
5. **Dois jogadores:** jogar no mesmo PC vem do próprio jogo. O jogo online usa o recomp-net, com rollback para 1 a 4 jogadores (issues #12 e #21). Mas ele exige que o jogo seja determinístico e tem um contrato próprio com o runner. Isso é trabalho extra e deve ficar para depois. `[PROVÁVEL]`
6. **Prazo realista:** nenhum port publica "dias até jogável". O melhor dado é o RKA: cerca de 4 meses do esqueleto até a v1.0, feitos pelo próprio autor do motor. O Shinobi precisou de muita IA, de cerca de 121 raízes manuais e de testes por fase. Para alguém de fora do projeto, espere **meses**, não dias nem semanas. `[INFERIDO]`
7. **Licença:** o port herda a licença PolyForm Noncommercial. Ele só pode ser projeto pessoal ou gratuito, sem venda. Também não pode distribuir a ROM. `[CONFIRMADO]` para a licença, `[INFERIDO]` para a aplicação ao caso.
8. **Build:** o caminho oficial é VS 2022 com CMake. É mais simples seguir o oficial do que copiar a cadeia do Shinobi (Zig). `[INFERIDO]`

---

## Lacunas / o que não consegui verificar

- **Tempo real até ficar jogável**: o histórico do Shinobi foi achatado e o do Gain Ground começa já jogável. O RKA dá as datas de esqueleto e de v1.0, mas não a data do primeiro "jogável".
- **Desmontagem pública do Golden Axe de Mega Drive**: o Golden Axe não aparece no índice `docs/DISASSEMBLIES.md` do repositório oficial nem na issue #17 (lista de jogos pedidos, corpo e comentários). Não pesquisei fora disso, porque a tarefa se limitava aos repositórios do Genesis Recomp e dos ports.
- **Detalhes do hardware do Golden Axe** (driver de som, uso de VDP): falei por inferência, sem fonte.
- **Requisitos de espaço em disco** depois de clonar os submódulos e compilar: só tenho o tamanho do repositório (cerca de 91 MB).
- **Não li**:
  - `recompiler/CMakeLists.txt` (para confirmar a versão mínima do CMake do motor);
  - `release/v0.1.1.md`;
  - `docs/DISASSEMBLIES.md` (só procurei "Golden Axe" nele);
  - `GENESIS_AUDIO_FIDELITY.md`;
  - o resto do `rka/DEVELOPMENT.md` (li só a primeira metade);
  - os documentos de comparação e auditoria do Shinobi (`UPSTREAM-PRACTICES-COMPARISON.md`, `REGENERATION-AUDIT.md`).
- **Não compilei nem rodei nada**, por restrição da tarefa. Tudo aqui é documentação e código lido, sem teste prático.
