# Modelo de ameaças inicial

- Tarefa: SIGAB-013
- Revisão: 2026-11-02, conferida com o código em `backend/` (SIGAB-014 a 020)
- Requisitos: RNF-03 (integridade da auditoria), RNF-04 (dados pessoais) e RNF-05 (isolamento entre organizações) do [DOC-0011 v0.1](fontes/DOC-0011-analise-de-requisitos-v0.1.md)
- Base: [decisão 0002 — papéis e escopos](decisoes/0002-papeis-e-escopos.md), [ADR 0005 — stack](adr/0005-api-django-e-frontend-react.md), [ADR 0006 — eventos e auditoria](adr/0006-eventos-auditoria-e-estornos.md), [modelo de domínio](modelo-de-dominio.md)

## 1. Escopo

Sistema coberto: backend Django (API `/api/v1/`, templates de fallback, Django Admin, comandos de gestão), frontend React servido na mesma origem e banco PostgreSQL. Fora do escopo desta revisão, por não existirem: biometria, anexos, operação offline, exportação, integrações oficiais e estoque quantitativo.

### Ativos

| Ativo | Por que importa |
|---|---|
| registro de posse do armamento (saída, devolução, responsável atual) | erro ou fraude deixa arma fora da reserva sem responsável conhecido |
| trilha de auditoria e eventos de domínio | prova de quem fez o quê; sem integridade, o registro de posse perde valor (RF-62) |
| isolamento entre organizações | cada cliente é um órgão público distinto (RNF-05) |
| dados pessoais (nome, matrícula, CPF, telefone) | LGPD (RNF-04) |
| credenciais e sessões | dão acesso a todos os ativos acima |

### Atores de ameaça

| Ator | Exemplo |
|---|---|
| operador interno mal-intencionado ou coagido | armeiro que registra devolução de arma que não voltou |
| usuário legítimo de outra organização | conta válida no tenant B tentando ler ou alterar dados do tenant A |
| atacante externo com credencial furtada | senha vazada, sessão capturada |
| administrador técnico (plataforma, Django Admin, banco) | acesso privilegiado fora do fluxo operacional |

### Fronteiras de confiança

```text
Navegador ──TLS──► Proxy ──► Django (API, templates, Admin) ──► PostgreSQL
   não confiável     │          autoridade: tenant, permissão,      confiável só para
   (inclusive o      │          validação, transação, auditoria     a aplicação; o DBA
   frontend React)   │                                              está fora do controle
                     └─ TLS, limite de taxa (pendente)              da aplicação
```

Tudo que vem do navegador (organização, IDs, chave de idempotência, `X-Request-ID`) é entrada não confiável.

## 2. Prioridade

| Prioridade | Critério |
|---|---|
| **P0** | permite, sem detecção, alterar ou esconder o registro de posse de armamento, ler ou alterar dados de outra organização, assumir uma conta, adulterar a auditoria ou expor dados pessoais em massa |
| P1 | amplia o dano de um P0, depende de condição adicional ou é detectável pela auditoria existente |
| P2 | impacto limitado ou mitigado pelo ambiente |

Estado do controle: **impl.** implementado e testado; **parcial** existe mas incompleto; **ausente** só previsto.

Responsáveis por papel: **Backend** (Tech Lead/Backend), **Implantação** (quem opera o ambiente, ADR 0005), **Produto** (Produto/Domínio), **Segurança** (Segurança/Tech Lead).

## 3. Ameaças

### 3.1 Acesso entre organizações (RNF-05)

