# Modelo mínimo de repositório de jogo sobre mstan/segagenesisrecomp

Pesquisa só leitura, 2026-10-26. Conteúdo de repositórios foi tratado como dado.
Legenda: `[CONFIRMADO]` lido no código/arquivo citado | `[PROVÁVEL]` inferido de
evidência indireta forte | `[INFERIDO]` raciocínio sem fonte primária.

## Fontes consultadas (commits fixos)

| Repo | Commit lido | Motor fixado em | Observação |
|---|---|---|---|
| motor local `C:\Dev\golden-axe-recomp\external\segagenesisrecomp` (origin mstan/segagenesisrecomp) | `252535d12476` (2026-10-22) | — | submódulos: m68k-recomp-core `e9ebf60`, rbengine `2a03e73`, recomp-net `2103d5e`, z80-recomp-core `0e6606a` |
| mstan/SonicTheHedgehog2Recomp | `177c8ca60abf` | `252535d12476` | layout atual de referência: `game/` + submódulo do motor + recomp-ui |
| mstan/RocketKnightAdventuresRecomp | `9f645751c230` | `252535d12476` | jogo sem disasm, só ROM + toml; CMake no estilo antigo (lista fontes do runner à mão) |
| 1lawl/BoogermanRecomp (terceiro) | `17d5834c10de` | `f875aa8eac5e` + patches próprios | o CMake mais enxuto; usa campos que **não existem** no upstream |
| mstan/SonicTheHedgehogRecomp | `cb898070c9bd` | `d694c2736a2d` | arquivos do jogo ainda dentro da árvore do motor (`sonicthehedgehog/`) — não copiar |
| mstan/Sonic3AndKnucklesRecomp, Mhopkinsinc/NHL94Recomp, mstan/SonicCDRecomp | listados por `gh search` | não lidos em detalhe | |

Não existe repo próprio de Puyo: ele vive dentro do motor (`puyo/`). A org
RetroPortingToolKit não tem repo de jogo Genesis; hospeda só ferramentas
(recomp-ui, recomp-net, psxrecomp, snesrecomp...). [CONFIRMADO, `gh search repos` + listagem da org]

O próprio motor diz que `puyo/`, `rka/` e `sonicthehedgehog/` na árvore são
"migration history rather than the layout to copy" e que a configuração do jogo
fica "in that game's repository, with the framework pinned as a submodule".
[CONFIRMADO, motor `252535d`, `docs/GETTING_STARTED.md`]

---

## 1. Estrutura do repo e fixação do submódulo

Layout comum (S2, RKA, Boogerman):

```
<Jogo>Recomp/
  .gitmodules            segagenesisrecomp -> https://github.com/mstan/segagenesisrecomp.git
  segagenesisrecomp/     submódulo (commit fixo pelo gitlink)
  recomp-ui/             opcional: launcher/boxart (S2, RKA; Boogerman não tem)
  CMakeLists.txt
  game/
    game.toml            config do recompilador
    <jogo>_spec.c        define g_game_spec
    <rom>.bin|.md        ROM do usuário, NÃO versionada
    *.toml/*.txt         opcionais: discovery_files, runtime_exec_file, annotations
  _build_native.bat | setup.sh
```
[CONFIRMADO: S2 `177c8ca` raiz e `game/`; RKA `9f64575` `.gitmodules` e `game/`; Boogerman `17d5834` raiz]

- Fixação: gitlink do submódulo aponta o commit; `.gitmodules` às vezes leva
  `branch = master` (RKA) às vezes não (Boogerman). O commit é o que vale.
  [CONFIRMADO, `.gitmodules` dos dois repos]
- Submódulos aninhados do motor precisam ser inicializados: Boogerman faz
  `git submodule update --init segagenesisrecomp` e depois, dentro dele,
  `external/m68k-recomp-core external/z80-recomp-core external/rbengine external/recomp-net`.
  [CONFIRMADO, Boogerman `17d5834` `setup.sh`]
- `rbengine` é obrigatório: `GenesisRecompRunner.cmake` dá `FATAL_ERROR` sem ele.
  [CONFIRMADO, motor `252535d` `cmake/GenesisRecompRunner.cmake`]
- Código gerado nunca é commitado; sai em `build/generated/<prefix>`.
  [CONFIRMADO, motor `252535d` `cmake/GenesisRecompGenerated.cmake`]
