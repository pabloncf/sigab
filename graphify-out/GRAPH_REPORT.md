# Graph Report - ..  (2026-11-10)

## Corpus Check
- 179 files · ~111,648 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1547 nodes · 4006 edges · 116 communities (93 shown, 23 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 296 edges (avg confidence: 0.56)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `2861d2cd`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_flow.py
- test_requirements_074_078.py
- Item
- 2. Matriz de obrigações aplicáveis
- Decisão de domínio 0004 — Ciclo de vida do item individual
- CLAUDE.md — SIGAB
- test_contingency.py
- api_view
- SIGAB — Análise de requisitos v0.1
- Próximos requisitos — lote de 06/11/2026
- AGENTS.md
- Decisão de domínio 0003 — Modelo de estoque quantitativo e munição
- test_authentication.py
- 4. Dicionário de dados
- 0002_item_condition_reason.py
- sigab
- permitted_unit_ids
- ADR 0006 — Eventos de domínio, auditoria e estornos
- Termos críticos
- Pesquisa 0001 — Formulário de armamento temporário
- plano-incremental.md
- Decisão de produto e segurança 0002 — Papéis e escopos
- client.ts
- _context
- package.json
- compilerOptions
- compilerOptions
- ADR 0005 — API Django e frontend React separados
- Frontend React do SIGAB
- tsconfig.json
- Decisão de produto 0001 — Segmento inicial
- vite.config.ts
- ItemDetailPage.tsx
- test_increment_047_051.py
- test_identity.py
- test_observability.py
- test_items.py
- test_creation_with_foreign_reference_fails
- Backup e ensaio de restauração — SIGAB-042
- 3. Ameaças
- test_catalog.py
- test_api_conventions.py
- api/views.py
- Convenções da API
- Contrato da saída de item individual
- SIGAB
- jira-071-a-075.md
- Observabilidade mínima
- decisoes-pendentes.md
- sigab/views.py
- _organization
- 0005_atomic_permission_codes.py
- django_db
- ThemeProvider.tsx
- test_authorization.py
- 0003_person_cpf_account_revocation.py
- 0007-single-tenant.md
- test_reversal.py
- Entrega e validação das tarefas 041 a 045
- Decisão de domínio 0005 — Restrição operacional da pessoa
- Contrato da devolução de item individual
- Política de dados pessoais
- 0007_audit_hash_chain.py
- Busca inicial
- test-backup.sh
- 0006_movement_reversal.py
- Contrato do lançamento de contingência
- models.py
- restore-test.sh
- 0010_personrestriction_restrictionevent_and_more.py
- Auditoria de alinhamento dos requisitos e divisão dos módulos
- backup.sh
- types.ts
- modules.tsx
- 0008_movement_contingency.py
- ValidationError
- StockPage.tsx
- 2. Ajustes prioritários encontrados
- test_audit.py
- Feedback.tsx
- Page
- Q: Analise as tareas 63 a 70
- domain/__init__.py
- 0001_initial.py
- 0009_inventorycount_inventorysession_inventorydivergence_and_more.py
- modulos-por-dominio.md
- Command
- ADR 0004 — Conectividade online, contingência em papel e reconciliação
- Q: analise a analise de requisitos e o sistema atual e veja as diferenças e o que podemos verificar para ajuste
- services.py
- 0011_unique_open_inventory.py
- Command
- Decisões pendentes
- stock-journey.mjs
- test_concurrency.py
- diferencas-requisitos-2026-11-10.md
- Contrato de atendimento com cesta
- Entrega e validação das tarefas 063 a 070
- 0012_single_tenant_installation.py
- validate_cpf
- test_single_tenant.py
- world
- Requisitos e rastreabilidade
- admin
- .handle
- two_units

## God Nodes (most connected - your core abstractions)
1. `api_view()` - 56 edges
2. `Item` - 56 edges
3. `has_permission()` - 54 edges
4. `ConflictError` - 54 edges
5. `Account` - 52 edges
6. `_response()` - 48 edges
7. `AuditEvent` - 47 edges
8. `Person` - 45 edges
9. `Organization` - 43 edges
10. `Grant` - 41 edges

## Surprising Connections (you probably didn't know these)
- `convert()` --references--> `Status`  [EXTRACTED]
  scripts/prepare_jira_csv.py → backend/sigab/models.py
- `ThrottledModelBackend` --uses--> `Account`  [INFERRED]
  backend/sigab/authentication.py → backend/sigab/models.py
- `ThrottledModelBackend` --uses--> `AuditEvent`  [INFERRED]
  backend/sigab/authentication.py → backend/sigab/models.py
- `ThrottledModelBackend` --uses--> `Organization`  [INFERRED]
  backend/sigab/authentication.py → backend/sigab/models.py
- `SessionVersionMiddleware` --uses--> `Account`  [INFERRED]
  backend/sigab/authentication.py → backend/sigab/models.py

## Import Cycles
- None detected.

## Communities (116 total, 23 thin omitted)

### Community 0 - "test_flow.py"
Cohesion: 0.10
Nodes (42): legacy_organization(), _post_json(), django_db, test_api_checkout_is_validated_and_idempotent(), test_api_lists_only_authorized_tenant_items(), test_api_rejects_missing_explicit_confirmation(), test_api_requires_authentication(), test_api_state_change_requires_csrf() (+34 more)

### Community 1 - "test_requirements_074_078.py"
Cohesion: 0.09
Nodes (48): close_inventory_session(), divergence_snapshot(), open_inventory_session(), atomic, record_inventory_count(), update_divergence(), _authorize_batch_replay(), checkout_basket() (+40 more)

### Community 2 - "Item"
Cohesion: 0.10
Nodes (50): AbstractUser, AccountAdmin, AuditedAdmin, AuditEventAdmin, ItemAdmin, MovementAdmin, MovementEventAdmin, OrganizationAdmin (+42 more)

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

### Community 7 - "api_view"
Cohesion: 0.18
Nodes (28): divergence_update(), inventory_close(), inventory_count(), inventory_detail(), inventory_open(), _session_resource(), batch_resource(), _due_at() (+20 more)

### Community 8 - "SIGAB — Análise de requisitos v0.1"
Cohesion: 0.10
Nodes (20): 1.1 Público-alvo, 1.2 Status dos requisitos, 1 Finalidade, 2 Glossário, 3 Perfis e permissões, 4.1 Organização, pessoas e acesso, 4.2 Acervo, 4.3 Movimentação (+12 more)

### Community 9 - "Próximos requisitos — lote de 06/11/2026"
Cohesion: 0.18
Nodes (9): Importação do backlog no Jira Cloud, Mapeamento, Regeneração, Importação incremental, Ordem sugerida, Pendências existentes preservadas, Próximos requisitos — lote de 06/11/2026, Tarefas (+1 more)

### Community 11 - "Decisão de domínio 0003 — Modelo de estoque quantitativo e munição"
Cohesion: 0.11
Nodes (18): 10. Divergências entre a proposta e o DOC-0011, 11. Conformidade com os requisitos relacionados, 12. Questões para validar com a Guarda participante, 13. Validação, 1. Decisão proposta, 2.1 Onde fica cada atributo, 2. Conceitos, 3. Posições de saldo (+10 more)

### Community 12 - "test_authentication.py"
Cohesion: 0.10
Nodes (31): AppConfig, SigabConfig, client_ip(), _correlation_id(), is_throttled(), login_identity(), Authentication hardening (SIGAB-021): throttling, login audit and session…, End sessions opened before the account's session_version was incremented. (+23 more)

### Community 13 - "4. Dicionário de dados"
Cohesion: 0.09
Nodes (23): 1. Diagrama, 2. Limites de organização, 3. Cardinalidades, 4.10 Item — item individual (RF-12), 4.11 Movement — movimentação, 4.12 MovementEvent — evento de domínio, 4.13 AuditEvent — evento de auditoria (RF-60), 4.14 AuthenticationFailure — tentativa de login malsucedida (+15 more)

### Community 19 - "permitted_unit_ids"
Cohesion: 0.10
Nodes (24): activity_feed(), audit_trail(), _can_read_structure(), _date_range(), _event_resource(), _filter_items(), item_events(), item_list() (+16 more)

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

### Community 29 - "client.ts"
Cohesion: 0.16
Nodes (21): ApiEnvelope, ApiError, apiRequest(), getCookie(), postJson(), sendJson(), EquipmentTypeInfo, LocationInfo (+13 more)

### Community 30 - "_context"
Cohesion: 0.21
Nodes (30): stock_loan_settle(), _boolean(), _catalog_object(), _context(), _contingency(), equipment_type_detail(), equipment_type_list(), equipment_type_status() (+22 more)

### Community 31 - "package.json"
Cohesion: 0.07
Nodes (28): dependencies, react, react-dom, devDependencies, @playwright/test, @types/react, @types/react-dom, typescript (+20 more)

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
Cohesion: 0.33
Nodes (5): Desenvolvimento, Estrutura de tema e navegação, Frontend React do SIGAB, Identidade visual por instalação, Produção

### Community 38 - "Decisão de produto 0001 — Segmento inicial"
Cohesion: 0.22
Nodes (9): Consequências, Decisão, Decisão de produto 0001 — Segmento inicial, Escopo e exclusões iniciais, Justificativa, Premissas validadas no levantamento inicial, Problema inicial, Público inicial (+1 more)

### Community 41 - "ItemDetailPage.tsx"
Cohesion: 0.17
Nodes (15): ADR-0004, apiPage(), apiWithMeta(), ItemDetail, ItemSummary, MovementResult, PersonMatch, Recipient (+7 more)

### Community 42 - "test_increment_047_051.py"
Cohesion: 0.33
Nodes (13): grant_manager(), django_db, parametrize, restriction(), test_admin_operational_models_are_readonly_and_platform_sees_no_tenant(), test_login_has_no_organization_selector_and_cannot_select_legacy_client(), test_new_accounts_allow_same_requested_username_across_tenants(), test_person_login_is_throttled() (+5 more)

### Community 43 - "test_identity.py"
Cohesion: 0.22
Nodes (26): _add_membership(), _create_account(), _create_person(), identity(), _json(), django_db, fixture, Build a valid CPF from nine synthetic digits. (+18 more)

### Community 44 - "test_observability.py"
Cohesion: 0.14
Nodes (19): _correlation_id(), CorrelationIdMiddleware, Accept a client request ID only when it is short and log-safe., CorrelationIdFilter, JsonFormatter, Remove CPF-like numbers and secret assignments from free text., redact(), _format() (+11 more)

### Community 45 - "test_items.py"
Cohesion: 0.20
Nodes (21): _checkout(), creator(), _post(), django_db, fixture, parametrize, Derive the item projection from confirmed facts only., _replay() (+13 more)

### Community 46 - "test_creation_with_foreign_reference_fails"
Cohesion: 0.33
Nodes (9): _call(), _key(), django_db, parametrize, _snapshot(), test_checkout_to_foreign_person_fails(), test_creation_with_foreign_reference_fails(), test_foreign_object_is_indistinguishable_from_missing() (+1 more)

### Community 47 - "Backup e ensaio de restauração — SIGAB-042"
Cohesion: 0.40
Nodes (5): Backup e ensaio de restauração — SIGAB-042, Critérios ainda pendentes, Cópia protegida, Ensaio isolado, Teste reproduzível

### Community 48 - "3. Ameaças"
Cohesion: 0.14
Nodes (14): 1. Escopo, 2. Prioridade, 3.1 Acesso entre organizações (RNF-05), 3.2 Abuso interno, 3.3 Furto de credencial e sessão, 3.4 Adulteração da auditoria (RNF-03), 3.5 Vazamento de dados e exportação (RNF-04), 3. Ameaças (+6 more)

### Community 49 - "test_catalog.py"
Cohesion: 0.35
Nodes (11): catalog(), _json(), django_db, fixture, test_classification_never_changes_even_unused(), test_deactivating_unit_keeps_its_items(), test_equipment_type_lifecycle(), test_location_deactivation_requires_confirmation() (+3 more)

### Community 50 - "test_api_conventions.py"
Cohesion: 0.40
Nodes (10): _post_json(), django_db, _second_item(), test_csrf_failure_on_api_returns_json(), test_idempotency_key_reused_for_another_item_is_a_conflict(), test_item_list_is_paginated(), test_unexpected_error_returns_json_with_correlation(), test_unit_grant_does_not_reach_other_unit() (+2 more)

### Community 51 - "api/views.py"
Cohesion: 0.16
Nodes (25): account_action(), account_grants(), _account_or_person_response(), _account_resource(), _audit_refusal(), csrf_failure(), _error(), _grant_resource() (+17 more)

### Community 52 - "Convenções da API"
Cohesion: 0.20
Nodes (10): 1. Base, 2. Autenticação e sessão, 3. Autorização e organização, 4. Escritas: validação, confirmação e idempotência, 5. Respostas, 6. Paginação, 7. Recursos atuais, 8. Dados pessoais na API (+2 more)

### Community 53 - "Contrato da saída de item individual"
Cohesion: 0.22
Nodes (9): 1. Comando, 2. Dados e origem de cada um, 3. Pré-condições, 4. Efeitos, 5. Repetição, 6. Concorrência, 7. Respostas, 8. Critérios de aceite e evidências (+1 more)

### Community 54 - "SIGAB"
Cohesion: 0.15
Nodes (13): 1. Backend, 2. Frontend, 3. Dados iniciais, Credenciais de teste, Estrutura, Evidências da entrega, Graphify, Operação e backup (+5 more)

### Community 55 - "jira-071-a-075.md"
Cohesion: 0.15
Nodes (10): Login por organização e matrícula — original 049 / Jira 73, Migração e rollback, Entrega técnica — Jira SIGAB-71 a SIGAB-75, Evidências executadas, Garantias e operação, Cronologia e decisões, Evidências de verificação, Identificação das tarefas (+2 more)

### Community 56 - "Observabilidade mínima"
Cohesion: 0.25
Nodes (8): Fora do escopo, Formato do log, Identificador de requisição, O que nunca é registrado, Observabilidade mínima, Separação, Testes, Tratamento centralizado de erros

### Community 58 - "sigab/views.py"
Cohesion: 0.16
Nodes (13): AuthenticationForm, CheckoutForm, ConditionForm, OrganizationAuthenticationForm, ReturnForm, change_condition(), checkin(), checkout() (+5 more)

### Community 59 - "_organization"
Cohesion: 0.24
Nodes (13): Versioned HTTP API consumed by the React frontend., _item_possession(), my_history(), my_possessions(), my_receipt(), possession_export(), possession_list(), _safe_csv() (+5 more)

### Community 60 - "0005_atomic_permission_codes.py"
Cohesion: 0.60
Nodes (4): backward(), forward(), Migration, _rewrite()

### Community 61 - "django_db"
Cohesion: 0.39
Nodes (8): _checkout(), _post(), django_db, test_feed_is_paginated_and_filterable(), test_feed_respects_unit_scope_and_is_not_the_audit(), test_possession_matches_confirmed_movements(), test_search_finds_items_and_people_within_scope(), test_search_hides_other_units_and_people_without_permission()

### Community 62 - "ThemeProvider.tsx"
Cohesion: 0.22
Nodes (13): ADR-0007, BrandConfig, BrandOverride, defaultBrand, Density, loadBrand(), mergeBrand(), applyBrand() (+5 more)

### Community 63 - "test_authorization.py"
Cohesion: 0.15
Nodes (27): atomic, create_tenant_roles(), Tenant role templates of decision 0002 (matrix 1.3.0). Global roles (platform…, Create the approved tenant roles for a new organization; return them by key., access_admin(), _grant(), _post(), django_db (+19 more)

### Community 65 - "0007-single-tenant.md"
Cohesion: 0.08
Nodes (21): ADR 0002 — Tenancy compartilhada e autorização explícita, Acesso e provisionamento, ADR 0007 — Produto single-tenant, Decisão, Requisitos e rastreabilidade, Transição de dados, Verificação, Banco e migrações (+13 more)

### Community 66 - "test_reversal.py"
Cohesion: 0.36
Nodes (16): _checkout(), flows(), _item(), _post(), django_db, fixture, _return(), _reverse() (+8 more)

### Community 67 - "Entrega e validação das tarefas 041 a 045"
Cohesion: 0.33
Nodes (6): Ata — aguardando sessão, Entrega e validação das tarefas 041 a 045, Rastreabilidade da SIGAB-043, SIGAB-041: informações necessárias, SIGAB-045: roteiro da sessão com usuário-alvo, Verificações executadas em 2026-11-02

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

### Community 76 - "models.py"
Cohesion: 0.11
Nodes (18): Migration, Category, ImmutableModel, InventoryCount, InventoryDivergence, InventorySession, PersonRestriction, RestrictionEvent (+10 more)

### Community 77 - "restore-test.sh"
Cohesion: 0.40
Nodes (3): DATABASE_URL, PGDATABASE, restore-test.sh script

### Community 79 - "Auditoria de alinhamento dos requisitos e divisão dos módulos"
Cohesion: 0.11
Nodes (18): 10. Índice de evidências, 11. Alterações realizadas nesta revisão, 1. Parecer, 2. Método e limites, 3. Matriz de requisitos funcionais, 4. Regras de negócio e requisitos não funcionais, 5. Achados prioritários e critérios de correção, 6. Avaliação da divisão atual (+10 more)

### Community 81 - "types.ts"
Cohesion: 0.12
Nodes (21): AccountInfo, ActivityEvent, GrantInfo, ItemEvent, Membership, PersonalHistoryEntry, PersonDetail, PersonSummary (+13 more)

### Community 82 - "modules.tsx"
Cohesion: 0.15
Nodes (22): Session, App(), AppModule, availableModules(), groupLabels, ModuleGroup, modules, Permissions (+14 more)

### Community 84 - "ValidationError"
Cohesion: 0.12
Nodes (14): fields(), resource(), restriction_detail(), restriction_list(), change_restriction(), create_restriction(), atomic, record_event() (+6 more)

### Community 85 - "StockPage.tsx"
Cohesion: 0.21
Nodes (10): Action, Balance, Loan, StockData, StockOptions, StockPage(), Body, PendingRequest (+2 more)

### Community 86 - "2. Ajustes prioritários encontrados"
Cohesion: 0.13
Nodes (15): 1. Evidências executadas, 2. Ajustes prioritários encontrados, 3. Matriz revisada dos 55 requisitos e regras, 4. Documentação e planejamento a reconciliar, 5. Sequência de verificação e ajuste, A1. Inventário permite fechar uma divergência nova usando resolução antiga — alta, A2. Atendimento pode mostrar erro depois de uma saída já confirmada — alta, A3. Reenvio da cesta não conserva a chave de idempotência — alta (+7 more)

### Community 87 - "test_audit.py"
Cohesion: 0.47
Nodes (8): _audited(), _post(), django_db, test_audit_trail_has_no_write_route(), test_audit_trail_requires_permission_and_stays_in_tenant(), test_chain_detects_direct_sql_changes_and_deletions(), test_chain_is_sequential_and_verifiable(), test_every_p0_operation_is_audited()

### Community 88 - "Feedback.tsx"
Cohesion: 0.21
Nodes (8): MyPossessions, PersonalHistory, PersonalReceipt, ErrorState(), LoadingState(), MyPossessionsPage(), ACTIONS, ActivityPage()

### Community 89 - "Page"
Cohesion: 0.29
Nodes (5): availableItem, ids, session(), session(), Page

### Community 90 - "Q: Analise as tareas 63 a 70"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: Analise as tareas 63 a 70, Source Nodes

### Community 96 - "Command"
Cohesion: 0.32
Nodes (4): Command, _key(), BaseCommand, Leave items in every state the flow supports, with history behind them.

### Community 97 - "ADR 0004 — Conectividade online, contingência em papel e reconciliação"
Cohesion: 0.14
Nodes (12): ADR 0004 — Conectividade online, contingência em papel e reconciliação, Consequências, Contexto, Decisão, Prevenção de dupla entrega, Procedimento de contingência, Ensaio periódico de restauração, Etapas (+4 more)

### Community 98 - "Q: analise a analise de requisitos e o sistema atual e veja as diferenças e o que podemos verificar para ajuste"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: analise a analise de requisitos e o sistema atual e veja as diferenças e o que podemos verificar para ajuste, Source Nodes

### Community 99 - "services.py"
Cohesion: 0.08
Nodes (75): Structure and catalog service boundary (SIGAB-064)., Identity service boundary (SIGAB-064)., Individual movement service boundary (SIGAB-064)., adjust_stock(), _account_for_update(), audit(), _audit_account_status(), _check_contingency_fact() (+67 more)

### Community 101 - "Command"
Cohesion: 0.40
Nodes (3): Command, atomic, BaseCommand

### Community 104 - "test_concurrency.py"
Cohesion: 0.09
Nodes (35): StockRequest, assert_eligible(), Caller holds the person's row lock until the delivery transaction commits., Command, BaseCommand, Return None when the chain is intact, else a description of the first break., verify_chain(), audit_record_hash() (+27 more)

### Community 105 - "diferencas-requisitos-2026-11-10.md"
Cohesion: 0.13
Nodes (13): Ajustes da revisão de requisitos — lote de 10/11/2026, Complementos das tarefas existentes, Execução em 10/11/2026, Importação e integridade, Novas tarefas, Ordem de execução, Arquivos de evidência, Entrega por tarefa (+5 more)

### Community 106 - "Contrato de atendimento com cesta"
Cohesion: 0.29
Nodes (6): Contrato de atendimento com cesta, Decisões, Encerramento de pendência, Evidência automatizada, Reenvio e interface — revisão de 10/11/2026, Segurança e escopo

### Community 107 - "Entrega e validação das tarefas 063 a 070"
Cohesion: 0.40
Nodes (4): Entrega e validação das tarefas 063 a 070, Garantias verificadas, Limites explícitos, Rastreabilidade

### Community 110 - "test_single_tenant.py"
Cohesion: 0.33
Nodes (3): django_db, test_database_rejects_second_customer_and_bypassing_the_singleton_key(), test_single_tenant_migration_refuses_legacy_database_without_removing_data()

### Community 111 - "world"
Cohesion: 0.67
Nodes (3): api_world(), fixture, world()

### Community 112 - "Requisitos e rastreabilidade"
Cohesion: 0.67
Nodes (3): Estado individual: ciclo de vida do item, Fotografia atual — 2026-11-06, Requisitos e rastreabilidade

### Community 113 - "admin"
Cohesion: 0.67
Nodes (3): admin(), fixture, Second account with every tenant permission except audit.export, at…

## Knowledge Gaps
- **467 isolated node(s):** `sigab`, `Migration`, `Migration`, `Migration`, `Migration` (+462 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Account` connect `Item` to `Command`, `test_flow.py`, `test_requirements_074_078.py`, `services.py`, `test_reversal.py`, `Command`, `test_contingency.py`, `test_concurrency.py`, `test_increment_047_051.py`, `test_identity.py`, `test_authentication.py`, `models.py`, `test_items.py`, `test_catalog.py`, `api/views.py`, `ValidationError`, `test_audit.py`, `test_authorization.py`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Why does `Item` connect `Item` to `Command`, `test_flow.py`, `test_requirements_074_078.py`, `services.py`, `test_reversal.py`, `test_contingency.py`, `api_view`, `test_concurrency.py`, `test_increment_047_051.py`, `models.py`, `test_items.py`, `test_catalog.py`, `test_api_conventions.py`, `api/views.py`, `ValidationError`, `sigab/views.py`, `_organization`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **Why does `ConflictError` connect `services.py` to `test_flow.py`, `test_requirements_074_078.py`, `Item`, `test_reversal.py`, `test_concurrency.py`, `models.py`, `api/views.py`, `ValidationError`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **Are the 48 inferred relationships involving `ValidationError` (e.g. with `_due_at()` and `_optional_uuid()`) actually correct?**
  _`ValidationError` has 48 INFERRED edges - model-reasoned connections that need verification._
- **Are the 20 inferred relationships involving `Item` (e.g. with `AccountAdmin` and `AuditedAdmin`) actually correct?**
  _`Item` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `ConflictError` (e.g. with `StockRequest` and `Account`) actually correct?**
  _`ConflictError` has 14 INFERRED edges - model-reasoned connections that need verification._
- **What connects `sigab`, `Migration`, `Migration` to the rest of the system?**
  _467 weakly-connected nodes found - possible documentation gaps or missing edges._