# Som do Golden Axe: análise do driver Z80 (Fase 0, 2026-10-25)

Fontes: `ga.asm` (lory1990), blocos extraídos dele (fora do repo),
`jvisser/golden-axe-32x-edition` `src/md/system/z80.s`, `goldenaxe.h`.
Nada foi executado; é leitura de código e varredura de bytes.

## Veredito: TRATÁVEL [PROVÁVEL]

O padrão é o clássico da Sega: o 68000 carrega o driver uma vez e conversa por
caixa de correio, e o Z80 faz todo o FM, PSG e DAC. Nenhum dos sinais de
driver "exótico" apareceu. Dois pontos de atenção estão listados no fim.

## Lado 68000 [CONFIRMADO no código]

| Rotina | Endereço | O que faz |
|---|---|---|
| audio_init | `$34BC` | BUSREQ, pulso de reset (`$3554`), zera 8 KB de RAM Z80 (`$34A8`), copia **$DF8 = 3.576 bytes** de ROM `$1D2F0` → `$A00000`, inicializa caixa `$A01C00..0B`, escreve `$A01FFE` (0 ou `$CD`, conforme bit 6 de `$FFFE00`), solta reset/bus |
| play_music | `$35E8` | interrupções mascaradas; se d7 ≠ última música (`$FFC126`), BUSREQ → `$A01C05`=d7 → solta. Mão única, sem esperar resposta |
| play_sound_effect | `$361C` | BUSREQ; se `$A01C04` ≠ `$E3` escreve d7 em `$A01C07` |
| (2º canal SFX) | `$3652` | igual, em `$A01C06` |
| comando 1C0B | `$3486` | BUSREQ → `$A01C0B`=d0 (provável fade/parada) [INFERIDO] |
| recarga de amostra | `$358C` / `$3594` | copia **$9D0 = 2.512 bytes** de `$1EAB8` ou `$1E0E8` → `$A00F00` (cache em `$FFC128`), escreve d7 em `$A00F06`, dispara SFX `$E3` |

- O 68000 **nunca** escreve no YM2612 (`$A04000`) nem no banco (`$A06000`). Os únicos acessos são `$A00000`, `$A00F00/06`, `$A01C00-0B`, `$A01FFE`, I/O de controle `$A10001-0D`, `$A11100` (22×) e `$A11200` (5×).
- O handshake bloqueante é só a espera padrão do BUSREQ (`btst #0,$A11100`).
- O reset do Z80 ocorre só no boot.

## Lado Z80 (driver de 3.576 bytes) [PROVÁVEL, decodificado à mão]

- `$0000`: `DI; IM 1; SP=$1FFD; ($1FFF)=3; EI` e espera 3 interrupções. Depois inicializa e chama a troca de banco.
- `$0038` (IRQ do VBlank): decrementa `$1FFF`; se `$1FFE`=0, roda o tick do driver (`$0086`, `$0094`).
- `$0068` (laço principal): se `$1FFE`≠0, programa o **Timer B do YM2612** (reg `$26`=valor de `$1FFE`, reg `$27`=`$2F`) e faz polling do bit 1 de `$4000`. Isso é o modo de tempo alternativo, provavelmente PAL [INFERIDO].
- `$05E1`: troca de banco padrão, 9 escritas seriais em `$6000` a partir de `$1C00/$1C01`. O 68000 só define isso no boot (`1C00`=1, `1C01`=`$80` → banco `$18000`), então é **banco fixo**.
- Escrita no YM (`$03CC`): espera o bit busy de `$4000` e escreve endereço/dado. O padrão é normal.
- DAC: reg `$2A` em `$0DDC`, com laço de atraso `DJNZ $` (`$0DD0`). A **altura das amostras depende da contagem de ciclos do Z80**.
- PSG: `$7F11` em `$0344`, `$0CA4`, `$0CB2`.
- Leitura da janela de ROM `$8000+`: 12 ponteiros, para dados de música/amostras no banco fixo.
- Código auto-modificável: **nenhum encontrado**. O único candidato (`$0A6D`) cai numa tabela de dados.
- Os blocos em `$1EAB8`/`$1E0E8` têm cabeçalho `c0 09 00 08 08 00 xx 80` seguido de dados de alta entropia: são **amostras (provável 4-bit DPCM, vozes/gritos)**, não código [INFERIDO]. O byte `$0F06` recebido do 68000 é o 7º byte desse cabeçalho.

## O que isso significa para o motor

- O Z80 é interpretado (SuperZazu) por padrão. O driver não precisa ser traduzido.
- Opcional: `docs/Z80_STATIC_RECOMP.md` do motor gera C do driver a partir de dumps da RAM Z80. A recarga em `$0F00` é dado, não código, então não exige `--flat-step-variant`.

## Pontos de atenção (testar na Fase 2)

1. **Gritos/vozes (DAC)**: dependem do tempo do Z80 e das pausas de BUSREQ. Comparar o WAV com um emulador preciso (o motor já tem ferramenta de captura pareada, `GENESIS_AUDIO_FIDELITY.md`).
2. **Modo PAL** (Timer B do YM): só importa se rodar como PAL. O alvo é NTSC/60 Hz.
3. Status `$E3` em `$A01C04` = driver ocupado carregando amostra [INFERIDO]. Se o tempo estiver errado, o SFX pode ser engolido.

## Lição do motor relevante para a Fase 2

`docs/DISASSEMBLIES.md` e `rka/DEVELOPMENT.md`: rótulos **não** viram raízes
de função automaticamente, e promover rótulo de dado a função corrompe o
codegen (caso RKA). Os ~4.900 `loc_` do lory1990 incluem dados (ex.: `loc_1D2F0`
é o driver Z80), então é preciso filtrar só rótulos que caem em instrução 68000
válida e são alvo de JSR/BSR. O motor também exige que a desmontagem remonte
**byte a byte igual** à ROM do usuário antes de importar rótulos.
