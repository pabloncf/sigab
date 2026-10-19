# Graph Report - sigab  (2026-10-19)

## Corpus Check
- 42 files · ~12,001 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 240 nodes · 526 edges · 28 communities (19 shown, 9 thin omitted)
- Extraction: 75% EXTRACTED · 25% INFERRED · 0% AMBIGUOUS · INFERRED: 133 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- test_flow.py
- Item
- admin.py
- CLAUDE.md — SIGAB
- Decisão de produto 0001 — Segmento inicial
- convert
- Command
- Importação do backlog no Jira Cloud
- AGENTS.md
- 0001-stack-e-frontend.md
- SigabConfig
- sigab
- 0002-tenancy-autorizacao.md
- 0003-eventos-idempotencia.md
- plano-incremental.md
- Decisão de produto e segurança 0002 — Papéis e escopos
- .handle
- CorrelationIdMiddleware

## God Nodes (most connected - your core abstractions)
1. `Item` - 25 edges
2. `AccountAdmin` - 23 edges
3. `CommandContext` - 22 edges
4. `AuditedAdmin` - 21 edges
5. `AuditEventAdmin` - 21 edges
6. `Organization` - 20 edges
7. `Person` - 20 edges
8. `OrganizationAdmin` - 19 edges
9. `MovementAdmin` - 19 edges
10. `AuditEvent` - 19 edges

## Surprising Connections (you probably didn't know these)
- `AccountAdmin` --uses--> `Item`  [INFERRED]
  sigab/admin.py → sigab/models.py
- `AuditedAdmin` --uses--> `Item`  [INFERRED]
  sigab/admin.py → sigab/models.py
- `OrganizationAdmin` --uses--> `Item`  [INFERRED]
  sigab/admin.py → sigab/models.py
- `ItemAdmin` --uses--> `Item`  [INFERRED]
  sigab/admin.py → sigab/models.py
- `MovementAdmin` --uses--> `Item`  [INFERRED]
  sigab/admin.py → sigab/models.py

## Import Cycles
- None detected.

## Communities (28 total, 9 thin omitted)

### Community 0 - "test_flow.py"
Cohesion: 0.16
Nodes (20): django_db, fixture, parametrize, Migration, test_checkout_is_idempotent_and_prevents_second_checkout(), test_checkout_requires_confirmation(), test_checkout_requires_permission(), test_concurrent_checkout_accepts_exactly_one() (+12 more)

### Community 1 - "Item"
Cohesion: 0.10
Nodes (24): login_required, CheckoutForm, ReturnForm, AdministrativeStatus, Availability, Condition, Item, has_permission() (+16 more)

### Community 2 - "admin.py"
Cohesion: 0.12
Nodes (32): AbstractUser, register, AccountAdmin, AuditedAdmin, AuditEventAdmin, ItemAdmin, MovementAdmin, MovementEventAdmin (+24 more)

### Community 5 - "CLAUDE.md — SIGAB"
Cohesion: 0.12
Nodes (15): Acervo e movimentações, Auditoria, Autorização, CLAUDE.md — SIGAB, Comandos obrigatórios, Documentação e entrega, Fora do escopo sem autorização explícita, graphify (+7 more)

### Community 6 - "Decisão de produto 0001 — Segmento inicial"
Cohesion: 0.05
Nodes (33): Consequências, Decisão, Decisão de produto 0001 — Segmento inicial, Escopo e exclusões iniciais, Justificativa, Premissas validadas no levantamento inicial, Problema inicial, Público inicial (+25 more)

### Community 7 - "convert"
Cohesion: 0.48
Nodes (6): Path, convert(), description(), main(), numeric_id(), slug()

### Community 8 - "Command"
Cohesion: 0.40
Nodes (3): Command, atomic, BaseCommand

### Community 9 - "Importação do backlog no Jira Cloud"
Cohesion: 0.50
Nodes (3): Importação do backlog no Jira Cloud, Mapeamento, Regeneração

### Community 27 - "Decisão de produto e segurança 0002 — Papéis e escopos"
Cohesion: 0.17
Nodes (10): Compatibilidade e implementação, Decisão, Decisão de produto e segurança 0002 — Papéis e escopos, Matriz resumida de autorização, Papéis aprovados, Rastreabilidade do critério de aceite, Regras de aplicação, Semântica dos escopos (+2 more)

## Knowledge Gaps
- **66 isolated node(s):** `sigab`, `Migration`, `Status`, `Scope`, `Classification` (+61 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Item` connect `Item` to `test_flow.py`, `admin.py`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **Why does `AccountAdmin` connect `admin.py` to `Item`, `.save_model`?**
  _High betweenness centrality (0.035) - this node is a cross-community bridge._
- **Why does `CommandContext` connect `admin.py` to `test_flow.py`, `Item`, `.save_model`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `Item` (e.g. with `AccountAdmin` and `AuditedAdmin`) actually correct?**
  _`Item` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `AccountAdmin` (e.g. with `Account` and `AuditEvent`) actually correct?**
  _`AccountAdmin` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `CommandContext` (e.g. with `AccountAdmin` and `AuditedAdmin`) actually correct?**
  _`CommandContext` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `AuditedAdmin` (e.g. with `Account` and `AuditEvent`) actually correct?**
  _`AuditedAdmin` has 14 INFERRED edges - model-reasoned connections that need verification._