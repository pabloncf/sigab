# Comparação entre requisitos e sistema atual — 10/11/2026

O sistema cobre o núcleo da operação individual e já tem uma primeira implementação de estoque, cesta mista, restrições, inventário e autosserviço. Ainda há requisitos ausentes, fluxos disponíveis apenas na API e diferenças entre decisões de domínio e código. As matrizes de 06/11 e 09/11 ajudam na rastreabilidade, mas contêm afirmações que já precisam de revisão.

Esta análise compara a [fonte DOC-0011 v0.1](../fontes/DOC-0011-analise-de-requisitos-v0.1.md), decisões posteriores, backend, rotas, frontend, testes e scripts de backup. Referência Git: `27e0d34`. Avalia o código local; não comprova a versão implantada nem aceite da organização-alvo. Nenhum fluxo da aplicação foi alterado.

## 1. Evidências executadas

- Suíte completa do backend com SQLite de teste: **223 passaram, 8 ignorados**, em 34,58 s. Os resultados não comprovam bloqueios/concorrência PostgreSQL.
- `bun run typecheck`: aprovado.
- Reprodução isolada de inventário, usando banco SQLite em memória, migrações e dados sintéticos: divergência resolvida, seguida de recontagem diferente, conservou `status=resolved`, responsável vazio e resolução anterior; a sessão fechou com `status=closed`.
- Inspeção dos serviços, modelos, APIs, componentes React, testes e workflows locais. PostgreSQL, navegador, restauração e desempenho não foram executados nesta revisão. Os workflows existentes não comprovam execução remota aprovada.

## 2. Ajustes prioritários encontrados

### A1. Inventário permite fechar uma divergência nova usando resolução antiga — alta

**Constatado por reprodução.** Em `record_inventory_count`, o `update_or_create` atualiza o resultado contado, mas preserva status, resolução e responsável da divergência anterior. `close_inventory_session` aceita esse status antigo como suficiente.

**Cenário:** contar como ausente → resolver → recontar como indisponível → fechar. A recontagem mudou o fato investigado, mas nenhuma nova resolução foi exigida. Também é possível resolver sem responsável atribuído, embora RF-42 peça responsável e status.

**Ajustar:** reabrir a divergência quando mudar o resultado, preservar o histórico das resoluções e definir responsável obrigatório. Reavaliar também a exclusão física de divergências abertas quando a recontagem coincide com o esperado: a auditoria de contagem permanece, mas a ocorrência deixa de existir na consulta.

**Verificar:** recontagem após resolução/justificativa, mudança de responsável, contagem corrigida e fechamento concorrente com atualização de divergência. A abertura usa consulta de existência sem bloqueio da unidade nem unicidade condicional de sessão aberta: testar duas aberturas simultâneas no PostgreSQL.

Evidências: [serviço de inventário](../../backend/sigab/domain/inventory.py), [modelos](../../backend/sigab/models.py), [testes existentes](../../backend/sigab/tests/test_requirements_063_070.py).

### A2. Atendimento pode mostrar erro depois de uma saída já confirmada — alta

**Identificado por inspeção estática.** `ServiceBatchPage.submit` usa `event.currentTarget.reset()` depois de aguardar a resposta. O React limpa `currentTarget` ao terminar o despacho do evento; a continuação assíncrona pode acessar `null`. A chamada ocorre antes de limpar as seleções e atualizar as opções.

**Efeito esperado:** atendimento gravado, comprovante mostrado, mensagem de erro e seleções antigas mantidas. O E2E atual verifica comprovante e uma requisição, mas não verifica ausência de erro ou limpeza do formulário.

**Ajustar:** guardar a referência do formulário antes do `await` e validar o ciclo completo de sucesso. Confirmar o comportamento em navegador antes de encerrar o ajuste.

Evidências: [tela de atendimento](../../frontend/src/features/operations/ServiceBatchPage.tsx:28), [jornadas](../../frontend/e2e/journeys.spec.ts).

### A3. Reenvio da cesta não conserva a chave de idempotência — alta

**Constatado no código.** A tela gera `newKey()` em cada submissão. O backend reconhece repetições da mesma chave, mas o reenvio do formulário passa a ser outra operação.

