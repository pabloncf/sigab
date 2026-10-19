# Graph Report - sigab  (2026-10-19)

## Corpus Check
- 40 files · ~10,257 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 230 nodes · 515 edges · 34 communities (21 shown, 13 thin omitted)
- Extraction: 74% EXTRACTED · 26% INFERRED · 0% AMBIGUOUS · INFERRED: 133 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- test_flow.py
- Item
- admin.py
- ValidationError
- AccountAdmin
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
- Termos críticos
- plano-incremental.md
- requisitos.md
- Organization
- .handle
- AuditedAdmin
- models.py
- .save_model
- MovementAdmin

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
- `AccountAdmin` --uses--> `Account`  [INFERRED]
  sigab/admin.py → sigab/models.py
- `AccountAdmin` --uses--> `AuditEvent`  [INFERRED]
  sigab/admin.py → sigab/models.py
- `AccountAdmin` --uses--> `EquipmentType`  [INFERRED]
  sigab/admin.py → sigab/models.py
- `AccountAdmin` --uses--> `Grant`  [INFERRED]
  sigab/admin.py → sigab/models.py
- `AccountAdmin` --uses--> `Item`  [INFERRED]
  sigab/admin.py → sigab/models.py

## Import Cycles
- None detected.

## Communities (34 total, 13 thin omitted)

### Community 0 - "test_flow.py"
Cohesion: 0.14
Nodes (29): django_db, fixture, parametrize, Migration, audit(), checkout_item(), ConflictError, _existing() (+21 more)

### Community 1 - "Item"
Cohesion: 0.17
Nodes (14): login_required, CheckoutForm, ReturnForm, AdministrativeStatus, Availability, Condition, Item, has_permission() (+6 more)

### Community 2 - "admin.py"
Cohesion: 0.26
Nodes (10): register, AuditEventAdmin, ItemAdmin, MovementEventAdmin, Membership, Movement, Person, Type (+2 more)

### Community 5 - "CLAUDE.md — SIGAB"
Cohesion: 0.12
Nodes (15): Acervo e movimentações, Auditoria, Autorização, CLAUDE.md — SIGAB, Comandos obrigatórios, Documentação e entrega, Fora do escopo sem autorização explícita, graphify (+7 more)

### Community 6 - "Decisão de produto 0001 — Segmento inicial"
Cohesion: 0.08
Nodes (19): Consequências, Decisão, Decisão de produto 0001 — Segmento inicial, Escopo e exclusões iniciais, Justificativa, Premissas validadas no levantamento inicial, Problema inicial, Público inicial (+11 more)

### Community 7 - "convert"
Cohesion: 0.48
Nodes (6): Path, convert(), description(), main(), numeric_id(), slug()

### Community 8 - "Command"
Cohesion: 0.40
Nodes (3): Command, atomic, BaseCommand

### Community 9 - "Importação do backlog no Jira Cloud"
Cohesion: 0.50
Nodes (3): Importação do backlog no Jira Cloud, Mapeamento, Regeneração

### Community 25 - "Termos críticos"
Cohesion: 0.14
Nodes (14): Cautela, Consignação, Convenções de uso, Custódia, Glossário operacional v0.2, Matriz de não sinonímia, Posse operacional, Relações entre os termos (+6 more)

### Community 28 - "Organization"
Cohesion: 0.27
Nodes (8): Command, BaseCommand, Grant, Organization, Role, Scope, Status, TimestampedModel

### Community 30 - "AuditedAdmin"
Cohesion: 0.25
Nodes (4): AuditedAdmin, OrganizationAdmin, Classification, EquipmentType

### Community 31 - "models.py"
Cohesion: 0.46
Nodes (6): AbstractUser, Account, AuditEvent, ImmutableModel, Meta, MovementEvent

## Knowledge Gaps
- **58 isolated node(s):** `sigab`, `Migration`, `Status`, `Scope`, `Classification` (+53 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **13 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Item` connect `Item` to `test_flow.py`, `MovementAdmin`, `admin.py`, `ValidationError`, `AccountAdmin`, `Organization`, `AuditedAdmin`, `models.py`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Why does `AccountAdmin` connect `AccountAdmin` to `.save_model`, `Item`, `admin.py`, `MovementAdmin`, `Organization`, `AuditedAdmin`, `models.py`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Why does `CommandContext` connect `admin.py` to `.save_model`, `MovementAdmin`, `test_flow.py`, `Item`, `AccountAdmin`, `Organization`, `AuditedAdmin`, `models.py`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `Item` (e.g. with `AccountAdmin` and `AuditedAdmin`) actually correct?**
  _`Item` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `AccountAdmin` (e.g. with `Account` and `AuditEvent`) actually correct?**
  _`AccountAdmin` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `CommandContext` (e.g. with `AccountAdmin` and `AuditedAdmin`) actually correct?**
  _`CommandContext` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `AuditedAdmin` (e.g. with `Account` and `AuditEvent`) actually correct?**
  _`AuditedAdmin` has 14 INFERRED edges - model-reasoned connections that need verification._