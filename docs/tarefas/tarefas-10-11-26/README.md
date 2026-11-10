# Ajustes da revisão de requisitos — lote de 10/11/2026

[CSV das tarefas novas](tarefas.csv) · [Análise de origem](../../validacao/diferencas-requisitos-2026-11-10.md) · [Guia de importação](../IMPORTAR-NO-JIRA.md)

Registradas **5 tarefas novas, IDs originais SIGAB-074 a SIGAB-078**, e um épico de correções. As demais diferenças da análise são complementos das tarefas existentes, listados abaixo para evitar duplicação. O registro é local: nenhuma tarefa foi criada ou atualizada no Jira ou em outro serviço.

Os IDs originais são identificadores de planejamento, não chaves reais do Jira. Por exemplo, a chave real Jira SIGAB-74 já corresponde ao ID original SIGAB-050; a nova tarefa com ID original SIGAB-074 receberá outra chave na importação. Conferir sempre descrição e mapeamento.

## Novas tarefas

| ID original | Tarefa | Prioridade | Responsável sugerido | Dependências |
|---|---|---|---|---|
| SIGAB-074 | Reabrir divergências após recontagem e preservar resoluções | Highest | Backend/QA | 063, 055 |
| SIGAB-075 | Garantir uma única sessão de inventário aberta por unidade | High | Backend/QA | 062, 063 |
| SIGAB-076 | Corrigir conclusão assíncrona do atendimento no React | Highest | Frontend/QA | 068, 066 |
| SIGAB-077 | Preservar idempotência da cesta após resposta perdida | Highest | Frontend/Backend/QA | 076, 068, 066 |
| SIGAB-078 | Completar jornada React de entrada e liquidação quantitativa | High | Frontend/Backend/QA | 076, 077, 008, 041, 054, 069, 067 |

Números abreviados na tabela representam IDs originais SIGAB. Critérios completos, requisitos, arquivos de evidência e dependências estão nas descrições do CSV. Os estados locais foram atualizados após execução: 074–077 em `Done`; 078 permanece `To Do` com jornada apta implementada e dependências de domínio pendentes. Não representam atualização no Jira. Não há datas ou atribuições pessoais assumidas.

## Execução em 10/11/2026

[Entrega e evidências](../../validacao/tarefas-074-a-078.md).

- **074–077 concluídas tecnicamente:** recontagem e histórico de inventário, abertura concorrente, conclusão da cesta e recuperação idempotente.
- **078 parcialmente entregue:** área `/estoque` com entrada, saldos, pendências, devolução parcial apta e consumo justificado, revisão e confirmação. Aceite integral aguarda decisões de domínio 008/041; posições inaptas e aprovação de ajustes não foram habilitadas.
- **Validação:** 251 testes PostgreSQL aprovados, 2 ignorados; 14 jornadas Playwright aprovadas; 1 jornada real React/Django/PostgreSQL aprovada; verificações Django/Ruff, TypeScript e build aprovados.
- Migração `0011_unique_open_inventory` criada e verificada em bancos de teste; ainda não aplicada ao banco de desenvolvimento/produção.

## Complementos das tarefas existentes

Esta tabela registra o trabalho e os critérios adicionais identificados na revisão. **Não é um arquivo de atualização de status nem uma declaração de reabertura no Jira.** Resolver a chave real antes de incorporar o complemento ao chamado existente. Documentação de tarefas anteriores permanece como fotografia histórica.