**Risco:** se a saída foi gravada e a resposta se perdeu, uma cesta só quantitativa pode ser entregue novamente se ainda houver saldo. A atomicidade de uma requisição não impede duplicação entre requisições com chaves diferentes.

**Ajustar:** conservar a chave e o conteúdo da tentativa enquanto o resultado for incerto; trocar a chave apenas para um novo atendimento. Verificar resposta perdida, timeout, reenvio, duplo clique e troca de conteúdo. Conferir que existe apenas uma saída no banco, inclusive para cesta exclusivamente quantitativa.

Evidências: [geração da chave no frontend](../../frontend/src/features/operations/ServiceBatchPage.tsx:50), [idempotência do serviço](../../backend/sigab/domain/operations.py).

### A4. Estoque implementado diverge da decisão 0003 — alta

Não é correto tratar estoque como ausente. Há entrada, saída, pendência, devolução parcial, consumo, ajuste e estorno nos serviços. Entretanto:

| Decisão 0003 | Código atual | Ajuste ou decisão necessária |
|---|---|---|
| Separar posição disponível e inapta | `StockBalance` possui uma quantidade por tipo/unidade/local, sem condição | Definir devolução quantitativa inapta. Hoje a devolução soma ao saldo disponível sem conferir condição. |
| Solicitação e aprovação de ajuste por atores distintos | `adjust_stock` aplica diretamente para quem possui `inventory.adjust.approve` | Implementar solicitação/aprovação ou registrar substituição formal da decisão. |
| Lançamentos em partidas de soma zero | Livro registra quantidade, delta do saldo e vínculo à pendência, sem modelo explícito de contrapartidas | Decidir se esse modelo simplificado será aceito e especificar sua reconciliação. |
| Calibre e unidade base estruturados e imutáveis após lançamento | `EquipmentType` tem nome, descrição e classificação | Definir dados estruturados, conversões e regras de imutabilidade. Nome livre não garante o modelo por calibre. |
| Modelo proposto usa quantidades inteiras | Código permite três casas decimais | Validar unidade de medida e granularidade por tipo. |

A decisão está identificada como proposta com validações pendentes; a divergência exige decisão de Produto/Domínio, não implementação automática de tudo que ela descreve. Lote não era obrigação literal do DOC-0011 e não deve ser acrescentado por inferência.

**Verificar:** entregar 50, devolver 20 aptos, justificar consumo de 10 e manter 20 pendentes; tratar devolução inapta sem disponibilizá-la; estornar cada operação; rejeitar saldo negativo; executar disputas por saldo no PostgreSQL.

Evidências: [decisão 0003](../decisoes/0003-modelo-de-estoque-e-municao.md), [operações](../../backend/sigab/domain/operations.py), [modelos](../../backend/sigab/models.py).

### A5. Algumas capacidades não têm jornada operacional completa no React — alta

O roteamento atual expõe acervo, detalhe, pessoas, cadastros, atividade, atendimento, restrições e autosserviço. Existem APIs de inventário, pendências consolidadas, entrada/devolução/consumo quantitativo e exportação CSV, mas faltam páginas correspondentes para operá-las de ponta a ponta. O ajuste quantitativo existe no serviço, sem rota própria no arquivo de URLs inspecionado.

**Ajustar:** concluir as jornadas sobre serviços existentes e definir permissões e confirmação. Não criar novamente o livro ou a consulta já disponíveis.

**Verificar:** um operador sem acesso direto à API consegue registrar entrada, conferir pendências, devolver parte, justificar consumo, inventariar e exportar? Registrar resultado por papel.

Evidências: [rotas React](../../frontend/src/App.tsx), [rotas API](../../backend/sigab/api/urls.py), [operações API](../../backend/sigab/api/operations.py), [pendências](../../backend/sigab/api/self_service.py).

### A6. Falta atualização entre balcões e navegação completa das listas — alta

