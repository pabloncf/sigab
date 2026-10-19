# Importação do backlog no Jira Cloud

O arquivo `tarefas-15-10-26/tarefas.csv` está preparado para o importador CSV administrativo do Jira Cloud. Ele contém primeiro os Epics e depois as Tasks, como exigido para reconstruir a hierarquia.

## Mapeamento

| Coluna CSV | Campo Jira |
|---|---|
| Work Type | Work type |
| Status | Status |
| Summary | Summary |
| Description | Description |
| Priority | Priority |
| Labels | Labels — mapear todas as quatro colunas |
| Component | Component |
| Work item ID | Work item ID |
| Parent | Parent |
| Is Blocked By | vínculo `is blocked by` — mapear todas as colunas repetidas |

Use o importador administrativo, não a criação simplificada em massa, para preservar hierarquia e vínculos. Valide antes de iniciar a importação.

Os valores de status usados são `To Do` e `Done`. Caso o workflow do projeto use nomes diferentes, faça o mapeamento de valores na etapa oferecida pelo Jira. As prioridades são `Highest`, `High` e `Medium`.

Os responsáveis originais não foram colocados em `Assignee`: os valores do backlog são funções de equipe, não IDs de contas Atlassian. Sprint e responsável sugeridos continuam na descrição e em labels para tratamento posterior.

## Regeneração

O conversor existe apenas para reproduzir a transformação a partir de uma cópia no formato original:

```bash
uv run python scripts/prepare_jira_csv.py origem.csv destino.csv
```

