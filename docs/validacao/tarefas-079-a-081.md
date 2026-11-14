# Entrega técnica — tarefas originais 079–081

Data: 13/11/2026. Origem: [lote de tarefas de 12/11](../tarefas/tarefas-12-11-26/README.md). Os números abaixo são IDs originais de planejamento, não chaves reais do Jira. Nenhum registro externo foi alterado. Nenhum aceite de produto é presumido.

## Entrega por tarefa

| ID original | Estado técnico local | Entrega e evidência |
|---|---|---|
| SIGAB-079 | Concluído tecnicamente | `/` passa a ser a página **Início**; a lista de itens foi para `/acervo`. Início mostra os totais de itens com registro por situação (disponível, em posse, indisponível/inapto), a reserva, a posse e o total de material sem registro por tipo, as pendências abertas (itens em posse, retiradas sem registro em aberto, prazos vencidos) e as 10 últimas retiradas e devoluções, com quem retirou ou devolveu e quem entregou ou recebeu. Os atalhos (Retirada, Devolução, Cadastrar equipamento, Estoque) aparecem conforme a permissão. Todos os números vêm de `GET /api/v1/overview/`, calculados no servidor dentro do escopo `item.view`. Quem não tem `item.view` não vê Início e cai em Minha posse. `/items/<id>` continua válido; `/?holder=<id>` redireciona para `/acervo?holder=<id>`. |
| SIGAB-080 | Concluído tecnicamente | Novo módulo **Equipamentos** (`/equipamentos`) com tipos separados em Com registro e Sem registro, com contagem de itens ou total em estoque de cada tipo. Novo tipo exige a classificação, sem valor padrão, e avisa que ela não muda. Pelo tipo com registro, o usuário abre a incorporação existente com o tipo já selecionado; pelo tipo sem registro, abre `/estoque?entrada=<tipo>`, que reaproveita a entrada com revisão, confirmação explícita e idempotência. A interface usa "com registro/sem registro"; a API mantém `individual`/`quantitative`. Cadastros ficou só com unidades e locais. A sessão expõe `can_receive_stock` e `can_return`. A listagem de tipos também atende quem só tem `inventory.adjust.approve`. |
| SIGAB-081 | Parcial: consulta pronta; disponível/inapto do material sem registro depende da SIGAB-008 | O Acervo tem as abas **Com registro** (lista, busca, filtro e ficha atuais) e **Sem registro**: posições por tipo, unidade e local com reserva, posse e total, busca por tipo, filtro por unidade, histórico do tipo (RF-54) e link para o Estoque conforme permissão. Novas APIs: `GET /api/v1/stock/summary/` e `GET /api/v1/stock/entries/?type=`. Os totais conferem com Início (teste automatizado). |

## Decisões e suposições

- **Escopo de leitura.** Início, Acervo sem registro, histórico e contagens por tipo usam o escopo `item.view`, o mesmo da lista de itens. As operações do Estoque continuam com o escopo já existente (`item.view`, `movement.return` ou `inventory.adjust.approve`).
- **Baixa.** Os totais contam só itens com situação administrativa ativa. O tratamento de baixa continua pendente (SIGAB-059 na revisão de 10/11).
- **Material sem registro.** "Em reserva" é o saldo do livro e "em posse" é a quantidade aberta das retiradas. A divisão entre disponível e inapto não é inferida: depende da SIGAB-008.
- **Devolução.** O atalho de Devolução abre o Acervo filtrado por itens em posse. A devolução por pessoa, em lote, é escopo da SIGAB-082.
- **Contagens por tipo.** Quem tem permissão de catálogo, mas não tem `item.view`, recebe contagens nulas em vez dos totais da organização.

## Verificações

- Suíte SQLite: **255 passaram, 13 ignorados**. Suíte PostgreSQL 17: **266 passaram, 2 ignorados**.
- Novos testes de backend (`test_requirements_079_081.py`): agregados, pendências, últimas movimentações com operador e recebedor, item inativo fora do total, escopo por unidade, recusa sem `item.view`, contagens por tipo e permissão, classificação errada e tipo inativo recusados na incorporação e na entrada, e reconciliação entre o Acervo sem registro e o Início.
- Isolamento: as rotas `overview`, `stock-summary` e `stock-history` foram registradas na guarda de rotas, e há um teste negativo de acesso cruzado sem vazamento de item, pessoa, unidade, saldo, retirada ou lançamento.
- Playwright com API simulada: **20 jornadas passaram**, 6 delas novas (Início por perfil, redirecionamento para Minha posse, endereço antigo `/?holder=`, Equipamentos com e sem permissão, entrada pelo tipo, abas e histórico do Acervo). As jornadas antigas foram ajustadas para `/acervo` e `/equipamentos`.
- Ruff, `manage.py check`, ausência de migrações faltantes, TypeScript e build aprovados. Nenhuma migração nova.

## Riscos

- O Início não tem paginação. Com muitos tipos, os blocos de totais crescem sem limite.
- A jornada real (React + Django + PostgreSQL) não foi estendida para Início e Equipamentos; a cobertura de navegador usa API simulada.
