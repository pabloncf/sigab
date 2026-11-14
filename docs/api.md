# Convenções da API

- Tarefa: SIGAB-014
- Revisão: 2026-11-02 (SIGAB-014; rotas e autenticação revistas na SIGAB-021 a 030), conferida com `backend/sigab/api/`
- Base: [ADR 0005](adr/0005-api-django-e-frontend-react.md) (fronteira React/API), [ADR 0006](adr/0006-eventos-auditoria-e-estornos.md) (eventos e auditoria), [modelo de ameaças](modelo-de-ameacas.md)
- Requisitos: RF-20, RF-21 e RF-60 do [DOC-0011 v0.1](fontes/DOC-0011-analise-de-requisitos-v0.1.md)

## 1. Base

- Prefixo único e versionado: `/api/v1/`. Mudança incompatível cria `/api/v2/`; a versão anterior continua até o frontend migrar.
- Corpo de requisição e resposta em JSON UTF-8. Escritas exigem `Content-Type: application/json` e corpo de no máximo 16 KiB.
- Identificadores são UUID. Instantes são ISO 8601 em UTC.
- Nomes de campo em inglês (`snake_case`); mensagens ao usuário em português.
- A API devolve contratos montados à mão; modelos Django nunca são serializados diretamente.

## 2. Autenticação e sessão

- Sessão Django em cookie `HttpOnly` (`SameSite=Lax`, expira em 8 h). Login e logout de formulário em `/entrar/` e `/sair/`; logout da SPA em `POST /api/v1/session/logout/`.
- `GET /api/v1/session/` devolve a conta, a organização e as permissões de interface (`permissions.can_manage_identity`) e grava o cookie `csrftoken`.
- Toda escrita (`POST`, `PATCH`) exige o cabeçalho `X-CSRFToken` com o valor do cookie. Sem ele, a resposta é `403` no formato de erro da seção 5.
- Conta inativa ou revogada, ou de organização suspensa, é tratada como não autenticada a partir da requisição seguinte.
- Sessões são revogáveis: suspender, revogar ou “encerrar sessões” de uma conta incrementa `session_version`, e toda sessão aberta com a versão anterior é encerrada na próxima requisição. Trocar a senha também encerra as sessões (hash de sessão do Django).
- Senhas são guardadas só como hash PBKDF2-SHA256 do Django e validadas pelos validadores de força configurados.
- Limite de tentativas: 5 falhas para o mesmo usuário ou 20 para o mesmo IP em 15 minutos bloqueiam novas tentativas, inclusive com a senha certa, com a mesma mensagem genérica de credencial inválida. O usuário digitado é guardado só como HMAC; o IP vem de `REMOTE_ADDR` até que um proxy confiável seja definido.
- Login com sucesso e com falha gera `AuditEvent` `auth.login` com `result` `success` ou `failure`, sem senha nem usuário digitado.
- Sem CORS: frontend e API na mesma origem.

## 3. Autorização e organização

- A organização vem sempre de `Account.organization` da sessão. A API não aceita organização no corpo, na URL ou em cabeçalho.
- Permissões explícitas avaliadas no servidor em cada requisição (`sigab/permissions.py`), no escopo da organização ou da unidade do objeto.
- **Coleção** sem permissão: `403 Acesso negado.`
- **Objeto** de outra organização, inexistente ou fora do escopo de unidade: `404 Recurso não encontrado.`, com a mesma mensagem nos três casos. A resposta nunca revela se o registro existe em outra organização.
- As flags de permissão devolvidas ao frontend (`permissions.*`) servem só para exibir botões; o backend verifica de novo.

## 4. Escritas: validação, confirmação e idempotência

Toda escrita passa por três camadas:

1. **Formato** (`api/views.py`): tipos, tamanhos, UUIDs e campos obrigatórios. Campo desconhecido em `PATCH` é rejeitado.
2. **Regra de domínio** (`services.py`): tenant, permissão, estado atual, `full_clean()` e restrições do banco, sob `transaction.atomic`.
3. **Banco**: restrições únicas e de verificação; violação concorrente vira `409`.

Confirmação explícita (RF-21): operações que mudam estado operacional ou situação exigem `"confirmed": true` no corpo. Hoje: incorporação, saída, devolução, condição e estorno do item; situação de pessoa, vínculo, unidade, local e tipo; suspensão, reativação, revogação e encerramento de sessões de conta; revogação de concessão.

