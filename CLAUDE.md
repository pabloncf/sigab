# CLAUDE.md — SIGAB

Este arquivo orienta agentes de IA que trabalham neste repositório. Leia também o `README.md`, os ADRs em `docs/adr/`, `docs/decisoes-pendentes.md` e o backlog em `docs/tarefas/tarefas-15-10-26/tarefas.csv` antes de alterar arquitetura ou regras de domínio.

## Objetivo atual

O SIGAB é um sistema multi-organização para gestão de acervo bélico. A base atual cobre somente o fluxo vertical de **item físico individual**:

1. organização, unidade e local de guarda;
2. pessoa, vínculo e conta de acesso separados;
3. papéis e permissões explícitas por organização ou unidade;
4. tipo de equipamento e item individual;
5. incorporação, saída, devolução, situação atual e histórico;
6. auditoria e idempotência.

Os requisitos ainda são `proposto`. Não transforme hipóteses em regra definitiva sem evidência e decisão registrada.

## Stack e estrutura

- Python 3.12+ e Django 5.2 LTS.
- PostgreSQL 17 é o banco de produção e do CI.
- SQLite é aceito para desenvolvimento simples, mas não valida concorrência real.
- Frontend principal em React + TypeScript + Vite, em `frontend/`, consumindo `/api/v1/`.
- Templates Django permanecem como fallback durante a migração incremental.
- Dependências e ambiente do backend gerenciados por `uv` em `backend/`.
- Aplicação: `backend/sigab/`.
- Configuração Django: `backend/config/`.
- API HTTP: `backend/sigab/api/`.
- Frontend React: `frontend/`.
- Templates legados: `backend/templates/`.
- Testes: `backend/sigab/tests/`.
- Migrações: `backend/sigab/migrations/`.

Não introduza filas, cache distribuído ou novos serviços sem necessidade demonstrada e ADR. Mudanças na fronteira React/API devem preservar a decisão do ADR 0005.

## Comandos obrigatórios

Instalação e execução:

```bash
cd backend
uv sync --dev
uv run python manage.py migrate
uv run python manage.py runserver
```

Antes de concluir qualquer alteração de código:

```bash
cd backend
uv run ruff format --check config sigab manage.py
uv run ruff check config sigab manage.py
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run pytest -q
cd ../frontend && bun run typecheck && bun run build
```

Para mudanças em transações, bloqueios ou idempotência, execute também a suíte com PostgreSQL:

```bash
docker compose up -d db
cd backend
DATABASE_URL=postgresql://sigab:local-only@127.0.0.1:5432/sigab uv run pytest -q
cd ..
docker compose down
```

## Invariantes obrigatórias

### Isolamento multi-organização

- Todo dado de negócio deve carregar ou derivar inequivocamente `organization_id`.
- Nunca aceite a organização enviada pelo navegador como fonte de autoridade; derive-a da conta autenticada.
- Toda leitura e escrita deve aplicar o tenant no servidor.
- Referências entre organizações devem falhar sem revelar se o registro externo existe.
- Toda funcionalidade nova precisa de teste negativo de acesso cruzado.

### Autorização

- Negue por padrão.
- Valide permissões no backend usando concessões explícitas e seu escopo.
- Não crie hierarquia implícita entre papéis.
- Não confie em ocultação de botão, URL ou validação apenas no frontend.
- O Django Admin é um mecanismo administrativo transitório, não a interface operacional final.

### Identidade e privacidade

- `Person`, `Membership` e `Account` têm ciclos de vida independentes.
- Pessoa pode existir sem conta; suspender conta não altera ou apaga pessoa e histórico.
- Não registre senha, token ou CPF completo em logs, eventos ou mensagens de erro.
- CPF é opcional e deve permanecer fora das telas operacionais comuns.
- Não implemente biometria, laudos, anexos sensíveis ou restrições pessoais sem política aprovada.

### Acervo e movimentações

- UUID interno nunca depende de número de série, patrimônio ou matrícula.
- Condição física, disponibilidade, localização e situação administrativa são conceitos separados.
- Tipo quantitativo não pode usar o fluxo de item individual.
- A classificação de um tipo em uso não pode mudar.
- Saída e devolução exigem confirmação explícita e chave de idempotência.
- Uma saída deve ser atômica; confirmações concorrentes aceitam exatamente uma operação.
- Item em posse não pode sair novamente.
- Devolução apta torna o item disponível; devolução inapta o mantém indisponível.
- Não edite nem apague movimentações ou eventos confirmados. Correções futuras devem ser compensatórias.

### Auditoria

- Separe log técnico, evento de domínio e evento de auditoria.
- Registre organização, ator quando disponível, ação, objeto, instante UTC e correlação.
- Minimize os valores registrados; não replique dados pessoais desnecessariamente.
- Não exponha rotas comuns de atualização ou exclusão de auditoria.
- A proteção atual é da camada de aplicação; controles contra administrador do banco permanecem pendentes.

## Padrões de implementação

- Regras transacionais pertencem a `backend/sigab/services.py`, não às views ou templates.
- Views devem obter objetos já filtrados pela organização e verificar permissão no servidor.
- Use `transaction.atomic`, restrições de banco e `select_for_update`/atualização condicional quando a integridade depender de concorrência.
- Chaves de idempotência devem possuir restrição única no banco.
- Execute `full_clean()` ou validação equivalente antes de persistir referências compostas criadas fora de `ModelForm`.
- Metadados de evento devem ser mínimos e conter contrato/schema versionado; não use JSON como depósito genérico.
- Preserve migrações existentes. Crie nova migração para mudanças de modelo.
- Use dados inteiramente sintéticos em testes e exemplos.
- Código técnico permanece em inglês; interface e documentação de domínio permanecem em português.
- Não deixe `TODO` silencioso em regra crítica; relacione a pendência a uma tarefa do backlog.

## Testes esperados

Escolha o nível mais baixo que prove o comportamento, mantendo integração real onde ela importa:

- regra pura: teste unitário;
- tenant, autorização, transação e restrição: teste de integração com banco;
- concorrência: PostgreSQL e conexões independentes;
- fluxo operacional: cliente HTTP do Django;
- migração: banco vazio e `makemigrations --check`.

Ao corrigir um defeito, adicione primeiro ou junto um teste que reproduza a falha. Não reduza cobertura de isolamento, autorização, idempotência, imutabilidade ou concorrência.

## Fora do escopo sem autorização explícita

- estoque quantitativo, munição e lotes;
- biometria;
- operação offline ou sincronização;
- retirada em nome de terceiro;
- restrições médicas, judiciais ou administrativas;
- anexos e assinatura definitiva;
- inventário, manutenção, transferência, sinistro ou baixa;
- integrações oficiais;
- catálogo pré-carregado;
- bloqueio comercial;
- relatórios e exportações gerais;
- feed público de atividade.

Documente extensões futuras, mas não crie tabelas, endpoints ou implementações vazias para elas.

## Documentação e entrega

- Decisões difíceis de reverter exigem ADR curto em `docs/adr/`.
- Lacunas de produto ficam em `docs/decisoes-pendentes.md`.
- Atualize documentação e testes no mesmo incremento do código.
- `docs/tarefas/tarefas-15-10-26/tarefas.csv` é o backlog preparado para importação no Jira. Não marque requisito como validado nem tarefa de produto como concluída apenas porque existe implementação técnica.
- Ao finalizar, informe arquivos alterados, comandos/testes executados, decisões, suposições, riscos e próxima tarefa recomendada.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
