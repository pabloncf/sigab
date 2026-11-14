# SIGAB

O SIGAB é **single-tenant: uma instalação e um banco exclusivos por cliente**, com uma única organização e várias unidades e reservas internas. O banco impede cadastrar uma segunda organização. A [decisão de arquitetura](docs/adr/0007-single-tenant.md) substitui a tenancy compartilhada anterior.

A base inclui identidade separada de conta, autorização por papel/unidade, acervo individual, movimentação, restrições, cesta, estoque quantitativo básico, inventário via API, autosserviço e auditoria. Consulte os limites e evidências nas [entregas técnicas](docs/validacao/tarefas-074-a-078.md). O login usa matrícula e senha; contas técnicas usam seu usuário, sem informar organização.

A [entrega histórica Jira SIGAB-71–75](docs/validacao/jira-071-a-075.md) corresponde aos IDs originais 047–051. Seu login por organização foi substituído pela decisão single-tenant; os identificadores de planejamento não são chaves reais do Jira.

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
```

Em uma instalação vazia, escolha **um** dos caminhos:

- **Demonstração com dados sintéticos:**

  ```bash
  docker compose exec backend python manage.py seed_demo
  ```

  Cria uma organização “Batalhão Demonstração Alfa”, com duas companhias, reservas, tipos, pessoas, itens e movimentações. Exige `DEBUG` ligado.

- **Instalação vazia para cadastro manual:**

  ```bash
  docker compose exec backend python manage.py bootstrap_sigab \
    --organization "Minha organização" \
    --username admin --email admin@example.invalid
  ```

Não execute `seed_demo` depois do bootstrap: ambos inicializam a organização única.

### Seleção do banco e recuperação de uma demonstração antiga

O Compose usa `SIGAB_DATABASE_NAME` do arquivo `.env` na raiz; sem essa variável, usa `sigab`. O nome é utilizado tanto pelo backend quanto pela inicialização do PostgreSQL. O `.env` é local e não é versionado.

Em 10/11/2026, o ambiente local foi recuperado com uma **nova** demonstração, no banco `sigab_single_tenant_demo_20261110`. A base anterior `sigab`, com três organizações, foi preservada. O `.env` local aponta para a nova base:

```dotenv
SIGAB_DATABASE_NAME=sigab_single_tenant_demo_20261110
```

Alterar a variável não cria um banco dentro de um volume PostgreSQL já inicializado. Para preparar uma nova base vazia nesse volume, confirme que o nome está livre, crie-a explicitamente e reinicie o backend. Por exemplo, para o nome acima:

```bash
docker compose up -d db
docker compose exec db psql -U sigab -d postgres \
  -c 'CREATE DATABASE sigab_single_tenant_demo_20261110 OWNER sigab'
docker compose up -d backend frontend
docker compose exec backend python manage.py seed_demo
```

O comando `CREATE DATABASE` recusa um nome já existente. Na configuração local atual, essa preparação **já foi executada**; use somente `docker compose up -d` para iniciar. Não use `docker compose down -v` como recuperação: isso remove o volume com todas as bases, inclusive a original preservada.

### Credenciais de teste

Somente para a instalação local criada por `seed_demo`. Todas usam a senha `Demo-sigab-2026` (personalizável com `seed_demo --password <senha>` antes da criação).

| Matrícula ou usuário | Pessoa | Papéis |
|---|---|---|
| `alfa.admin` | Conta técnica de administração | Administrador de acesso e Gestor de acervo |
| `1001` | Sd Ana | Operador de reserva nas duas companhias |

Informe somente matrícula/usuário e senha. A organização é determinada pela instalação; o formulário não pede UUID e não permite escolher outro cliente. Cada cliente adicional exige outro banco, credenciais, implantação e cópias de segurança próprios.

Bancos antigos com Alfa e Bravo precisam ser separados antes da migração `0012`; a migração recusa várias organizações e preserva todos os dados. Não exclua uma organização nem misture seus registros para contornar a validação. Consulte o [procedimento de transição](docs/adr/0007-single-tenant.md).

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
3. **Pessoas:** cadastre pessoas e vínculos; crie a conta de quem vai operar e conceda o papel “Operador de reserva” na unidade.
4. **Atendimento:** o próprio administrador (Gestor de acervo, matriz 1.5.0) ou o operador registra retirada, devolução e condição de qualquer material. Quem registra uma operação por termo assinado não aprova o próprio termo; para isso, é preciso outro administrador.

O Django Admin (`http://127.0.0.1:8000/admin/`) continua disponível como mecanismo administrativo transitório, e os templates Django em `http://127.0.0.1:8000/` como fallback.

Para suspender ou reativar uma organização pelo plano de controle:

```bash
cd backend
uv run python manage.py set_organization_status \
  --status inactive --reason "Motivo"
```

Também há um comando para criar conta sem interface (a senha é pedida sem eco):

```bash
cd backend
uv run python manage.py create_sigab_account \
  --person-id UUID_DA_PESSOA \
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
- **Biometria facial ([ADR 0008](docs/adr/0008-biometria-facial.md)).** Retirada e devolução exigem verificação facial aprovada ou termo assinado aprovado pelo administrador do acervo. Variáveis:
  - `SIGAB_REQUIRE_IDENTITY_CHECK`: padrão `true`, e deve ficar `true` em produção. `false` serve só para desenvolvimento.
  - `SIGAB_BIOMETRIC_KEY`: chave Fernet que criptografa os modelos biométricos. Gere com `uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` e guarde fora do banco e dos backups do banco.
  - `SIGAB_FACE_ENGINE=sigab.biometrics.OpenCVFaceEngine`, com `SIGAB_FACE_DETECTOR_MODEL` e `SIGAB_FACE_RECOGNIZER_MODEL` apontando para os arquivos ONNX do YuNet e do SFace (OpenCV Zoo, Apache 2.0). O motor exige `uv sync --extra face`.
  - `SIGAB_FACE_VERIFICATION_TTL_SECONDS`: validade da verificação aprovada, padrão `600` (a pessoa é identificada antes da escolha dos materiais).
  - `SIGAB_FACE_THRESHOLD`: limiar de similaridade, padrão `0.363`. Deve ser ajustado pela medição da [pesquisa 0002](docs/pesquisas/0002-verificacao-facial-no-balcao.md).
  - Sem motor ou sem chave, a verificação responde 503 e o balcão usa o termo.

Consulte também a [decisão do segmento inicial](docs/decisoes/0001-segmento-inicial.md), a [nota regulatória preliminar](docs/notas-regulatorias/0001-guardas-municipais.md), as [decisões pendentes](docs/decisoes-pendentes.md), o [modelo de domínio](docs/modelo-de-dominio.md) e a documentação de [segurança](docs/seguranca-e-privacidade.md). O backlog preparado para importação no Jira está em [tarefas.csv](docs/tarefas/tarefas-15-10-26/tarefas.csv).

## Evidências da entrega

A [revisão das tarefas 041 a 045](docs/validacao/tarefas-041-a-045.md) liga requisitos aos testes e registra as evidências da primeira fatia. A [entrega das tarefas 063 a 070](docs/validacao/tarefas-063-a-070.md) acrescenta inventário, cesta mista, estoque quantitativo, autosserviço e testes Playwright no CI.