Estratégia de idempotência por tipo de escrita:

| Escrita | Estratégia | Repetição da mesma requisição | Mesma chave com outro conteúdo |
|---|---|---|---|
| saída, devolução, condição do item | `idempotency_key` (UUID) obrigatório, único por organização no banco | `200` com a movimentação original e `"created": false` | `409` |
| estorno | `idempotency_key` obrigatório; no máximo um estorno por movimentação (restrição única) | `200` com o estorno original | `409` |
| incorporação de item | chave natural: número de série e patrimônio únicos na organização (RN-02), ao menos um obrigatório | `400` (número já usado) | — |
| unidade, local de guarda, tipo | chave natural: código ou nome único na organização | `400` | — |
| concessão de papel | sem chave; repetir cria outra concessão equivalente, visível e revogável | — | — |
| situação de pessoa, vínculo e conta | transição de estado: repetir a mesma transição falha porque o estado já mudou | `409` com mensagem de estado (“já está nessa situação”) | — |
| cadastro de pessoa | sem chave. A duplicidade é barrada por CPF único na organização, quando informado | pode criar outro registro se o CPF não for informado; o frontend desabilita o botão durante o envio | — |
| cadastro de vínculo e de conta | chave natural única: matrícula na organização; uma conta não revogada por pessoa | `400` (matrícula) ou `409` (conta) | — |

O cliente gera a `idempotency_key` **ao abrir** a ação e a reutiliza em qualquer reenvio da mesma ação; só uma nova ação gera nova chave.

## 5. Respostas

Sucesso:

```json
{ "success": true, "data": { }, "meta": { } }
```

`meta` só aparece em coleções paginadas. Criação devolve `201`; repetição idempotente e demais escritas, `200`.

Erro:

```json
{
  "success": false,
  "error": "Dados inválidos.",
  "details": { "recipient_id": ["Informe um UUID válido."] },
  "correlation_id": "4f0c..."
}
```

- `details` aparece só em `400` de validação: chave = campo; `non_field_errors` para regras sem campo.
- `correlation_id` é o mesmo valor do cabeçalho `X-Request-ID` e liga a resposta ao log técnico e à auditoria.
- Mensagens nunca incluem CPF, senha, token, dado de outra organização nem detalhe técnico.
- Escrita recusada com `403`, `404` ou `409` gera `AuditEvent` `api.<rota>` com `result` `denied`, `not_found` ou `conflict`, ator e correlação.

| Status | Quando | `error` |
|---|---|---|
| 400 | formato, validação ou regra sem conflito de estado | `Dados inválidos.`, `JSON inválido.` ou mensagem da regra |
| 401 | sem sessão ou conta inativa | `Autenticação necessária.` |
| 403 | sem permissão na coleção, ou CSRF inválido | `Acesso negado.` ou mensagem de segurança expirada |
| 404 | objeto não visível ou rota inexistente | `Recurso não encontrado.` |
| 405 | método não suportado (com cabeçalho `Allow`) | `Método não permitido.` |
| 409 | conflito com o estado atual, chave de idempotência reutilizada ou corrida em restrição única | mensagem do conflito |
| 500 | erro inesperado; detalhe só no log técnico | `Erro interno. Informe o código de correlação ao suporte.` |

## 6. Paginação

Coleções que crescem com o cadastro (`/items/`, `/people/`) aceitam `limit` (padrão 100, máximo 500) e `offset` (padrão 0). Fora desses limites: `400`.

```json
{ "success": true, "data": [ ], "meta": { "count": 742, "limit": 100, "offset": 0 } }
```

`count` é o total visível para a conta, já filtrado por organização e escopo. Listas auxiliares pequenas (`/units/`, `/items/<id>/recipients/`) não são paginadas. `/people/` aceita `q` para busca por nome, nome funcional ou matrícula.

## 7. Recursos atuais

Permissões da [matriz 0002](decisoes/0002-papeis-e-escopos.md) (versão 1.4.0). “Unidade” significa a unidade de lotação do objeto; concessão de organização alcança todas.

