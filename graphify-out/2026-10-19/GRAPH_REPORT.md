# Graph Report - sigab  (2026-10-19)

## Corpus Check
- 70 files · ~34,510 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 518 nodes · 997 edges · 41 communities (33 shown, 8 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 139 edges (avg confidence: 0.53)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `2a45690a`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_flow.py
- sigab/views.py
- Item
- 2. Matriz de obrigações aplicáveis
- Decisão de domínio 0004 — Ciclo de vida do item individual
- CLAUDE.md — SIGAB
- 0004-ciclo-de-vida-do-item-individual.md
- convert
- SIGAB — Análise de requisitos v0.1
- Importação do backlog no Jira Cloud
- AGENTS.md
- Decisão de domínio 0003 — Modelo de estoque quantitativo e munição
- SigabConfig
- sigab
- 0002-tenancy-autorizacao.md
- Termos críticos
- Pesquisa 0001 — Formulário de armamento temporário
- plano-incremental.md
- Decisão de produto e segurança 0002 — Papéis e escopos
- Decisão de produto 0001 — Segmento inicial
- App.tsx
- api/views.py
- package.json
- CorrelationIdMiddleware
- compilerOptions
- compilerOptions
- ADR 0005 — API Django e frontend React separados
- Frontend React do SIGAB
- tsconfig.json
- 0002_item_condition_reason.py

## God Nodes (most connected - your core abstractions)
1. `Item` - 28 edges
2. `CommandContext` - 27 edges
3. `AccountAdmin` - 23 edges
4. `Person` - 23 edges
5. `AuditedAdmin` - 21 edges
6. `AuditEventAdmin` - 21 edges
7. `Organization` - 21 edges
8. `OrganizationAdmin` - 19 edges
9. `ItemAdmin` - 19 edges
10. `MovementAdmin` - 19 edges

## Surprising Connections (you probably didn't know these)
- `convert()` --references--> `Status`  [EXTRACTED]
  scripts/prepare_jira_csv.py → sigab/models.py
- `CheckoutForm` --uses--> `Item`  [INFERRED]
  sigab/forms.py → sigab/models.py
- `CheckoutForm` --uses--> `Person`  [INFERRED]
  sigab/forms.py → sigab/models.py
- `ReturnForm` --uses--> `Item`  [INFERRED]
  sigab/forms.py → sigab/models.py
- `ReturnForm` --uses--> `Person`  [INFERRED]
  sigab/forms.py → sigab/models.py

## Import Cycles
- None detected.

## Communities (41 total, 8 thin omitted)

### Community 0 - "test_flow.py"
Cohesion: 0.11
Nodes (45): parametrize, Migration, audit(), checkout_item(), _condition_reason(), ConflictError, _existing(), atomic (+37 more)

### Community 1 - "sigab/views.py"
Cohesion: 0.20
Nodes (12): login_required, CheckoutForm, ConditionForm, ReturnForm, has_permission(), change_condition(), checkin(), checkout() (+4 more)

### Community 2 - "Item"
Cohesion: 0.08
Nodes (49): AbstractUser, register, AccountAdmin, AuditedAdmin, AuditEventAdmin, ItemAdmin, MovementAdmin, MovementEventAdmin (+41 more)

### Community 3 - "2. Matriz de obrigações aplicáveis"
Cohesion: 0.08
Nodes (24): 1. Escopo e conclusão executiva, 2. Matriz de obrigações aplicáveis, 3. Sistemas oficiais e posição do SIGAB, 4. Requisitos derivados para o produto, 5. Evidências obrigatórias antes da implantação, 6. Pendências jurídicas e de produto, 7. Histórico de versões, Nota regulatória 0001 — Guardas Municipais com acervo de armamentos e equipamentos (+16 more)

### Community 4 - "Decisão de domínio 0004 — Ciclo de vida do item individual"
Cohesion: 0.09
Nodes (22): 10. Regras de detalhamento, 11. Validação, 1. Decisão, 2.1 Situação administrativa, 2.2 Condição física, 2.3 Localização, 2.4 Lotação, 2.5 Bloqueios que tornam o item indisponível (+14 more)

### Community 5 - "CLAUDE.md — SIGAB"
Cohesion: 0.12
Nodes (15): Acervo e movimentações, Auditoria, Autorização, CLAUDE.md — SIGAB, Comandos obrigatórios, Documentação e entrega, Fora do escopo sem autorização explícita, graphify (+7 more)

### Community 6 - "0004-ciclo-de-vida-do-item-individual.md"
Cohesion: 0.09
Nodes (21): ADR 0001 — Monólito Django e templates server-side, ADR 0003 — Eventos, projeção atual e idempotência, ADR 0004 — Conectividade online, contingência em papel e reconciliação, Consequências, Contexto, Decisão, Prevenção de dupla entrega, Procedimento de contingência (+13 more)

### Community 7 - "convert"
Cohesion: 0.39
Nodes (7): Path, convert(), description(), main(), numeric_id(), slug(), Status

### Community 8 - "SIGAB — Análise de requisitos v0.1"
Cohesion: 0.10
Nodes (20): 1.1 Público-alvo, 1.2 Status dos requisitos, 1 Finalidade, 2 Glossário, 3 Perfis e permissões, 4.1 Organização, pessoas e acesso, 4.2 Acervo, 4.3 Movimentação (+12 more)

### Community 9 - "Importação do backlog no Jira Cloud"
Cohesion: 0.50
Nodes (3): Importação do backlog no Jira Cloud, Mapeamento, Regeneração

### Community 11 - "Decisão de domínio 0003 — Modelo de estoque quantitativo e munição"
Cohesion: 0.11
Nodes (18): 10. Divergências entre a proposta e o DOC-0011, 11. Conformidade com os requisitos relacionados, 12. Questões para validar com a Guarda participante, 13. Validação, 1. Decisão proposta, 2.1 Onde fica cada atributo, 2. Conceitos, 3. Posições de saldo (+10 more)

### Community 24 - "Termos críticos"
Cohesion: 0.14
Nodes (14): Cautela, Consignação, Convenções de uso, Custódia, Glossário operacional v0.2, Matriz de não sinonímia, Posse operacional, Relações entre os termos (+6 more)

### Community 25 - "Pesquisa 0001 — Formulário de armamento temporário"
Cohesion: 0.14
Nodes (14): 1. Conclusões, 2. Fontes analisadas, 3. Modalidades e correspondência com o glossário, 4. Pessoas e responsabilidades, 5.1 Termo de Responsabilidade e Cautela (F1 Anexo II; F2 Anexo II), 5.2 Termo de Cautelamento, documento de porte (F1 Anexo I; F2 Anexo I), 5.3 Registro de cautela no livro, planilha ou sistema (F3 6.1.6 e 6.1.10; F4 art. 43; F1 e F2 art. 8º), 5.4 Documentos acessórios encontrados (+6 more)

### Community 27 - "Decisão de produto e segurança 0002 — Papéis e escopos"
Cohesion: 0.20
Nodes (10): Compatibilidade e implementação, Decisão, Decisão de produto e segurança 0002 — Papéis e escopos, Matriz resumida de autorização, Papéis aprovados, Rastreabilidade do critério de aceite, Regras de aplicação, Revisão 1.1.0 — SIGAB-009 (+2 more)

### Community 28 - "Decisão de produto 0001 — Segmento inicial"
Cohesion: 0.22
Nodes (9): Consequências, Decisão, Decisão de produto 0001 — Segmento inicial, Escopo e exclusões iniciais, Justificativa, Premissas validadas no levantamento inicial, Problema inicial, Público inicial (+1 more)

### Community 29 - "App.tsx"
Cohesion: 0.16
Nodes (21): ApiEnvelope, ApiError, apiRequest(), getCookie(), postJson(), ItemDetail, ItemSummary, MovementResult (+13 more)

### Community 30 - "api/views.py"
Cohesion: 0.13
Nodes (23): ensure_csrf_cookie, Versioned HTTP API consumed by the React frontend., api_view(), _context(), _item(), item_checkout(), item_condition(), item_detail() (+15 more)

### Community 31 - "package.json"
Cohesion: 0.08
Nodes (25): dependencies, react, react-dom, devDependencies, @types/react, @types/react-dom, typescript, vite (+17 more)

### Community 33 - "compilerOptions"
Cohesion: 0.09
Nodes (21): compilerOptions, allowJs, allowSyntheticDefaultImports, esModuleInterop, forceConsistentCasingInFileNames, isolatedModules, jsx, lib (+13 more)

### Community 34 - "compilerOptions"
Cohesion: 0.20
Nodes (9): compilerOptions, allowImportingTsExtensions, composite, module, moduleResolution, noEmit, skipLibCheck, include (+1 more)

### Community 35 - "ADR 0005 — API Django e frontend React separados"
Cohesion: 0.40
Nodes (4): ADR 0005 — API Django e frontend React separados, Consequências, Contexto, Decisão

### Community 36 - "Frontend React do SIGAB"
Cohesion: 0.50
Nodes (3): Desenvolvimento, Frontend React do SIGAB, Produção

## Knowledge Gaps
- **206 isolated node(s):** `name`, `private`, `version`, `type`, `dev` (+201 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Nota regulatória 0001 — Guardas Municipais com acervo de armamentos e equipamentos` connect `2. Matriz de obrigações aplicáveis` to `0004-ciclo-de-vida-do-item-individual.md`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Why does `Decisão de domínio 0004 — Ciclo de vida do item individual` connect `Decisão de domínio 0004 — Ciclo de vida do item individual` to `0004-ciclo-de-vida-do-item-individual.md`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Why does `SIGAB — Análise de requisitos v0.1` connect `SIGAB — Análise de requisitos v0.1` to `0004-ciclo-de-vida-do-item-individual.md`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Are the 12 inferred relationships involving `Item` (e.g. with `AccountAdmin` and `AuditedAdmin`) actually correct?**
  _`Item` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `CommandContext` (e.g. with `AccountAdmin` and `AuditedAdmin`) actually correct?**
  _`CommandContext` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `AccountAdmin` (e.g. with `Account` and `AuditEvent`) actually correct?**
  _`AccountAdmin` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `Person` (e.g. with `AccountAdmin` and `AuditedAdmin`) actually correct?**
  _`Person` has 13 INFERRED edges - model-reasoned connections that need verification._