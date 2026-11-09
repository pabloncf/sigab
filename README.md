# SIGAB

Primeira base executável do Sistema Integrado de Gestão de Acervo Bélico. Esta entrega cobre somente item físico individual: fundação multi-organização, identidade separada de conta, autorização explícita, incorporação, saída, devolução e histórico/auditoria.

## Estrutura

```text
backend/   Django, API, modelos, templates legados e testes Python
frontend/  React, TypeScript, estilos e build Vite
docs/      decisões e documentação do produto
```

## Rodar com Docker (desenvolvimento)

Só exige Docker. Sobe PostgreSQL 17, Django e Vite com o código montado: alterações no backend reiniciam o `runserver` e no frontend recarregam o navegador.

```bash
docker compose up -d --build
docker compose exec backend python manage.py bootstrap_sigab \
  --organization "Organização de demonstração" \
  --username admin --email admin@example.invalid
```

Para ver o sistema já povoado, gere dados sintéticos de demonstração (só com `DEBUG` ligado; roda uma vez por banco):

```bash
docker compose exec backend python manage.py seed_demo
```

Cria os batalhões “Demonstração Alfa” e “Bravo” com unidades, reservas, tipos, pessoas, itens e movimentações em todos os estados (em posse, devolvido, inapto, liberado, estornado e lançado em contingência). Para recomeçar do zero, use `docker compose down -v`.

Credenciais de teste (somente para o banco local de desenvolvimento):

| Login | Senha | Organização | Papéis |
|---|---|---|---|
| `alfa.admin` | `Demo-sigab-2026` | Batalhão Demonstração Alfa | Administrador de acesso e Gestor de acervo (organização) |
| `alfa.operador` | `Demo-sigab-2026` | Batalhão Demonstração Alfa | Operador de reserva (1ª e 2ª Companhia) |
| `bravo.admin` | `Demo-sigab-2026` | Batalhão Demonstração Bravo | Administrador de acesso e Gestor de acervo (organização) |
| `bravo.operador` | `Demo-sigab-2026` | Batalhão Demonstração Bravo | Operador de reserva (Sede) |

Use as contas `alfa.*` e `bravo.*` para conferir o isolamento: uma organização não enxerga os dados da outra. A senha pode ser trocada com `seed_demo --password <senha>`.

Acesse `http://localhost:5173`. As migrações rodam a cada início do backend. Comandos úteis:

```bash
docker compose logs -f backend frontend          # acompanhar
docker compose exec backend uv run --no-sync pytest -q   # testes no PostgreSQL do container
docker compose exec backend python manage.py makemigrations
docker compose down                               # parar (os dados ficam no volume)
docker compose down -v                            # parar e apagar o banco local
```

