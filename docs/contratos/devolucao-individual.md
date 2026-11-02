# Contrato da devolução de item individual

- Tarefa: SIGAB-032 (contrato) e SIGAB-033 (implementação)
- Revisão: 2026-11-02, conferida com `return_item` em `backend/sigab/services.py` e `POST /api/v1/items/{id}/return/`
- Requisitos: RF-21, RF-22, RF-23 e RF-60 do [DOC-0011 v0.1](../fontes/DOC-0011-analise-de-requisitos-v0.1.md)
- Base: transições T03 e T04 da [decisão 0004](../decisoes/0004-ciclo-de-vida-do-item-individual.md), [contrato da saída](saida-individual.md), [ADR 0006](../adr/0006-eventos-auditoria-e-estornos.md)

## 1. Comando

```http
POST /api/v1/items/{item_id}/return/
Content-Type: application/json
X-CSRFToken: <cookie csrftoken>

{
  "condition": "fit" | "unfit",
  "reason": "obrigatório se unfit, até 200 caracteres",
  "idempotency_key": "uuid gerado ao abrir a ação",
  "confirmed": true
}
```

Um comando devolve **um** item. A conferência de RF-22 (“item por item”) é o próprio comando: o operador confere o item físico e declara sua condição antes de confirmar. Devolver vários itens de uma vez será um agrupamento de comandos, não um comando com lista.

## 2. Dados e origem

| Dado | Origem | Regra |
|---|---|---|
| organização | conta autenticada | nunca enviada pelo cliente |
| operador | conta autenticada | `movement.return` na unidade do item; não precisa ser quem registrou a saída |
| item | URL | da organização; fora do escopo → 404 |
| saída encerrada | servidor | a saída **em vigor** do item: não estornada e sem devolução em vigor. O cliente não escolhe a saída |
| quem devolve | servidor | o responsável atual (`current_holder`), copiado para `Movement.recipient` |
| condição | `condition` | conferência física (RF-22) |
| motivo | `reason` | obrigatório quando inapto (RF-14); ignorado quando apto |
| instante | relógio do servidor, UTC | `confirmed_at` = `occurred_at` do evento |

## 3. Pré-condições

1. `confirmed` é `true`.
2. Chave já usada: regra de repetição (seção 5).
3. Item da organização, bloqueado por `SELECT … FOR UPDATE`.
4. Operador com `movement.return` na unidade do item.
5. Item em posse operacional (`availability = in_custody`) **e** existe saída em vigor.
6. Condição válida; motivo presente se inapto.

Bloqueio da organização por inadimplência **nunca** impede a devolução (RN-07); quando esse bloqueio for implementado, esta pré-condição continua sem ele.

## 4. Efeitos (atômicos)

| Registro | Conteúdo |
|---|---|
| `Movement` | tipo `return`, `related_movement` = saída encerrada, operador, quem devolveu, condição e motivo |
| projeção do item | apto → `available`, condição `fit`, motivo vazio, disponível **no mesmo instante** (RF-23); inapto → `unavailable`, condição `unfit` com motivo; em ambos, `current_holder` vazio |
| `MovementEvent` | `item.returned`, schema `item.returned.v1`, `metadata.condition` |
| `AuditEvent` | `item.return`, com `item_id`, condição e motivo, encadeado na trilha da organização |

A atualização da projeção é condicional (`availability = in_custody`); se outra transação mudou o item, a devolução é desfeita com `409`.

## 5. Repetição e devolução duplicada

| Situação | Resposta |
|---|---|
| mesma chave, mesmo item e mesma condição | `200`, `"created": false`, a devolução original |
| mesma chave com outro item ou outra condição | `409` |
| chave nova para item já devolvido | `409` “O item não possui saída aberta.” |
| duas devoluções simultâneas do mesmo item | uma `201`, a outra `409` (bloqueio de linha) |

Uma restrição de banco “uma devolução por saída” não é usada: o estorno de uma devolução reabre a mesma saída, que então recebe nova devolução. A exclusividade vem do bloqueio do item e da verificação da saída em vigor.

## 6. Correção

Devolução registrada por engano é corrigida por **estorno** (`POST /api/v1/movements/{id}/reverse/`, ADR 0006): o item volta à posse do mesmo responsável, apto, e a saída original fica de novo em aberto. Condição declarada errada em item já na reserva é corrigida por alteração de condição (T05/T06), não por estorno.

## 7. Respostas

| Status | Quando |
|---|---|
| 201 | devolução registrada |
| 200 | repetição idempotente |
| 400 | corpo inválido, sem confirmação, condição inválida ou inapto sem motivo |
| 404 | item inexistente, de outra organização ou fora do escopo |
| 409 | item sem saída aberta, corrida perdida ou chave reutilizada |

## 8. Critérios de aceite e evidências

| Critério (SIGAB-033) | Teste |
|---|---|
| encerra a posse correta | `test_return_closes_the_right_checkout_and_audits`, `test_return_reversal_reopens_the_same_checkout` |
| gera evento e auditoria | `test_return_closes_the_right_checkout_and_audits`, `test_every_p0_operation_is_audited` |
| apto volta a disponível; inapto fica indisponível com motivo | `test_return_closes_custody_and_derives_availability`, `test_unfit_return_requires_reason` |
| repetição não duplica | `test_repeated_return_does_not_duplicate_effects`, `test_two_simultaneous_returns_close_the_checkout_once` (PostgreSQL) |
| isolamento | `test_foreign_object_is_indistinguishable_from_missing[item-return-post]` |

A meta de propagação entre terminais (quanto tempo outro terminal leva para ver o item disponível) não é definida aqui: hoje cada consulta lê o banco, sem cache.