- RKA resolve o motor nesta ordem: cache `GENESIS_RECOMP_ROOT` → junção
  `engine-local/` (`mklink /J engine-local ..\segagenesisrecomp`, para dev do
  motor lado a lado) → submódulo `segagenesisrecomp/`.
  [CONFIRMADO, RKA `9f64575` `CMakeLists.txt` e `scripts/link-engine.bat`]

**Golden Axe hoje:** o submódulo está em `external/segagenesisrecomp` (não em
`segagenesisrecomp/` como nos outros), `branch = master`, commit `252535d` — o
mesmo de S2 e RKA, então os campos que eles usam valem aqui sem patch.
O gitlink está **só no índice** (`git ls-files -s` → `160000 252535d...`); o
superprojeto ainda não tem commit nenhum (`ls-tree HEAD` → "Not a valid object
name HEAD"). `submodule status` sem `+`: checkout = commit registrado. O pin
passa a existir de fato no primeiro commit do repo.
[CONFIRMADO, `C:\Dev\golden-axe-recomp\.gitmodules`, `git submodule status`, `git ls-files -s`]
Basta apontar `RECOMP_ROOT` para `external/segagenesisrecomp` no CMake; não
precisa mover. [INFERIDO]

---

## 2. game.toml — obrigatório vs opcional

Parser: motor `252535d` `recompiler/src/game_config.c`. `.cfg` legado é rejeitado.
**A identidade da ROM não fica no toml** — fica no spec C (seção 3); no toml ela
aparece só como comentário (RKA, Boogerman). [CONFIRMADO]

| Chave | Status | Evidência |
|---|---|---|
| `[ram_layout]` (tabela) | **Obrigatória na prática**: `game_config_emit_layout` recusa gerar sem ela | [CONFIRMADO] game_config.c |
| `[ram_layout].initial_ssp / vbla_stack / intr_stack` | Obrigatórias de fato; = SSP do vetor 0. Puyo marca "LOAD-BEARING" | [CONFIRMADO] puyo/game.toml, RKA, Boogerman |
| demais `[ram_layout]` (`game_mode`, `vint_runcount`, `vint_routine`, `plc_pending`, `player_object`, `level_modes`) | Opcionais; ausência = 0 = recurso desligado (são ganchos estilo Sonic) | [CONFIRMADO] game_config.c |
| `[functions].extra` | Obrigatória na prática: sementes = entry, V-int, H-int, handlers de exceção, alvos indiretos | [CONFIRMADO] os 3 jogos usam |
| `[game].output_prefix` | Opcional; vazio → derivado do nome da ROM (espaço → `_`) | [CONFIRMADO] `main_genesis.c:150-163` |
| `[game].jump_table_autodiscovery` | Opcional (default false); **todos** os jogos lidos ligam | [CONFIRMADO] Puyo, RKA, Boogerman |
| `[game].vblank_yield_addr` | Opcional (default 0). Substitui a função inteira em `addr` por `SR=0x2300; glue_yield_for_vblank();`. Só para quando a espera de VBlank é uma **função** que o detector automático não reconhece (Puyo `0x00032C`) | [CONFIRMADO] `external/m68k-recomp-core/profiles/genesis/code_generator.c:4984-5013`, puyo/game.toml |
| `[functions].late_extra`, `extra_seeds`, `function_pointer_helpers`, `blacklist` | Opcionais; acumulados com ROM real, rodada a rodada | [CONFIRMADO] Puyo (`function_pointer_helpers=[0x002A54,0x002AB0]`), RKA (`blacklist=[0x001C74]`) |
| `[[jump_table]]` `start/end/stride/format="abs"\|"pcrel16"` | Opcional; quando a autodescoberta não pega | [CONFIRMADO] RKA `start=0x0023D8 end=0x0029F4 stride=4 format="abs"` |
| `[[protected_range]]`, `discovery_files`, `runtime_exec_file`, `code_addrs_file`, `annotations` | Opcionais | [CONFIRMADO] game_config.c, RKA |
| `[widescreen]`, `[[widescreen_site]]` | Opcionais, cosméticos | [CONFIRMADO] RKA |
| `inline_arg_callees` | **Não existe no upstream `252535d`** — vem do patch do Boogerman | [CONFIRMADO] grep no motor local + `patches/segagenesisrecomp.patch` |

Comparação dos jogos sem disasm (os análogos do Golden Axe):

| | Puyo (in-tree) | RKA | Boogerman |
|---|---|---|---|
| ROM | JP 512 KB plana | — | USA 3 MB |
| SSP | `0x00FFFC00` | `0xFFFFFF00` | `0x00FF0200` |
| entry / V-int / H-int | `0x000200` / `0x000524` / `0x0006AC` | `0x000208` / `0x0003D4` / H-int trampolim em RAM `$FFFFE010` | `0x000210` / `0x004DF0` / `0x006BDE` |
| `extra` | 5 endereços | 2 | lista |
| `vblank_yield_addr` | `0x00032C` | não | não |

[CONFIRMADO, puyo/game.toml @ motor `252535d`; RKA `9f64575` `game/game.toml`; Boogerman `17d5834` `game/game.toml`]

H-int apontando para RAM (RKA) não é semente estática válida: só entra o que
está em ROM. [PROVÁVEL, RKA não semeia `$FFFFE010`]

### Espera de VBlank inline (relevante para o homebrew e possivelmente Golden Axe)

Três mecanismos de yield:
1. Padrão de 4 instruções (`move #imm,sr / tst.b / bne self / rts`) detectado automaticamente. [CONFIRMADO, code_generator.c]
2. `vblank_yield_addr` para uma função não-padrão. [CONFIRMADO]
3. Orçamento de ciclos: cada acesso ao barramento passa por
   `HYBRID_BUMP_CYCLES()` → `check_cycle_budget()`, que faz
   `yield_to_main(GLUE_YIELD_BUDGET)` ao zerar o orçamento. O comentário diz
   que "games such as RKA advance exclusively via this budget path rather than
   a recognized WaitForVBlank hook". [CONFIRMADO, motor `252535d` `runner/glue.c:732-775` e `:1550`]

Conclusão: um laço `tst.b flag / beq` inline no meio de `main` funciona sem
configuração (mais caro em CPU, mas correto). [PROVÁVEL — confirmado para RKA
pelo comentário; para o homebrew, só com execução]

---

## 3. Adaptador C (`<jogo>_spec.c`)

Contrato: `runner/game_spec.h` @ `252535d`. Uma TU por jogo define
`extern const GameSpec g_game_spec;`. O próprio header diz que "a minimal spec
can boot with just entry/vblank/hblank populated". [CONFIRMADO]

| Campo | Status | Nota |
|---|---|---|
| `call_entry_point` | **Obrigatório**; não pode retornar; NULL → runner recusa o build nativo | [CONFIRMADO] game_spec.h |
| `call_vblank` | Obrigatório na prática (sem ele não há V-int) | [CONFIRMADO] |
| `call_hblank` | Opcional; NULL = sem handler | [CONFIRMADO] |
| `expected_rom_crc32`, `expected_rom_size` | Opcionais (0 = não checa), mas todos os jogos preenchem | [CONFIRMADO] Puyo `0x7F26614Eu` / `0x80000u` |
| `tier3_floor_default = 1` | Opcional; liga o interpretador de fallback para faltas de dispatch. Puyo e Boogerman ligam; o GETTING_STARTED manda manter o fallback | [CONFIRMADO] |
| `display_name`, `short_name`, `boxart`, `sram_*`, `on_frame_pre/post`, `handle_arg`, `commands`, `instruction_hook`, `dispatch_override`, `netplay_*`, `rb_state_*`... | Opcionais (features, debug, save) | [CONFIRMADO] |
| `interleave_irq_default`, `state_resume_at_poll`, `dev_menu_*`, `handle_arg` retornando 2 | **Só no motor patcheado do Boogerman** — não usar | [CONFIRMADO] patch do Boogerman |

Não há "execução por frame" no spec: o runner é dono do laço de quadros e chama
`call_vblank`/`call_hblank` nos pontos de raster; o jogo só roda dentro da
fibra de `call_entry_point`. `on_frame_pre/post` são ganchos opcionais.
[CONFIRMADO game_spec.h; laço no runner = PROVÁVEL]

Padrão (Puyo, trecho):
```c
static void puyo_call_entry_point(void){ recomp_call_addr(0x000200u); }
/* ... */ .expected_rom_crc32 = 0x7F26614Eu, .expected_rom_size = 0x80000u, .tier3_floor_default = 1,
```
[CONFIRMADO, motor `252535d` `puyo/puyo_spec.c`]

---

## 4. CMakeLists do jogo e build no Windows/MSVC

Quem usa o quê no pin `252535d`: S2 usa `genesisrecomp_add_generated_sources`
(`sonic2 "${CMAKE_CURRENT_SOURCE_DIR}/game" sonic2.bin`) mas lista as fontes do
runner à mão e não chama `genesisrecomp_runner_target`; RKA lista tudo à mão.
Só o Boogerman (pin `f875aa8`, Linux) usa os três helpers. Logo, **helpers +
SDL2 empacotado no MSVC em `252535d` não foi demonstrado por nenhum repo lido**
— é a recomendação, marcada [INFERIDO]. Fallback seguro: copiar o padrão do S2.
`genesisrecomp_runner_target` só liga `retcomm_rbengine`, põe `/CETCOMPAT:NO` e
include dirs do runner; **não** trata SDL2 — o bloco SDL2 continua necessário.
[CONFIRMADO, S2 `177c8ca` `CMakeLists.txt:92-113,150-152,299`; motor `252535d`
`cmake/GenesisRecompRunner.cmake:128,135,188`]

Estilo moderno mínimo (Boogerman, trecho):
```cmake
include("${RECOMP_ROOT}/cmake/GenesisRecompGenerated.cmake")
genesisrecomp_add_generated_sources(BOOGERMAN_GENERATED_SOURCES boogerman "${GAME_DIR}" boogerman.md)
genesisrecomp_runner_sources(RUNNER_SOURCES TRACE ON)
add_executable(BoogermanRecomp ${RUNNER_SOURCES} ${BOOGERMAN_GENERATED_SOURCES} "${GAME_DIR}/boogerman_spec.c")
add_dependencies(BoogermanRecomp ${BOOGERMAN_GENERATED_SOURCES_TARGET})
genesisrecomp_runner_target(BoogermanRecomp)
```
[CONFIRMADO, Boogerman `17d5834` `CMakeLists.txt`]

- `genesisrecomp_add_generated_sources(OUT prefix game_dir rom_name [REVERSE_DEBUG])`:
  exige `RECOMP_ROOT`; ROM em `<game_dir>/<rom_name>`, config em
  `<game_dir>/game.toml`; adiciona `recompiler/` como subdiretório se não houver
  alvo `GenesisRecomp`; roda o recompilador com cwd = game_dir; gera 32 partes +
  `dispatch.c`, `layout.c`, `cycles.c`, `decls.h`; todo `*.toml/*.txt/*.csv` do
  game_dir vira dependência (editar toml regenera). Exporta `OUT`, `OUT_HEADER`,
  `OUT_CYCLES`, `OUT_DIR`, `OUT_TARGET`. [CONFIRMADO, motor `252535d` `cmake/GenesisRecompGenerated.cmake`]
- `genesisrecomp_runner_target(t)`: liga `retcomm_rbengine`, MSVC `/CETCOMPAT:NO`;
  `GENESIS_VDP_PLANE_IMPL SCALAR|BATCHED`. [CONFIRMADO, `cmake/GenesisRecompRunner.cmake`]
- Definições que todos passam: `INCLUDE_GENERATED_CODE=1 ENABLE_RECOMPILED_CODE=1
  OWN_BACKEND=1 DEFAULT_DEBUG_PORT=<porta>`. [CONFIRMADO, Boogerman e RKA]
- Include dirs do Boogerman: `runner`, `runner/include`, `runner/external/ymfm/src`,
  `runner/external/superzazu`, `runner/external/clowncommon`, `runner/video`,
  `recompiler/src`, `game`. [CONFIRMADO]
- **Windows:** Boogerman usa `find_package(SDL2 REQUIRED)` + `m` — é Linux. Para
  MSVC copiar o bloco do RKA: SDL2 do motor em
  `runner/external/SDL2/SDL2-2.28.5` via `find_package(SDL2 CONFIG NO_DEFAULT_PATH)`
  e cópia de `SDL2.dll` pós-build; não ligar `m`. [CONFIRMADO, RKA `9f64575`
  `CMakeLists.txt`; pasta SDL2 existe no motor local]
- Flags MSVC usadas: `/W3 /WX- /utf-8 /wd4102 /wd4996 /wd4013`, `/MAP`, `/bigobj`
  nos gerados. [CONFIRMADO, RKA `CMakeLists.txt`]
- Nome do executável = nome do alvo (`RKARecomp`, `BoogermanRecomp`). [CONFIRMADO]

Passos Windows:
```
git submodule update --init --recursive
cmake -S . -B build -G "Visual Studio 17 2022" -A x64
cmake --build build --config Release --target <Jogo>Recomp
```
[CONFIRMADO para o gerador/arch em `docs/GETTING_STARTED.md` @ `252535d`; o
`--target` em RKA `_build_native.bat`]

---

## 5. Esboço concreto

### 5a. Homebrew stamps9k/sega-md-homebrew

Dados de `rom/src/header.s` (lido do scratchpad, tratado como dado): SSP
`$00FFE000`; PC `entryPoint`; IRQ4 `hblankInterrupt` (em `lib/h_blank.s`); IRQ6
`vblankInterrupt`; todo o resto `errorHandler` (`illegal`, cai textualmente em
`vblankInterrupt`); sem SRAM; `.text` em `0x000000` (`rom.ld`). [CONFIRMADO no fonte]

Os **endereços** dos símbolos não estão disponíveis: não há ROM nem
`build/output.map` construídos. Primeiro: `make` (vasm + m68k-elf-ld) → ler
`output.map`. [CONFIRMADO, ausência; makefile]

`game/game.toml`:
```toml
[game]
output_prefix = "stamps9k"
jump_table_autodiscovery = true

[ram_layout]
initial_ssp = 0x00FFE000
vbla_stack  = 0x00FFE000
intr_stack  = 0x00FFE000

[functions]
extra = [ <entryPoint>, <vblankInterrupt>, <hblankInterrupt>, <errorHandler> ]  # do output.map
late_extra = [ ]   # handlers de cena chamados via `jsr (a1)` / `jsr (a2)` em scene_manager.s
blacklist = [ ]
```
- `errorHandler` (`illegal`) é adjacente a `vblankInterrupt` no fonte. Em
  execução `illegal` dispara o vetor 4 de novo e nunca cai no V-int; a
  adjacência só importa para o corte de funções do recompilador. Conferir no
  código gerado que a função de `errorHandler` não absorveu `vblankInterrupt`.
  [INFERIDO]
- Sem `vblank_yield_addr`: o laço de `main.s` é inline
  (`loop: tst.b vblank_flag / beq .done / ... / bra loop`), não é função; apontar
  `vblank_yield_addr` para `entryPoint` substituiria o boot inteiro. Fica no
  yield por orçamento de ciclos. [PROVÁVEL]
- `jsr (a1)` via tabela de cenas: semear cada handler em `extra`/`late_extra`
  (ou `[[jump_table]]` se a tabela for contígua de `dc.l`). Com
  `tier3_floor_default=1` uma falta cai no interpretador em vez de travar.
  [CONFIRMADO o mecanismo; a forma da tabela = INFERIDO, conferir no map]

`game/stamps9k_spec.c`: `call_entry_point` → `recomp_call_addr(<entryPoint>)`,
`call_vblank` → `<vblankInterrupt>`, `call_hblank` → `<hblankInterrupt>`,
`expected_rom_size` = tamanho real do arquivo `hello.bin` (o cabeçalho declara
fim em `$0FFFFF`, 1 MB, mas o binário linkado é bem menor — usar o tamanho do
arquivo, não o do header), `expected_rom_crc32` = CRC dele
(ou 0 enquanto o fonte muda), `tier3_floor_default = 1`.

CMake: modelo Boogerman + bloco SDL2 do RKA; ROM `game/hello.bin`.

### 5b. O que muda para Golden Axe (World Rev A, 512 KB, sem bancos)

- Mais próximo de Puyo: 512 KB plana, sem disasm, sem mapper →
  `expected_rom_size = 0x80000u`, nenhum `[[protected_range]]`/banco. [CONFIRMADO o
  modelo Puyo; ausência de banco = dado do pedido]
- CRC32: calcular do dump do próprio usuário; não verificado aqui.
  Não usar valor de internet sem conferir. [INFERIDO]
- SSP/entry/V-int/H-int: ler dos vetores `$000000-$0000FF` do dump; vão para
  `[ram_layout]` (pilhas = SSP) e `extra`. [CONFIRMADO o mapeamento; valores pendentes]
- VBlank: desmontar o alvo da espera. Se for função do padrão de 4 instruções,
  nada a fazer; se for função não-padrão, `vblank_yield_addr` (como Puyo); se for
  inline, orçamento de ciclos (como RKA). [CONFIRMADO os 3 caminhos]
- Sem disasm, a descoberta é heurística (vetores + BSR/JSR/RTS) e as sementes
  crescem por rodadas com `late_extra`, validando contra emulador confiável
  (boot, título, primeiro gameplay). [CONFIRMADO, `docs/GETTING_STARTED.md`]
- CMake: `RECOMP_ROOT = ${CMAKE_SOURCE_DIR}/external/segagenesisrecomp`; ROM em
  `game/<nome>.bin`, fora do git (`.gitignore`). [INFERIDO]
- Não copiar campos do Boogerman (`inline_arg_callees`, `interleave_irq_default`,
  `dev_menu_*`): não compilam contra `252535d`. [CONFIRMADO]