| ID | P | Ameaça | Preventivo | Detectivo | Estado | Resp. | Teste |
|---|---|---|---|---|---|---|---|
| A-01 | P0 | ler ou alterar item, pessoa ou movimentação de outra organização trocando o UUID na URL ou no corpo | consultas sempre filtradas por `organization` da conta; objeto externo responde 404 idêntico ao inexistente | auditoria por organização | impl. | Backend | `test_isolation.py`: todas as rotas da API, com guarda que falha se uma rota nova não tiver caso |
| A-02 | P0 | gravar referência a objeto de outra organização (local, pessoa, tipo) | `clean()` e serviços verificam a organização de cada referência | — | parcial: sem chave estrangeira composta no banco (D-06) | Backend | `test_cross_tenant_references_are_rejected`, `test_creation_with_foreign_reference_fails`, `test_checkout_to_foreign_person_fails` |
| A-03 | P0 | organização enviada pelo cliente usada como autoridade | organização derivada de `Account.organization`; a API não aceita campo de organização | — | impl. | Backend | previsto: `test_api_ignores_client_supplied_organization` |
| A-04 | P0 | superusuário lê e altera dados de negócio de qualquer organização | superusuário sem permissão de tenant em `has_permission` (decisão 0002, revisão 1.2.0) | auditoria de ações administrativas | parcial: API e serviços fechados; o Django Admin transitório ainda mostra dados ao superusuário | Backend | `test_superuser_has_no_operational_permission_in_tenant` |
| A-05 | P1 | enumeração de registros externos por diferença de resposta | 404 idêntico para inexistente e de outra organização; UUID não sequencial | — | impl. | Backend | coberto por A-01 |

### 3.2 Abuso interno

| ID | P | Ameaça | Preventivo | Detectivo | Estado | Resp. | Teste |
|---|---|---|---|---|---|---|---|
| I-01 | P0 | operador registra devolução de item que não voltou, ou saída para pessoa diferente da que retirou | confirmação explícita com resumo; destinatário ativo com vínculo ativo; papel restrito à unidade | auditoria com ator, instante e correlação; conferência física periódica (inventário, futura) | parcial: sem conferência periódica nem assinatura do responsável | Produto, Backend | `test_checkout_requires_confirmation`, `test_api_rejects_missing_explicit_confirmation`; previsto: teste de que toda saída e devolução gera `AuditEvent` com ator e correlação |
| I-02 | P0 | operador age fora da unidade da sua concessão | concessão com escopo de unidade avaliada no servidor | auditoria | impl. | Backend | `test_unit_grant_does_not_reach_other_unit` |
| I-03 | P0 | conta sem a permissão executa saída, devolução ou alteração de condição | negação por padrão; concessão explícita | auditoria | impl. | Backend | `test_checkout_requires_permission`, `test_condition_change_requires_permission` |
| I-04 | P0 | dupla saída do mesmo item por confirmações concorrentes | `select_for_update` e atualização condicional | — | impl. | Backend | `test_concurrent_checkout_accepts_exactly_one` (PostgreSQL) |
| I-05 | P1 | repetição da mesma requisição gera duas movimentações | chave de idempotência única por organização | — | impl. | Backend | `test_checkout_is_idempotent_and_prevents_second_checkout`, `test_api_checkout_is_validated_and_idempotent` |
| I-06 | P1 | operador registra saída para si mesmo ou em conluio | regra de produto ainda não decidida | auditoria; relatório de saídas por operador (futuro) | ausente | Produto | previsto após decisão |
| I-07 | P1 | saída e devolução com a mesma permissão | `movement.checkout` e `movement.return` separados (matriz 0002) | — | impl. | Backend | `test_checkout_and_return_are_separate_permissions` |
| I-08 | P1 | gestor concede a si mesmo papel mais amplo | `no_self_grant`; motivo obrigatório; `granted_by` registrado | auditoria `grant.create`/`grant.revoke` com motivo | impl. | Backend | `test_no_self_grant`, `test_grant_requires_reason_and_is_audited`, `test_independent_auditor_conflict` |
| I-09 | P1 | correção feita apagando ou editando o histórico | estorno compensatório com motivo e permissão própria (ADR 0006) | histórico mostra original marcado e estorno | impl. | Backend | `test_checkout_reversal_restores_reserve_and_keeps_original`, `test_reversal_rules`, `test_reversal_requires_permission` |

### 3.3 Furto de credencial e sessão