| Método e rota | Permissão | Uso |
|---|---|---|
| `GET /session/` | autenticado | conta, organização, flags de interface (`can_manage_identity`, `can_manage_catalog`, `can_create_item`, `can_view_items`, `can_view_audit`) e `item_scope` (`all_units` ou a lista de unidades com `item.view`, só da própria organização), usado para nomear o escopo consultado nas telas |
| `POST /session/logout/` | autenticado | encerra a sessão |
| `GET /items/` | `item.view` no escopo | itens visíveis, paginado; `?holder=<pessoa>` dá a posse atual (RF-51); aceita `q`, `availability`, `condition`, `unit`, `type` |
| `POST /items/` | `item.create` na unidade | incorporação (T01) com condição declarada |
| `GET /items/<id>/` | `item.view` na unidade | situação atual, identificadores e flags de ação |
| `GET /items/<id>/events/` | `item.view` na unidade | histórico cronológico e paginado, somente leitura, com marca de estornado (RF-15, RF-53) |
| `POST /movements/<id>/reverse/` | `movement.reverse` na unidade | estorno da movimentação mais recente em vigor, com motivo (SIGAB-034); `reversible_movement_id` no detalhe do item indica qual |
| `GET /search/` | `item.view` (itens) e `person.view_minimal` (pessoas) | busca única (RF-50), [detalhes](busca.md) |
| `GET /activity/` | `item.view` no escopo | feed de eventos de domínio, do mais recente ao mais antigo; filtros `person`, `item`, `action`, `from`, `to` (RF-61). Não substitui a auditoria |
| `GET /audit/` | `audit.view` na organização | trilha de auditoria com `sequence`, filtros `action`, `result`, `actor`, `object_id`, `from`, `to`; somente leitura |
| `GET /items/<id>/recipients/` | `movement.checkout` na unidade | pessoas ativas com vínculo ativo |
| `POST /items/<id>/checkout/` | `movement.checkout` | saída (T02), [contrato](contratos/saida-individual.md) |
| `POST /items/<id>/return/` | `movement.return` | devolução (T03/T04), [contrato](contratos/devolucao-individual.md) |
| `POST /items/<id>/condition/` | `item.condition.set` | declarar inapto ou liberar (T05/T06) |
| `GET`, `POST /people/` | `identity.manage` | listar e cadastrar pessoa, sem conta; o `POST` aceita `registration`, `main_unit_id` e `rank` opcionais para criar o primeiro vínculo na mesma transação |
| `GET`, `PATCH /people/<id>/` | `identity.manage` | ficha, contas e concessões; edição cadastral |
| `POST /people/<id>/status/` | `identity.manage` | desativar ou reativar pessoa |
| `POST /people/<id>/memberships/` | `identity.manage` | novo vínculo |
| `POST /memberships/<id>/status/` | `identity.manage` | desativar ou reativar vínculo |
| `POST /people/<id>/account/` | `identity.manage` | criar conta de acesso |
| `POST /accounts/<id>/suspend/`, `/reactivate/`, `/revoke/`, `/end-sessions/` | `identity.manage` | ciclo de vida e sessões da conta |
| `POST /accounts/<id>/grants/` | `identity.manage` | conceder papel em escopo e vigência, com motivo (RF-04) |
| `POST /grants/<id>/revoke/` | `identity.manage` | revogar concessão, com motivo |
| `GET /roles/` | `identity.manage` | papéis da organização com permissões e escopos permitidos |
| `GET /units/` | `identity.manage`, `catalog.manage` ou `item.create` | unidades com locais de guarda |
| `POST /units/`, `PATCH /units/<id>/`, `POST /units/<id>/status/` | `catalog.manage` | cadastro, nome e situação da unidade |
| `POST /units/<id>/locations/`, `POST /locations/<id>/status/` | `catalog.manage` | locais de guarda |
| `GET /equipment-types/` | `catalog.manage` ou `item.create` | catálogo de tipos |
| `POST /equipment-types/`, `PATCH /equipment-types/<id>/`, `POST /equipment-types/<id>/status/` | `catalog.manage` | cadastro, nome e descrição, situação; a classificação nunca muda (RN-03) |

### Retirada, devolução e biometria (SIGAB-082, 085 e 086)

