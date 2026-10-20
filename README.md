# SIGAB

Primeira base executável do Sistema Integrado de Gestão de Acervo Bélico. Esta entrega cobre somente item físico individual: fundação multi-organização, identidade separada de conta, autorização explícita, incorporação, saída, devolução e histórico/auditoria.

## Estrutura

```text
backend/   Django, API, modelos, templates legados e testes Python
frontend/  React, TypeScript, estilos e build Vite
docs/      decisões e documentação do produto
```

## Executar localmente

Requisitos: Python 3.12+ e [uv](https://docs.astral.sh/uv/). PostgreSQL 17 é recomendado; SQLite serve para desenvolvimento, exceto o teste de concorrência real.

```bash
cd backend
uv sync --dev
uv run python manage.py migrate
uv run python manage.py bootstrap_sigab \
  --organization "Organização de demonstração" \
  --username admin --email admin@example.invalid
uv run python manage.py runserver
```

Acesse `/admin/` para o cadastro administrativo inicial de unidade, local, pessoa, vínculo, papel, tipo e item. Use `/` para o fluxo operacional de consulta, saída, devolução e alteração de condição (declarar inapto ou liberar como apto). O Django Admin é apenas o mecanismo controlado de implantação/cadastro inicial, não a interface operacional definitiva.

## Frontend React

O backend Django expõe a API versionada em `/api/v1/`; regras de domínio, tenant, autorização, sessão, CSRF e idempotência permanecem no servidor. A nova interface fica em `frontend/`:

```bash
cd frontend
bun install
bun run dev
```

Acesse `http://localhost:5173` com o Django em `http://127.0.0.1:8000`. Consulte `frontend/README.md` para build e implantação. Os templates Django permanecem como fallback durante a migração incremental.

Contas adicionais são criadas separadamente de Pessoa e Vínculo, sem expor gestão de superusuário ao administrador do tenant:

```bash
cd backend
uv run python manage.py create_sigab_account \
  --organization-id UUID_DA_ORGANIZACAO --person-id UUID_DA_PESSOA \
  --username usuario --email usuario@example.invalid
```

Para PostgreSQL local:

```bash
docker compose up -d db
cd backend
export DATABASE_URL=postgresql://sigab:local-only@127.0.0.1:5432/sigab
uv run python manage.py migrate
```

## Qualidade

```bash
cd backend
uv run ruff format --check config sigab manage.py
uv run ruff check config sigab manage.py
uv run python manage.py makemigrations --check --dry-run
uv run pytest -q
```

O CI repete esses comandos sobre PostgreSQL e executa o teste com duas saídas concorrentes. Dados de teste são sintéticos. Não use a chave de desenvolvimento nem a senha do Compose em produção.

## Graphify

O Graphify está configurado localmente para Claude Code e Codex. O grafo inicial, gerado somente por análise AST local, fica em `graphify-out/`.

```bash
graphify query "item checkout authorization"
graphify explain "checkout_item"
graphify path "checkout" "AuditEvent"
graphify update .
```

Depois de mudanças no código, execute `graphify update .`. A lista de arquivos ignorados está em `.graphifyignore`.

## Operação e backup

- Banco: faça backup consistente com `pg_dump --format=custom` e proteja o arquivo fora do host; restaure periodicamente em ambiente isolado com `pg_restore`. As metas definidas no [ADR 0004](docs/adr/0004-conectividade-e-contingencia.md) são RPO ≤ 15 min, o que exige arquivamento contínuo de WAL/PITR além do dump, e RTO ≤ 4 h. Retenção e criptografia ainda dependem de decisão formal.
- Migrações: em `backend/`, aplique `uv run python manage.py migrate` antes de iniciar a nova versão; mantenha backup anterior à implantação.
- Timestamps são persistidos em UTC; a organização carrega seu fuso para apresentação futura.
- Configure `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`, `DJANGO_ALLOWED_HOSTS` e TLS no proxy em qualquer ambiente não local.

Consulte a [decisão do segmento inicial](docs/decisoes/0001-segmento-inicial.md), a [nota regulatória preliminar](docs/notas-regulatorias/0001-guardas-municipais.md), as [decisões pendentes](docs/decisoes-pendentes.md), o [modelo de domínio](docs/modelo-de-dominio.md) e a documentação de [segurança](docs/seguranca-e-privacidade.md). O backlog preparado para importação no Jira está em [tarefas.csv](docs/tarefas/tarefas-15-10-26/tarefas.csv).

