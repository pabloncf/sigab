# Importação do backlog no Jira Cloud

O arquivo `tarefas-15-10-26/tarefas.csv` está preparado para o importador CSV administrativo do Jira Cloud. Ele contém primeiro os Epics e depois as Tasks, como exigido para reconstruir a hierarquia.

O lote seguinte está em [tarefas-06-11-26/tarefas.csv](tarefas-06-11-26/tarefas.csv), com SIGAB-047 a SIGAB-073. Consulte o [guia do incremento](tarefas-06-11-26/README.md) para ordem sugerida e dependências do lote anterior. Ele contém apenas novas tarefas e épicos do incremento; não reimporte o lote inicial para adicionar essas tarefas.

A revisão de 10/11 está em [tarefas-10-11-26/tarefas.csv](tarefas-10-11-26/tarefas.csv): cinco tarefas novas, IDs originais SIGAB-074 a SIGAB-078, e um épico com ID local 3001. O [guia da revisão](tarefas-10-11-26/README.md) também registra complementos de aceite nas tarefas existentes, sem duplicá-las no CSV. Os IDs originais 074/075 não são as chaves Jira SIGAB-74/75 já atribuídas a outros registros. Nenhuma importação desse novo lote foi executada.

## Mapeamento

A importação relatada em 09/11/2026 atribuiu as chaves Jira SIGAB-71–75 às tarefas originais SIGAB-047–051. As chaves reais não preservam o número entre colchetes da descrição. Consulte a [linha de base de 09/11](../validacao/linha-base-2026-11-09.md) e confira sempre o campo `ID original` antes de executar ou atualizar uma tarefa.

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

`Work item ID` é um identificador local do arquivo, não uma chave real do Jira. No lote de 06/11, `Is Blocked By` contém somente referências a tarefas do próprio arquivo. As dependências de SIGAB-001 a SIGAB-046 constam nas descrições e devem ser vinculadas às chaves reais existentes após a importação. Os novos épicos usam IDs locais 2001–2008 e nomes com o sufixo do incremento, sem recriar os épicos originais. A reimportação do mesmo arquivo não deve ser tratada como atualização idempotente.

Os valores de status usados são `To Do` e `Done`. Caso o workflow do projeto use nomes diferentes, faça o mapeamento de valores na etapa oferecida pelo Jira. As prioridades são `Highest`, `High` e `Medium`.

Os responsáveis originais não foram colocados em `Assignee`: os valores do backlog são funções de equipe, não IDs de contas Atlassian. Sprint e responsável sugeridos continuam na descrição e em labels para tratamento posterior.

## Regeneração

O conversor existe apenas para reproduzir a transformação a partir de uma cópia no formato original:

```bash
uv run python scripts/prepare_jira_csv.py origem.csv destino.csv
```

