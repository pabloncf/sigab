# Contrato da saída de item individual

- Tarefa: SIGAB-029 (contrato) e SIGAB-030 (implementação)
- Revisão: 2026-11-02, conferida com `checkout_item` em `backend/sigab/services.py` e `POST /api/v1/items/{id}/checkout/`
- Requisitos: RF-20, RF-21, RF-51, RF-60 e RN-10 do [DOC-0011 v0.1](../fontes/DOC-0011-analise-de-requisitos-v0.1.md)
- Base: transição T02 da [decisão 0004](../decisoes/0004-ciclo-de-vida-do-item-individual.md), [ADR 0003](../adr/0003-eventos-idempotencia.md), [ADR 0006](../adr/0006-eventos-auditoria-e-estornos.md), [convenções da API](../api.md)

## 1. Comando

```http
POST /api/v1/items/{item_id}/checkout/
Content-Type: application/json
X-CSRFToken: <cookie csrftoken>

{
  "recipient_id": "uuid da pessoa que usará o item",
  "idempotency_key": "uuid gerado ao abrir a ação",
  "confirmed": true
}
```

Um comando registra a saída de **um** item individual. RF-20 prevê vários itens e itens de estoque numa mesma saída; agrupar itens e estoque quantitativo ficam para tarefas próprias.

## 2. Dados e origem de cada um

| Dado | Origem | Regra |
|---|---|---|
| organização | conta autenticada (`Account.organization`) | nunca enviada pelo cliente |
| operador | conta autenticada | precisa de `movement.checkout` na unidade do item; gravado em `Movement.operator` e como ator do evento e da auditoria |
| item | `item_id` na URL | da organização do operador; outro tenant ou fora do escopo → 404 |
| unidade | lotação do item (`Item.unit`) | define o escopo de autorização; não é enviada |
| usuário (destinatário) | `recipient_id` | pessoa ativa da organização com vínculo ativo; a posse fica em nome dela (RN-10) |
| instante | relógio do servidor no momento da confirmação, em UTC | `Movement.confirmed_at` = `MovementEvent.occurred_at` |
| chave de idempotência | `idempotency_key` | UUID único por organização |
| confirmação | `confirmed` | precisa ser exatamente `true` (RF-21) |

Retirada em nome de terceiro (RF-25: quem retirou ≠ quem usa) está fora: o destinatário é sempre quem recebe e usa o item.

## 3. Pré-condições

Verificadas no servidor, nesta ordem, dentro da transação:

1. `confirmed` é `true`.
2. Se a chave já existe na organização, aplica-se a regra de repetição (seção 5).
3. O item existe na organização e é bloqueado (`SELECT … FOR UPDATE`).
4. O destinatário existe na organização e está ativo.
5. O operador tem `movement.checkout` na unidade do item.
6. O destinatário tem vínculo ativo.
7. O item está disponível: situação `active`, condição `fit` e disponibilidade `available` (regra 1 da decisão 0004). Item em posse não sai de novo.

Restrição pessoal (RN-06) e bloqueio da organização (RN-07) entram como pré-condições quando suas políticas forem aprovadas.

## 4. Efeitos

Numa única transação, todos ou nenhum:

| Registro | Conteúdo |
|---|---|
| `Movement` | tipo `checkout`, item, operador, destinatário, chave, `confirmed_at` |
| projeção do item | `availability = in_custody`, `current_holder = destinatário`, por atualização condicional |
| `MovementEvent` | `item.checked_out`, schema `item.checked_out.v1`, `metadata.recipient_id`, ator e instante |
| `AuditEvent` | `item.checkout`, organização, ator, objeto (movimentação), instante, `correlation_id`, `changes` com `item_id` e `recipient_id` |

Falha em qualquer passo desfaz todos os anteriores. A posse atual de uma pessoa (RF-51) é consultada por `GET /api/v1/items/?holder={person_id}`.

## 5. Repetição

| Situação | Resposta |
|---|---|
| mesma chave, mesmo item e mesmo destinatário | `200`, `"created": false`, a movimentação original; nada é gravado |
| mesma chave com outro item, outro destinatário ou outra operação | `409`, nada é gravado |
| chave nova para item já em posse | `409` “O item não está disponível para saída.” |

O cliente gera a chave ao abrir a ação e a reusa em qualquer reenvio; a repetição é segura mesmo após falha de rede sem resposta.

## 6. Concorrência

Duas confirmações simultâneas para o mesmo item, com chaves diferentes:

- o bloqueio de linha serializa as transações no PostgreSQL;
- a atualização condicional (`availability = available`) aceita exatamente uma;
- a outra recebe `409` e não grava movimentação, evento nem auditoria.

Duas confirmações simultâneas com a **mesma** chave: uma grava; a outra encontra a chave ou colide na restrição única `uniq_movement_idempotency_org` e responde `409`, que o cliente trata recarregando o item.

## 7. Respostas

| Status | Quando |
|---|---|
| 201 | saída registrada |
| 200 | repetição idempotente |
| 400 | corpo inválido, sem confirmação, destinatário inválido, inativo ou sem vínculo |
| 401 | sem sessão |
| 403 | CSRF inválido |
| 404 | item inexistente, de outra organização ou fora do escopo do operador |
| 409 | item indisponível, corrida perdida ou chave reutilizada com outro conteúdo |

## 8. Critérios de aceite e evidências

| Critério (SIGAB-030) | Teste |
|---|---|
| somente item disponível sai | `test_only_available_item_can_leave`, `test_checkout_rejects_inactive_item`, `test_checkout_is_idempotent_and_prevents_second_checkout` |
| confirmação explícita | `test_checkout_requires_confirmation`, `test_api_rejects_missing_explicit_confirmation` |
| evento com ator e instante | `test_checkout_event_has_actor_and_instant` |
| histórico e posse atualizados atomicamente | `test_checkout_is_atomic_when_a_later_step_fails`, `test_history_is_chronological_paginated_and_matches_state` |
| repetição e concorrência | `test_idempotency_key_reused_for_another_item_is_a_conflict`, `test_concurrent_checkout_accepts_exactly_one` (PostgreSQL) |
| permissão e isolamento | `test_checkout_and_return_are_separate_permissions`, `test_checkout_to_foreign_person_fails`, `test_foreign_object_is_indistinguishable_from_missing[item-checkout-post]` |
| posse atual de uma pessoa (RF-51) | `test_current_possession_of_a_person` |
