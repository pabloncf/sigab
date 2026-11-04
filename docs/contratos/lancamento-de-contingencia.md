# Contrato do lançamento de contingência

- Tarefa: SIGAB-046
- Revisão: 2026-11-03, conferida com `checkout_item`/`return_item` em `backend/sigab/services.py`
- Requisitos: RNF-01, RNF-02, RF-20 a RF-23, RF-60
- Base: [ADR 0004](../adr/0004-conectividade-e-contingencia.md) (procedimento de contingência), [contrato da saída](saida-individual.md), [contrato da devolução](devolucao-individual.md), [ADR 0006](../adr/0006-eventos-auditoria-e-estornos.md)

## 1. Comando

Não há rota nova. Saída e devolução aceitam um objeto opcional `contingency` com a linha do livro em papel:

```http
POST /api/v1/items/{item_id}/checkout/
{
  "recipient_id": "uuid",
  "idempotency_key": "uuid gerado ao abrir a ação",
  "confirmed": true,
  "contingency": {
    "occurred_at": "2026-11-03T08:40:00-03:00",
    "paper_reference": "F03/L07"
  }
}
```

`POST /api/v1/items/{item_id}/return/` aceita o mesmo objeto junto com `condition` e `reason`. Na tela do item, a opção "Lançar registro do livro de contingência" abre os dois campos.

## 2. Dados

| Dado | Origem | Regra |
|---|---|---|
| instante do fato | `contingency.occurred_at` | ISO 8601 **com fuso**; não pode estar no futuro; gravado em `Movement.declared_occurred_at` e em `MovementEvent.occurred_at` |
| instante do lançamento | relógio do servidor | `Movement.confirmed_at` e `AuditEvent.occurred_at`; nunca apresentado como instante da entrega |
| referência do papel | `contingency.paper_reference` | folha/linha, até 64 caracteres, obrigatória |
| origem | servidor | `Movement.origin = contingency` |
| operador do lançamento | conta autenticada | `Movement.operator` e ator do evento e da auditoria |
| demais dados | iguais aos da saída e da devolução | destinatário, condição e motivo seguem os contratos originais |

A restrição de banco `contingency_has_fact_instant_and_reference` exige instante do fato ≤ instante do lançamento e referência preenchida, e só aceita contingência em saída e devolução.

## 3. Regras

1. **Mesmas regras da operação ao vivo.** Permissão (`movement.checkout`/`movement.return` na unidade do item), tenant, confirmação explícita, bloqueio da linha do item e chave de idempotência são os mesmos. Item em posse não sai de novo.
2. **Divergência não é forçada.** É recusada como divergência (409, mensagem iniciada por "Divergência", auditoria de recusa com `result = divergence`):
   - estado atual incompatível (saída de item indisponível, devolução sem saída aberta);
   - instante do fato igual ou anterior ao último fato em vigor do item. Fatos estornados e os próprios estornos não contam, para que uma linha lançada errado possa ser estornada e lançada de novo;
   - folha/linha já lançada, e não estornada, para um item da mesma reserva (local de guarda).
3. **Ordem cronológica.** Lança-se o livro em ordem, como manda o ADR 0004. O histórico do item fica ordenado pelo instante do fato.
4. **Idempotência.** A mesma chave com o mesmo conteúdo, incluindo instante e referência, é repetição (200). A mesma chave com outra referência, outro instante ou sem contingência é conflito (409).

## 4. Efeitos

| Registro | Conteúdo |
|---|---|
| `Movement` | igual ao da operação ao vivo, com `origin`, `declared_occurred_at` e `paper_reference` |
| `MovementEvent` | mesmo tipo e schema v1 (`item.checked_out.v1`, `item.returned.v1`); `occurred_at` = instante do fato. Origem e referência ficam nas colunas da movimentação (ADR 0006: dado de consulta não vai para `metadata`) |
| `AuditEvent` | `item.checkout.contingency` ou `item.return.contingency`, com `occurred_at` declarado e `paper_reference` em `changes` |
| API de leitura | eventos de `/items/<id>/events/` e `/activity/` trazem `movement.origin`, `movement.paper_reference` e `movement.recorded_at` |

## 5. Fora deste contrato

- Declaração e encerramento da contingência por reserva, e bloqueio do sistema durante ela: continuam procedimento em papel (ADR 0004). A corrida entre lançamento ao vivo e lançamento de contingência no mesmo item é resolvida pelo banco: só uma saída é aceita.
- Conferência do lançamento por segunda pessoa: procedimento, sem dupla aprovação no sistema.
- Operação offline e sincronização: proibidas pelo ADR 0004.
- Retirada por terceiro, vários itens por linha e estoque quantitativo.

## 6. Critérios de aceite e evidências

Testes em `backend/sigab/tests/test_contingency.py`, salvo indicação.

| Critério (SIGAB-046) | Teste |
|---|---|
| origem, instante do fato separado do lançamento, folha/linha, operador | `test_contingency_checkout_keeps_fact_instant_apart_from_registration` |
| devolução de contingência fecha saída do sistema; histórico mostra os dois instantes | `test_contingency_return_closes_system_checkout_and_history_shows_both_instants` |
| validação do instante e da referência | `test_future_fact_instant_is_rejected`, `test_contingency_requires_aware_instant_and_reference` |
| conflito vira divergência, sem forçar | `test_state_conflict_is_a_divergence_and_is_not_forced`, `test_fact_before_the_last_record_of_the_item_is_a_divergence`, `test_sheet_line_is_reconciled_only_once_per_reserve` |
| idempotência | `test_replay_is_idempotent_and_key_reuse_with_other_paper_data_conflicts` |
| correção por estorno | `test_wrong_reconciliation_can_be_reversed_and_entered_again` |
| permissão e acesso cruzado | `test_contingency_requires_the_same_permission_as_live_checkout`, `test_contingency_cannot_reach_an_item_of_another_organization` |
| restrição de banco | `test_database_rejects_contingency_without_fact_instant_or_reference` |
| concorrência com lançamento ao vivo | `test_live_checkout_racing_a_contingency_entry_accepts_exactly_one` em `test_concurrency.py` (PostgreSQL) |
