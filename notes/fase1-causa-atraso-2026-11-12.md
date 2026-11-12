# Fase 1: por que o recomp atrasa em degraus com `cycle_drift_correction = true` (2026-11-12)

Marcas: [CONFIRMADO] medido ou lido no código; [PROVÁVEL] bem indicado, não provado; [INFERIDO] dedução.
Sintoma de partida (`notes/fase1-som-2026-11-12.md`): o som do recomp atrasa em degraus nas trocas de tela, +43 quadros em 2 minutos, e sem a correção adianta.

## Resumo

1. **Os degraus têm causa confirmada**: um defeito de uma linha na correção (registrador errado nos deslocamentos). Consertado, os degraus somem e o atraso de +43 quadros deixa de existir.
2. **Mas o conserto não deixa o tempo certo**: o recomp passa a *adiantar* 16 quadros em 2 minutos. O defeito escondia, por excesso de ciclos, um déficit que continua sem explicação confirmada. A pergunta "por que adianta sem a correção" **segue aberta**.

## Causa dos degraus [CONFIRMADO]

`emit_cycle_drift_correction` (`m68k-recomp-core/profiles/genesis/code_generator.c:2121`) lê o registrador errado nos deslocamentos com contagem em registrador (`lsl.w d1,d0`):

```c
int dreg = w0 & 7;          // bits 2-0 = registrador DESLOCADO (o dado); a contagem está nos bits 11-9
```

A correção soma `2*((Dn & 63) - 4)`; com o `Dn` do dado, o termo vale em média ~31 se os bits baixos forem uniformes, ou seja, ~+55 ciclos de excesso por deslocamento executado [INFERIDO a conta; o efeito foi medido, abaixo].

**Por que só as cargas sofrem [CONFIRMADO]:** a ROM inteira tem exatamente 7 deslocamentos com contagem em registrador (`ga.asm`), e os 7 estão em rotinas de `$30BE` a `$33AE` (`loc_30BE`, `loc_30E6`, `loc_32C2`, `loc_337E`, `loc_33AE`), o bloco de descompressão de gráficos logo depois de `loc_2FBC`, que roda com o VBlank mascarado (`ori #$700,sr`). Esses 7 são os mesmos 7 pontos que mudam no código gerado ($30C0, $30C6, $30EC, $32CA, $338E, $3392, $33B0).

## Prova

Previsão que podia falhar: trocar por `(w0 >> 9) & 7` tira os degraus e a troca de modo chega mais cedo. Confirmou-se.

| Medida | Correção original | Sem correção | Correção consertada |
|---|---|---|---|
| Quadro das trocas de modo (até o fim de 7.800 quadros) | 1267, 3190, 3559, 5335, 5704, 7007, 7376 | 1261 (1ª troca; só 1.800 quadros medidos) | 1261, 3163, 3528, 5289, 5654, 6945, 7310 |
| Serviços de VBlank até o modo `$10` | 934 | 934 | 934 |
| Som, 4 a 120 s: variação do atraso | **+43,8 quadros** | (3.000 quadros) −5,4 em 40 s | **−16,2 quadros** |
| Som: maior degrau entre janelas | **13,8 quadros** | 1,2 | **2,4** |
| `audio_lag.py` | VERMELHO | VERDE | VERDE |

Rodadas são determinísticas: duas execuções do mesmo build dão WAV idêntico (md5) [CONFIRMADO]. A referência é o áudio do BlastEm 1.0.0, não quadros de evento.

## O que continua em aberto (ranqueado)

O recomp consertado adianta ~0,14 quadro por segundo (−7 quadros já aos 4 s, −23 aos 120 s), ou seja, ~0,24% mais rápido que o BlastEm. Em ciclos isso é da ordem de ~300 por quadro [INFERIDO a conversão], mesma ordem dos ~490 ciclos/quadro que o comentário do motor mede para o custo estático sem correção.

O adiantamento aparece nas janelas com carga (−6,6 quadros somados) e nas sem carga (−9,6): é **mais contínuo que concentrado nas cargas** [CONFIRMADO a medida, janelas de 4 s].

