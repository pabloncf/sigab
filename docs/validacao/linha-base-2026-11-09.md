# Linha de base e rastreabilidade — tarefas originais 047–051

Data: 09/11/2026. Esta matriz atualiza tecnicamente a revisão de 06/11 sem substituir a fonte DOC-0011 ou declarar aceite de Produto. I técnico significa implementação com testes, não aprovação institucional. P: parcial; A: ausente.

## Identificação das tarefas

A lista de importação fornecida pelo usuário associa Jira SIGAB-71–75 às tarefas originais SIGAB-047–051, nesta ordem. Os componentes e prioridades coincidem com o CSV. Não inferir o conteúdo da chave Jira SIGAB-70. O commit 5702369 se refere aos IDs originais 063–070, não às chaves Jira.

## Cronologia e decisões

- DOC-0011 v0.1 continua como fonte original proposta, intacta; referência documental não equivale a entrevista ou aceite do alvo.
- ADR 0002 e matriz 0002 substituem hierarquia implícita por concessões explícitas e escopos. Aprovação institucional continua pendente onde não há ata.
- ADR 0004 define online com livro de papel e lançamento posterior; não representa operação digital offline (RNF-01).
- ADR 0006 define eventos imutáveis e compensação por estorno. Documentos antigos contrários a estorno devem ser lidos pela cronologia desse ADR.
- A revisão 06/11 registra lacunas naquele instante. Commit 5702369 e esta entrega acrescentam implementação; não retroagem a revisão nem comprovam nova entrevista.
- Restrições seguem a decisão 0005: sem anexos, laudos ou exceção. Escopo suportado: todos os materiais ou tipos explícitos. Classes agregadas e recolhimento automático continuam pendentes.

## Matriz dos 55 requisitos e regras

Todos os registros abaixo têm revisão de referência concluída e validação com o alvo/aceite pendentes. Produto responde por escopo e aceite; Backend/Frontend/QA respondem por implementação e evidências técnicas. Jurídico/Encarregado respondem pelas aprovações institucionais de privacidade.

