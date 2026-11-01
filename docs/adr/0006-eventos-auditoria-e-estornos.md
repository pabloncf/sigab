# ADR 0006 — Eventos de domínio, auditoria e estornos

Status: aceito, 2026-10-31 (SIGAB-012). Amplia o [ADR 0003](0003-eventos-idempotencia.md), que continua válido para projeção atual e idempotência.

Requisitos: RF-60, RF-61, RF-62, RN-05 e RN-09 do [DOC-0011 v0.1](../fontes/DOC-0011-analise-de-requisitos-v0.1.md). Estados e transições: [decisão 0004](../decisoes/0004-ciclo-de-vida-do-item-individual.md). Entidades: [modelo de domínio](../modelo-de-dominio.md).

## Contexto

O ADR 0003 fixou que movimentações e eventos não são editados e que correções serão compensatórias, mas não definiu o formato dos eventos, o contrato da auditoria nem o estorno. A reunião de requisitos pediu um histórico “com opções de editar e excluir”, o que conflita com RF-62; o DOC-0011 resolve o conflito transformando correção em estorno com motivo (RN-05).

## Decisão

### 1. Três registros, três finalidades

| Registro | Onde | Responde | Pode conter |
|---|---|---|---|
| Log técnico | saída do processo (stdout) | o que aconteceu no software | rota, status, duração, `correlation_id`, erro técnico. **Nunca** dado de negócio, CPF, senha ou token |
| Evento de domínio | `MovementEvent` | que fato ocorreu com o item | tipo do fato, item, ator, instante, metadados mínimos versionados |
| Evento de auditoria | `AuditEvent` | quem fez o quê, quando, com que resultado e por quê | ação, objeto, ator, organização, instante, correlação, valores anterior e novo minimizados, motivo |

Um fato operacional gera, na mesma transação, a movimentação, o evento de domínio, o evento de auditoria e a atualização da projeção do item. Se qualquer gravação falha, nenhuma persiste.

O **feed de atividade** (RF-61) é uma consulta de leitura sobre os eventos de domínio da organização, filtrada pelo tenant e pela permissão do leitor. Ele não grava nada, não é fonte de verdade e **não substitui a auditoria**: o feed pode omitir, agrupar ou resumir fatos; a auditoria não. O feed não está implementado e depende de tarefa própria.

### 2. Evento de domínio

Envelope (campos estruturados de `MovementEvent`):

| Campo | Regra |
|---|---|
| `id` | UUID |
| `organization`, `item`, `movement`, `actor` | chaves estrangeiras, todas da mesma organização |
| `event_type` | fato no passado, `item.<verbo_no_particípio>` |
| `occurred_at` | instante UTC do fato |
| `schema_version` | versão do contrato de `metadata`; igual ao sufixo de `metadata.schema` |
| `metadata` | objeto pequeno com `schema` = `<event_type>.v<N>` e apenas os campos do contrato |

Regras de `metadata`:

- dado crítico para regra ou consulta fica em coluna estruturada, não em `metadata`;
- pessoas aparecem só por `id`; nunca nome, CPF ou telefone;
- mudança incompatível de contrato cria nova versão (`v2`); versões antigas continuam legíveis e nunca são reescritas;
- campos fora do contrato não são aceitos. JSON não é depósito genérico.

Catálogo vigente:

| `event_type` | Schema | `metadata` além de `schema` | Movimentação |
|---|---|---|---|
| `item.incorporated` | v1 | — | `incorporation` |
| `item.checked_out` | v1 | `recipient_id` | `checkout` |
| `item.returned` | v1 | `condition` | `return` |
| `item.condition_changed` | v1 | `previous_condition`, `condition` | `condition_change` |
| `item.movement_reversed` | v1 (seção 4) | `reversed_type` | `reversal` (SIGAB-034) |

### 3. Evento de auditoria

| Campo | Regra |
|---|---|
| `organization` | do contexto autenticado; nula só para ação sobre registro sem tenant (plataforma) |
| `actor` | conta autenticada; nula só em comando de implantação controlado |
| `action` | `<objeto>.<verbo>`, por exemplo `item.checkout`, `item.condition_change`, `movement.reverse` |
| `object_type`, `object_id` | referência lógica ao objeto afetado |
| `occurred_at` | instante UTC |
| `correlation_id` | identificador da requisição (`X-Request-ID` recebido, truncado em 64, ou gerado); serve para rastrear, nunca para autorizar |
| `result` | `success`, `denied` ou `conflict` |
| `changes` | ver abaixo |
| `reason` | obrigatório nas ações de RN-09 e em todo estorno |

Formato de `changes`:

- alteração de valor: `{"<campo>": {"from": <anterior>, "to": <novo>}}`, que atende ao “valor anterior e novo” de RF-60;
- referência: `{"<campo>_id": "<uuid>"}`;
- dado pessoal (CPF, telefone, nome) **não** entra em `from`/`to`; registra-se só o nome do campo alterado;
- senha, token e hash nunca entram.

Ações que exigem motivo (RN-09): baixa de item, ajuste de estoque, consumo, alteração de perfil, restrição (registro, alteração e encerramento), estorno; e, pela decisão 0004, declarar item inapto e devolução inapta.

### 4. Estorno

