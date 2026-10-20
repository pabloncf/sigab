# ADR 0005 — API Django e frontend React separados

Status: aceito para a base técnica, 2026-10-19.

## Contexto

O ADR 0001 escolheu templates Django para a primeira fatia, evitando uma SPA antes de existir necessidade demonstrada. A evolução solicitada em 2026-10-19 requer agora uma fronteira explícita entre backend e frontend e uma base React, sem mover regras de domínio ou controles de segurança para o navegador.

## Decisão

O backend permanece em Django, fica isolado fisicamente em `backend/` e expõe uma API versionada em `/api/v1/`. O frontend operacional fica em `frontend/`, usa React, TypeScript e Vite e acessa dados somente por essa API.

- Django continua responsável por persistência, tenant, autorização, validação, transações, auditoria e idempotência.
- A autenticação continua baseada na sessão Django e em cookie `HttpOnly`.
- Operações de escrita continuam protegidas por CSRF e exigem confirmação explícita e chave de idempotência.
- Backend e frontend são servidos na mesma origem lógica. Em desenvolvimento, o proxy do Vite mantém essa propriedade.
- Os templates atuais permanecem disponíveis como fallback durante a migração incremental; não recebem novas regras de domínio.
- A API usa contratos JSON explícitos e não expõe modelos Django diretamente.

## Consequências

Passam a existir dois pipelines de desenvolvimento e build: `uv` para o backend e `bun` para o frontend. A implantação deve servir os artefatos estáticos de `frontend/dist/` e encaminhar rotas de API e autenticação ao Django.

Não habilitamos CORS nesta etapa. Uma implantação em origens diferentes exigirá uma decisão adicional sobre origens confiáveis, cookies `SameSite`, CSRF e encerramento de sessão.

O ADR 0001 continua válido para a base histórica e para o fallback server-side, mas sua decisão de frontend principal é substituída por este ADR.
