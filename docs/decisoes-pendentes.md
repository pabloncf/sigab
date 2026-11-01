# Decisões pendentes

| Tema | Tarefa | Estado/impacto |
|---|---|---|
| Primeiro segmento | SIGAB-001 | decidido e validado: Guardas Municipais; ver [decisão 0001](decisoes/0001-segmento-inicial.md) |
| Obrigações regulatórias | SIGAB-005 | pesquisa federal preliminar concluída; validação municipal/jurídica pendente; ver [nota regulatória 0001](notas-regulatorias/0001-guardas-municipais.md) |
| Conectividade, contingência, RPO/RTO | SIGAB-006 | decidida: online exclusivo, contingência em papel, RPO ≤ 15 min e RTO ≤ 4 h; ver [ADR 0004](adr/0004-conectividade-e-contingencia.md) |
| Registro de movimentação de contingência | SIGAB-046 | bloqueia operação real; lançamento com instante do fato e referência ao papel, exigido pelo ADR 0004 |
| Matriz final de papéis | SIGAB-004 | decidida; ver [decisão e matriz 0002](decisoes/0002-papeis-e-escopos.md) |
| Formulário de armamento temporário e retirada por terceiro | SIGAB-007 | análise preliminar com modelos públicos de outros Municípios em [pesquisa 0001](pesquisas/0001-formulario-armamento-temporario.md); nenhuma fonte autoriza retirada por terceiro (cautela "pessoal e intransferível"); RF-25 exige decisão; modelo local ainda não obtido |
| Estoque, lotes e munição | SIGAB-008 | modelo proposto em [decisão 0003](decisoes/0003-modelo-de-estoque-e-municao.md) (livro de partidas dobradas por tipo, saldo não negativo); controle só por calibre, sem lote, validado no sistema de referência em 2026-10-19; faltam a organização-alvo, o impacto da OBR-10 e o anexo de consumo; SIGAB-041 segue bloqueada; nenhuma implementação |
| Ciclo de vida do item individual | SIGAB-009 | decidido e validado: [decisão 0004](decisoes/0004-ciclo-de-vida-do-item-individual.md), com base no DOC-0011; matriz de papéis 1.1.0 com `item.condition.set`; liberação de inapto, motivo obrigatório e bloqueio de item inativo na saída implementados; estorno e anulação (T20) ainda sem implementação |
| Stack e frontend | SIGAB-010 | decidida: Django + API `/api/v1/` + React/TypeScript/Vite, PostgreSQL 17; ver [ADR 0005](adr/0005-api-django-e-frontend-react.md); pendentes: testes e lint do frontend e servidor de aplicação/empacotamento de produção |
| Dados pessoais e retenção | SIGAB-039 | linha de base e dependências identificadas na nota regulatória 0001; política municipal e tabela de temporalidade pendentes |
| Biometria, restrições, anexos e integrações | futuras | deliberadamente ausentes |
| Manutenção, sinistro, transferência e baixa | futuras | transições decididas na [decisão 0004](decisoes/0004-ciclo-de-vida-do-item-individual.md) (T07–T18 e seção 10); sem implementação nem tarefa no backlog |
| Prova/assinatura e comprovantes | futura | ausentes |
| Dupla aprovação e estorno operacional | futura | modelo preserva fatos; UI não implementada |
| Catálogo global e licenciamento | futura | catálogo privado por organização |