| ID | P | Ameaça | Preventivo | Detectivo | Estado | Resp. | Teste |
|---|---|---|---|---|---|---|---|
| C-01 | P0 | força bruta ou *credential stuffing* em `/entrar/` e `/admin/` | bloqueio por usuário (5 falhas) e por IP (20 falhas) em 15 min, na aplicação; validadores de senha | auditoria `auth.login` de sucesso e falha | parcial: limite também no proxy e uso de IP real atrás de proxy dependem da implantação | Backend, Implantação | `test_login_is_throttled_after_repeated_failures`, `test_throttle_by_ip_covers_many_usernames`, `test_login_failure_is_audited_without_secrets` |
| C-02 | P0 | sessão capturada por tráfego sem TLS | `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, HSTS e redirecionamento HTTPS fora de `DEBUG`; TLS no proxy | — | **parcial**: `HttpOnly`, `SameSite=Lax` e expiração de 8 h existem; `Secure` e HSTS não | Backend, Implantação | previsto: `manage.py check --deploy` sem alertas no CI com configuração de produção |
| C-03 | P0 | implantação sem `DJANGO_SECRET_KEY` ou sem `DJANGO_DEBUG=false` sobe com chave pública e páginas de depuração | `DEBUG` falso por padrão; inicialização falha sem chave quando `DEBUG` é falso | — | **ausente**: padrões atuais são `unsafe-development-key` e `DEBUG=true` | Backend | previsto: teste de configuração que falha sem chave em modo produção |
| C-04 | P0 | conta de servidor desligado continua ativa | suspensão imediata (`is_active`), verificada a cada requisição; troca de senha invalida sessões (hash de sessão do Django) | revisão periódica de contas ativas × vínculos ativos | parcial: suspensão e revogação pela aplicação; sem revisão periódica | Produto, Backend | `test_suspended_account_cannot_login`, `test_suspension_blocks_login_without_touching_person_or_history`, `test_revocation_is_final_and_allows_new_account` |
| C-05 | P0 | requisição forjada a partir de outro site (CSRF) | CSRF do Django em toda escrita; mesma origem; sem CORS | — | impl. | Backend | `test_api_state_change_requires_csrf`, `test_session_endpoint_sets_csrf_cookie` |
| C-06 | P1 | conta administrativa sem segundo fator | MFA para superusuário e gestor de acesso | auditoria de login administrativo | ausente | Segurança | previsto com a escolha de MFA |
| C-07 | P1 | XSS rouba ação da sessão | escaping de templates e do React; `HttpOnly`; `X-Frame-Options: DENY`; `nosniff` | — | parcial: sem *Content-Security-Policy* | Backend | previsto: cabeçalho CSP presente nas respostas |

### 3.4 Adulteração da auditoria (RNF-03)

| ID | P | Ameaça | Preventivo | Detectivo | Estado | Resp. | Teste |
|---|---|---|---|---|---|---|---|
| T-01 | P0 | alterar ou apagar movimentação, evento ou auditoria pela aplicação, Admin ou operação em lote | `save`/`delete` bloqueados, `AppendOnlyQuerySet`, Admin somente leitura, API sem `PUT`/`PATCH`/`DELETE` | — | impl. | Backend | `test_events_are_immutable`, `test_bulk_update_and_delete_are_blocked` |
| T-02 | P0 | alterar ou apagar registros por SQL direto ou pelo administrador do banco | papel da aplicação sem `UPDATE`/`DELETE` nessas tabelas; acesso ao banco restrito e nominal | cadeia de hashes por organização e `verify_audit_chain`; ancoragem externa do último hash (pendente) | parcial: detectivo implementado; preventivo depende da implantação | Implantação, Segurança, Backend | `test_chain_detects_direct_sql_changes_and_deletions` |
| T-03 | P0 | ação crítica executada sem registro de auditoria | movimentação, evento e auditoria na mesma transação (`transaction.atomic`) | — | impl. | Backend | `test_every_p0_operation_is_audited`, `test_checkout_is_atomic_when_a_later_step_fails` |
| T-04 | P1 | tentativa negada ou em conflito não deixa rastro | escrita recusada pela API gera `AuditEvent` com `result` `denied`, `not_found` ou `conflict` | trilha consultável em `/api/v1/audit/`; alerta por volume (pendente) | impl. | Backend | `test_reversal_requires_permission` |
| T-05 | P2 | injeção de conteúdo no log por `X-Request-ID` | aceita só `[A-Za-z0-9._-]{1,64}`; caso contrário gera UUID | — | impl. | Backend | `test_unsafe_request_id_is_replaced` |

### 3.5 Vazamento de dados e exportação (RNF-04)

| ID | P | Ameaça | Preventivo | Detectivo | Estado | Resp. | Teste |
|---|---|---|---|---|---|---|---|
| V-01 | P0 | exportação em massa de pessoas, posse ou auditoria (RF-56, RN-07) | **hoje não existe rota de exportação**; quando existir: permissão própria (`audit.export`), filtro por tenant, limite de volume, sem CPF, uma auditoria por exportação com filtros usados | auditoria de exportação com alerta por volume | preventivo impl. pela ausência; controles da futura exportação previstos | Produto, Backend | previsto na tarefa de exportação: negação sem permissão, isolamento por tenant, ausência de CPF e auditoria da exportação |
| V-02 | P0 | CPF, senha ou token em log, evento, auditoria ou mensagem de erro | minimização; CPF somente escrita e mascarado na API; formato de `changes` do ADR 0006; `redact()` no log técnico | — | parcial: falta teste sobre `MovementEvent` | Backend | `test_person_is_created_without_account`, `test_invalid_cpf_is_rejected_without_echo`, `test_formatter_redacts_traceback`, `test_login_does_not_log_password` |
| V-03 | P0 | página de depuração expõe configuração e dados | `DEBUG` falso em produção | — | ausente (ver C-03) | Backend | coberto por C-03 |
| V-04 | P1 | backup do banco vazado | criptografia do backup e armazenamento restrito fora do host | restauração periódica controlada | ausente (ADR 0004: retenção e criptografia abertas) | Implantação | previsto no roteiro de backup |
| V-05 | P1 | resposta da API expõe campos além do necessário | contratos JSON explícitos, sem serializar modelos (ADR 0005) | — | impl. | Backend | previsto: teste de contrato da listagem de destinatários sem CPF e telefone |

## 4. Lacunas P0 a tratar

Ameaças P0 cujo controle está ausente ou parcial, em ordem sugerida:

| Ordem | Ameaças | Ação | Responsável |
|---|---|---|---|
| 1 | C-03, V-03, C-02 | configuração de produção segura por padrão: `DEBUG` falso, falha sem chave, cookies `Secure`, HSTS; `check --deploy` no CI | Backend |
| 2 | A-04 | ~~remover o atalho de superusuário~~ feito na SIGAB-022; falta tirar dados de negócio do Django Admin do superusuário | Backend |
| 3 | C-01 | ~~limite de tentativas e auditoria de login~~ feito na SIGAB-021; falta limite no proxy | Implantação |
| 4 | V-02, A-03 | testes previstos para controles já existentes (T-03 feito na SIGAB-035) | Backend |
| 5 | T-02 | papel de banco sem `UPDATE`/`DELETE` e ancoragem externa do hash, junto com a implantação (detecção feita na SIGAB-035) | Implantação |
| 6 | A-02 | chaves estrangeiras compostas ou verificação no banco para referências entre organizações | Backend |
| 7 | I-01, C-04 | conferência física periódica e revisão de contas: processos de produto | Produto |

V-01 só passa a exigir ação quando houver tarefa de exportação.

## 5. Revisão obrigatória

Este modelo deve ser revisto antes de implementar qualquer um destes itens, que mudam ativos ou fronteiras:

- biometria, laudos ou restrições médicas, judiciais ou administrativas (dados sensíveis);
- anexos e assinatura;
- operação offline ou sincronização;
- exportação ou relatórios (V-01);
- integrações oficiais;
- separação de origens entre frontend e backend (CORS);
- sessão de suporte da plataforma em tenant (decisão 0002).

Também deve ser revisto a cada nova permissão, papel ou rota de escrita.
