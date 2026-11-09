# game.toml + spec do Garland: integração e análise do bug de controle

Recebido por DM em 2026-11-06 (goldenaxe.zip, SHA-256 `4e0ed0db5f3dbb03517e93786964acd4cf5a9622f8c01f544ee28445c35685a7`). Legenda: `[CONFIRMADO]` li no código/ROM-asm, `[INFERIDO]` raciocínio meu.

## Estado da integração

- `game/game.toml` e `game/golden_axe_spec.c` são os arquivos dele, byte a byte (o spec dele se chamava `goldenaxe_spec.c`). `[CONFIRMADO]` SHA-256 idêntico.
- TOML lê sem erro (tomllib). O spec compila limpo (`cl /Zs`, mesmos includes do CMakeLists). `[CONFIRMADO]`
- **Não testado:** build completo e execução. Falta o dump da ROM (`game/golden_axe.bin`). O arquivo `Downloads\Golden Axe (World) (Rev A).md` tem 0 bytes.
- O `output_prefix = "goldenaxe"` dele bate com o prefixo do nosso CMakeLists. O rascunho antigo (`golden_axe`) não batia.
- Sem licença declarada. Uso interno; não publicar sem o OK dele.

## Risco que o build vai expor: o motor não tem a correção dele

O toml registra `loc_2C00` como função nativa. Esse trecho termina num loop de espera de DMA de 3 instruções (`move.w (a5),d4 / btst #1,d4 / bne.s -`). Ele diz ter corrigido o codegen para ceder a vez nesse padrão. `[CONFIRMADO]` no nosso motor (252535d / m68k-recomp-core v0.1.0) só existe o padrão de 2 instruções (`tst.X mem; bne self`, `profiles/genesis/code_generator.c:5060-5090`). O `GENESIS_WRITE_TRACE_ADDR` que ele cita também não existe aqui.

Previsão `[INFERIDO]`: com o motor atual, `loc_2C00` vira código nativo que gira no loop do DMA sem ceder a vez. Isso trava a thread do jogo. Se acontecer, o conserto é estender o padrão no `code_generator.c` do submódulo (que é PolyForm Noncommercial, do mstan; vale mandar de volta como PR).

## Causa raiz do bug de controle

**O spec sozinho não prova a causa raiz.** O próprio comentário dele admite: "NOT yet root-caused why bit6 gets set". O que dá para afirmar:

### O que os bits realmente são (lido no `ga.asm`, `loc_6DCC`) `[CONFIRMADO]`

`loc_6DCC` não é código de cutscene. É o tratamento de **golpe recebido / agarrão** do jogador:

| Bit | Significado |
|---|---|
| `$3(a0)` bit 1 | pedido de "você foi atingido", ligado pelo atacante (`bset #1,$3(a6)`) e consumido por `bclr` em `loc_6DCC` |
| `$3(a0)` bit 6 | "preso a um atacante", cujo ponteiro está em `$38(a0)`; ligado em `loc_6ED8` |
| `$2(a0)` bit 2 | trava de "esse agarrão já foi processado"; só `loc_6DCC` liga |
| `$FFC104` bit 3 | congela objetos fora de cutscene; liga em `loc_7330` (abre diálogo), desliga em `loc_8DFC` |

Os estados que ele chama de "scripted" (entradas 18, 19 etc.) incluem os estados de reação a golpe (`$480D`..`$4810` = entrada 18, `$4C1A` = entrada 19). A conta `((state42>>8)&0x7F)/4` do spec está certa: `loc_6F3E` usa o byte `&$7F` como deslocamento direto em `jmp loc_6F68(pc,d0.w)`.

### Hipótese `[INFERIDO]`

Os bits só "ficam presos" se o código que os desliga não rodou. O bit 6 de `$3(a0)` e o bit 2 de `$2(a0)` são desligados em pares nos mesmos três trechos (`ga.asm` 8847-8848, 9062-9063, 9445-9446), que são saídas de estados de recuperação. O bit 3 de `$FFC104` só é desligado em `loc_8DFC`. Ou seja, o jogo original é correto, e o que muda é a **recompilação desviar o fluxo** antes de chegar nessas saídas. O toml dele documenta justamente isso:

- o `$FFFFF400`/`$FFFFF410` digitado sem um `F` no override (toda chamada caía no interpretador "floor");
- `loc_2C00` travando no interpretador, que só reconhece loops de 2 PCs (data da causa: 2026-08-27);
- `[FLOOR][UNSAFE] capsule exit_pc != native loose-A7 return`, com `exit_pc` lixo (`$3FFF7E`, `$DF01EE`), isto é, endereço de retorno corrompido.

Então o `ga_call_vblank` que zera as flags a cada frame provavelmente **trata sintoma** de problemas que ele mesmo corrigiu depois (o toml é mais novo que a lógica de flags). Isso está sem prova.

### Como provar (precisa da ROM)

1. Compilar com o bloco de limpeza de flags desligado (macro) e ver se o controle trava mesmo assim.
2. Se travar, registrar um contador toda vez que a limpeza dispara e qual flag era. Se nunca dispara, o código é morto.
3. Descobrir quem escreve nos bits: o `ring` de reverse-debug do nosso motor (`rdb_on_insn`) e o servidor de debug (`read_ram`) servem no lugar do `GENESIS_WRITE_TRACE_ADDR`. Vigiar `$FFD002`, `$FFD003` e `$FFC104`.
4. Checar se `s_bra_override_depth` (limite 8 no override de `bra.w`) vaza: ele sobe antes de `recomp_call_addr` e só desce se a chamada retorna. Se o contador ficar alto, o override recusa e a chamada cai no floor.

Não alterei o arquivo dele. A instrumentação dos passos 1-2 deve entrar numa cópia, e o arquivo volta para ele só depois de testado.
