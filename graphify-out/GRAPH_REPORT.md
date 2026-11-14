# Graph Report - sigab  (2026-11-13)

## Corpus Check
- 228 files · ~169,201 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2107 nodes · 5650 edges · 142 communities (113 shown, 29 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 376 edges (avg confidence: 0.57)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `201978d7`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- django_db
- django_db
- models.py
- 2. Matriz de obrigações aplicáveis
- Decisão de domínio 0004 — Ciclo de vida do item individual
- CLAUDE.md — SIGAB
- test_flow.py
- domain/operations.py
- SIGAB — Análise de requisitos v0.1
- Próximos requisitos — lote de 06/11/2026
- AGENTS.md
- Decisão de domínio 0003 — Modelo de estoque quantitativo e munição
- test_authentication.py
- 4. Dicionário de dados
- 0002_item_condition_reason.py
- sigab
- api/views.py
- ADR 0006 — Eventos de domínio, auditoria e estornos
- Termos críticos
- Pesquisa 0001 — Formulário de armamento temporário
- plano-incremental.md
- Decisão de produto e segurança 0002 — Papéis e escopos
- client.ts
- Auditoria de design, UX/UI e qualidade da interface do SIGAB
- package.json
- compilerOptions
- compilerOptions
- ADR 0005 — API Django e frontend React separados
- Frontend React do SIGAB
- tsconfig.json
- Decisão de produto 0001 — Segmento inicial
- vite.config.ts
- PeoplePage.tsx
- Padrões de interface do frontend
- sigab/biometrics.py
- test_observability.py
- test_items.py
- test_requirements_074_078.py
- Backup e ensaio de restauração — SIGAB-042
- 3. Ameaças
- _json
- test_api_conventions.py
- test_identity.py
- Convenções da API
- Contrato da saída de item individual
- SIGAB
- test_contingency.py
- Observabilidade mínima
- decisoes-pendentes.md
- set_item_condition
- counter.py
- 0005_atomic_permission_codes.py
- django_db
- ConflictError
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
- has_permission
- restore-test.sh
- 0010_personrestriction_restrictionevent_and_more.py
- Auditoria de alinhamento dos requisitos e divisão dos módulos
- backup.sh
- Decisão proposta
- modules.tsx
- 0008_movement_contingency.py
- test_audit.py
- ThemeProvider.tsx
- 2. Ajustes prioritários encontrados
- jira-071-a-075.md
- ServiceBatchPage.tsx
- Page
- Q: Analise as tareas 63 a 70
- api_view
- 0001_initial.py
- 0009_inventorycount_inventorysession_inventorydivergence_and_more.py
- modulos-por-dominio.md
- test_seed_demo.py
- ADR 0004 — Conectividade online, contingência em papel e reconciliação
- Q: analise a analise de requisitos e o sistema atual e veja as diferenças e o que podemos verificar para ajuste
- services.py
- 0011_unique_open_inventory.py
- Pesquisa 0002 — Verificação facial no balcão
- HomePage.tsx
- stock-journey.mjs
- test_concurrency.py
- diferencas-requisitos-2026-11-10.md
- test_requirements_085_086.py
- world
- 0012_single_tenant_installation.py
- ItemDetailPage.tsx
- test_single_tenant.py
- types.ts
- Requisitos e rastreabilidade
- Command
- Segurança e privacidade
- return_item
- 0013_return_batch.py
- Integração contínua
- Entrega técnica — tarefas originais 082–086
- Entrega e validação das tarefas 063 a 070
- 0015_inventory_manager_identity_permissions.py
- sigab/views.py
- 0014_facial_biometrics.py
- test_requirements_079_081.py
- ValidationError
- convert
- Decisões pendentes
- api/restrictions.py
- TenantReadOnlyAdmin
- Command
- Command
- test_api.py
- two_units
- catalog
- Command
- 0016_inventory_manager_movements.py
- purge_after_last_membership
- validate_cpf
- _check_grant_conflicts
- BiometricStatus
- 0004_authorization_matrix_and_login_throttle.py

## God Nodes (most connected - your core abstractions)
1. `api_view()` - 77 edges
2. `ConflictError` - 72 edges
3. `_response()` - 68 edges
4. `Item` - 64 edges
5. `has_permission()` - 64 edges
6. `Account` - 55 edges
7. `Person` - 53 edges
8. `CommandContext` - 51 edges
9. `AuditEvent` - 50 edges
10. `audit()` - 49 edges

## Surprising Connections (you probably didn't know these)
- `convert()` --references--> `Status`  [EXTRACTED]
  scripts/prepare_jira_csv.py → backend/sigab/models.py
- `TenantReadOnlyAdmin` --uses--> `Account`  [INFERRED]
  backend/sigab/admin.py → backend/sigab/models.py
- `TenantReadOnlyAdmin` --uses--> `AuditEvent`  [INFERRED]
  backend/sigab/admin.py → backend/sigab/models.py
- `TenantReadOnlyAdmin` --uses--> `EquipmentType`  [INFERRED]
  backend/sigab/admin.py → backend/sigab/models.py
- `TenantReadOnlyAdmin` --uses--> `Grant`  [INFERRED]
  backend/sigab/admin.py → backend/sigab/models.py

## Import Cycles
- None detected.

## Communities (142 total, 29 thin omitted)

### Community 0 - "django_db"
Cohesion: 0.24
Nodes (12): grant_manager(), django_db, parametrize, restriction(), test_admin_operational_models_are_readonly_and_platform_sees_no_tenant(), test_login_has_no_organization_selector_and_cannot_select_legacy_client(), test_new_accounts_allow_same_requested_username_across_tenants(), test_person_login_is_throttled() (+4 more)

### Community 1 - "django_db"
Cohesion: 0.22
Nodes (13): _call(), _key(), django_db, parametrize, SIGAB-079/081: aggregates, stock positions and ledger history stay in the…, _snapshot(), test_checkout_to_foreign_person_fails(), test_counter_identify_never_finds_foreign_registration() (+5 more)

### Community 2 - "models.py"
Cohesion: 0.09
Nodes (55): AbstractUser, AccountAdmin, AuditedAdmin, AuditEventAdmin, ItemAdmin, MovementAdmin, MovementEventAdmin, OrganizationAdmin (+47 more)

### Community 3 - "2. Matriz de obrigações aplicáveis"
Cohesion: 0.08
Nodes (24): 1. Escopo e conclusão executiva, 2. Matriz de obrigações aplicáveis, 3. Sistemas oficiais e posição do SIGAB, 4. Requisitos derivados para o produto, 5. Evidências obrigatórias antes da implantação, 6. Pendências jurídicas e de produto, 7. Histórico de versões, Nota regulatória 0001 — Guardas Municipais com acervo de armamentos e equipamentos (+16 more)

### Community 4 - "Decisão de domínio 0004 — Ciclo de vida do item individual"
Cohesion: 0.09
Nodes (22): 10. Regras de detalhamento, 11. Validação, 1. Decisão, 2.1 Situação administrativa, 2.2 Condição física, 2.3 Localização, 2.4 Lotação, 2.5 Bloqueios que tornam o item indisponível (+14 more)

### Community 5 - "CLAUDE.md — SIGAB"
Cohesion: 0.12
Nodes (15): Acervo e movimentações, Auditoria, Autorização, CLAUDE.md — SIGAB, Comandos obrigatórios, Documentação e entrega, Fora do escopo sem autorização explícita, graphify (+7 more)

### Community 6 - "test_flow.py"
Cohesion: 0.13
Nodes (37): checkout_item(), legacy_organization(), _checkout(), django_db, parametrize, _set_condition(), test_bulk_update_and_delete_are_blocked(), test_checkout_is_idempotent_and_prevents_second_checkout() (+29 more)

### Community 7 - "domain/operations.py"
Cohesion: 0.12
Nodes (42): _authorize_batch_replay(), checkout_basket(), ItemReturnLine, UUID, Atomically deliver a mixed basket; every retry returns the same batch. The…, Atomically return several materials held by one person. Every line is checked…, _replay_return(), _request_hash() (+34 more)

### Community 8 - "SIGAB — Análise de requisitos v0.1"
Cohesion: 0.10
Nodes (20): 1.1 Público-alvo, 1.2 Status dos requisitos, 1 Finalidade, 2 Glossário, 3 Perfis e permissões, 4.1 Organização, pessoas e acesso, 4.2 Acervo, 4.3 Movimentação (+12 more)

### Community 9 - "Próximos requisitos — lote de 06/11/2026"
Cohesion: 0.09
Nodes (19): Importação do backlog no Jira Cloud, Mapeamento, Regeneração, Importação incremental, Ordem sugerida, Pendências existentes preservadas, Próximos requisitos — lote de 06/11/2026, Tarefas (+11 more)

### Community 11 - "Decisão de domínio 0003 — Modelo de estoque quantitativo e munição"
Cohesion: 0.11
Nodes (18): 10. Divergências entre a proposta e o DOC-0011, 11. Conformidade com os requisitos relacionados, 12. Questões para validar com a Guarda participante, 13. Validação, 1. Decisão proposta, 2.1 Onde fica cada atributo, 2. Conceitos, 3. Posições de saldo (+10 more)

### Community 12 - "test_authentication.py"
Cohesion: 0.10
Nodes (30): AppConfig, SigabConfig, client_ip(), _correlation_id(), is_throttled(), login_identity(), Authentication hardening (SIGAB-021): throttling, login audit and session…, End sessions opened before the account's session_version was incremented. (+22 more)

### Community 13 - "4. Dicionário de dados"
Cohesion: 0.09
Nodes (23): 1. Diagrama, 2. Limites de organização, 3. Cardinalidades, 4.10 Item — item individual (RF-12), 4.11 Movement — movimentação, 4.12 MovementEvent — evento de domínio, 4.13 AuditEvent — evento de auditoria (RF-60), 4.14 AuthenticationFailure — tentativa de login malsucedida (+15 more)

### Community 19 - "api/views.py"
Cohesion: 0.12
Nodes (52): account_action(), account_grants(), _account_or_person_response(), _account_resource(), _audit_refusal(), _boolean(), _catalog_object(), _context() (+44 more)

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
Cohesion: 0.14
Nodes (14): Compatibilidade e implementação, Decisão, Decisão de produto e segurança 0002 — Papéis e escopos, Matriz resumida de autorização, Papéis aprovados, Rastreabilidade do critério de aceite, Regras de aplicação, Revisão 1.1.0 — SIGAB-009 (+6 more)

### Community 29 - "client.ts"
Cohesion: 0.10
Nodes (40): ApiEnvelope, apiRequest(), apiWithMeta(), describeError(), getCookie(), postForm(), postJson(), sendJson() (+32 more)

### Community 30 - "Auditoria de design, UX/UI e qualidade da interface do SIGAB"
Cohesion: 0.04
Nodes (46): 01. Biometria: pessoa selecionada sem identificação visual suficiente — P1 · V/C, 02. Biometria: estado anterior preservado ao trocar de pessoa — P1 · C, 03. Consultas: resposta antiga pode aparecer sob filtro novo — P1 · C, 04. Autosserviço: estrutura da linha do tempo incompatível com o CSS — P1 · C, 05. Cadastros: coluna vazia permanente — P2 · V/C, 06. Estoque: painéis encostados e títulos com margem residual — P2 · V/C, 07. Cabeçalhos de contagem separam número e significado — P2 · V/C, 08. Separadores removidos de todas as linhas — P2 · V/C (+38 more)

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

### Community 41 - "PeoplePage.tsx"
Cohesion: 0.11
Nodes (39): apiPage(), RegisterOptions, RegisterRow, StockHistoryEntry, ErrorState(), LoadingState(), UpdatingState(), formatDateTime() (+31 more)

### Community 42 - "Padrões de interface do frontend"
Cohesion: 0.17
Nodes (11): Ações, Biometria e câmera, Cabeçalho de página, Consulta (busca, filtros, paginação), Diálogos, Formulários e mensagens, Listas, Padrões de interface do frontend (+3 more)

### Community 43 - "sigab/biometrics.py"
Cohesion: 0.14
Nodes (16): compare(), Comparison, decrypt(), encrypt(), engine(), FaceEngine, FaceEngineUnavailable, _fernet() (+8 more)

### Community 44 - "test_observability.py"
Cohesion: 0.14
Nodes (19): _correlation_id(), CorrelationIdMiddleware, Accept a client request ID only when it is short and log-safe., CorrelationIdFilter, JsonFormatter, Remove CPF-like numbers and secret assignments from free text., redact(), _format() (+11 more)

### Community 45 - "test_items.py"
Cohesion: 0.20
Nodes (21): _checkout(), creator(), _post(), django_db, fixture, parametrize, Derive the item projection from confirmed facts only., _replay() (+13 more)

### Community 46 - "test_requirements_074_078.py"
Cohesion: 0.18
Nodes (28): close_inventory_session(), divergence_snapshot(), open_inventory_session(), atomic, record_inventory_count(), update_divergence(), positive_quantity(), settle_stock_loan() (+20 more)

### Community 47 - "Backup e ensaio de restauração — SIGAB-042"
Cohesion: 0.40
Nodes (5): Backup e ensaio de restauração — SIGAB-042, Critérios ainda pendentes, Cópia protegida, Ensaio isolado, Teste reproduzível

### Community 48 - "3. Ameaças"
Cohesion: 0.13
Nodes (15): 1. Escopo, 2. Prioridade, 3.1 Acesso entre organizações (RNF-05), 3.2 Abuso interno, 3.3 Furto de credencial e sessão, 3.4 Adulteração da auditoria (RNF-03), 3.5 Vazamento de dados e exportação (RNF-04), 3.6 Biometria facial (ADR 0008, SIGAB-085/086) (+7 more)

### Community 49 - "_json"
Cohesion: 0.36
Nodes (9): _json(), django_db, test_classification_never_changes_even_unused(), test_deactivating_unit_keeps_its_items(), test_equipment_type_lifecycle(), test_location_deactivation_requires_confirmation(), test_structure_requires_catalog_permission(), test_type_deactivation_keeps_history_and_blocks_new_items() (+1 more)

### Community 50 - "test_api_conventions.py"
Cohesion: 0.40
Nodes (10): _post_json(), django_db, _second_item(), test_csrf_failure_on_api_returns_json(), test_idempotency_key_reused_for_another_item_is_a_conflict(), test_item_list_is_paginated(), test_unexpected_error_returns_json_with_correlation(), test_unit_grant_does_not_reach_other_unit() (+2 more)

### Community 51 - "test_identity.py"
Cohesion: 0.19
Nodes (28): _add_membership(), _create_account(), _create_person(), identity(), _json(), django_db, fixture, Build a valid CPF from nine synthetic digits. (+20 more)

### Community 52 - "Convenções da API"
Cohesion: 0.18
Nodes (11): 1. Base, 2. Autenticação e sessão, 3. Autorização e organização, 4. Escritas: validação, confirmação e idempotência, 5. Respostas, 6. Paginação, 7. Recursos atuais, 8. Dados pessoais na API (+3 more)

### Community 53 - "Contrato da saída de item individual"
Cohesion: 0.22
Nodes (9): 1. Comando, 2. Dados e origem de cada um, 3. Pré-condições, 4. Efeitos, 5. Repetição, 6. Concorrência, 7. Respostas, 8. Critérios de aceite e evidências (+1 more)

### Community 54 - "SIGAB"
Cohesion: 0.15
Nodes (13): 1. Backend, 2. Frontend, 3. Dados iniciais, Credenciais de teste, Estrutura, Evidências da entrega, Graphify, Operação e backup (+5 more)

### Community 55 - "test_contingency.py"
Cohesion: 0.25
Nodes (22): _ago(), _checkout(), _item(), paper(), _post(), django_db, fixture, parametrize (+14 more)

### Community 56 - "Observabilidade mínima"
Cohesion: 0.25
Nodes (8): Fora do escopo, Formato do log, Identificador de requisição, O que nunca é registrado, Observabilidade mínima, Separação, Testes, Tratamento centralizado de erros

### Community 58 - "set_item_condition"
Cohesion: 0.15
Nodes (14): Individual movement service boundary (SIGAB-064)., _existing(), latest_movement_in_force(), UUID, Most recent movement of the item that is neither a reversal nor reversed., Unfit reason in force before `movement`, from the last earlier fact that stated…, Projection the item had before `original`, after checking it still shows its…, Return the movement already recorded under this key, if it is the same request.… (+6 more)

### Community 59 - "counter.py"
Cohesion: 0.07
Nodes (51): overview(), _quantitative_by_type(), Read-only views for the home page (SIGAB-079) and the split collection…, Read-only ledger history of material without registration (RF-54)., Home page summary: totals, open possessions and latest counter movements., Material without registration per type, unit and location (RF-13, RF-14)., stock_history(), stock_summary() (+43 more)

### Community 60 - "0005_atomic_permission_codes.py"
Cohesion: 0.60
Nodes (4): backward(), forward(), Migration, _rewrite()

### Community 61 - "django_db"
Cohesion: 0.39
Nodes (8): _checkout(), _post(), django_db, test_feed_is_paginated_and_filterable(), test_feed_respects_unit_scope_and_is_not_the_audit(), test_possession_matches_confirmed_movements(), test_search_finds_items_and_people_within_scope(), test_search_hides_other_units_and_people_without_permission()

### Community 62 - "ConflictError"
Cohesion: 0.11
Nodes (44): biometric_status(), cancel_identity_exception(), cancel_verification(), _confirmed(), _consume_verification(), decide_identity_exception(), delete_biometric(), enroll_biometric() (+36 more)

### Community 63 - "test_authorization.py"
Cohesion: 0.21
Nodes (23): access_admin(), _grant(), _post(), django_db, fixture, parametrize, _role(), scoped() (+15 more)

### Community 65 - "0007-single-tenant.md"
Cohesion: 0.09
Nodes (19): ADR 0002 — Tenancy compartilhada e autorização explícita, Acesso e provisionamento, ADR 0007 — Produto single-tenant, Decisão, Requisitos e rastreabilidade, Transição de dados, Verificação, Banco e migrações (+11 more)

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

### Community 76 - "has_permission"
Cohesion: 0.10
Nodes (41): batch_resource(), service_batch_options(), stock_loans(), stock_options(), stock_positions(), _stock_units(), _item_possession(), my_history() (+33 more)

### Community 77 - "restore-test.sh"
Cohesion: 0.40
Nodes (3): DATABASE_URL, PGDATABASE, restore-test.sh script

### Community 79 - "Auditoria de alinhamento dos requisitos e divisão dos módulos"
Cohesion: 0.11
Nodes (18): 10. Índice de evidências, 11. Alterações realizadas nesta revisão, 1. Parecer, 2. Método e limites, 3. Matriz de requisitos funcionais, 4. Regras de negócio e requisitos não funcionais, 5. Achados prioritários e critérios de correção, 6. Avaliação da divisão atual (+10 more)

### Community 81 - "Decisão proposta"
Cohesion: 0.12
Nodes (16): 1. Obrigatoriedade, 2. Modo de reconhecimento, 3. Prova de vida, 4. Equipamento e captura, 5. Processamento, 6. O que é armazenado, 7. Base legal e governança, 8. Quando a biometria não for possível: termo assinado e aprovação do administrador (+8 more)

### Community 82 - "modules.tsx"
Cohesion: 0.11
Nodes (28): Session, App(), ALWAYS_VISIBLE, AppModule, availableModules(), FALLBACK_ORDER, groupLabels, legacyRedirect() (+20 more)

### Community 84 - "test_audit.py"
Cohesion: 0.19
Nodes (15): Command, BaseCommand, Return None when the chain is intact, else a description of the first break., verify_chain(), admin(), _audited(), _post(), django_db (+7 more)

### Community 85 - "ThemeProvider.tsx"
Cohesion: 0.16
Nodes (17): ADR-0007, BrandConfig, BrandOverride, defaultBrand, Density, loadBrand(), mergeBrand(), ModuleId (+9 more)

### Community 86 - "2. Ajustes prioritários encontrados"
Cohesion: 0.13
Nodes (15): 1. Evidências executadas, 2. Ajustes prioritários encontrados, 3. Matriz revisada dos 55 requisitos e regras, 4. Documentação e planejamento a reconciliar, 5. Sequência de verificação e ajuste, A1. Inventário permite fechar uma divergência nova usando resolução antiga — alta, A2. Atendimento pode mostrar erro depois de uma saída já confirmada — alta, A3. Reenvio da cesta não conserva a chave de idempotência — alta (+7 more)

### Community 87 - "jira-071-a-075.md"
Cohesion: 0.15
Nodes (10): Login por organização e matrícula — original 049 / Jira 73, Migração e rollback, Entrega técnica — Jira SIGAB-71 a SIGAB-75, Evidências executadas, Garantias e operação, Cronologia e decisões, Evidências de verificação, Identificação das tarefas (+2 more)

### Community 88 - "ServiceBatchPage.tsx"
Cohesion: 0.09
Nodes (33): ApiError, CounterIdentity, ServiceBatchOptions, ServiceBatchResult, dateTimeFormat, formatQuantity(), quantityFormat, ScopeSource (+25 more)

### Community 89 - "Page"
Cohesion: 0.08
Nodes (33): addRegistered(), addUnregistered(), mockIdentify(), availableItem, ids, session(), session(), ids (+25 more)

### Community 90 - "Q: Analise as tareas 63 a 70"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: Analise as tareas 63 a 70, Source Nodes

### Community 91 - "api_view"
Cohesion: 0.12
Nodes (37): biometric_list(), exception_resource(), face_verification_cancel(), face_verification_create(), _form_true(), _form_uuid(), identity_exception_cancel(), identity_exception_decision() (+29 more)

### Community 96 - "test_seed_demo.py"
Cohesion: 0.67
Nodes (3): django_db, test_seed_demo_creates_items_in_every_state(), test_seed_demo_refuses_without_debug_or_twice()

### Community 97 - "ADR 0004 — Conectividade online, contingência em papel e reconciliação"
Cohesion: 0.33
Nodes (6): ADR 0004 — Conectividade online, contingência em papel e reconciliação, Consequências, Contexto, Decisão, Prevenção de dupla entrega, Procedimento de contingência

### Community 98 - "Q: analise a analise de requisitos e o sistema atual e veja as diferenças e o que podemos verificar para ajuste"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: analise a analise de requisitos e o sistema atual e veja as diferenças e o que podemos verificar para ajuste, Source Nodes

### Community 99 - "services.py"
Cohesion: 0.15
Nodes (43): Structure and catalog service boundary (SIGAB-064)., Identity service boundary (SIGAB-064)., _account_for_update(), audit(), _audit_account_status(), create_account(), create_equipment_type(), create_grant() (+35 more)

### Community 101 - "Pesquisa 0002 — Verificação facial no balcão"
Cohesion: 0.25
Nodes (8): 1. Pergunta, 2. O que esta pesquisa entrega e o que falta, 3. Opções avaliadas, 4. Leitura dos critérios do SIGAB, 5. Recomendação provisória para a SIGAB-083, 6. Protocolo de medição (pendente de execução), 7. Resultados da medição, Pesquisa 0002 — Verificação facial no balcão

### Community 102 - "HomePage.tsx"
Cohesion: 0.10
Nodes (18): FaceVerificationResult, IdentityExceptionTerm, Overview, CropRect, FACE_FRAME, FaceCapture(), FaceCaptureProps, ADR-0008 (+10 more)

### Community 104 - "test_concurrency.py"
Cohesion: 0.16
Nodes (23): _assert_single_checkout(), _checkout(), _delivered_basket(), postgresql_only(), fixture, _race(), Real concurrency on PostgreSQL (SIGAB-031). Each attempt uses its own…, Mixing paper and system in one reserve is forbidden (ADR 0004); the bank still… (+15 more)

### Community 105 - "diferencas-requisitos-2026-11-10.md"
Cohesion: 0.09
Nodes (19): Contrato de atendimento com cesta, Decisões, Encerramento de pendência, Evidência automatizada, Reenvio e interface — revisão de 10/11/2026, Segurança e escopo, Ajustes da revisão de requisitos — lote de 10/11/2026, Complementos das tarefas existentes (+11 more)

### Community 106 - "test_requirements_085_086.py"
Cohesion: 0.09
Nodes (49): administrator(), _basket(), _capture(), _checked_out(), engine(), _enroll(), gestor(), _post() (+41 more)

### Community 107 - "world"
Cohesion: 0.40
Nodes (5): api_world(), identity_check_off_by_default(), fixture, Movement-rule tests run without the ADR 0008 identity requirement. Tests of the…, world()

### Community 109 - "ItemDetailPage.tsx"
Cohesion: 0.11
Nodes (18): ADR-0004, MovementResult, Recipient, FOCUSABLE, lockBackground(), Modal(), ModalProps, lastListUrl() (+10 more)

### Community 110 - "test_single_tenant.py"
Cohesion: 0.33
Nodes (3): django_db, test_database_rejects_second_customer_and_bypassing_the_singleton_key(), test_single_tenant_migration_refuses_legacy_database_without_removing_data()

### Community 111 - "types.ts"
Cohesion: 0.07
Nodes (33): AccountInfo, ActivityEvent, GrantInfo, IdentityExceptionStatus, ItemDetail, ItemEvent, ItemSummary, Membership (+25 more)

### Community 112 - "Requisitos e rastreabilidade"
Cohesion: 0.67
Nodes (3): Estado individual: ciclo de vida do item, Fotografia atual — 2026-11-06, Requisitos e rastreabilidade

### Community 113 - "Command"
Cohesion: 0.22
Nodes (6): Command, atomic, BaseCommand, create_tenant_roles(), Tenant role templates of decision 0002 (matrix 1.5.0). Global roles (platform…, Create the approved tenant roles for a new organization; return them by key.

### Community 115 - "return_item"
Cohesion: 0.16
Nodes (14): _check_contingency_fact(), _condition_reason(), incorporate_item(), _is_contingency(), _movement_audit(), _open_checkout(), _origin_fields(), Register an individual item in the reserve with its declared condition. (+6 more)

### Community 117 - "Integração contínua"
Cohesion: 0.33
Nodes (6): Ensaio periódico de restauração, Etapas, Integração contínua, Pendências, Reprodutibilidade, Segredos

### Community 119 - "Entrega técnica — tarefas originais 082–086"
Cohesion: 0.20
Nodes (10): Devolução, Entrega por tarefa, Entrega técnica — tarefas originais 082–086, Fora do escopo desta entrega, Registro de movimentações, Revisão de 13/11/2026: Início com entrada e saída e cadastro facial na pessoa, SIGAB-082 em detalhe, SIGAB-085/086: decisões de implementação (+2 more)

### Community 120 - "Entrega e validação das tarefas 063 a 070"
Cohesion: 0.40
Nodes (4): Entrega e validação das tarefas 063 a 070, Garantias verificadas, Limites explícitos, Rastreabilidade

### Community 122 - "sigab/views.py"
Cohesion: 0.17
Nodes (13): AuthenticationForm, CheckoutForm, ConditionForm, OrganizationAuthenticationForm, ReturnForm, change_condition(), checkin(), checkout() (+5 more)

### Community 124 - "test_requirements_079_081.py"
Cohesion: 0.17
Nodes (20): django_db, skipif, Opt-in real browser/API/PostgreSQL journey; no mutation of the development…, test_real_browser_quantitative_journey(), _quantitative_stock(), test_stock_workspace_filters_units_and_hides_mutations_from_readers(), _basket(), _foreign_unit() (+12 more)

### Community 125 - "ValidationError"
Cohesion: 0.10
Nodes (20): _lines(), return_batch_create(), identity_exception_list(), _due_at(), _optional_uuid(), service_batch_create(), stock_entry_reverse(), stock_loan_settle() (+12 more)

### Community 126 - "convert"
Cohesion: 0.60
Nodes (5): convert(), description(), main(), numeric_id(), slug()

### Community 128 - "api/restrictions.py"
Cohesion: 0.36
Nodes (13): fields(), resource(), restriction_detail(), restriction_list(), change_restriction(), create_restriction(), atomic, record_event() (+5 more)

### Community 130 - "Command"
Cohesion: 0.40
Nodes (3): Command, atomic, BaseCommand

### Community 131 - "Command"
Cohesion: 0.40
Nodes (3): Command, atomic, BaseCommand

### Community 132 - "test_api.py"
Cohesion: 0.44
Nodes (8): _post_json(), django_db, test_api_checkout_is_validated_and_idempotent(), test_api_lists_only_authorized_tenant_items(), test_api_rejects_missing_explicit_confirmation(), test_api_requires_authentication(), test_api_state_change_requires_csrf(), test_session_endpoint_sets_csrf_cookie()

### Community 135 - "Command"
Cohesion: 0.32
Nodes (4): Command, _key(), BaseCommand, Leave items in every state the flow supports, with history behind them.

### Community 137 - "purge_after_last_membership"
Cohesion: 0.67
Nodes (3): _delete_template(), purge_after_last_membership(), Retention rule: the template exists only while the person has an active…

### Community 139 - "_check_grant_conflicts"
Cohesion: 0.67
Nodes (3): _check_grant_conflicts(), Independent auditor: audit.export never coexists with mutation in the same…, _scopes_overlap()

### Community 140 - "BiometricStatus"
Cohesion: 0.67
Nodes (3): BiometricStatus, BiometricPanelProps, Row

## Knowledge Gaps
- **621 isolated node(s):** `sigab`, `Migration`, `Migration`, `Migration`, `Migration` (+616 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **29 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Item` connect `models.py` to `TenantReadOnlyAdmin`, `test_api.py`, `test_flow.py`, `domain/operations.py`, `Command`, `api/views.py`, `test_items.py`, `test_requirements_074_078.py`, `test_api_conventions.py`, `test_contingency.py`, `counter.py`, `ConflictError`, `test_reversal.py`, `has_permission`, `api_view`, `test_seed_demo.py`, `services.py`, `test_concurrency.py`, `test_requirements_085_086.py`, `return_item`, `sigab/views.py`, `test_requirements_079_081.py`, `ValidationError`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Why does `AuditEvent` connect `models.py` to `TenantReadOnlyAdmin`, `Command`, `Command`, `test_flow.py`, `domain/operations.py`, `test_authentication.py`, `api/views.py`, `test_items.py`, `test_requirements_074_078.py`, `test_identity.py`, `test_contingency.py`, `ConflictError`, `test_authorization.py`, `test_reversal.py`, `test_audit.py`, `services.py`, `test_concurrency.py`, `test_requirements_085_086.py`, `Command`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Why does `Account` connect `models.py` to `TenantReadOnlyAdmin`, `Command`, `Command`, `test_flow.py`, `Command`, `test_authentication.py`, `api/views.py`, `test_items.py`, `test_requirements_074_078.py`, `test_identity.py`, `test_contingency.py`, `counter.py`, `ConflictError`, `test_authorization.py`, `test_reversal.py`, `test_audit.py`, `services.py`, `test_concurrency.py`, `test_requirements_085_086.py`, `Command`, `ValidationError`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Are the 73 inferred relationships involving `ValidationError` (e.g. with `counter_identify()` and `_lines()`) actually correct?**
  _`ValidationError` has 73 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `ConflictError` (e.g. with `ItemReturnLine` and `StockRequest`) actually correct?**
  _`ConflictError` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 23 inferred relationships involving `Item` (e.g. with `AccountAdmin` and `AuditedAdmin`) actually correct?**
  _`Item` has 23 INFERRED edges - model-reasoned connections that need verification._
- **What connects `sigab`, `Migration`, `Migration` to the rest of the system?**
  _621 weakly-connected nodes found - possible documentation gaps or missing edges._