# golden-axe-recomp

Recompilação estática de **Golden Axe (Mega Drive, 1989)** para PC nativo,
usando o motor [Genesis Recomp](https://github.com/mstan/segagenesisrecomp)
(submódulo em `external/segagenesisrecomp`, licença PolyForm Noncommercial).

**Sem ROM aqui.** O jogo é da Sega. Cada pessoa usa o próprio dump do
cartucho (alvo: World "Rev A" (cabeçalho `GM 00054018-01`, REV01), CRC32 `665D7DF9`, SHA-256
`e9f5340ecf8151253eb6fcda136c4d4d8940e373340ce2eeb2bf24f9f6c1004d`).
A desmontagem pública (lory1990, romhacking.net #719) também contém dados do
jogo e fica **fora** deste repositório.

## Estado

Fase 0 (pesquisa gratuita). Nada compilado ainda.

- `notes/genesis-recomp-research.md` — como o motor funciona
- `notes/som-z80.md` — análise do driver de som (veredito: tratável)
