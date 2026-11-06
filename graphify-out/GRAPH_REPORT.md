# Graph Report - sigab  (2026-11-05)

## Corpus Check
- 120 files · ~76,410 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1177 nodes · 2845 edges · 86 communities (70 shown, 16 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 224 edges (avg confidence: 0.54)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `89a44344`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_flow.py
- has_permission
- CommandContext
- 2. Matriz de obrigações aplicáveis
- Decisão de domínio 0004 — Ciclo de vida do item individual
- CLAUDE.md — SIGAB
- test_contingency.py
- convert
- SIGAB — Análise de requisitos v0.1
- Importação do backlog no Jira Cloud
- AGENTS.md
- Decisão de domínio 0003 — Modelo de estoque quantitativo e munição
- test_authentication.py
- 4. Dicionário de dados
- 0002_item_condition_reason.py
- sigab
- ADR 0006 — Eventos de domínio, auditoria e estornos
- Termos críticos
- Pesquisa 0001 — Formulário de armamento temporário
- plano-incremental.md
- Decisão de produto e segurança 0002 — Papéis e escopos
- types.ts
- api/views.py
- package.json
- compilerOptions
- compilerOptions
- ADR 0005 — API Django e frontend React separados
- Frontend React do SIGAB
- tsconfig.json
- Decisão de produto 0001 — Segmento inicial
- vite.config.ts
- services.py
- models.py
- test_identity.py
- test_observability.py
- test_items.py
- test_isolation.py
- 3. Ameaças
- test_catalog.py
- test_api_conventions.py
- test_api.py
- Convenções da API
- Contrato da saída de item individual
- SIGAB
- AccountAdmin
- Observabilidade mínima
- Banco e migrações
- test_audit.py
- ADR 0004 — Conectividade online, contingência em papel e reconciliação
- 0005_atomic_permission_codes.py
- Item
- Integração contínua
- validate_cpf
- 0003_person_cpf_account_revocation.py
- 0001-guardas-municipais.md
- test_reversal.py
- backup-e-restauracao.md
- Decisão de domínio 0005 — Restrição operacional da pessoa
- Contrato da devolução de item individual
- Política de dados pessoais
- 0007_audit_hash_chain.py
- Busca inicial
- test-backup.sh
- 0006_movement_reversal.py
- Contrato do lançamento de contingência
- 0006-eventos-auditoria-e-estornos.md
- restore-test.sh
- Decisões pendentes
- roles.py
- backup.sh
- world
- 0008_movement_contingency.py
- 0002-tenancy-autorizacao.md
- Segurança e privacidade

## God Nodes (most connected - your core abstractions)
1. `Account` - 44 edges
2. `Item` - 43 edges
3. `AuditEvent` - 42 edges
4. `CommandContext` - 39 edges
5. `Grant` - 38 edges
6. `ConflictError` - 38 edges
7. `Organization` - 37 edges
8. `Person` - 35 edges
9. `Role` - 35 edges
10. `api_view()` - 33 edges

## Surprising Connections (you probably didn't know these)
- `convert()` --references--> `Status`  [EXTRACTED]
  scripts/prepare_jira_csv.py → backend/sigab/models.py
- `AccountAdmin` --uses--> `Account`  [INFERRED]
  backend/sigab/admin.py → backend/sigab/models.py
- `AccountAdmin` --uses--> `AuditEvent`  [INFERRED]
  backend/sigab/admin.py → backend/sigab/models.py
- `AccountAdmin` --uses--> `EquipmentType`  [INFERRED]
  backend/sigab/admin.py → backend/sigab/models.py
- `AccountAdmin` --uses--> `Grant`  [INFERRED]
  backend/sigab/admin.py → backend/sigab/models.py

## Import Cycles
- None detected.

## Communities (86 total, 16 thin omitted)

### Community 0 - "test_flow.py"
Cohesion: 0.14
Nodes (31): _checkout(), django_db, parametrize, _set_condition(), test_bulk_update_and_delete_are_blocked(), test_checkout_is_idempotent_and_prevents_second_checkout(), test_checkout_rejects_inactive_item(), test_checkout_requires_confirmation() (+23 more)

### Community 1 - "has_permission"
Cohesion: 0.10
Nodes (37): CheckoutForm, ConditionForm, ReturnForm, _effective_grants(), has_permission(), Server-side authorization (decision 0002, matrix 1.3.0). Default deny. A…, access_admin(), _grant() (+29 more)

### Community 2 - "CommandContext"
Cohesion: 0.14
Nodes (32): AuditedAdmin, AuditEventAdmin, ItemAdmin, MovementAdmin, MovementEventAdmin, OrganizationAdmin, AuthenticationFailure, Classification (+24 more)

### Community 3 - "2. Matriz de obrigações aplicáveis"
Cohesion: 0.08
Nodes (24): 1. Escopo e conclusão executiva, 2. Matriz de obrigações aplicáveis, 3. Sistemas oficiais e posição do SIGAB, 4. Requisitos derivados para o produto, 5. Evidências obrigatórias antes da implantação, 6. Pendências jurídicas e de produto, 7. Histórico de versões, Nota regulatória 0001 — Guardas Municipais com acervo de armamentos e equipamentos (+16 more)

### Community 4 - "Decisão de domínio 0004 — Ciclo de vida do item individual"
Cohesion: 0.09
Nodes (22): 10. Regras de detalhamento, 11. Validação, 1. Decisão, 2.1 Situação administrativa, 2.2 Condição física, 2.3 Localização, 2.4 Lotação, 2.5 Bloqueios que tornam o item indisponível (+14 more)

### Community 5 - "CLAUDE.md — SIGAB"
Cohesion: 0.12
Nodes (15): Acervo e movimentações, Auditoria, Autorização, CLAUDE.md — SIGAB, Comandos obrigatórios, Documentação e entrega, Fora do escopo sem autorização explícita, graphify (+7 more)

### Community 6 - "test_contingency.py"
Cohesion: 0.25
Nodes (22): _ago(), _checkout(), _item(), paper(), _post(), django_db, fixture, parametrize (+14 more)

### Community 7 - "convert"
Cohesion: 0.39
Nodes (7): Status, Path, convert(), description(), main(), numeric_id(), slug()

### Community 8 - "SIGAB — Análise de requisitos v0.1"
Cohesion: 0.10
Nodes (20): 1.1 Público-alvo, 1.2 Status dos requisitos, 1 Finalidade, 2 Glossário, 3 Perfis e permissões, 4.1 Organização, pessoas e acesso, 4.2 Acervo, 4.3 Movimentação (+12 more)

### Community 9 - "Importação do backlog no Jira Cloud"
Cohesion: 0.50
Nodes (3): Importação do backlog no Jira Cloud, Mapeamento, Regeneração

### Community 11 - "Decisão de domínio 0003 — Modelo de estoque quantitativo e munição"
Cohesion: 0.11
Nodes (18): 10. Divergências entre a proposta e o DOC-0011, 11. Conformidade com os requisitos relacionados, 12. Questões para validar com a Guarda participante, 13. Validação, 1. Decisão proposta, 2.1 Onde fica cada atributo, 2. Conceitos, 3. Posições de saldo (+10 more)

### Community 12 - "test_authentication.py"
Cohesion: 0.11
Nodes (27): AppConfig, SigabConfig, client_ip(), _correlation_id(), is_throttled(), Authentication hardening (SIGAB-021): throttling, login audit and session…, End sessions opened before the account's session_version was incremented., ModelBackend that refuses throttled attempts and accounts of suspended… (+19 more)

### Community 13 - "4. Dicionário de dados"
Cohesion: 0.09
Nodes (23): 1. Diagrama, 2. Limites de organização, 3. Cardinalidades, 4.10 Item — item individual (RF-12), 4.11 Movement — movimentação, 4.12 MovementEvent — evento de domínio, 4.13 AuditEvent — evento de auditoria (RF-60), 4.14 AuthenticationFailure — tentativa de login malsucedida (+15 more)

### Community 23 - "ADR 0006 — Eventos de domínio, auditoria e estornos"
Cohesion: 0.18
Nodes (11): 1. Três registros, três finalidades, 2. Evento de domínio, 3. Evento de auditoria, 4. Estorno, 5. Imutabilidade, ADR 0006 — Eventos de domínio, auditoria e estornos, Alternativas consideradas, Consequências (+3 more)

### Community 24 - "Termos críticos"
Cohesion: 0.14
Nodes (14): Cautela, Consignação, Convenções de uso, Custódia, Glossário operacional v0.2, Matriz de não sinonímia, Posse operacional, Relações entre os termos (+6 more)

### Community 25 - "Pesquisa 0001 — Formulário de armamento temporário"
Cohesion: 0.14
Nodes (14): 1. Conclusões, 2. Fontes analisadas, 3. Modalidades e correspondência com o glossário, 4. Pessoas e responsabilidades, 5.1 Termo de Responsabilidade e Cautela (F1 Anexo II; F2 Anexo II), 5.2 Termo de Cautelamento, documento de porte (F1 Anexo I; F2 Anexo I), 5.3 Registro de cautela no livro, planilha ou sistema (F3 6.1.6 e 6.1.10; F4 art. 43; F1 e F2 art. 8º), 5.4 Documentos acessórios encontrados (+6 more)

### Community 27 - "Decisão de produto e segurança 0002 — Papéis e escopos"
Cohesion: 0.17
Nodes (12): Compatibilidade e implementação, Decisão, Decisão de produto e segurança 0002 — Papéis e escopos, Matriz resumida de autorização, Papéis aprovados, Rastreabilidade do critério de aceite, Regras de aplicação, Revisão 1.1.0 — SIGAB-009 (+4 more)

### Community 29 - "types.ts"
Cohesion: 0.07
Nodes (59): ADR-0004, ApiEnvelope, ApiError, apiPage(), apiRequest(), apiWithMeta(), getCookie(), postJson() (+51 more)

### Community 30 - "api/views.py"
Cohesion: 0.09
Nodes (88): account_action(), account_grants(), _account_or_person_response(), _account_resource(), activity_feed(), api_view(), _audit_refusal(), audit_trail() (+80 more)

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
Cohesion: 0.20
Nodes (10): ADR 0005 — API Django e frontend React separados, Alternativas de frontend, Banco de dados, Comandos locais, Consequências, Contexto, Decisão, Implantação (+2 more)

### Community 36 - "Frontend React do SIGAB"
Cohesion: 0.50
Nodes (3): Desenvolvimento, Frontend React do SIGAB, Produção

### Community 38 - "Decisão de produto 0001 — Segmento inicial"
Cohesion: 0.22
Nodes (9): Consequências, Decisão, Decisão de produto 0001 — Segmento inicial, Escopo e exclusões iniciais, Justificativa, Premissas validadas no levantamento inicial, Problema inicial, Público inicial (+1 more)

### Community 41 - "services.py"
Cohesion: 0.07
Nodes (73): AppendOnlyQuerySet, Block bulk writes that bypass the per-instance immutability guards., _account_for_update(), audit(), _audit_account_status(), _check_contingency_fact(), _check_grant_conflicts(), checkout_item() (+65 more)

### Community 42 - "models.py"
Cohesion: 0.10
Nodes (22): AbstractUser, Command, BaseCommand, Command, atomic, BaseCommand, Command, atomic (+14 more)

### Community 43 - "test_identity.py"
Cohesion: 0.21
Nodes (26): _add_membership(), _create_account(), _create_person(), identity(), _json(), django_db, fixture, Build a valid CPF from nine synthetic digits. (+18 more)

### Community 44 - "test_observability.py"
Cohesion: 0.14
Nodes (19): _correlation_id(), CorrelationIdMiddleware, Accept a client request ID only when it is short and log-safe., CorrelationIdFilter, JsonFormatter, Remove CPF-like numbers and secret assignments from free text., redact(), _format() (+11 more)

### Community 45 - "test_items.py"
Cohesion: 0.20
Nodes (21): _checkout(), creator(), _post(), django_db, fixture, parametrize, Derive the item projection from confirmed facts only., _replay() (+13 more)

### Community 46 - "test_isolation.py"
Cohesion: 0.19
Nodes (14): Versioned HTTP API consumed by the React frontend., _call(), _key(), django_db, fixture, parametrize, Cross-organization isolation suite (SIGAB-025, RF-01, RNF-05). Every API route…, _snapshot() (+6 more)

### Community 48 - "3. Ameaças"
Cohesion: 0.14
Nodes (14): 1. Escopo, 2. Prioridade, 3.1 Acesso entre organizações (RNF-05), 3.2 Abuso interno, 3.3 Furto de credencial e sessão, 3.4 Adulteração da auditoria (RNF-03), 3.5 Vazamento de dados e exportação (RNF-04), 3. Ameaças (+6 more)

### Community 49 - "test_catalog.py"
Cohesion: 0.35
Nodes (11): catalog(), _json(), django_db, fixture, test_classification_never_changes_even_unused(), test_deactivating_unit_keeps_its_items(), test_equipment_type_lifecycle(), test_location_deactivation_requires_confirmation() (+3 more)

### Community 50 - "test_api_conventions.py"
Cohesion: 0.40
Nodes (10): _post_json(), django_db, _second_item(), test_csrf_failure_on_api_returns_json(), test_idempotency_key_reused_for_another_item_is_a_conflict(), test_item_list_is_paginated(), test_unexpected_error_returns_json_with_correlation(), test_unit_grant_does_not_reach_other_unit() (+2 more)

### Community 51 - "test_api.py"
Cohesion: 0.44
Nodes (8): _post_json(), django_db, test_api_checkout_is_validated_and_idempotent(), test_api_lists_only_authorized_tenant_items(), test_api_rejects_missing_explicit_confirmation(), test_api_requires_authentication(), test_api_state_change_requires_csrf(), test_session_endpoint_sets_csrf_cookie()

### Community 52 - "Convenções da API"
Cohesion: 0.22
Nodes (9): 1. Base, 2. Autenticação e sessão, 3. Autorização e organização, 4. Escritas: validação, confirmação e idempotência, 5. Respostas, 6. Paginação, 7. Recursos atuais, 8. Dados pessoais na API (+1 more)

### Community 53 - "Contrato da saída de item individual"
Cohesion: 0.22
Nodes (9): 1. Comando, 2. Dados e origem de cada um, 3. Pré-condições, 4. Efeitos, 5. Repetição, 6. Concorrência, 7. Respostas, 8. Critérios de aceite e evidências (+1 more)

### Community 54 - "SIGAB"
Cohesion: 0.18
Nodes (11): 1. Backend, 2. Frontend, 3. Dados iniciais, Estrutura, Evidências da entrega, Graphify, Operação e backup, Primeiros passos (sem Docker) (+3 more)

### Community 56 - "Observabilidade mínima"
Cohesion: 0.25
Nodes (8): Fora do escopo, Formato do log, Identificador de requisição, O que nunca é registrado, Observabilidade mínima, Separação, Testes, Tratamento centralizado de erros

### Community 57 - "Banco e migrações"
Cohesion: 0.33
Nodes (6): Banco e migrações, Bancos, Convenções, Do banco vazio à versão atual, Migrações atuais, Verificação em ambiente descartável

### Community 58 - "test_audit.py"
Cohesion: 0.11
Nodes (26): Command, BaseCommand, Return None when the chain is intact, else a description of the first break., verify_chain(), audit_record_hash(), SHA-256 over the canonical content of an audit event and the previous hash., admin(), _audited() (+18 more)

### Community 59 - "ADR 0004 — Conectividade online, contingência em papel e reconciliação"
Cohesion: 0.33
Nodes (6): ADR 0004 — Conectividade online, contingência em papel e reconciliação, Consequências, Contexto, Decisão, Prevenção de dupla entrega, Procedimento de contingência

### Community 60 - "0005_atomic_permission_codes.py"
Cohesion: 0.60
Nodes (4): backward(), forward(), Migration, _rewrite()

### Community 61 - "Item"
Cohesion: 0.18
Nodes (17): AdministrativeStatus, Availability, Condition, Item, _checkout(), _post(), django_db, fixture (+9 more)

### Community 62 - "Integração contínua"
Cohesion: 0.33
Nodes (6): Ensaio periódico de restauração, Etapas, Integração contínua, Pendências, Reprodutibilidade, Segredos

### Community 65 - "0001-guardas-municipais.md"
Cohesion: 0.27
Nodes (3): Estado individual: ciclo de vida do item, Requisitos e rastreabilidade, Visão do produto

### Community 66 - "test_reversal.py"
Cohesion: 0.36
Nodes (16): _checkout(), flows(), _item(), _post(), django_db, fixture, _return(), _reverse() (+8 more)

### Community 67 - "backup-e-restauracao.md"
Cohesion: 0.15
Nodes (11): Backup e ensaio de restauração — SIGAB-042, Critérios ainda pendentes, Cópia protegida, Ensaio isolado, Teste reproduzível, Ata — aguardando sessão, Entrega e validação das tarefas 041 a 045, Rastreabilidade da SIGAB-043 (+3 more)

### Community 68 - "Decisão de domínio 0005 — Restrição operacional da pessoa"
Cohesion: 0.20
Nodes (10): 1. Decisão, 2. Dados, 3. Vigência e decisão na saída, 4. Registro, alteração e encerramento, 5. Exceção, 6. Recolhimento, 7. Privacidade e auditoria, 8. Fora desta decisão (+2 more)

### Community 69 - "Contrato da devolução de item individual"
Cohesion: 0.22
Nodes (9): 1. Comando, 2. Dados e origem, 3. Pré-condições, 4. Efeitos (atômicos), 5. Repetição e devolução duplicada, 6. Correção, 7. Respostas, 8. Critérios de aceite e evidências (+1 more)

### Community 70 - "Política de dados pessoais"
Cohesion: 0.25
Nodes (8): 1. Papéis no tratamento, 2. Finalidade e base legal comuns, 3. Matriz de dados, 4. Regras de acesso e exibição, 5. Direitos do titular, 6. Exportação, 7. Pendências, Política de dados pessoais

### Community 71 - "0007_audit_hash_chain.py"
Cohesion: 0.67
Nodes (3): chain_existing_events(), _hash(), Migration

### Community 72 - "Busca inicial"
Cohesion: 0.67
Nodes (3): Busca inicial, Contrato, Medição

### Community 73 - "test-backup.sh"
Cohesion: 0.22
Nodes (7): AGE_IDENTITY, BACKUP_DIR, DATABASE_URL, PGDATABASE, REPORT_PATH, RESTORE_TEST_ISOLATED, test-backup.sh script

### Community 75 - "Contrato do lançamento de contingência"
Cohesion: 0.29
Nodes (7): 1. Comando, 2. Dados, 3. Regras, 4. Efeitos, 5. Fora deste contrato, 6. Critérios de aceite e evidências, Contrato do lançamento de contingência

### Community 77 - "restore-test.sh"
Cohesion: 0.40
Nodes (3): DATABASE_URL, PGDATABASE, restore-test.sh script

### Community 79 - "roles.py"
Cohesion: 0.33
Nodes (4): atomic, create_tenant_roles(), Tenant role templates of decision 0002 (matrix 1.3.0). Global roles (platform…, Create the approved tenant roles for a new organization; return them by key.

### Community 82 - "world"
Cohesion: 0.67
Nodes (3): api_world(), fixture, world()

## Knowledge Gaps
- **360 isolated node(s):** `sigab`, `Migration`, `Migration`, `Migration`, `Migration` (+355 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **16 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Account` connect `models.py` to `test_flow.py`, `has_permission`, `CommandContext`, `test_reversal.py`, `test_contingency.py`, `services.py`, `test_identity.py`, `test_authentication.py`, `test_items.py`, `test_isolation.py`, `test_catalog.py`, `AccountAdmin`, `test_audit.py`, `Item`, `api/views.py`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Why does `AuditEvent` connect `models.py` to `test_flow.py`, `has_permission`, `CommandContext`, `test_reversal.py`, `test_contingency.py`, `services.py`, `test_identity.py`, `test_authentication.py`, `test_items.py`, `test_isolation.py`, `.save`, `test_catalog.py`, `AccountAdmin`, `test_audit.py`, `api/views.py`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Why does `Organization` connect `models.py` to `test_flow.py`, `has_permission`, `CommandContext`, `test_contingency.py`, `convert`, `services.py`, `test_identity.py`, `test_authentication.py`, `test_isolation.py`, `test_api.py`, `AccountAdmin`, `test_audit.py`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Are the 29 inferred relationships involving `ValidationError` (e.g. with `_boolean()` and `_contingency()`) actually correct?**
  _`ValidationError` has 29 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `Account` (e.g. with `AccountAdmin` and `AuditedAdmin`) actually correct?**
  _`Account` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `Item` (e.g. with `AccountAdmin` and `AuditedAdmin`) actually correct?**
  _`Item` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `AuditEvent` (e.g. with `AccountAdmin` and `AuditedAdmin`) actually correct?**
  _`AuditEvent` has 18 INFERRED edges - model-reasoned connections that need verification._