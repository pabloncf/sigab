# ADR 0005 — API Django e frontend React separados

Status: aceito para a base técnica, 2026-10-19. Revisado em 2026-10-31 (SIGAB-010) para registrar alternativas, banco, testes, implantação e comandos locais.

Este é o ADR da stack do SIGAB. Ele substitui a decisão de frontend principal do [ADR 0001](0001-stack-e-frontend.md), que continua válido para a base histórica e para o fallback server-side.

## Contexto

O ADR 0001 escolheu templates Django para a primeira fatia, evitando uma SPA antes de existir necessidade demonstrada. A evolução solicitada em 2026-10-19 requer agora uma fronteira explícita entre backend e frontend e uma base React, sem mover regras de domínio ou controles de segurança para o navegador.

Restrições da SIGAB-010: Python com Django no backend é obrigatório; o frontend é livre; componentes distribuídos e complexidade sem necessidade comprovada devem ser evitados.

## Decisão

O backend permanece em Django, fica isolado fisicamente em `backend/` e expõe uma API versionada em `/api/v1/`. O frontend operacional fica em `frontend/`, usa React, TypeScript e Vite e acessa dados somente por essa API.

- Django continua responsável por persistência, tenant, autorização, validação, transações, auditoria e idempotência.
- A autenticação continua baseada na sessão Django e em cookie `HttpOnly`.
- Operações de escrita continuam protegidas por CSRF e exigem confirmação explícita e chave de idempotência.
- Backend e frontend são servidos na mesma origem lógica. Em desenvolvimento, o proxy do Vite mantém essa propriedade.
- Os templates atuais permanecem disponíveis como fallback durante a migração incremental; não recebem novas regras de domínio.
- A API usa contratos JSON explícitos e não expõe modelos Django diretamente.

| Camada | Escolha |
|---|---|
| Backend | Python 3.12+, Django 5.2 LTS, dependências por `uv` (`backend/pyproject.toml`, `uv.lock`) |
| Banco | PostgreSQL 17 em produção e CI; SQLite só em desenvolvimento simples |
| Frontend | React 19, TypeScript, Vite; dependências por `bun` (`frontend/package.json`, `bun.lock`) |
| Fallback | templates Django em `backend/templates/` |

## Alternativas de frontend

Critérios: manter regras e segurança no backend; servir tudo da mesma origem com sessão e CSRF; não exigir servidor adicional em produção; criar uma fronteira de API explícita e testável; ter manutenção previsível.

| Alternativa | Fronteira de API | Servidor extra em produção | Avaliação |
|---|---|---|---|
| Templates Django (ADR 0001) | não | não | mais simples e já existente; não atende à fronteira explícita pedida em 2026-10-19. Mantido como fallback |
| Templates Django + HTMX | não; o servidor devolve fragmentos HTML | não | baixa complexidade, mas acopla tela e view e não cria contrato JSON reutilizável |
| **React + TypeScript + Vite** | sim | não; o build gera arquivos estáticos | **escolhida**: contrato JSON tipado no cliente, ecossistema amplo, build estático servido pelo mesmo proxy do Django |
| Vue ou Svelte + Vite | sim | não | tecnicamente equivalentes para este escopo; sem vantagem que justificasse divergir do pedido de React |
| Next.js ou outro meta-framework com SSR | sim | **sim** (processo Node) | descartado: adiciona um serviço em produção e uma segunda camada de servidor sem necessidade comprovada |

A escolha não depende de nenhum recurso exclusivo do React. O custo aceito é manter dois pipelines e um contrato de API; o ganho é a fronteira explícita, que impede regra de domínio no navegador e permite testar a API isoladamente.

## Banco de dados