| ID original existente | Prioridade proposta | Complemento e verificação de aceite |
|---|---|---|
| SIGAB-047 — linha de base | High | Reconciliar README, índice de requisitos, matriz de 09/11 e backlog com a revisão de 10/11. Registrar separadamente decisão, backend, interface, testes e aceite para os 55 requisitos. Corrigir afirmações de ausência de estoque/restrições/cesta; preservar cronologia e fonte original. |
| SIGAB-008 — modelo quantitativo | Highest | Decidir disponível/inapto, calibre e unidade base, quantidade inteira/fracionária, contrapartidas do livro e solicitação/aprovação por atores distintos. Comparar decisão 0003 com código e registrar responsáveis e evidência de aceite ou substituição formal. Não acrescentar lote por inferência. |
| SIGAB-041 — livro de estoque | Highest | Adequar o backend ao modelo aprovado na 008: devolução inapta não disponibiliza material; ajuste respeita aprovação definida; saldo reconcilia com livro e pendências. Testar entradas, devolução parcial, consumo, ajuste e estorno sem saldo negativo e com concorrência PostgreSQL. Não recriar operações já implementadas. |
| SIGAB-053 — atualização entre balcões | High | Com dois navegadores reais na mesma unidade, uma devolução atualiza a disponibilidade no outro dentro do prazo aceito. Verificar reconexão, falha de rede, acesso por escopo e ausência de atualização de outra organização. |
| SIGAB-054 — paginação e filtros | High | Navegar além de 100 itens, 200 pessoas e 20 resultados de pessoas na busca integrada. Expor unidade/tipo e definir período da busca. Verificar combinações, matrícula, limites e coleções grandes nas opções de atendimento e autosserviço, sem perda de resultados. |
| SIGAB-055 — auditoria e histórico | High | Padronizar antes/depois das alterações de pessoa/acervo e definir representação minimizada para campos pessoais. Preservar trilha das recontagens e resoluções. Conferir se o histórico do item inclui alterações cadastrais, além de movimentos. |
| SIGAB-056 — proteção da trilha | High | Definir proteção e ancoragem independente para detectar alteração/remoção por acesso privilegiado. Testar alteração, remoção e reescrita da cadeia; não equiparar hash local à impossibilidade de alteração. |
| SIGAB-057 — histórico de perfis e auditoria | High | Exibir concessões e revogações com ator, instante e motivo na ficha da pessoa. Verificar evolução de perfil sem recadastro e leitura somente por papel autorizado. |
| SIGAB-058 — comprovantes | High | Concluir documento imprimível de saída/devolução, incluindo saída individual fora da cesta, cesta mista, devolução parcial, consumo e estorno. Separar dados originais de situação atual, preservando o conteúdo histórico após mudanças posteriores. |
| SIGAB-059 — painel | High | Exibir total, disponível, em posse e inapto por tipo, respeitando unidade/organização. Reconciliar agregados com itens e livro quantitativo; definir tratamento de baixa. |
| SIGAB-060 — relatórios e exportação | High | Completar histórico de pessoa, tipo quantitativo e operador com datas/atores, filtros e exportação PDF. CSV existente de pendências é reaproveitado; não substitui PDF. Validar impressão e acesso por escopo. |
| SIGAB-061 — baixa/anulação | High | Implementar baixa com motivo, autor e histórico; tratar anulação/estorno de incorporação sem apagar original nem permitir saída indevida. Inatividade administrativa não substitui baixa formal. |
| SIGAB-062 / SIGAB-063 — inventário | High | Completar a jornada React de abertura, contagem, responsável, investigação, resolução e fechamento sobre as APIs existentes. Definir referência temporal e movimentos durante a sessão. Integrar as correções 074/075; resolução não altera saldo/baixa silenciosamente. |
| SIGAB-066 — jornadas de navegador | High | Ampliar verificações para limpeza após sucesso, ausência de erro, resposta perdida e reenvio, dois balcões e inventário. Jornadas com API simulada devem ser identificadas como tais; complementar com integração real para transações e banco. |
| SIGAB-067 — contrato de atendimento | High | Revisar resumo/confirmacão, modalidades, prazos e referência temporal do comprovante. Retirada por terceiro depende do formulário da 007; manter bloqueio até decisão explícita. |
| SIGAB-069 — pendências e histórico quantitativo | High | Expor tela consolidada por pessoa, unidade e organização, com acesso às ações da 078. Exibir histórico por tipo, quantidades em aberto e consumo justificado, ator/data e CSV integral. Verificar cenário 50 entregues, 20 devolvidos e 10 consumidos, restando 20 pendentes. |
| SIGAB-070 — autosserviço | Medium | Verificar histórico longo e paginação, identificação de quem entregou/recebeu, posse individual/quantitativa e acesso aos próprios comprovantes. Rejeitar identificadores de outra pessoa e acesso cruzado entre organizações. |
| SIGAB-052 — bloqueio comercial | Highest | Criar estado separado da suspensão de segurança. Em bloqueio comercial, negar novas saídas/cadastros e permitir devolução, consulta de posse e exportação, tanto na API quanto na interface. |
| SIGAB-071 / SIGAB-007 — capacidades futuras e formulário | Medium | Registrar decisão explícita de incluir, adiar ou retirar biometria, catálogo sugerido e retirada por terceiro. Obter formulário para definir retirante/usuário sem confundir operador com recebedor. Criar implementação apenas após decisão de escopo. |
| SIGAB-039 / SIGAB-072 — privacidade | High | Fechar política de anexos, retenção/descarte e leitura de dados pessoais. Distinguir anexos previstos em RF-24/30 do escopo atual sem anexos; registrar substituição/adiamento e testar acesso ao motivo restrito. |
| SIGAB-042 — backup e recuperação | High | Validar WAL/PITR, cópia externa, retenção, gestão de chaves, alertas e ensaio com volume representativo. Comprovar RPO ≤ 15 min e recuperação completa ≤ 4 h; dump e restauração sintética isolados não concluem esses critérios. |
| SIGAB-046 / SIGAB-045 — contingência e demonstração | High | Formalizar aceite de online + papel como substituição de RNF-01. Ensaiar queda, registro em papel, retomada e lançamento/reconciliação sem duplicidade, com responsável e evidência de homologação. Reaproveitar contingência já existente. |
| SIGAB-073 — desempenho e balcão | High | Acordar volume por turno e metas de saída/devolução; medir com dados sintéticos representativos, PostgreSQL e dois balcões. Validar seletores, listas grandes e permissões. Registrar aceites por cenário e versão. |

## Ordem de execução

1. Corrigir recontagem de inventário (074), conclusão do atendimento (076) e reenvio idempotente (077). Verificar abertura concorrente (075) em PostgreSQL.
2. Fechar a decisão quantitativa (008) e adequar garantias do livro (041). Atualização entre balcões (053) e consultas/paginação (054) podem avançar em paralelo conforme dependências.
3. Completar jornada quantitativa (078), pendências/históricos (069/070), inventário React (062/063), comprovantes e relatórios (058/060).
4. Concluir demais pendências conforme prioridade do piloto e executar continuidade, desempenho e homologação (042/045/046/073). Atualizar rastreabilidade durante as entregas.

## Importação e integridade

- CSV com 18 colunas, quatro `Labels` e seis `Is Blocked By`, no mesmo formato dos lotes anteriores.
- Um épico novo com ID local `3001`, antes das cinco tarefas; IDs locais sem colisão com os lotes anteriores.
- `Parent` e `Is Blocked By` apontam somente a registros deste lote. As demais dependências constam em `Dependências originais` e devem ser vinculadas manualmente às chaves reais existentes.
- Não importar a tabela de complementos como novas tarefas. Incorporar os critérios ao registro existente após identificar a chave correta.
- Não reimportar lotes para atualizar status e não aplicar o conversor do formato original a este CSV já preparado.
- Validados: cabeçalho, quantidade de campos, unicidade, sequência 074–078, referências internas, ausência de ciclos, existência das dependências antigas e presença dos critérios de aceite.
