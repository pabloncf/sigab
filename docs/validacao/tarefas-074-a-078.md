# Entrega técnica — tarefas originais 074–078

Data: 10/11/2026. Origem: [revisão de requisitos](diferencas-requisitos-2026-11-10.md) e [lote de tarefas](../tarefas/tarefas-10-11-26/README.md). Os números abaixo são IDs originais de planejamento, não chaves reais do Jira. Nenhum registro externo foi alterado.

## Entrega por tarefa

| ID original | Estado técnico local | Entrega e evidência |
|---|---|---|
| SIGAB-074 | Concluído | Recontagem diferente reabre divergência, limpa a resolução vigente e preserva o antes/depois na auditoria. Recontagem igual mantém a decisão; contagem que coincide com o esperado preserva a ocorrência e registra justificativa automática com responsável. Investigação e encerramento exigem responsável. Contagem, alteração de divergência e fechamento bloqueiam a mesma sessão. |
| SIGAB-075 | Concluído | Abertura bloqueia a unidade e o banco garante uma sessão aberta por unidade. Migração 0011 recusa duplicidades preexistentes com instrução de reconciliação, sem apagar sessões ou contagens. Testes PostgreSQL cobrem mesma unidade e unidades distintas; teste de migração confirma preservação do histórico. |
| SIGAB-076 | Concluído | Formulário capturado antes do `await`; sucesso limpa campos e seleções e atualiza opções. Falha de atualização posterior aparece separada do resultado confirmado e bloqueia nova operação até atualização. Recusa de validação preserva campos para correção. |
| SIGAB-077 | Concluído | Tentativa guarda chave e conteúdo na sessão do navegador, por conta/organização. Reenvio e recarga recuperam a mesma operação; edição fica bloqueada durante resultado incerto. Nova operação recebe nova chave. Backend verifica acesso no replay e reconhece o atendimento mesmo após vencimento do prazo original. |
| SIGAB-078 | Parcial: jornada apta implementada; dependências de domínio pendentes | Nova área `/estoque`: entrada com referência, saldos disponíveis, pendências quantitativas, devolução parcial apta e consumo com motivo, revisão e confirmação explícita. APIs de opções e pendências respeitam unidade e organização; entradas exigem `inventory.adjust.approve`, devolução/consumo exigem `movement.return`. Reutiliza o livro existente e a proteção de reenvio. O aceite integral depende de SIGAB-008/041 e da validação do modelo. |

## Limite quantitativo explícito

A decisão 0003 continua com validações pendentes. Esta entrega utiliza o contrato já existente de entrada, devolução apta e consumo; não declara aprovado o modelo completo de estoque. A interface identifica a devolução como **apta** e orienta que material inapto não seja lançado por ela. Posições inaptas, calibre/unidade estruturados, conversões, contrapartidas e aprovação de ajustes por atores distintos permanecem nas tarefas 008/041. A tela não expõe ajuste direto nem retirada por terceiro.

A consulta mostra as pendências das unidades autorizadas; a consulta consolidada e seus filtros/históricos completos continuam na 069. Contagem e gestão de inventário em React continuam nas tarefas 062/063. Não foram apresentadas como parte da nova tela de estoque.

## Verificações

- Suíte completa PostgreSQL: **251 passaram, 2 ignorados**, em 75,54 s. Ignorados: ensaio opcional de desempenho e integração de navegador opt-in (esta foi executada separadamente).
- Regressões SQLite das tarefas novas e isolamento: **60 passaram**.
- Playwright com API simulada: **14 jornadas passaram**, incluindo cesta individual, mista e quantitativa, resposta perdida e recarga, duplo clique, erro de atualização após sucesso, correção após recusa de validação e operação de estoque.
- React + Django + PostgreSQL reais: **1 jornada passou**, com entrada de 100, saída de 50, perda da resposta após commit, recarga, reenvio da mesma tentativa, devolução de 20 e consumo de 10. Banco final: um atendimento, 20 em posse, 70 disponíveis e quatro lançamentos (entrada/saída/devolução/consumo).
- Ruff, verificações Django, ausência de migrações faltantes, TypeScript e build: aprovados.
- Graphify atualizado por AST local; avisos sobre JSONs sem nós não são prova de ausência de conteúdo nesses documentos.

A suíte PostgreSQL usa `test_sigab_validation_074_078`; a jornada real usa `test_sigab_browser_074_078`. São bancos temporários criados e removidos pelo Django. Nenhuma migração foi aplicada ao banco de desenvolvimento ou produção.

## Reproduzir a integração com navegador

Exige Bun, dependências frontend instaladas, Chromium do Playwright e PostgreSQL local com permissão de criar banco de teste. Na raiz, usar o fluxo de testes existente; para a jornada real, em `backend/`:

```bash
SIGAB_BROWSER_INTEGRATION=1 \
DATABASE_URL=postgresql://USUARIO:SENHA@127.0.0.1:5432/sigab_browser_074_078 \
.venv/bin/python -m pytest -q sigab/tests/test_browser_integration.py
```

A variável habilita o ensaio opt-in; sem ela, ele é ignorado na suíte normal. Vite e Django são iniciados para o teste e encerrados ao final. A autenticação usa sessão sintética do banco de teste; a jornada não depende de contas de demonstração ou de servidor já em uso.

## Migração e recuperação de tentativa

Aplicar `0011_unique_open_inventory` antes de disponibilizar a nova versão do backend. Se houver duas sessões abertas na mesma unidade, a migração para com uma mensagem: reconciliar as sessões preservando contagens e auditoria, depois repetir. Não há fechamento automático nem exclusão de histórico.

Uma tentativa incerta permanece na mesma aba, inclusive após recarga, até receber confirmação. O botão de verificação reenvia o conteúdo original com a mesma chave. Em caso de perda do armazenamento da aba, troca de navegador ou revogação de acesso, conferir o registro com pessoa autorizada antes de iniciar outra operação. A proteção não equivale a operação digital offline.

## Arquivos de evidência

- `backend/sigab/tests/test_requirements_074_078.py`: recontagem, responsável, unicidade persistente, migração, acesso e jornada quantitativa pela API.
- `backend/sigab/tests/test_concurrency.py`: abertura concorrente, atualização versus fechamento e cesta quantitativa com a mesma chave.
- `backend/sigab/tests/test_isolation.py`: cobertura das novas rotas e ausência de dados de outro tenant.
- `frontend/e2e/requirements-074-078.spec.ts`: jornadas React com respostas controladas.
- `backend/sigab/tests/test_browser_integration.py` e `frontend/integration/stock-journey.mjs`: integração real com banco temporário.