- RNF-02: não foi encontrado push, polling ou outro mecanismo de atualização entre clientes. A transação libera o item no servidor; outra tela aberta mantém o estado anterior até nova consulta.
- Acervo mostra até 100 itens; pessoas até 200, com orientação para refinar busca, sem navegação pelos demais resultados.
- Busca integrada limita pessoas a 20. A API filtra itens por unidade/tipo, mas a página não oferece esses seletores. Período está no feed, não na busca integrada.
- Autosserviço e opções de atendimento carregam coleções completas sem paginação, o que exige avaliação de volume.

**Verificar:** dois navegadores na mesma unidade; devolução em um e nova saída no outro; pessoas e itens além dos limites; filtros combinados e busca por matrícula; histórico longo no autosserviço.

Evidências: [acervo](../../frontend/src/pages/ItemsPage.tsx), [pessoas](../../frontend/src/pages/PeoplePage.tsx), [busca e filtros](../../backend/sigab/api/views.py), [autosserviço](../../backend/sigab/api/self_service.py).

### A7. Comprovante de atendimento não cobre comprovantes imprimíveis e PDF — média

Há código de comprovante na cesta e consulta pessoal de seu conteúdo. Falta o documento próprio de saída e devolução para impressão e a exportação PDF dos relatórios. O comprovante atual consulta dados relacionados, incluindo quantidade ainda aberta; definir quais informações devem refletir o instante original e quais representam situação atual.

**Verificar:** saída individual fora da cesta, saída mista, devolução parcial, consumo e estorno; acesso do operador e do destinatário; documento original preservado após mudanças posteriores.

Evidências: [serialização do comprovante](../../backend/sigab/api/operations.py), [consulta pessoal](../../frontend/src/features/self-service/MyPossessionsPage.tsx).

### A8. Lacunas funcionais ainda presentes — prioridade por necessidade do piloto

- **Bloqueio comercial (RF-06/RN-07):** suspensão genérica desativa permissões; falta estado que bloqueie novas saídas/cadastros e preserve devolução, consulta e exportação.
- **Baixa e anulação de incorporação (RF-14/RN-05):** `inactive` não substitui baixa com motivo, autor e histórico; estorno de movimentos não cobre automaticamente a incorporação.
- **Painel agregado (RF-40):** lista e total de resultados não substituem total/disponível/em posse/inapto por tipo.
- **Histórico de perfil (RF-04):** concessões e revogações existem; falta apresentar a evolução na ficha da pessoa.
- **Histórico do operador e PDFs (RF-55/56):** auditoria filtra ator, mas falta relatório operacional completo na interface e PDF.
- **Retirada por terceiro (RF-25/RN-10):** campo de modelo não significa fluxo habilitado; permanece bloqueado até validação do formulário.
- **Biometria e catálogo sugerido (RF-05/11):** ausentes; decidir se entram no incremento. A operação sem biometria já existe.
- **Anexos (RF-24/30):** indisponíveis na política atual; registrar adiamento ou substituição do requisito original.

### A9. Auditoria, continuidade e homologação precisam de evidência própria — alta antes de uso real

A auditoria tem proteção na aplicação e cadeia local de hashes. Ainda não equivale à impossibilidade de alteração por SQL privilegiado; falta ancoragem independente. Registros como `person.update` guardam nomes de campos alterados, sem antes/depois, portanto RF-60 não é uniforme. Para campos pessoais, definir uma representação compatível com a minimização de dados.

Backup criptografado, timer, restauração sintética e workflow existem. Dump diário não comprova o RPO de 15 minutos definido posteriormente; WAL/PITR, cópia externa, retenção, chaves e restauração completa no RTO ainda precisam de ensaio representativo.

RNF-01 também mudou: a decisão adotou operação online com papel e lançamento posterior. Isso exige aceite formal da substituição da continuidade digital originalmente pedida.

Evidências: [serviços de auditoria](../../backend/sigab/services.py), [backup](../backup-e-restauracao.md), [script](../../ops/backup/backup.sh), [contingência](../adr/0004-conectividade-e-contingencia.md).

## 3. Matriz revisada dos 55 requisitos e regras

**I:** implementação identificada no caminho normal da aplicação; **P:** atendimento parcial; **A:** capacidade ausente. I não significa homologado nem proteção contra qualquer escrita direta no banco. As evidências por domínio estão nas seções anteriores e nas [revisões existentes](linha-base-2026-11-09.md).