Estorno corrige **erro de registro**. Um fato real posterior (item recuperado, condição que mudou de verdade) é registrado pela transição normal, não por estorno.

Modelo (a implementar na SIGAB-034):

- nova movimentação do tipo `reversal`, com:
  - `reverses`: chave estrangeira para a movimentação estornada, obrigatória neste tipo;
  - `reason`: motivo em texto, obrigatório e não vazio;
- novo evento `item.movement_reversed.v1`, com `compensates` como chave estrangeira estruturada para o evento de domínio original, e `metadata.reversed_type`;
- auditoria `movement.reverse` com `changes` do estado anterior e posterior do item e o motivo.

Restrições de banco:

- restrição única em `reverses`: uma movimentação é estornada no máximo uma vez;
- verificação: `movement_type = reversal` ⇔ `reverses` preenchido ⇔ `reason` não vazio.

Regras de serviço, sob `transaction.atomic` e `select_for_update` no item:

1. confirmação explícita, chave de idempotência e permissão `movement.reverse` na unidade de lotação do item;
2. a movimentação estornada é da mesma organização (outra organização → “não encontrada”);
3. só se estorna a **movimentação mais recente não estornada** do item; havendo fato posterior, estorna-se primeiro o posterior;
4. o item deve estar no estado que a movimentação estornada produziu; caso contrário, conflito;
5. não se estorna `incorporation` (o caminho é a anulação, T20) nem `reversal` (o caminho é refazer a operação normal).

Efeito por tipo:

| Estornada | Efeito na projeção do item |
|---|---|
| `checkout` | volta à reserva, `current_holder` vazio, disponibilidade recalculada. A saída é encerrada pelo estorno, sem registrar devolução |
| `return` | reabre a mesma saída: `in_custody`, `current_holder` = destinatário da saída, condição e motivo anteriores à devolução |
| `condition_change` | restaura condição e motivo anteriores, lidos do fato anterior do item |

Baixa e anulação, quando implementadas, seguem o mesmo padrão e exigem, além disso, aprovador diferente de quem aplicou o ato (decisão 0004, seção 6).

O fato original nunca é editado. Ele é exibido no histórico com a marca “estornado”, derivada da existência de um `reversal` que o referencia.

### 5. Imutabilidade

| Camada | Proteção | Estado |
|---|---|---|
| Instância | `Movement.save/delete` e `ImmutableModel` rejeitam alteração e exclusão | implementado |
| Consulta em lote | `AppendOnlyQuerySet` rejeita `update()` e `delete()` em `Movement`, `MovementEvent` e `AuditEvent` | implementado nesta entrega |
| Django Admin | movimentações e eventos somente leitura, sem incluir, alterar ou excluir | implementado |
| API | nenhuma rota `PUT`, `PATCH` ou `DELETE` para movimentação ou evento; só `POST` de fatos novos | implementado |
| Banco | papel da aplicação sem `UPDATE`/`DELETE` nessas tabelas, ou gatilho de rejeição | **pendente**; depende da implantação (ADR 0005) |

SQL direto e o administrador do banco ainda conseguem alterar registros. Proteção contra esse nível exige controle na implantação e, para RF-62 pleno, verificação de integridade (por exemplo, encadeamento por hash), a decidir.

## Alternativas consideradas

| Alternativa | Motivo da rejeição |
|---|---|
| Edição com histórico de versões (“editar e excluir” da reunião) | viola RN-05 e RF-62; o histórico deixa de ser o fato confirmado |
| Exclusão lógica (`is_deleted`) da movimentação | esconde o fato em vez de compensá-lo; consultas passam a depender de filtro para serem corretas |
| Event sourcing completo (estado só derivado dos eventos) | complexidade sem necessidade; a projeção transacional no item já garante concorrência e leitura simples (ADR 0003) |
| Usar a auditoria como feed | mistura finalidade de controle com exibição; o feed precisa resumir, a auditoria não pode |
| Estorno como campo “estornado” na movimentação original | exige atualizar o fato original, violando a imutabilidade |

## Consequências

- O critério “não existe atualização destrutiva de movimentação” vale na aplicação inteira, inclusive em operações em lote.
- O estorno precisa de dois campos e um tipo novos em `Movement`, uma chave em `MovementEvent` e a permissão `movement.reverse` na matriz da decisão 0002, todos criados pela SIGAB-034 com migração nova.
- Consultas de histórico precisam marcar movimentações estornadas e mostrar o estorno ao lado do original.
- Auditar tentativas negadas (`result = denied`) aumenta o volume da tabela de auditoria; o índice `(organization, occurred_at)` atende à consulta principal.

## Pendências

- **SIGAB-034:** implementar o estorno. A tarefa consta como `Done`, mas não há código de estorno.
- **Tentativas negadas e conflitos:** hoje só se audita `success`. Auditar `denied` e `conflict` nos serviços.
- **Auditoria do Django Admin:** grava só nomes de campos; adotar o formato `from`/`to` da seção 3, respeitando a regra de dado pessoal ([modelo de domínio](../modelo-de-dominio.md), D-11).
- **Proteção no banco:** revogar `UPDATE`/`DELETE` do papel da aplicação ou criar gatilho, junto com a decisão de implantação.
- **Permissão `movement.reverse`:** definir em quais papéis entra na matriz 0002.
