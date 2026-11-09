# Próximos requisitos — lote de 06/11/2026

[CSV para importação](tarefas.csv) · [Relatório de origem](../../validacao/alinhamento-requisitos-2026-11-06.md) · [Guia de importação](../IMPORTAR-NO-JIRA.md)

27 tarefas novas, **SIGAB-047 a SIGAB-073**, com 8 épicos do incremento. O arquivo mantém as 18 colunas do backlog existente, incluindo quatro Labels e seis Is Blocked By. Todas as novas tarefas estão em `To Do`; prioridades, responsáveis por função e ondas são sugestões, sem datas ou atribuições pessoais assumidas.

## Ordem sugerida

1. **Onda 1 — garantias e consultas:** linha de base, Admin, login, restrições, atualização entre balcões, paginação, auditoria e testes React.
2. **Onda 2 — operação individual e organização:** bloqueio comercial, comprovantes, painel/relatórios, baixa/anulação, histórico de acesso, proteção da auditoria, privacidade e modularização.
3. **Onda 3 — ampliação validada:** inventário, atendimento com cesta, pendências quantitativas, autosserviço, decisões futuras e desempenho.

As ondas não substituem as dependências. Restrição só avança após as decisões e a política de dados existentes; cesta quantitativa aguarda estoque. Dentro de cada onda, executar primeiro os pré-requisitos. As tarefas SIGAB-064/065 são refatorações incrementais e não bloqueiam correções urgentes.

## Tarefas

| ID | Tarefa | Prioridade | Onda | Dependências |
|---|---|---|---|---|
| SIGAB-047 | Consolidar linha de base e rastreabilidade dos requisitos | Highest | 1 | — |
| SIGAB-048 | Unificar garantias do Django Admin e dos serviços | Highest | 1 | SIGAB-047 |
| SIGAB-049 | Autenticar por organização e matrícula | High | 1 | SIGAB-047, SIGAB-021, SIGAB-022 |
| SIGAB-050 | Implementar cadastro e ciclo de vida de restrições | Highest | 1 | SIGAB-040, SIGAB-039, SIGAB-047 |
| SIGAB-051 | Bloquear saída por restrição ativa | Highest | 1 | SIGAB-050, SIGAB-030 |
| SIGAB-052 | Separar bloqueio comercial de suspensão de segurança | Highest | 2 | SIGAB-047, SIGAB-023, SIGAB-058, SIGAB-060 |
| SIGAB-053 | Atualizar acervo entre balcões | High | 1 | SIGAB-047, SIGAB-033 |
| SIGAB-054 | Completar paginação e filtros de acervo e pessoas | High | 1 | SIGAB-038, SIGAB-037 |
| SIGAB-055 | Padronizar auditoria de alterações e histórico do item | High | 1 | SIGAB-048, SIGAB-035 |
| SIGAB-056 | Proteger e ancorar a trilha de auditoria | High | 2 | SIGAB-055, SIGAB-042 |
| SIGAB-057 | Exibir histórico de perfis e tela de auditoria | High | 2 | SIGAB-055, SIGAB-022 |
| SIGAB-058 | Emitir comprovantes de saída e devolução | High | 2 | SIGAB-047, SIGAB-030, SIGAB-033, SIGAB-046 |
| SIGAB-059 | Criar painel por tipo e situação do acervo | High | 2 | SIGAB-054 |
| SIGAB-060 | Completar relatórios por pessoa e operador com exportação | High | 2 | SIGAB-054, SIGAB-055, SIGAB-058 |
| SIGAB-061 | Implementar baixa e anulação de incorporação | High | 2 | SIGAB-047, SIGAB-048, SIGAB-055, SIGAB-009 |
| SIGAB-062 | Implementar contagem guiada de itens individuais | High | 3 | SIGAB-047, SIGAB-054 |
| SIGAB-063 | Tratar divergências de inventário até resolução | High | 3 | SIGAB-062, SIGAB-055 |
| SIGAB-064 | Separar serviços e API por domínio | Medium | 2 | SIGAB-047, SIGAB-048 |
| SIGAB-065 | Organizar frontend por domínio e esclarecer navegação | Medium | 2 | SIGAB-047, SIGAB-054 |
| SIGAB-066 | Automatizar jornadas React em navegador no CI | High | 1 | SIGAB-043 |
| SIGAB-067 | Definir atendimento com vários itens e modalidades de cautela | High | 2 | SIGAB-047, SIGAB-007, SIGAB-008 |
| SIGAB-068 | Implementar saída por pessoa com cesta de materiais | High | 3 | SIGAB-067, SIGAB-051, SIGAB-041, SIGAB-058 |
| SIGAB-069 | Consolidar pendências e histórico quantitativo | High | 3 | SIGAB-041, SIGAB-054, SIGAB-067, SIGAB-068 |
| SIGAB-070 | Permitir consulta apenas da própria posse e histórico | Medium | 3 | SIGAB-049, SIGAB-054, SIGAB-060 |
| SIGAB-071 | Decidir escopo das capacidades futuras ainda não detalhadas | Medium | 3 | SIGAB-047, SIGAB-005, SIGAB-007 |
| SIGAB-072 | Aplicar controles de retenção e acesso a dados pessoais | High | 2 | SIGAB-039, SIGAB-047, SIGAB-055 |
| SIGAB-073 | Validar desempenho e uso no balcão com volume acordado | High | 3 | SIGAB-045, SIGAB-053, SIGAB-054, SIGAB-066 |

