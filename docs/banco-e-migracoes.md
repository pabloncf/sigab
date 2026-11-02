# Banco e migrações

- Tarefa: SIGAB-016
- Revisão: 2026-11-02
- Base: [ADR 0005](adr/0005-api-django-e-frontend-react.md), [modelo de domínio](modelo-de-dominio.md)

## Bancos

| Ambiente | Banco | Como |
|---|---|---|
| produção e CI | PostgreSQL 17 | `DATABASE_URL=postgresql://usuario:senha@host:5432/banco` |
| local com PostgreSQL | PostgreSQL 17 do `compose.yaml` | `docker compose up -d db` e `DATABASE_URL=postgresql://sigab:local-only@127.0.0.1:5432/sigab` |
| local simples | SQLite em `backend/db.sqlite3` | sem `DATABASE_URL` |

SQLite não valida bloqueio de linha nem concorrência; mudanças de transação, bloqueio ou idempotência exigem a suíte no PostgreSQL. A senha `local-only` do Compose é só para a máquina local.

## Do banco vazio à versão atual

```bash
cd backend
uv run python manage.py migrate
```

O comando cria todas as tabelas a partir do banco vazio e aplica as migrações pendentes em ordem. Não há passo manual. Os testes criam um banco descartável próprio (`test_<nome>`) aplicando as mesmas migrações a cada execução.

## Verificação em ambiente descartável

O CI, sobre um PostgreSQL efêmero, executa a cada mudança:

1. `makemigrations --check --dry-run`: falha se algum modelo mudou sem migração;
2. `migrate` → `migrate sigab zero` → `migrate`: o banco vazio chega à versão atual, todas as migrações do SIGAB são revertidas e aplicadas de novo;
3. `pytest`: a suíte roda sobre um banco de teste criado pelas migrações.

Para repetir localmente sem tocar no banco de trabalho:

```bash
docker compose up -d db
docker compose exec -T db psql -U sigab -d postgres -c "CREATE DATABASE sigab_migr"
cd backend
export DATABASE_URL=postgresql://sigab:local-only@127.0.0.1:5432/sigab_migr
uv run python manage.py migrate
uv run python manage.py migrate sigab zero
uv run python manage.py migrate
```

## Convenções

- Uma migração por incremento de modelo, gerada por `makemigrations` e revisada antes do commit. Migrações aplicadas nunca são editadas nem apagadas.
- Toda migração é reversível. `RunPython` declara a função reversa, ou `RunPython.noop` quando a ida só completa dados e a volta não precisa desfazê-los.
- Toda tabela de domínio tem `organization` explícito (exceções do plano de controle no [modelo de domínio](modelo-de-dominio.md#2-limites-de-organização)).
- Unicidade de negócio é restrição do banco, composta com `organization` e, quando o campo é opcional, parcial (`condition=~Q(campo="")`). Mensagens de violação ficam em `violation_error_message`, para que `full_clean()` devolva texto de domínio.
- Restrição nova sobre tabela com dados exige verificar antes se os dados existentes a satisfazem; quando não satisfazem, a migração inclui o ajuste de dados (como a `0002`, que preenche o motivo de itens inaptos antigos).
- Produção: backup antes de `migrate` e aplicação da migração antes de iniciar a nova versão do código (README, “Operação e backup”).

## Migrações atuais

| Migração | Conteúdo |
|---|---|
| `0001_initial` | base multi-organização, identidade, autorização, acervo, movimentações e auditoria |
| `0002_item_condition_reason` | motivo de inapto no item e na movimentação; preenche itens inaptos antigos |
| `0003_person_cpf_account_revocation` | CPF único por organização (RN-01); revogação de conta; pessoa pode ter várias contas no histórico, no máximo uma não revogada |
