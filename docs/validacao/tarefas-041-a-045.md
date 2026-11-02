# Entrega e validação das tarefas 041 a 045

Revisão: 2026-11-02. Requisitos continuam propostos até validação com a organização-alvo.

| Tarefa | Entrega/evidência | Estado |
|---|---|---|
| 041 — estoque quantitativo | [decisão 0003, seções 12–13](../decisoes/0003-modelo-de-estoque-e-municao.md#12-questões-para-validar-com-a-guarda-participante) | bloqueada pela SIGAB-008; sem implementação de estoque |
| 042 — backup/restauração | scripts, timer, imagem de ferramentas e [procedimento](../backup-e-restauracao.md) | implementação técnica; aceite de continuidade em produção pendente |
| 043 — fluxo vertical | `backend/sigab/tests/test_vertical_flow.py` + suítes de isolamento e concorrência | teste HTTP integrado com CSRF, banco e autorização reais; CI em PostgreSQL; comportamento do navegador React ainda não coberto |
| 044 — operação | README, procedimento de backup e esta rastreabilidade | documentação atualizada, limitações explícitas |
| 045 — demonstração | roteiro e ata abaixo | preparada; sessão com usuário-alvo não realizada |

## SIGAB-041: informações necessárias

Registrar na decisão 0003 responsável, data e evidência para: controle por calibre/lote na Guarda participante; unidades inteiras ou fracionárias; posições e pendências do livro; justificativa de consumo; validade; estojos; transferência; aprovação de ajuste. A confirmação no sistema de referência não confirma o processo da organização-alvo.

Após resolver a SIGAB-008, implementar e testar entrada, saída, devolução parcial apta/inapta, consumo justificado, ajuste e estorno com vínculo ao original. Para cada operação verificar saldo derivado de eventos, saldo não negativo sob concorrência PostgreSQL, conservação entre posições, isolamento por organização, permissão/escopo, ator/origem/motivo, imutabilidade e idempotência. Definir permissões na matriz antes de expor API e telas. Não há decisão implícita de lotes ou unidades neste incremento.

## Rastreabilidade da SIGAB-043

| Cenário | Requisitos/tarefas | Evidência automatizada |
|---|---|---|
| cadastro de unidade, local, tipo, pessoa e vínculo; incorporação | RF-12; SIGAB-019/020/024/026/027 | teste vertical, `test_identity.py`, `test_catalog.py`, `test_items.py` |
| saída confirmada; repetição da mesma chave; dupla saída bloqueada | RF-20; SIGAB-030/031 | teste vertical, `test_api.py`, `test_concurrency.py` |
| devolução e disponibilidade | RF-22; SIGAB-032/033 | teste vertical, `test_flow.py` |
| histórico e auditoria | RF-53; RF-60; SIGAB-028/035 | teste vertical, `test_audit.py` |
| negação sem permissão e entre organizações | RF-01; SIGAB-022/025 | teste vertical, `test_isolation.py`, `test_authorization.py` |

O fluxo integrado cria os cadastros pela API; apenas contas e concessões para montar o ambiente são criadas diretamente no teste. Usa sessões autenticadas e CSRF obrigatório. Não é um teste de navegador e não substitui validação visual/usabilidade.

## SIGAB-045: roteiro da sessão com usuário-alvo

Pré-condições: identificar organização participante e armeiro/gestor que executa o processo real (SIGAB-002); confirmar autorização para sessão e registro das respostas; usar ambiente isolado com dados sintéticos; registrar revisão Git demonstrada. Não usar acervo ou dados pessoais reais.

1. Apresentar limites: item individual online; estoque quantitativo e reconciliação de contingência ainda indisponíveis; sem alegação de conformidade ou aceite de produção.
2. Gestor cadastra unidade, reserva, tipo, pessoa/vínculo e incorpora item sintético.
3. Operador localiza item e destinatário e confirma a saída. Conferir posse e histórico.
4. Repetir confirmação e tentar segunda saída: conferir ausência de duplicidade e clareza do erro.
5. Devolver como apto; repetir como inapto com motivo e conferir disponibilidade.
6. Mostrar tentativa sem permissão e acesso de outra organização; conferir negação sem vazamento.
7. Mostrar histórico/auditoria e explicar backup, contingência em papel e limitações.
8. Pedir ao participante para executar o fluxo, registrar pontos de dúvida e comparar com o processo observado. Registrar aceite/rejeição por cenário, sem inferir aceite por silêncio.

## Ata — aguardando sessão

- Data/hora/fuso: **não realizada**.
- Organização-alvo e participantes/papéis: **pendentes**.
- Facilitador e revisão Git: **pendentes**.
- Evidência de observação do processo real (SIGAB-002): **pendente**.

| Cenário/requisito/tarefa | Resultado observado | Aceito/rejeitado/pendente | Feedback literal ou síntese confirmada | Mudança e tarefa vinculada | Responsável/prazo |
|---|---|---|---|---|---|
| Cadastro/incorporação — RF-12 / SIGAB-027 | não demonstrado | pendente | — | — | — |
| Saída/dupla saída — RF-20 / SIGAB-030/031 | não demonstrado | pendente | — | — | — |
| Devolução — RF-22 / SIGAB-033 | não demonstrado | pendente | — | — | — |
| Histórico/auditoria — RF-53/60 / SIGAB-028/035 | não demonstrado | pendente | — | — | — |
| Autorização/isolamento — RF-01 / SIGAB-022/025 | não demonstrado | pendente | — | — | — |

Após a sessão: anexar evidência autorizada, vincular mudanças ao backlog com prioridade e responsável, registrar rejeições sem marcar requisito validado e agendar reteste dos itens corrigidos. Preparar este roteiro não conclui a SIGAB-045.

## Verificações executadas em 2026-11-02

- Ruff (formatação e lint), Django check e migrações sem alterações: passaram.
- SQLite: 181 testes passaram, 5 ignorados (concorrência PostgreSQL e medição opcional de volume).
- PostgreSQL 17 descartável: 185 testes passaram, 1 ignorado (`SIGAB_PERF`, ensaio opcional de volume).
- Frontend: typecheck e build passaram.
- Backup e restauração reais: [relatório sintético](restauracao-sintetica-2026-11-02.json), 1 organização, 1 item, 3 movimentos e 3 registros de auditoria; restauração e verificações em 0,636 s. Volume mínimo sintético, sem extrapolação para produção.
- Falhas verificadas: chave incorreta, corrupção de checksum, ciphertext adulterado mesmo com checksum recalculado, dump de banco inexistente; sem relatório falso de sucesso e com limpeza dos bancos descartáveis.
- Graphify atualizado por AST local. O utilitário avisou que a matriz JSON de papéis e o relatório JSON de restauração não produziram nós; ambos permanecem disponíveis nos arquivos originais.

O CI remoto será disparado pelo push; os resultados acima são locais e não antecipam o resultado do GitHub Actions.