Os critérios de aceite completos estão na coluna Description do CSV, junto de entregável, requisitos, responsável sugerido e dependências. A conclusão exige evidência dos critérios; documentação de decisão não equivale à implementação do requisito.

## Pendências existentes preservadas

| Tarefa existente | Tratamento neste lote |
|---|---|
| SIGAB-005 — regulação | Mantida como decisão anterior; não presumir validação municipal/jurídica. |
| SIGAB-007 — formulário de armamento temporário | Pré-requisito de SIGAB-067; retirada por terceiro não é autorizada por inferência. |
| SIGAB-008 — modelo quantitativo | Pré-requisito de SIGAB-041 e SIGAB-067; não duplicado. |
| SIGAB-039 — política de dados pessoais | Continua necessária antes de implementar controles ou tratar motivos/anexos restritos. |
| SIGAB-040 — especificação de restrições | Decisão 0005 é insumo; SIGAB-050/051 implementam o que falta, após fechar as decisões pendentes. |
| SIGAB-041 — livro de estoque | Continua responsável por entrada, saída, devolução parcial, consumo, ajuste e estorno. SIGAB-068 integra a cesta e SIGAB-069 cria consultas; não reimplementam o livro. |
| SIGAB-042 — backup/restauração | Mantém WAL/PITR, armazenamento externo, retenção e ensaio RPO/RTO ainda pendentes; não foi criada outra tarefa de backup. |
| SIGAB-043 — fluxo vertical HTTP | Preservada; SIGAB-066 complementa com navegador React real. |
| SIGAB-045 — demonstração | Preservada para aceite por cenário; SIGAB-073 complementa com volume, desempenho e uso no balcão. |
| SIGAB-046 — contingência | Já implementada; não criada novamente. Novos comprovantes e testes devem contemplá-la. |

## Importação incremental

- O CSV contém primeiro os 8 épicos do incremento (IDs locais 2001–2008), depois as 27 tarefas. Nomes dos épicos incluem `(incremento 2026-11)` para distingui-los dos originais.
- Os IDs SIGAB nas descrições são identificadores de planejamento. O Jira pode atribuir outras chaves reais; guardar o mapeamento após importar.
- `Parent` e `Is Blocked By` apontam somente a IDs presentes neste arquivo. Dependências anteriores aparecem em `Dependências originais` e `Observações`; vincular manualmente às chaves reais existentes, sem recriar tarefas antigas.
- Conferir também critérios/evidências das dependências antigas: status `Done` no CSV histórico não comprova aceite atual.
- Não reimportar o CSV inicial nem este lote para tentar atualizar status. Nenhuma importação externa foi executada nesta entrega.
- O conversor `scripts/prepare_jira_csv.py` atende ao formato original do backlog e recalcula IDs de épicos; não o aplicar diretamente a este CSV já formatado.

## Verificação do lote

Validados: cabeçalho idêntico ao anterior, 18 campos por registro, IDs únicos e sem colisão com o lote anterior, sequência 047–073 completa, épicos antes das tarefas, pais e dependências internas existentes, dependências anteriores identificadas, ausência de ciclos e presença dos campos de descrição. O CSV preserva acentos e descrições com múltiplos parágrafos.

Este lote prioriza as lacunas do relatório. Biometria, catálogo pré-carregado e capacidades sem definição permanecem decisões em SIGAB-071; se aprovadas, precisarão de tarefas de implementação próprias. A criação deste backlog não declara atendimento de 100% dos requisitos.
