# Busca inicial

- Tarefa: SIGAB-038
- Revisão: 2026-11-02, conferida com `search` e `_filter_items` em `backend/sigab/api/views.py`
- Requisito: RF-50 do [DOC-0011 v0.1](fontes/DOC-0011-analise-de-requisitos-v0.1.md)

## Contrato

`GET /api/v1/search/?q=<termo>&limit=&offset=` com filtros opcionais `availability`, `condition`, `unit` (UUID) e `type` (UUID).

| Alvo | Campos pesquisados | Quem vê | O que volta |
|---|---|---|---|
| itens | série, patrimônio, registro oficial, nome do tipo, código e nome da unidade, nome e nome funcional do responsável | `item.view`, só nas unidades do escopo | resumo do item, paginado (`meta.items_count`) |
| pessoas | nome, nome funcional, matrícula | `person.view_minimal` em algum escopo | `id`, nome de exibição, situação e matrículas ativas, até 20. **Nunca** CPF nem telefone |

- O termo tem de 2 a 100 caracteres e é buscado por “contém”, sem diferenciar maiúsculas.
- Organização e escopo vêm da conta; resultado de outra organização ou unidade nunca aparece (`test_isolation.py`, `test_search_hides_other_units_and_people_without_permission`).
- `GET /api/v1/items/` aceita os mesmos `q` e filtros, além de `holder` (posse atual, RF-51).
- Filtro por **período** fica no feed de atividade (`/api/v1/activity/?from=&to=`), onde há instante de fato; o item não tem data de referência única que torne “período” inequívoco.
- Nenhum dado é enviado a serviço externo de indexação; a busca roda no próprio PostgreSQL.

## Medição

Volume de teste (`test_search_response_time_with_test_volume`, ativado com `SIGAB_PERF=1`):

| Elemento | Quantidade |
|---|---|
| organização | 1 |
| unidades | 10 |
| itens individuais | 5.000 |
| pessoas, com um vínculo cada | 2.000 |
| consultas | 30 (6 termos × 5): prefixo de série, de patrimônio, nome, matrícula, código de unidade, tipo |

Resultado em 2026-11-02, cliente de teste do Django contra PostgreSQL 17 em contêiner local (Apple M5, 16 GB):

| Métrica | Valor |
|---|---|
| mediana | 19,0 ms |
| p95 | 23,4 ms |

O teste falha se o p95 passar de 1 s. Para repetir:

```bash
docker compose up -d db
cd backend
DATABASE_URL=postgresql://sigab:local-only@127.0.0.1:5432/sigab SIGAB_PERF=1 \
  uv run pytest -q -s sigab/tests/test_activity_and_search.py -k response_time
```

Os números medem a aplicação com a rede local; não incluem proxy, TLS nem latência do usuário. Com volume muito maior que o de uma Guarda Municipal, “contém” deixa de usar índice comum; a alternativa é índice trigram (`pg_trgm`) no PostgreSQL, a decidir quando a medição indicar.