1. **Custo estático ainda subestimado em outras instruções** [PROVÁVEL]. O próprio comentário do motor diz que MULU/MULS/DIVU/DIVS não são corrigidos. Previsão: contar essas instruções por quadro e somar o custo real (MULU 38+2n, DIVU até ~140) deve cobrir ~300 ciclos/quadro. Teste ainda não feito.
2. **Esperas de barramento não modeladas** (FIFO da porta de dados do VDP, DMA, Z80 segurando o barramento) [INFERIDO]. Previsão: o adiantamento deveria crescer só dentro das cargas. A medida acima favorece isso menos que a hipótese 1.
3. **O relógio do áudio não é o do 68000** [PROVÁVEL]. Entre a correção original e a consertada o som difere ~6 quadros aos 4 s, mas o evento do jogo (modo `$04`) difere 1. O áudio usa `g_audio_cycle_counter`, que também recebe a correção. A referência do BlastEm é áudio, então parte do "adiantamento" pode ser do caminho Z80/YM e não do 68000. Teste: obter quadros de evento do BlastEm (depurador `-d`) e comparar direto.
4. **Offset inicial de ~7 quadros aos 4 s**, presente com e sem correção. Origem não localizada.

## Descartado

- **`--pacing fiber|accurate`**: sem efeito. Logs de escrita de 1.800 quadros idênticos byte a byte nos dois modos, nos dois builds [CONFIRMADO]. (`glue.h` diz que `accurate` é o padrão; `glue.c:155` define `FIBER_FULL`.)
- **Bcc/DBcc/Scc da correção**: valores conferidos contra a tabela de tempos do 68000 (8/12, 12/14, 4/6): corretos [CONFIRMADO, lido].

## Limite do laço (`tools/probe/audio_lag.py`)

Ele só fica vermelho em **degraus** (≥ 3 quadros entre janelas). Dá VERDE para o build sem correção e para o consertado, mesmo adiantados 7 a 23 quadros. **VERDE não quer dizer "o tempo bate com o console"**; quer dizer "sem saltos". A segunda pergunta (adiantamento) não tem laço que a capture ainda. Cada rodada leva ~1 min: o jogo roda a ~60 quadros/s mesmo com `--turbo`.

## Entrega

- `patches/m68k-recomp-core-drift-shift-count-register.patch`: uma linha, aplica limpo no motor (m68k-recomp-core `0890f0d`, segagenesisrecomp `f92e278`).
- `patches/test_m68k-recomp-core-drift-shift-count-register.py`: ROM sintética com `lsl.w d1,d0` e `lsr.l d3,d5`. Falha no motor atual (lê d0 e d5) e passa com o patch (lê d1 e d3) [CONFIRMADO, rodado nos dois]. O verde foi rodado contra um recompilador compilado de uma edição equivalente (comentário diferente), não do arquivo de patch em si.
- O motor do projeto **não foi alterado**: foi editado no lugar duas vezes (build de teste e geração do patch) e restaurado com `git checkout`, conferido limpo depois. O build de teste está em `build-fixshift/` (ignorado pelo git).
- A fase 1 não troca o `game.toml`; a correção continua `true`.

## Como repetir

```
git -C segagenesisrecomp/external/m68k-recomp-core apply ../../../patches/m68k-recomp-core-drift-shift-count-register.patch
cmake -S . -B build-fixshift -G "Visual Studio 17 2022" -A x64
cmake --build build-fixshift --config Release --target GoldenAxeRecomp --parallel
git -C segagenesisrecomp/external/m68k-recomp-core checkout -- profiles/genesis/code_generator.c

cd build-fixshift\Release
GoldenAxeRecomp.exe goldenaxe.bin --no-launcher --turbo --max-frames 7800 --wav C:\tmp\fix.wav
python -I tools\probe\audio_lag.py C:\tmp\fix.wav C:\tmp\ref.raw 4 128 4
```
