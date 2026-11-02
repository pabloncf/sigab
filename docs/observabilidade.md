# Observabilidade mínima

- Tarefa: SIGAB-018
- Revisão: 2026-11-02, conferida com `backend/sigab/observability.py` e `backend/sigab/middleware.py`
- Base: [ADR 0006](adr/0006-eventos-auditoria-e-estornos.md) (separação entre log técnico, evento de domínio e auditoria), [modelo de ameaças](modelo-de-ameacas.md)
- Requisitos: RF-60 e RNF-04

## Separação

O log técnico responde “o que aconteceu no software” e vai para a saída padrão do processo. Ele **não** é auditoria: não é imutável, não tem retenção definida e pode ser descartado. Fatos de negócio ficam em `MovementEvent` e `AuditEvent`, no banco (ADR 0006). O identificador de correlação liga os três registros.

## Identificador de requisição

- O middleware `CorrelationIdMiddleware` aceita `X-Request-ID` do cliente somente se tiver de 1 a 64 caracteres em `[A-Za-z0-9._-]`; caso contrário gera um UUID. Isso impede quebra de linha e injeção no log.
- O valor fica em `request.correlation_id`, volta no cabeçalho de resposta `X-Request-ID`, no campo `correlation_id` de toda resposta de erro da API e no `AuditEvent.correlation_id`.
- O identificador serve para rastrear, nunca para autorizar.

## Formato do log

Uma linha JSON por registro (`sigab.observability.JsonFormatter`):

```json
{"timestamp": "2026-11-02T16:40:41.743900+00:00", "level": "INFO", "logger": "sigab.request", "message": "request", "correlation_id": "req-1", "method": "GET", "path": "/api/v1/items/", "status": 200, "duration_ms": 1.2, "account_id": "…", "organization_id": "…"}
```

- Uma linha por requisição (`sigab.request`): método, caminho **sem query string**, status, duração, UUID da conta e da organização quando autenticado.
- Campos extras só entram se estiverem na lista permitida (`ALLOWED_EXTRA_FIELDS`). Objetos de requisição, corpo, cabeçalhos, cookies e instâncias de modelo nunca são serializados.
- Exceções incluem `error_type` e `traceback`.
- Nível por `DJANGO_LOG_LEVEL` (padrão `INFO`).

## O que nunca é registrado

| Dado | Proteção |
|---|---|
| senha, token, cookie de sessão, CSRF | corpo e cabeçalhos não são registrados; mensagens e tracebacks passam por `redact()`, que mascara atribuições como `password=…`, `token: …` |
| CPF | não é registrado; `redact()` mascara qualquer sequência no formato de CPF, com ou sem pontuação, em mensagens e tracebacks |
| termos de busca | a query string fica fora do log |
| dados de pessoa | o log usa só UUIDs de conta e organização |

O mascaramento é uma segunda linha de defesa; a primeira é não incluir esses dados nas mensagens.

## Tratamento centralizado de erros

| Origem | Resposta | Log |
|---|---|---|
| erro de domínio na API (`ValidationError`, `ConflictError`, permissão, não encontrado) | JSON com status 400/403/404/409 ([convenções da API](api.md)) | linha de requisição; `django.request` registra 4xx como aviso |
| CSRF inválido em `/api/` | JSON 403 (`CSRF_FAILURE_VIEW`) | idem |
| rota inexistente em `/api/` | JSON 404 | idem |
| exceção inesperada | `/api/`: JSON 500 com `correlation_id` e mensagem genérica (`handler500`); demais rotas: página 500 padrão do Django | `django.request` em nível `ERROR`, com traceback mascarado e o mesmo `correlation_id` |

Com `DEBUG=true` (desenvolvimento), o Django mostra a página de depuração no lugar do `handler500` fora da API; por isso `DEBUG` nunca pode estar ativo em produção (C-03 do modelo de ameaças).

## Testes

`backend/sigab/tests/test_observability.py` e `test_api_conventions.py`: mascaramento de CPF e segredos, campos permitidos, traceback mascarado, correlação e ausência de query string na linha de requisição, rejeição de `X-Request-ID` inseguro, login sem senha no log, erro 500 em JSON sem detalhe técnico.

## Fora do escopo

Métricas, rastreamento distribuído, agregação e retenção de logs dependem da implantação (ADR 0005) e não exigem novos serviços nesta fase.