| Método e rota | Permissão | Uso |
|---|---|---|
| `GET /overview/` | `item.view` | página Início: totais, pendências e últimas retiradas e devoluções |
| `GET /stock/summary/`, `GET /stock/entries/` | `item.view` | acervo sem registro: posições e histórico do tipo |
| `GET /return-batches/options/` | `movement.return` | pessoas com posse e, com `?person=`, os materiais; marca `awaiting_approval` |
| `POST /return-batches/` | `movement.return` | devolução em lote atômica e idempotente; exige `face_verification_id` quando a biometria é obrigatória |
| `POST /service-batches/` | `movement.checkout` | retirada; exige `face_verification_id` quando a biometria é obrigatória |
| `GET /movements/`, `GET /movements/options/` | `item.view` | registro de retiradas, devoluções e consumos, com método de identificação |
| `GET /biometrics/` | `biometric.manage` | pessoas ativas e se a biometria está cadastrada |
| `GET`, `POST /people/<id>/biometric/` | `biometric.manage` | situação e cadastro (multipart `image`, `confirmed=true`) |
| `POST /people/<id>/biometric/delete/` | `biometric.manage` | exclusão definitiva com motivo |
| `GET /counter/identify/?registration=` ou `?person=<id>` | `movement.checkout` ou `movement.return` | entrada e saída no balcão: busca por matrícula **exata** com vínculo ativo (ou pelo id, para reabrir a pessoa já identificada); devolve só `id`, nome, matrícula, `biometric_enrolled`, `open_possessions` e as operações permitidas; matrícula parcial, inativa ou de outra organização: `404` |
| `POST /face-verifications/<id>/cancel/` | operador que fez a verificação | desiste da operação depois da identidade confirmada (`confirmed: true`): a verificação deixa de valer; já usada: `409`; de outro operador ou organização: `404` |
| `POST /face-verifications/` | `movement.checkout` ou `movement.return` | verificação 1:1 (multipart `person_id`, `operation`, `operator_confirmed=true`, `image`); devolve só `id`, `result` e `expires_at` |
| `GET`, `POST /identity-exceptions/` | operador do balcão ou `movement.exception.approve` | termos visíveis; geração do termo com a operação solicitada |
| `GET /identity-exceptions/<id>/` | quem registrou ou quem pode aprovar | termo para impressão |
| `POST /identity-exceptions/<id>/signed/`, `/cancel/` | quem registrou | termo assinado recolhido; cancelamento com motivo |
| `POST /identity-exceptions/<id>/decision/` | `movement.exception.approve` em todas as unidades, e diferente de quem registrou | aprova (executa a operação) ou recusa com motivo |

Captura de rosto usa `multipart/form-data` (JPEG ou PNG, até 2 MB). Sem motor ou chave configurados, a resposta é 503. Fora da contingência em papel, `POST /items/<id>/checkout/` e `/return/` recusam a operação quando a biometria é obrigatória.

Saída e devolução aceitam o objeto opcional `contingency` (`occurred_at` ISO 8601 com fuso e `paper_reference` de até 64 caracteres) para lançar fato do livro de contingência (SIGAB-046, ADR 0004). Os eventos do histórico e do feed trazem `movement.origin`, `movement.paper_reference` e `movement.recorded_at`; `occurred_at` é o instante do fato. Divergência com o estado atual responde 409 com mensagem iniciada por "Divergência".

Toda rota nova precisa de caso em `backend/sigab/tests/test_isolation.py`; um teste falha quando alguma rota não tem.

## 8. Dados pessoais na API

- CPF é **somente escrita**: a resposta traz apenas `cpf_masked` (`***.***.***-09`). Erro de CPF não ecoa o valor enviado.
- Telefone e CPF só aparecem nos recursos de `/people/`, que exigem `identity.manage`. Listas operacionais (destinatários, responsável do item) trazem só `id` e nome.
- Senha nunca é devolvida, nem em erro de validação.

## Operação quantitativa — revisão de 10/11/2026

- `GET /api/v1/stock/options/`: tipos quantitativos ativos e unidades/locais ativos no escopo da conta. Cada unidade informa `can_receive`; entrada exige `inventory.adjust.approve` naquela unidade.
- `GET /api/v1/stock/loans/`: pendências quantitativas abertas, com pessoa, tipo, unidade, local, quantidade restante e `can_settle`. A ação exige `movement.return` na unidade.
- `GET /api/v1/stock/positions/`: leitura nas unidades com `item.view`, `movement.return` ou `inventory.adjust.approve`; sem concessão, responde 403.

Organização vem da conta autenticada; flags da interface não substituem autorização no serviço. Escritas existentes de entrada e liquidação continuam exigindo confirmação e chave de idempotência. A tela de estoque expõe somente devolução apta; fluxo quantitativo inapto permanece pendente. Consulte a [entrega 074–078](validacao/tarefas-074-a-078.md).
