# Golden Axe (Mega Drive): revisões da ROM

Pesquisa de 2026-11-05. Legenda: `[CONFIRMADO]` li na fonte, `[PROVÁVEL]` a fonte indica, `[INFERIDO]` raciocínio meu.

## Versões conhecidas (No-Intro)

| Nome No-Intro | Cabeçalho | CRC32 | Observação |
|---|---|---|---|
| Golden Axe (World) | REV00 | `E8182B90` | original, 1989 |
| **Golden Axe (World) (Rev A)** | **REV01** | **`665D7DF9`** | **nosso alvo**, 524288 bytes, SHA-1 `2CE17105CA916FBBE3AC9AE3A2086E66B07996DD` |
| Golden Axe (USA) (Rev B) (Sega Smash Pack) | REV02 | `31227079` | cartucho Sega Classics / Smash Pack |
| Golden Axe (World) (Beta) (1989-10-14) | — | `B01B26FF` | protótipo |
| Golden Axe (World) (Rev A) (Beta) (1989-11-22) | diz REV00 | `3E640C09` | protótipo do REV01 (Hidden Palace) |
| Mega Games 2 (Europe) | — | `30D59F2F` | coletânea |

CRC e nomes: `[CONFIRMADO]` ROMdb, dat No-Intro 20251108. SHA-1: `[CONFIRMADO]` romhacking.net #7112 e #6949.

## "Rev A" é REV01, não REV00

- O ga.asm do lory1990 traz `dc.b "GM 00054018-01"` e checksum `$C17B`. `[CONFIRMADO]`
- O SHA-256 do jvisser (`e9f5340e…004d`) é o mesmo que já registramos para `665D7DF9`. `[CONFIRMADO]`
- Antes o README e o `game.toml` diziam "REV00/Rev A". Os dois já foram corrigidos.

## O que muda entre as revisões

Fonte: TCRF via resumo de busca, `[PROVÁVEL]`. O TCRF bloqueia acesso automático e não consegui ler a página direto.

- **REV00 → REV01:** os textos foram reescritos. No teste de som, "PATH OF FIEND" virou "FIEND'S PATH" e "THEME OF THIEF" virou "THIEF'S THEME". Também foi corrigido o gráfico do machado do Death Bringer, que vinha quebrado no final em modo cooperativo. A fonte não cita mudança de jogabilidade.
- **REV01 → REV02:** o logo da Sega é desenhado de outro jeito, "®" vira "™" e entrou uma mensagem de bloqueio de região nos consoles japoneses e europeus.

Para o recomp: qualquer código que mudou de lugar desloca endereços, então **o `game.toml` de uma revisão não serve em outra**. `[INFERIDO]`

## Por que ficar no Rev A

- O ga.asm (romhacking #719) é do Rev A. O Gamemaster recomendou escolher a revisão com mais desmontagem. `[CONFIRMADO]`
- jvisser (32X), Golden Axe Plus, Arcade Colors (romhacking #7004) e o MSU-MD/MD+ (que tem patch separado para Rev 0 e Rev A) partem todos do Rev A. É o padrão da comunidade. `[CONFIRMADO]`/`[PROVÁVEL]`
- É a versão com o texto corrigido e o bug do machado resolvido, sem a trava de região do REV02.

## Fontes legais de dump (no lugar do cartucho + OSCR)

- **Steam, SEGA Mega Drive & Genesis Classics:** quem tem o jogo encontra a ROM na pasta "Uncompressed ROMs" (`.68k`/`.SGD`), segundo um guia da comunidade Steam. `[CONFIRMADO]` A Sega tirou a coletânea da loja no fim de 2024, mas quem comprou continua com acesso. `[PROVÁVEL]`
- Não achei fonte que diga qual revisão vem na Steam. Existe um mod "Golden Axe Plus 2.0" na Workshop, e o Plus é patch para o Rev A, o que sugere Rev A. `[INFERIDO]` **Para confirmar, é só calcular o CRC32 do arquivo e comparar com a tabela acima.**
- Se a sua conta Steam tiver a coletânea, o dump sai de graça e a compra de £220–270 deixa de ser necessária.

## Para a conversa com o Garland

- Se ele usa REV00 ou REV02, os endereços dele não batem com o ga.asm nem com o nosso `game.toml`. Seria preciso migrar um dos lados.
- Se ele usa Rev A, o trabalho dele encaixa direto.

## Fontes

- https://romdb.geeklogger.com/versions/mdr-crt/665d7df9
- https://www.romhacking.net/hacks/7112/ , https://www.romhacking.net/hacks/6949/ , https://www.romhacking.net/hacks/7004/
- https://github.com/jvisser/golden-axe-32x-edition (README, SHA-256)
- https://tcrf.net/Golden_Axe_(Genesis) (não lido direto, bloqueado)
- https://www.sega-16forums.com/forum/console-talk/genesis-does/21800-difference-between-genesis-games-with-multiple-revisions-rev-00-rev-01-etc
- https://hiddenpalace.org/Golden_Axe_(Nov_22,_1989_prototype)
- https://steamcommunity.com/sharedfiles/filedetails/?id=398334923
- https://steamcommunity.com/sharedfiles/filedetails/?id=2991317093