- PostgreSQL 17 é o banco de produção e do CI. Concorrência, `select_for_update`, atualização condicional e restrições únicas de idempotência só são validadas nele.
- SQLite é aceito apenas para desenvolvimento simples (`DATABASE_URL` ausente) e não valida concorrência.
- Conexão por `DATABASE_URL`; driver `psycopg` 3.
- Mudanças de modelo exigem nova migração; o CI roda `makemigrations --check`.
- Backup, RPO ≤ 15 min e RTO ≤ 4 h seguem o [ADR 0004](0004-conectividade-e-contingencia.md).

## Testes

| Nível | Ferramenta | Onde roda |
|---|---|---|
| Regra pura, serviço, tenant, autorização, restrição | `pytest` + `pytest-django` | local (SQLite) e CI (PostgreSQL) |
| Fluxo HTTP e API | cliente de teste do Django | idem |
| Concorrência | `pytest` com conexões independentes | PostgreSQL (CI ou `compose.yaml` local) |
| Estilo e lint do backend | `ruff format --check`, `ruff check` | local e CI |
| Migrações | `makemigrations --check --dry-run` | local e CI |
| Frontend | `tsc -b` (typecheck) e `vite build` | local e CI |

O frontend ainda não tem testes de comportamento nem lint (pendência abaixo). Enquanto isso, as regras de segurança e domínio são cobertas pelos testes de API no backend, que é onde elas vivem.

## Implantação

Topologia: um proxy HTTP com TLS, um processo Django e um banco PostgreSQL. Não há fila, cache distribuído nem servidor Node em produção.

- O proxy serve os arquivos de `frontend/dist/` e encaminha `/api/`, `/entrar/`, `/sair/` e `/admin/` ao Django no mesmo domínio.
- CORS não é habilitado. Separar domínios exige decisão adicional sobre origens confiáveis, cookies `SameSite`, CSRF e encerramento de sessão.
- Variáveis obrigatórias fora do ambiente local: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`, `DJANGO_ALLOWED_HOSTS`, `DATABASE_URL`.
- Ordem de publicação: backup do banco, `migrate`, início da nova versão do Django, troca dos arquivos estáticos.
- O servidor de aplicação de produção (WSGI) e a forma de empacotamento ainda não foram escolhidos (pendência abaixo). `runserver` não é aceito em produção.

## Comandos locais

Backend:

```bash
cd backend
uv sync --dev
uv run python manage.py migrate
uv run python manage.py runserver
```

Frontend, em outro terminal (acesso em `http://localhost:5173`):

```bash
cd frontend
bun install
bun run dev
```

Verificação antes de concluir uma alteração (mesmos passos do CI):

```bash
cd backend
uv run ruff format --check config sigab manage.py
uv run ruff check config sigab manage.py
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run pytest -q
cd ../frontend && bun run typecheck && bun run build
```

Suíte com PostgreSQL, obrigatória para transação, bloqueio e idempotência:

```bash
docker compose up -d db
cd backend
DATABASE_URL=postgresql://sigab:local-only@127.0.0.1:5432/sigab uv run pytest -q
cd ..
docker compose down
```

## Consequências

- Passam a existir dois pipelines de desenvolvimento e build: `uv` para o backend e `bun` para o frontend, ambos com lockfile e verificados no CI.
- Toda tela nova depende de um endpoint em `/api/v1/` com contrato explícito; o teste de acesso cruzado entre organizações fica na API.
- O frontend pode ser trocado sem tocar em regras de domínio, porque nenhuma regra vive nele.
- A implantação continua sendo um processo web e um banco, mais arquivos estáticos.
- Offline não é suportado ([ADR 0004](0004-conectividade-e-contingencia.md)).

## Pendências

- **Testes e lint do frontend.** Escolher a ferramenta (sugestão: Vitest + Testing Library, e ESLint) na primeira tarefa que adicionar comportamento relevante ao frontend, e incluí-la no CI.
- **Servidor de aplicação e empacotamento.** Escolher o servidor WSGI (por exemplo, gunicorn), o proxy e a forma de entrega (imagem de contêiner ou pacote) antes da primeira implantação fora do ambiente local.