Ao mudar `pyproject.toml`/`uv.lock` ou `package.json`/`bun.lock`, reconstrua com `docker compose up -d --build`. A configuração é só para desenvolvimento local (chave e senha inseguras, `DEBUG` ligado); imagem de produção é tarefa de infraestrutura e ainda não existe. A porta 5432 continua publicada, então `docker compose up -d db` segue servindo a suíte local descrita em [Testes e verificação](#testes-e-verificação).

## Primeiros passos (sem Docker)

Pré-requisitos:

- [uv](https://docs.astral.sh/uv/) (instala o Python 3.12 fixado em `backend/.python-version`, se faltar);
- [Bun](https://bun.sh/) para o frontend;
- Docker, opcional, para rodar a suíte com PostgreSQL 17. Sem ele, o backend usa SQLite em `backend/db.sqlite3`, que não valida concorrência real.

### 1. Backend

```bash
cd backend
uv sync --dev
uv run python manage.py migrate
uv run python manage.py bootstrap_sigab \
  --organization "Organização de demonstração" \
  --username admin --email admin@example.invalid
uv run python manage.py runserver
```

O `bootstrap_sigab` pede a senha inicial sem eco e cria a organização e a primeira conta, com o papel “Administrador inicial” (inclui `identity.manage`). Sem variáveis de ambiente, o Django roda em modo de desenvolvimento com chave insegura; não use essa configuração fora da máquina local.

### 2. Frontend

Em outro terminal, com o backend ativo em `127.0.0.1:8000`:

```bash
cd frontend
bun install
bun run dev
```

Acesse `http://localhost:5173` e entre com a conta criada no passo 1. O Vite encaminha `/api`, `/entrar`, `/sair` e `/admin` ao Django na mesma origem.

### 3. Dados iniciais

O primeiro administrador recebe os papéis “Administrador de acesso” e “Gestor de acervo” da [matriz de papéis](docs/decisoes/0002-papeis-e-escopos.md). Com ele:

1. **Cadastros:** crie unidades, locais de guarda e tipos de equipamento.
2. **Acervo → Incorporar item:** registre os itens individuais.
3. **Pessoas:** cadastre pessoas e vínculos; crie a conta de quem vai operar e conceda o papel “Operador de reserva” na unidade. Ninguém concede papel a si mesmo, por isso a saída e a devolução são feitas pela conta do operador.
4. **Acervo:** com a conta do operador, registre saída, devolução e condição.

O Django Admin (`http://127.0.0.1:8000/admin/`) continua disponível como mecanismo administrativo transitório, e os templates Django em `http://127.0.0.1:8000/` como fallback.

Para suspender ou reativar uma organização pelo plano de controle:

```bash
cd backend
uv run python manage.py set_organization_status \
  --organization-id UUID_DA_ORGANIZACAO --status inactive --reason "Motivo"
```

Também há um comando para criar conta sem interface (a senha é pedida sem eco):

```bash
cd backend
uv run python manage.py create_sigab_account \
  --organization-id UUID_DA_ORGANIZACAO --person-id UUID_DA_PESSOA \
  --username usuario --email usuario@example.invalid
```

## Testes e verificação

Os mesmos passos rodam no CI ([integração contínua](docs/integracao-continua.md)). Antes de concluir uma alteração:

```bash
cd backend
uv run ruff format --check config sigab manage.py
uv run ruff check config sigab manage.py
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run pytest -q
cd ../frontend && bun run typecheck && bun run build
```

Com PostgreSQL, obrigatório para mudanças de transação, bloqueio ou idempotência:

```bash
docker compose up -d db
cd backend
DATABASE_URL=postgresql://sigab:local-only@127.0.0.1:5432/sigab uv run pytest -q
cd ..
docker compose down
```

Banco e migrações: [banco e migrações](docs/banco-e-migracoes.md). API: [convenções da API](docs/api.md). Logs e erros: [observabilidade](docs/observabilidade.md). Dados de teste são sempre sintéticos.

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

- Procedimento automatizado: [backup criptografado e ensaio de restauração](docs/backup-e-restauracao.md), com scripts e timer em `ops/backup/`. Aceite de continuidade em produção ainda pendente.
- Banco: faça backup consistente com `pg_dump --format=custom` e proteja o arquivo fora do host; restaure periodicamente em ambiente isolado com `pg_restore`. As metas definidas no [ADR 0004](docs/adr/0004-conectividade-e-contingencia.md) são RPO ≤ 15 min, o que exige arquivamento contínuo de WAL/PITR além do dump, e RTO ≤ 4 h. Criptografia com age implementada para o dump; retenção, armazenamento externo e gestão das chaves dependem da implantação.
- Auditoria: `uv run python manage.py verify_audit_chain` verifica a cadeia de hashes da trilha de cada organização e aponta o primeiro registro alterado ou removido; rode após restaurar backup e periodicamente.
- Migrações: em `backend/`, aplique `uv run python manage.py migrate` antes de iniciar a nova versão; mantenha backup anterior à implantação.
- Timestamps são persistidos em UTC; a organização carrega seu fuso para apresentação futura.
- Configure `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`, `DJANGO_ALLOWED_HOSTS` e TLS no proxy em qualquer ambiente não local.

Consulte também a [decisão do segmento inicial](docs/decisoes/0001-segmento-inicial.md), a [nota regulatória preliminar](docs/notas-regulatorias/0001-guardas-municipais.md), as [decisões pendentes](docs/decisoes-pendentes.md), o [modelo de domínio](docs/modelo-de-dominio.md) e a documentação de [segurança](docs/seguranca-e-privacidade.md). O backlog preparado para importação no Jira está em [tarefas.csv](docs/tarefas/tarefas-15-10-26/tarefas.csv).

## Evidências da entrega

A [revisão das tarefas 041 a 045](docs/validacao/tarefas-041-a-045.md) liga requisitos aos testes e registra as evidências da primeira fatia. A [entrega das tarefas 063 a 070](docs/validacao/tarefas-063-a-070.md) acrescenta inventário, cesta mista, estoque quantitativo, autosserviço e testes Playwright no CI.