| ID | Estado | Diferença ou verificação necessária |
|---|---|---|
| RF-01 | I | Organização e isolamento implementados; validar implantação e acesso por papel. |
| RF-02 | I | Organização + matrícula + senha; contas técnicas têm caminho separado. |
| RF-03 | I | Campos distribuídos entre pessoa, vínculo, conta e concessão; validar vocabulário. |
| RF-04 | P | Alterar acesso sem recadastrar existe; falta histórico apresentado na pessoa. |
| RF-05 | A | Vinculação biométrica ausente; alternativa sem biometria existe. |
| RF-06 | A | Falta bloqueio comercial compatível com RN-07. |
| RF-10 | I | Tipos individual e quantitativo. |
| RF-11 | A | Sem catálogo pré-carregado de sugestões. |
| RF-12 | I | Incorporação via serviço; Admin operacional somente leitura. |
| RF-13 | P | Entrada quantitativa existe na API; fechar modelo e jornada React. |
| RF-14 | P | Disponível, posse e inapto individuais; falta baixa formal. |
| RF-15 | P | Detalhe e movimentos existem; histórico completo de alterações não uniforme. |
| RF-16 | I | Classificação não muda nos caminhos ordinários da aplicação. |
| RF-20 | P | Cesta mista existe; corrigir conclusão no frontend e reenvio. |
| RF-21 | P | Confirmações existem; falta resumo e garantia uniforme em alterações de acervo. |
| RF-22 | P | Individual confere apto/inapto; quantitativo não separa devolução inapta. |
| RF-23 | I | Devolução individual apta libera no servidor; atualização entre clientes é RNF-02. |
| RF-24 | P | Devolução parcial/consumo com motivo existem na API; faltam jornada e anexos. |
| RF-25 | A | Retirada por terceiro desabilitada. |
| RF-26 | P | Conteúdo/código de comprovante de cesta existem; falta documento imprimível de saída/devolução. |
| RF-27 | P | API consolida pendências individuais/quantitativas por pessoa/unidade; falta tela própria. |
| RF-30 | P | Restrições implementadas; anexos indisponíveis e aceite pendente. |
| RF-31 | I | Bloqueio transacional por vigência/tipo sem divulgar motivo ao operador. |
| RF-32 | I | Alteração/encerramento com motivo, confirmação e eventos. |
| RF-40 | A | Falta painel agregado por tipo e estado. |
| RF-41 | P | Contagem individual via API; falta jornada, reconciliação e teste de abertura concorrente. |
| RF-42 | P | Ocorrências existem; falha reproduzida de recontagem e responsável não obrigatório. |
| RF-50 | P | Busca existe; faltam paginação completa na UI, seletores e período integrado. |
| RF-51 | I | Posse própria individual/quantitativa disponível; validar volume de coleções completas. |
| RF-52 | P | Feed individual informa ator/data; autosserviço não expõe operador em cada linha e falta jornada completa do histórico quantitativo. |
| RF-53 | I | Histórico paginado do item e indicação de estornos. |
| RF-54 | P | Livro quantitativo existe; falta consulta dedicada por tipo e interface completa. |
| RF-55 | P | Filtro técnico por ator na auditoria; falta relatório operacional de entregas/recebimentos. |
| RF-56 | A | CSV de pendências existe; exportação PDF de relatórios ausente. |
| RF-60 | P | Registro de eventos existe; antes/depois não é uniforme. |
| RF-61 | P | Feed individual implementado; não reúne integralmente estoque, restrições e demais domínios. |
| RF-62 | P | Proteção na aplicação e hashes locais; sem garantia contra SQL privilegiado/reescrita integral. |
| RN-01 | P | Perfil evolui sem recadastro; deduplicação da pessoa depende de CPF opcional e vínculos. |
| RN-02 | P | Série e patrimônio têm unicidade separada; definir identificador canônico e duplicidades cruzadas. |
| RN-03 | I | Classificação protegida nos caminhos ordinários. |
| RN-04 | P | Saldos mudam via serviços; modelo e aprovação de ajustes divergem da decisão 0003. |
| RN-05 | P | Estornos individuais/quantitativos existem; falta anulação de incorporação. |
| RN-06 | I | Restrição vigente bloqueia entrega aplicável e permite devolução. |
| RN-07 | A | Suspensão atual não implementa bloqueio comercial seletivo. |
| RN-08 | P | Individual inapto bloqueado; falta representar estoque quantitativo inapto. |
| RN-09 | P | Motivos já exigidos em consumo, ajuste, restrição, perfil e estorno; baixa ausente. |
| RN-10 | A | Sem fluxo habilitado de retirante distinto do usuário. |
| RNF-01 | P | Online + papel + lançamento posterior; substituição do requisito original depende de aceite. |
| RNF-02 | A | Sem sincronização entre balcões. |
| RNF-03 | P | Mesma limitação de RF-62. |
| RNF-04 | P | Minimização e acesso restrito existem; retenção/descarte e aceite institucional pendentes. |
| RNF-05 | I | Isolamento por organização e testes negativos; validar implantação. |
| RNF-06 | P | Cesta existe; falta ensaio de balcão, seletores adequados ao volume e correção do sucesso. |
| RNF-07 | P | Backup/restauração sintética existem; faltam evidências de RPO/RTO em ambiente representativo. |
| RNF-08 | P | Volume e metas precisam ser acordados e medidos; suíte funcional não mede capacidade. |

