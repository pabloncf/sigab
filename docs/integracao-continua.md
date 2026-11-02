# Integração contínua

- Tarefa: SIGAB-017
- Revisão: 2026-11-02
- Pipeline: [.github/workflows/ci.yml](../.github/workflows/ci.yml), em todo `push` e `pull_request`

## Etapas

| Job | Etapa | Falha quando |
|---|---|---|
| backend | `uv sync --locked --dev` | `uv.lock` não corresponde ao `pyproject.toml` |
| backend | `ruff format --check` | código fora do formato |
| backend | `ruff check` | erro de lint, import não usado, regra Django violada |
| backend | `manage.py check` | configuração ou modelo inválido |
| backend | `makemigrations --check --dry-run` | modelo alterado sem migração |
| backend | `migrate` → `migrate sigab zero` → `migrate` | migração que não aplica ou não reverte em banco vazio |
| backend | `pytest` sobre PostgreSQL 17 | qualquer teste, inclusive concorrência real |
| frontend | `bun install --frozen-lockfile` | `bun.lock` desatualizado |
| frontend | `bun run typecheck` | erro de tipo |
| frontend | `bun run build` | build de produção quebrado |

## Reprodutibilidade

- Python fixado em `backend/.python-version` (3.12); dependências travadas em `backend/uv.lock` e `frontend/bun.lock`, instaladas em modo travado.
- Banco efêmero `postgres:17` como serviço do job, com verificação de prontidão.
- Os mesmos comandos rodam localmente (README, “Testes e verificação”); o resultado local e o do CI vêm dos mesmos arquivos de trava.

## Segredos

O pipeline não usa segredos. `DJANGO_SECRET_KEY: ci-only-key` e a senha do banco efêmero são valores descartáveis, válidos só dentro do job. O token do GitHub é somente leitura (`permissions: contents: read`). Credenciais reais nunca entram no repositório nem no workflow.

## Pendências

- Testes e lint de comportamento do frontend ([ADR 0005](adr/0005-api-django-e-frontend-react.md#pendências)).
- `manage.py check --deploy` com configuração de produção, junto com a correção das lacunas C-02 e C-03 do [modelo de ameaças](modelo-de-ameacas.md).
- Proteção de branch exigindo o CI verde antes do merge: configuração do repositório, fora do código.