| Requisito | Estado técnico | Evidência ou pendência | Responsável sugerido |
|---|---|---|---|
| RF-01 | P | Admin operacional somente leitura e sem acesso global; homologação institucional pendente. | Produto / Backend / Frontend / QA |
| RF-02 | I técnico | Login por organização UUID + matrícula ativa; contas técnicas usam username. | Produto / Backend / Frontend / QA |
| RF-03 | I | Campos distribuídos entre Person, Membership e Account/Grant; separação correta de responsabilidades. | Produto / Backend / Frontend / QA |
| RF-04 | P | Concessão/revogação preserva pessoa, ator e motivo. Não há histórico de alterações de perfil apresentado na ficha da pessoa; a trilha usa objetos Grant e a tela mostra concessões ativas. | Produto / Backend / Frontend / QA |
| RF-05 | A | Operação sem biometria existe; vinculação biométrica opcional não foi implementada. | Produto / Backend / Frontend / QA |
| RF-06 | A | Há suspensão administrativa, mas não bloqueio comercial que preserve devoluções, consultas e exportações. | Produto / Backend / Frontend / QA |
| RF-10 | I | Cadastro distingue `individual` e `quantitative`. Isso atende a classificação do tipo, não implementa estoque. | Produto / Backend / Frontend / QA |
| RF-11 | A | Sem catálogo de sugestões pré-carregado; catálogo atual é privado da organização. | Produto / Backend / Frontend / QA |
| RF-12 | I técnico | Incorporação confirmada por serviço; Admin não permite escrita. | Produto / Backend / Frontend / QA |
| RF-13 | P | Livro quantitativo básico no commit 5702369; validação de lote/calibre e domínio 0003 pendente. | Produto / Backend / Frontend / QA |
| RF-14 | P | Disponível, em posse e inapto existem por composição de campos. Baixa não tem fluxo; `inactive` não equivale a baixa com motivo. | Produto / Backend / Frontend / QA |
| RF-15 | P | Detalhe, posse e movimentos paginados existem. Histórico exibido é MovementEvent; alterações cadastrais pelo Admin ficam fora desse histórico. | Produto / Backend / Frontend / QA |
| RF-16 | I | Classificação de tipo imutável no caminho de edição da aplicação. | Produto / Backend / Frontend / QA |
| RF-20 | P | Cesta mista disponível; contrato anterior e homologação de produto pendentes. | Produto / Backend / Frontend / QA |
| RF-21 | P | Movimentos e incorporação exigem confirmação. Não é garantia uniforme para toda alteração de acervo: edição de tipo e Admin não usam o mesmo contrato de resumo/confirmação. | Produto / Backend / Frontend / QA |
| RF-22 | I | Devolução individual exige condição apto/inapto, com motivo quando inapto. | Produto / Backend / Frontend / QA |
| RF-23 | I | Devolução apta libera o item na transação. Disponibilidade no servidor não significa atualização automática das outras telas (RNF-02). | Produto / Backend / Frontend / QA |
| RF-24 | P | Devolução parcial/consumo implementados; anexos permanecem desabilitados. | Produto / Backend / Frontend / QA |
| RF-25 | A | `operator` é quem lança e `recipient` quem recebe; não existe terceiro retirante distinto do usuário do material. | Produto / Backend / Frontend / QA |
| RF-26 | A | Sem comprovante próprio de saída/devolução para impressão. | Produto / Backend / Frontend / QA |
| RF-27 | P | Posse individual consultável por pessoa, unidade/escopo e organização; sem gestão consolidada das pendências quantitativas ou tela específica de pendências. | Produto / Backend / Frontend / QA |
| RF-30 | P | Cadastro de restrição implementado sem anexos; política de anexos pendente. | Produto / Backend / Frontend / QA |
| RF-31 | I técnico | Saída verifica vigência e tipo dentro da transação; motivo não chega ao operador. | Produto / Backend / Frontend / QA |
| RF-32 | I técnico | Alteração e encerramento confirmados, eventos imutáveis e auditoria minimizada. | Produto / Backend / Frontend / QA |
| RF-40 | A | Listagem de itens e total de resultados não constituem painel agregado por tipo e estado. | Produto / Backend / Frontend / QA |
| RF-41 | P | Sessões e contagem implementadas; reconciliação de movimentos durante sessão ainda requer validação. | Produto / Backend / Frontend / QA |
| RF-42 | P | Divergências auditadas; integração das resoluções com baixa ainda pendente. | Produto / Backend / Frontend / QA |
| RF-50 | P | Busca integrada por referências existe; período está no feed, não na busca. UI de acervo expõe situação, mas não seletores de unidade/tipo; resultados limitados. | Produto / Backend / Frontend / QA |
| RF-51 | P | Autosserviço com posse, histórico e comprovantes; paginação completa ainda pendente. | Produto / Backend / Frontend / QA |
| RF-52 | I | Feed filtrado por destinatário reúne saídas/devoluções com data e ator; não é necessário um módulo novo para isso. | Produto / Backend / Frontend / QA |
| RF-53 | I | Histórico do item com paginação, saídas, devoluções e identificação de estorno. | Produto / Backend / Frontend / QA |
| RF-54 | P | Livro e consultas quantitativas básicos; reconciliação ampla e interface de relatórios pendentes. | Produto / Backend / Frontend / QA |
| RF-55 | P | Auditoria filtra ator, permitindo consulta técnica; feed operacional não filtra armeiro e não há relatório correspondente na UI. | Produto / Backend / Frontend / QA |
| RF-56 | A | Sem exportação PDF dos relatórios. Imprimir página pelo navegador não equivale à entrega desse requisito. | Produto / Backend / Frontend / QA |
| RF-60 | P | Ator, ação, instante e motivo disponíveis; antes/depois não são uniformes. Admin registra nomes de campos, e movimentos nem sempre registram ambos os estados em `changes`. | Produto / Backend / Frontend / QA |
| RF-61 | I | Feed cronológico com filtro por pessoa, item e ação; pessoa/item entram também por links e parâmetros. | Produto / Backend / Frontend / QA |
| RF-62 | P | Imutabilidade na aplicação e cadeia de hashes; SQL privilegiado não é impedido e falta âncora externa. Detecção não equivale a impossibilidade de alteração. | Produto / Backend / Frontend / QA |
| RN-01 | P | Matrícula e CPF preenchido são únicos por organização; CPF opcional e múltiplos vínculos não asseguram deduplicação de toda pessoa física. Perfil evolui sem recadastrar pessoa. | Produto / Backend / Frontend / QA |
| RN-02 | P | Série e patrimônio têm unicidade separada por organização; falta fechar semântica de “número” e eliminar cadastro sem ambos pelo Admin. Identificador oficial não é único. | Produto / Backend / Frontend / QA |
| RN-03 | I | Classificação não muda nos caminhos ordinários da aplicação. | Produto / Backend / Frontend / QA |
| RN-04 | P | Livro básico quantitativo implementado; aderência completa à decisão 0003 pendente. | Produto / Backend / Frontend / QA |
| RN-05 | P | Movimentos imutáveis e estorno de saída/devolução/condição; incorporação ainda não pode ser anulada/estornada pelo fluxo. | Produto / Backend / Frontend / QA |
| RN-06 | I técnico | Restrição vigente bloqueia entrega; devolução permanece disponível. | Produto / Backend / Frontend / QA |
| RN-07 | A | Bloqueio comercial não existe; suspensão genérica impede tudo. Não usar suspensão administrativa como bloqueio por inadimplência. | Produto / Backend / Frontend / QA |
| RN-08 | I | Condição inapta impede saída e não fica disponível. | Produto / Backend / Frontend / QA |
| RN-09 | P | Motivo exigido para condição inapta, concessão/revogação e estorno; baixa, consumo, ajuste e restrição ainda não existem. | Produto / Backend / Frontend / QA |
| RN-10 | A | Sem retirada por terceiro; destinatário e operador não representam os dois recebedores descritos no requisito. | Produto / Backend / Frontend / QA |
| RNF-01 | P | Decisão posterior adota online + papel + lançamento posterior. Operação digital não continua sem servidor. É alteração de requisito, a formalizar, não atendimento literal. | Produto / Backend / Frontend / QA |
| RNF-02 | A | React busca ao abrir/agir; não há push, polling ou invalidação entre clientes para atualizar outros balcões imediatamente. | Produto / Backend / Frontend / QA |
| RNF-03 | P | Mesmos limites de RF-62: proteção na aplicação, cadeia local e ausência de ancoragem independente. | Produto / Backend / Frontend / QA |
| RNF-04 | P | CPF minimizado/mascarado, permissões e proposta de política existem; retenção/descarte e aceite institucional pendentes. Sem parecer de conformidade nesta revisão. | Produto / Encarregado |
| RNF-05 | P | Admin sem escrita e sem leitura global; testes de isolamento adicionados, homologação pendente. | Produto / Backend / Frontend / QA |
| RNF-06 | P | Operação individual simples, mas sem validação atual de balcão e sem cesta; seletores e navegação precisam de ensaio com volume real. | Produto / Backend / Frontend / QA |
| RNF-07 | P | Dump criptografado, timer e restauração sintética documentados. WAL/PITR, cópia externa, retenção e metas em produção não comprovados. | Produto / Backend / Frontend / QA |
| RNF-08 | P | Ensaio anterior de busca sintética existe; volume por turno, concorrência sustentada e metas de saída/devolução continuam sem aceite. | Produto / Backend / Frontend / QA |

## Evidências de verificação

- `backend/sigab/tests/test_increment_047_051.py`: login multitenant, Admin, restrições, privacidade e cesta.
- `backend/sigab/tests/test_isolation.py`: rotas e referências cruzadas entre organizações.
- `backend/sigab/tests/test_concurrency.py`: serialização no PostgreSQL; execução SQLite não comprova concorrência.
- `frontend/e2e/journeys.spec.ts`: navegador com API simulada; não substitui integração com banco real ou homologação de balcão.

A aprovação do escopo, das substituições e dos textos operacionais deve ser registrada por Produto. Não marcar anexos de RF-30 nem exceções como entregues. As tarefas originais 047 e 050 mantêm pendências de aceite institucional, mesmo com implementação técnica disponível.