## 4. Documentação e planejamento a reconciliar

| Documento | Problema identificado | Tratamento recomendado |
|---|---|---|
| `README.md` | Abertura ainda limita a entrega a item individual, embora outras capacidades estejam presentes. | Atualizar escopo técnico e explicitar quais jornadas dependem de API. |
| `docs/requisitos.md` | Fotografia de 06/11 diz que estoque, restrições e inventário não têm fluxos. | Apontar para revisão atual; preservar a fotografia histórica identificada pela data. |
| Linha de base de 09/11 | RN-09 diz que consumo/ajuste/restrição não existem; RNF-06 diz que não há cesta. RF-27 não reconhece consolidação quantitativa da API. | Corrigir referência atual com evidências e separar interface, serviço e aceite. |
| Linha de base de 09/11 | Restrições de isolamento/validação institucional aparecem misturadas ao estado técnico de RF-01/RNF-05. | Registrar implementação, testes e aceite em colunas separadas. |
| Entrega Jira 71–75 | Texto diz que CI foi removido; workflows existem no checkout. | Registrar o estado atual sem reescrever a cronologia dos commits. |
| Backlog de 06/11 | Todas as novas tarefas aparecem `To Do`, mas há implementações posteriores. | Reconciliar com evidências por critério e chave real do Jira, sem reimportar o CSV como atualização de status. |

Não houve consulta ao Jira nesta revisão. Os IDs locais não devem ser tratados automaticamente como chaves reais; o mapeamento conhecido de 047–051 para Jira 71–75 está na documentação de entrega.

## 5. Sequência de verificação e ajuste

1. **Fechar falhas dos fluxos existentes:** A1–A3, com regressões específicas de inventário, sucesso da cesta e reenvio após resposta perdida.
2. **Decidir o modelo quantitativo:** disponível/inapto, unidade/calibre, aprovação de ajuste e reconciliação do livro. Registrar o que foi aceito ou substituído na decisão 0003.
3. **Completar operação e consulta:** telas quantitativas e inventário, paginação, filtros, sincronização entre balcões, comprovantes e pendências.
4. **Completar ciclo de vida e gestão:** baixa/anulação, bloqueio comercial, painel, histórico de perfis e relatórios/PDF conforme prioridade do piloto.
5. **Validar o piloto com dados sintéticos representativos:** duas sessões reais com PostgreSQL, dois tenants, perfis distintos, falha de rede, restrição concorrente e estorno; medir tempos com volume acordado.
6. **Ensaiar continuidade e registrar aceite:** restauração/PITR, procedimento em papel e reconciliação posterior; documentar responsável, versão e resultado de cada cenário.

Para cada requisito, manter separadamente **decisão de escopo, implementação backend, interface, teste e aceite**. Uma capacidade entregue na API pode ser reaproveitada sem ainda estar pronta para operação no balcão.
