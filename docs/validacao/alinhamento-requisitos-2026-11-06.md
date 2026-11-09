# Auditoria de alinhamento dos requisitos e divisão dos módulos

Data: 2026-11-06 · Base Git: `d6d61c8` + arquivos locais presentes na revisão.

## 1. Parecer

**O SIGAB não está 100% alinhado ao documento inicial DOC-0011 v0.1.** Hoje ele é uma base funcional online de gestão de **itens individuais**, com organização/unidade/reserva, pessoas e acessos, incorporação, saída, devolução, condição, estorno, lançamento de contingência, busca, atividade e auditoria. O documento inicial descreve um produto mais amplo, incluindo estoque quantitativo, consumo, restrições pessoais, inventário, comprovantes e relatórios.

Há três situações diferentes:

1. **Redução deliberada do primeiro incremento:** estoque, biometria, terceiros e outras capacidades ficaram fora ou aguardam definição. Isso explica a ausência, mas não significa atendimento do requisito original.
2. **Evolução válida do desenho:** pessoa separada de conta, papéis por escopo, estado do item em dimensões e eventos compensatórios são melhorias em relação ao rascunho. Precisam constar de uma versão atual dos requisitos.
3. **Lacunas e inconsistências:** login global, ausência de atualização entre balcões, caminhos administrativos que não usam as mesmas regras e documentação que se contradiz. Estas precisam de correção, não apenas de uma nova descrição do escopo.

**Os módulos conceituais estão parcialmente bem separados; a implementação ainda não é um monólito modular.** A interface tem quatro áreas (Acervo, Atividade, Pessoas e Cadastros), mas o backend concentra múltiplos domínios nos mesmos arquivos. Recomenda-se preservar Django/PostgreSQL e evoluir a separação internamente, sem criar microsserviços.

## 2. Método e limites

- Fonte inicial: [DOC-0011 v0.1](../fontes/DOC-0011-analise-de-requisitos-v0.1.md), transcrição versionada do `requisitos.pdf`. O PDF original e os vídeos não foram examinados nesta revisão.
- Comparação com modelos, serviços, rotas, permissões, Django Admin, telas React, testes e decisões posteriores. O graphify foi consultado como mapa; os achados foram conferidos no código atual.
- Foram considerados os **37 RF, 10 RN e 8 RNF**, além dos perfis e dos itens ainda não detalhados nas seções 4.8 e 7 da fonte.
- Implementação, teste automatizado e aceite pelo usuário são estados distintos. Não se deduziu homologação de tarefas `Done` ou de testes aprovados.
- Revisão de código e testes locais; não houve inspeção visual no navegador, execução em produção, auditoria jurídica nem nova demonstração com organização-alvo.
- README, arquivos graphify e arquivos de demonstração já tinham alterações locais. Foram tratados como parte da fotografia atual, sem atribuir sua autoria a esta revisão.
- A consulta graphify não exigiu nova extração semântica nem API externa. Custo de extração semântica nesta revisão: zero; não é uma medição dos tokens totais da conversa.

### Verificações executadas

| Verificação | Resultado nesta revisão |
|---|---|
| Backend: `.venv/bin/python -m pytest -q` | **198 passaram, 6 ignorados**, 29,49 s, SQLite |
| Frontend: `bun run typecheck` | passou |
| Frontend: `bun run build` | passou |
| Concorrência PostgreSQL | não executada nesta revisão; testes ignorados no SQLite |
| Ensaio opcional de desempenho | não executado nesta revisão |
| Navegador e homologação | não executados |

A evidência anterior de PostgreSQL e restauração está em [tarefas 041–045](tarefas-041-a-045.md); não deve ser apresentada como resultado desta execução. Testes verdes validam cenários implementados, não os requisitos ainda ausentes.

## 3. Matriz de requisitos funcionais

**I — implementado:** capacidade encontrada no fluxo atual; não equivale a aceite. **P — parcial:** existe parte da capacidade, mas a redação integral não é atendida. **A — ausente:** não há o fluxo solicitado, mesmo que haja proposta, permissão reservada ou cadastro preparatório.

As referências E1–E12 são detalhadas na seção 10. A classificação considera as superfícies atuais, inclusive limitações da interface e caminhos administrativos. Não se atribui um percentual de conformidade: os requisitos têm pesos e extensões diferentes, e não há aceite individual completo.

Resultado dos 37 requisitos funcionais pelo critério desta revisão: **8 implementados, 14 parciais e 15 ausentes**. A contagem não é percentual de progresso: um requisito pode abranger um módulo inteiro, enquanto outro descreve apenas uma regra de edição.

| ID | Estado | Comparação com o sistema atual | Evidência |
|---|---|---|---|
| RF-01 | P | Organização e escopos aplicados na API; superusuário no Admin ainda acessa dados de várias organizações, sem fluxo de suporte autorizado. | E1, E3, E4 |
| RF-02 | P | Senha existe, mas autenticação usa `username` global, não organização + matrícula. Matrículas iguais entre clientes não podem ser usadas como o mesmo login. | E1, E4 |
| RF-03 | I | Campos distribuídos entre Person, Membership e Account/Grant; separação correta de responsabilidades. | E1, E2, E5 |
| RF-04 | P | Concessão/revogação preserva pessoa, ator e motivo. Não há histórico de alterações de perfil apresentado na ficha da pessoa; a trilha usa objetos Grant e a tela mostra concessões ativas. | E2, E5, E6 |
| RF-05 | A | Operação sem biometria existe; vinculação biométrica opcional não foi implementada. | E1, E7 |
| RF-06 | A | Há suspensão administrativa, mas não bloqueio comercial que preserve devoluções, consultas e exportações. | E4, E10 |
| RF-10 | I | Cadastro distingue `individual` e `quantitative`. Isso atende a classificação do tipo, não implementa estoque. | E1, E2, E5 |
| RF-11 | A | Sem catálogo de sugestões pré-carregado; catálogo atual é privado da organização. | E1, E5 |
| RF-12 | P | Incorporação via API/tela exige série ou patrimônio, tipo e unidade; criação pelo Admin não passa pela mesma exigência de identificador. | E1, E2, E3 |
| RF-13 | A | Sem entidade/fluxo de saldo quantitativo. Tipo quantitativo cadastrado não recebe quantidade. | E1, E7, E10 |
| RF-14 | P | Disponível, em posse e inapto existem por composição de campos. Baixa não tem fluxo; `inactive` não equivale a baixa com motivo. | E1, E2 |
| RF-15 | P | Detalhe, posse e movimentos paginados existem. Histórico exibido é MovementEvent; alterações cadastrais pelo Admin ficam fora desse histórico. | E3, E6, E8 |
| RF-16 | I | Classificação de tipo imutável no caminho de edição da aplicação. | E1, E2 |
| RF-20 | P | Saída de um item por operação, iniciada pelo item. Não há atendimento iniciado pela pessoa com cesta de vários itens e quantidades. | E2, E7, E8 |
| RF-21 | P | Movimentos e incorporação exigem confirmação. Não é garantia uniforme para toda alteração de acervo: edição de tipo e Admin não usam o mesmo contrato de resumo/confirmação. | E2, E3, E5, E8 |
| RF-22 | I | Devolução individual exige condição apto/inapto, com motivo quando inapto. | E2, E8 |
| RF-23 | I | Devolução apta libera o item na transação. Disponibilidade no servidor não significa atualização automática das outras telas (RNF-02). | E2 |
| RF-24 | A | Sem consumo, devolução parcial quantitativa, justificativa com anexo e encerramento do saldo pendente. | E1, E7, E10 |
| RF-25 | A | `operator` é quem lança e `recipient` quem recebe; não existe terceiro retirante distinto do usuário do material. | E1, E2, E10 |
| RF-26 | A | Sem comprovante próprio de saída/devolução para impressão. | E7, E8 |
| RF-27 | P | Posse individual consultável por pessoa, unidade/escopo e organização; sem gestão consolidada das pendências quantitativas ou tela específica de pendências. | E6, E8 |
| RF-30 | A | Restrição descrita em decisão, sem modelo, endpoints ou tela. | E1, E7, E10 |
| RF-31 | A | Saída verifica pessoa e vínculo ativos; não consulta restrição ativa nem decisão minimizada de elegibilidade. | E2 |
| RF-32 | A | Sem ciclo de alteração/encerramento de restrição. | E1, E7 |
| RF-40 | A | Listagem de itens e total de resultados não constituem painel agregado por tipo e estado. | E6, E8 |
| RF-41 | A | Sem sessão de contagem guiada ou comparação entre contado e esperado. | E1, E7 |
| RF-42 | A | Sem ocorrência de divergência de inventário com responsável e resolução. Erro de contingência não é esse processo. | E1, E7 |
| RF-50 | P | Busca integrada por referências existe; período está no feed, não na busca. UI de acervo expõe situação, mas não seletores de unidade/tipo; resultados limitados. | E6, E8 |
| RF-51 | P | API e tela consultam posse por pessoa; tela mostra só primeiros 100 itens, sem paginação navegável. Sem autosserviço limitado à própria posse. | E6, E8 |
| RF-52 | I | Feed filtrado por destinatário reúne saídas/devoluções com data e ator; não é necessário um módulo novo para isso. | E2, E6, E8 |
| RF-53 | I | Histórico do item com paginação, saídas, devoluções e identificação de estorno. | E6, E8 |
| RF-54 | A | Sem estoque, não há histórico quantitativo. | E1, E7 |
| RF-55 | P | Auditoria filtra ator, permitindo consulta técnica; feed operacional não filtra armeiro e não há relatório correspondente na UI. | E6, E8 |
| RF-56 | A | Sem exportação PDF dos relatórios. Imprimir página pelo navegador não equivale à entrega desse requisito. | E7, E8 |
| RF-60 | P | Ator, ação, instante e motivo disponíveis; antes/depois não são uniformes. Admin registra nomes de campos, e movimentos nem sempre registram ambos os estados em `changes`. | E2, E3, E6 |
| RF-61 | I | Feed cronológico com filtro por pessoa, item e ação; pessoa/item entram também por links e parâmetros. | E6, E8 |
| RF-62 | P | Imutabilidade na aplicação e cadeia de hashes; SQL privilegiado não é impedido e falta âncora externa. Detecção não equivale a impossibilidade de alteração. | E1, E3, E9 |

## 4. Regras de negócio e requisitos não funcionais

| ID | Estado | Resultado |
|---|---|---|
| RN-01 | P | Matrícula e CPF preenchido são únicos por organização; CPF opcional e múltiplos vínculos não asseguram deduplicação de toda pessoa física. Perfil evolui sem recadastrar pessoa. |
| RN-02 | P | Série e patrimônio têm unicidade separada por organização; falta fechar semântica de “número” e eliminar cadastro sem ambos pelo Admin. Identificador oficial não é único. |
| RN-03 | I | Classificação não muda nos caminhos ordinários da aplicação. |
| RN-04 | A | Não há estoque quantitativo implementado; ausência de edição direta não comprova o livro de movimentações. |
| RN-05 | P | Movimentos imutáveis e estorno de saída/devolução/condição; incorporação ainda não pode ser anulada/estornada pelo fluxo. |
| RN-06 | A | Restrição pessoal não é avaliada na entrega. Pessoa inativa não substitui restrição categorizada com vigência. |
| RN-07 | A | Bloqueio comercial não existe; suspensão genérica impede tudo. Não usar suspensão administrativa como bloqueio por inadimplência. |
| RN-08 | I | Condição inapta impede saída e não fica disponível. |
| RN-09 | P | Motivo exigido para condição inapta, concessão/revogação e estorno; baixa, consumo, ajuste e restrição ainda não existem. |
| RN-10 | A | Sem retirada por terceiro; destinatário e operador não representam os dois recebedores descritos no requisito. |
| RNF-01 | P | Decisão posterior adota online + papel + lançamento posterior. Operação digital não continua sem servidor. É alteração de requisito, a formalizar, não atendimento literal. |
| RNF-02 | A | React busca ao abrir/agir; não há push, polling ou invalidação entre clientes para atualizar outros balcões imediatamente. |
| RNF-03 | P | Mesmos limites de RF-62: proteção na aplicação, cadeia local e ausência de ancoragem independente. |
| RNF-04 | P | CPF minimizado/mascarado, permissões e proposta de política existem; retenção/descarte e aceite institucional pendentes. Sem parecer de conformidade nesta revisão. |
| RNF-05 | P | API testa isolamento; Admin global e referências sem FK composta continuam exceções ao enunciado absoluto. |
| RNF-06 | P | Operação individual simples, mas sem validação atual de balcão e sem cesta; seletores e navegação precisam de ensaio com volume real. |
| RNF-07 | P | Dump criptografado, timer e restauração sintética documentados. WAL/PITR, cópia externa, retenção e metas em produção não comprovados. |
| RNF-08 | P | Ensaio anterior de busca sintética existe; volume por turno, concorrência sustentada e metas de saída/devolução continuam sem aceite. |

### Perfis e escopo ainda não detalhado

A hierarquia original Dev > Adm > Armeiro > Usuário foi substituída pela [matriz de papéis por escopo](../decisoes/0002-papeis-e-escopos.md). A mudança é coerente: administradores de acesso não precisam movimentar acervo; operadores não devem conceder seus próprios poderes. Entretanto, possuir um código de permissão para baixa, ajuste ou restrição não significa que o fluxo existe.

O usuário final da fonte podia consultar somente a própria posse/histórico. Não há um portal com essa autorização específica; conceder `item.view` dá leitura de unidade/organização, não apenas “meus itens”.

Das capacidades citadas sem detalhamento: unidades e locais existem; posto/graduação é texto em Membership, sem cadastro normalizado. Sinistro, avisos, fotografia, manutenção, transferência e integrações não têm os fluxos completos. Anexos também não têm infraestrutura funcional atual. Não classificar todo esse conjunto como falha de entrega: parte era expressamente futura, mas deve continuar identificada no escopo.

## 5. Achados prioritários e critérios de correção

Prioridades abaixo são recomendações para o próximo incremento, não declaração de incidentes em produção.

| Prioridade | Achado e efeito | Correção proposta e critério verificável |
|---|---|---|
| P0 antes de operação que dependa da regra | **Restrições ausentes.** Pessoa ativa com vínculo pode receber material mesmo que exista impedimento conhecido fora do sistema. | Implementar decisão de elegibilidade na mesma transação da saída; testar vigência, escopo, privacidade do motivo e revogação concorrente. Definir exceções com Produto antes de implementá-las. |
| P0 antes de liberar Admin operacional | **Duas portas de escrita com garantias diferentes.** Admin permite criação de item sem série/patrimônio e gestão global fora das concessões da API. | Tornar cadastros operacionais do Admin somente leitura ou fazê-los chamar os mesmos comandos; teste deve negar incorporação sem identificador em toda superfície habilitada. Plano de suporte com aprovação e trilha própria. |
| P0 antes de bloqueio comercial | **Suspensão bloqueia devolução.** Reutilizar o comando administrativo para inadimplência violaria RN-07. | Separar suspensão de segurança de bloqueio comercial; devolver, consultar posse e exportar devem continuar disponíveis no estado comercial bloqueado. |
| P1 | **Login global incompatível com matrícula por cliente.** | Resolver organização antes da autenticação e usar identificador composto; testar duas organizações com mesma matrícula e ausência de enumeração entre clientes. |
| P1 | **Tela desatualizada em outro balcão.** Banco atualizado não atualiza navegador. | Definir latência aceitável e mecanismo de atualização; teste com dois clientes: devolução em A aparece em B dentro da meta acordada, preservando bloqueio transacional. |
| P1 | **Acervo limitado na UI.** API pagina, tela para nos primeiros 100; pessoas da busca nos primeiros 20. | Paginação ou cursor navegável, total confiável e filtros; verificar acesso aos registros 101+ e pessoas 21+ sem depender de adivinhar termo mais específico. |
| P1 | **Tipo quantitativo parece disponível, mas não tem operações.** | Explicitar “somente cadastro; movimentação ainda indisponível” ou ocultar essa opção da jornada operacional enquanto estoque estiver bloqueado. |
| P1 | **Auditoria não contém antes/depois de forma uniforme.** | Versionar contratos por ação, com minimização de dados; testar ações de API e Admin, campos obrigatórios e encadeamento. Definir proteção de banco e ancoragem externa. |
| P1 | **Sem comprovantes, inventário, painel e pendências completas.** | Entregar consultas/projeções e fluxos com critérios das matrizes; não tratar filtragem de itens como inventário físico. |
| P1 | **Continuidade ainda não demonstrada em escala.** | Ensaio de restauração com volume acordado, WAL/PITR e cópia externa; medir RPO/RTO em ambiente representativo. |
| P2 | **Concentração do código e divergência documental.** | Separar comandos e consultas por domínio; alinhar requisitos/backlog/decisões, mantendo a suíte verde a cada extração. |

Outras lacunas de produto posteriores ao documento inicial: a decisão de segmento prevê retirada por turno, cautela com prazo e atribuição sem prazo; Movement não possui modalidade ou previsão de devolução. É necessário validar esses campos e sua consequência em pendências antes de chamar o fluxo de “cautela completa”.

## 6. Avaliação da divisão atual

### O que deve ser preservado

- **Pessoa ≠ vínculo ≠ conta:** permite destinatário sem login, mudanças de unidade/perfil e revogação de acesso sem perder histórico.
- **Tipo ≠ item:** categoria é cadastro, item é bem físico. Quantidade não deve virar atributo editável de Item.
- **Movimento ≠ evento ≠ auditoria:** operação de negócio, fato publicado e rastreio de acesso/alteração têm finalidades distintas.
- **Posse atual como projeção transacional:** evita recalcular todo histórico a cada consulta, preservando fatos e compensações.
- **Organização, unidade e local de guarda separados:** são fronteiras úteis de isolamento, autorização e localização.

### Onde a divisão atual é fraca

| Local | Evidência | Consequência |
|---|---|---|
| `backend/sigab/services.py` | 1.199 linhas; identidade, catálogo, estrutura, auditoria, movimento e estorno | Mudanças de domínios diferentes compartilham arquivo e dependências. |
| `backend/sigab/api/views.py` | 1.193 linhas; parsing, serialização, autorização, comandos e consultas | API difícil de revisar por responsabilidade; contratos ficam dispersos. |
| `backend/sigab/models.py` | 587 linhas, entidades de todos os domínios | Ainda administrável, mas novas entidades de estoque/restrição/inventário ampliariam acoplamento. |
| `CatalogPage.tsx` | Estrutura organizacional e catálogo no mesmo componente | “Cadastros” oculta duas responsabilidades e tende a crescer sem limite. |
| `PersonDetailPage.tsx` | Dados pessoais, vínculos, contas, concessões e ações administrativas | “Pessoas” mistura destinatários operacionais com administração de acesso. |
| API + templates Django + Admin | Superfícies distintas com cobertura de regras diferente | Manutenção repetida; Admin pode contornar contratos do fluxo principal. |

Tamanho de arquivo é indício, não defeito isolado. O problema concreto é a coexistência de responsabilidades e entradas com garantias diferentes.

## 7. Divisão de módulos proposta

Esta é uma **proposta de evolução**, não uma descrição de módulos já implementados. Manter inicialmente um app Django e o banco existentes; organizar pacotes internos, sem renomear tabelas ou mudar `app_label` só para reorganizar arquivos.

| Módulo | Responsabilidade e dados próprios | Limite e dependências |
|---|---|---|
| Organizações e estrutura | Organização, unidade, reserva/local de guarda, configuração de fuso | Estado comercial separado de estado de segurança; não concede papéis nem movimenta material. |
| Pessoas e vínculos | Pessoa, matrícula, posto/graduação, vínculos e situação funcional | Não armazena credenciais; fornece identificação mínima ao balcão. |
| Identidade e acesso | Conta, sessão, papel, concessão, autenticação e escopo | Depende de pessoa/organização; não decide aptidão operacional para receber material. |
| Catálogo e acervo individual | Tipos, identificadores e ciclo de vida do bem; incorporação, condição, baixa/anulação futuras | Movimentos atualizam posse por contratos explícitos; estoque não é um Item sem número. |
| Operação de balcão | Saída, devolução, estorno, atendimento e registro posterior de contingência | Orquestra autorização, elegibilidade, item e estoque; preserva atomicidade e idempotência. |
| Estoque quantitativo | Livro de entradas/saídas, posições, consumo, devolução parcial, saldo e ajustes | Saldo derivado de lançamentos; aguarda decisão de domínio 0003. Não criar campo de saldo livre. |
| Restrições e elegibilidade | Restrições com vigência, motivo protegido, anexos e exceções aprovadas | Expõe decisão mínima ao balcão; motivo não transita pelo módulo de operação. |
| Inventário e divergências | Sessão de contagem, fotografia do esperado, itens contados, divergências e responsáveis | Solicita ajuste/baixa ao módulo dono do dado; não reescreve saldo ou posse diretamente. |
| Consultas e documentos | Painel, busca, pendências, histórico por pessoa/item/operador, comprovantes e exportação | Projeções de leitura com o mesmo escopo de autorização; não mantém livro paralelo. |
| Auditoria | Eventos de segurança/alteração, contratos antes/depois, verificação e ancoragem | Separada do feed operacional; política de acesso e retenção própria. |
| Plataforma e operação técnica | Provisionamento, suporte autorizado, implantação, observabilidade e recuperação | Fora do menu do cliente; sem acesso operacional implícito por ser Dev. |

Anexos, geração de documentos e armazenamento protegido podem ser serviços compartilhados, com autorização definida pelo módulo dono. Não criar um módulo genérico que permita acesso a todos os arquivos sem verificar o recurso original.

### Navegação sugerida

- **Balcão:** escolher pessoa, preparar entrega, conferir devolução, registrar contingência. Disponibilizar cesta apenas quando houver contrato de operação com vários itens.
- **Acervo:** itens e tipos, condição e histórico; estoque quantitativo quando implementado.
- **Pendências:** posse e obrigações em aberto, filtradas por pessoa/unidade, com encerramento derivado dos fatos.
- **Inventário:** contagens e divergências, quando implementadas.
- **Pessoas:** identificação e vínculos; restrições em área autorizada, sem revelar motivos aos operadores.
- **Consultas:** painel, atividade, relatórios e comprovantes.
- **Administração:** estrutura, contas, papéis e auditoria, cada seção condicionada às permissões.

Não adicionar menus vazios para “parecer completo”. Hoje, a melhoria imediata é distinguir **Estrutura**, **Tipos de equipamento** e **Acessos** dentro das áreas existentes, e tornar os limites de estoque explícitos. Feed de atividade e histórico individual são vistas dos mesmos fatos, não dois módulos de escrita.

### Organização técnica sugerida

```text
backend/sigab/
  services/       # identity, people, structure, catalog, movements, audit
  api/            # views por domínio; parsing e respostas compartilhados
  queries/        # busca, posse, atividade, auditoria
  models/         # extrair depois, preservando app_label e imports públicos
  tests/          # por domínio + contratos entre módulos + fluxo vertical
frontend/src/
  features/       # people, access, catalog, items, movements, activity
  components/     # primitivas compartilhadas
  api/            # cliente HTTP e contratos
```

Extrair primeiro funções sem alterar comportamento, mantendo reexportações para compatibilidade de imports. Depois separar modelos, se trouxer benefício. Novos módulos devem entrar com contratos explícitos, não com imports circulares entre todos os serviços. O comando de balcão deve continuar controlando uma única transação quando alterar item, movimento, evento e auditoria.

## 8. Inconsistências documentais encontradas

| Documento | Divergência | Tratamento recomendado |
|---|---|---|
| `docs/requisitos.md` anterior a esta revisão | Só quatro fatias e “os demais requisitos permanecem fora do escopo”, embora busca, posse, atividade, estorno e contingência já existam | Índice atualizado nesta revisão para apontar a matriz integral. |
| `docs/decisoes-pendentes.md` | SIGAB-009/012 dizem estorno sem implementação; linha SIGAB-031–034 registra estorno pronto | Consolidar por capacidade; preservar anulação de incorporação como pendência distinta. |
| Mesmo arquivo | SIGAB-011 diz D-01/D-02/D-03 abertas; modelo de domínio registra resoluções, algumas com ressalva do Admin | Atualizar estado e indicar superfície: API corrigida não implica Admin corrigido. |
| Mesmo arquivo | SIGAB-019/020 dizem que histórico de perfil depende da gestão de concessões | Gestão já existe; pendência real é completar consulta/histórico na pessoa. |
| Mesmo arquivo | Linha futura de “dupla aprovação e estorno operacional” diz UI não implementada | UI de estorno existe; dupla aprovação continua distinta e futura. |
| Roteiro SIGAB-045 | Afirma reconciliação indisponível | Lançamento de contingência existe; conferência por segunda pessoa e procedimento ainda precisam de validação. |
| Visão/plano/requisitos versus fonte | Documentos atuais afirmam validação prévia com alvo; fonte original diz que nenhum órgão-alvo foi ouvido | Não apagar a fonte histórica. Registrar cronologia e evidência da validação posterior, distinguindo referência, alvo e aceite da implementação. |
| Backlog versus ata | SIGAB-002 aparece `Done`, mas ata pede evidência e demonstração continua pendente | Referenciar evidência da entrevista; não tratar entrevista, validação de vocabulário e homologação como a mesma entrega. |
| ADR 0004 | Diz que documento inicial não está versionado e usa contexto de templates | Acrescentar nota de evolução: fonte já versionada e React adotado; preservar a decisão histórica online/papel. |

As contradições acima não provam que entrevistas não aconteceram. Demonstram que a trilha no repositório não sustenta um aceite único e inequívoco para cada requisito.

## 9. Sequência de melhoria recomendada

1. **Fixar a linha de base atual.** Manter DOC-0011 intacto, aprovar um escopo de incremento e adotar estados separados: decisão, implementação, testes e aceite. Cada requisito deve ter responsável, evidência, revisão e eventual substituição formal.
2. **Fechar garantias dos fluxos existentes.** Corrigir Admin versus serviços, login, consulta completa/paginação, confirmação e atualização entre balcões. Adicionar testes de navegador para duas sessões, erros/reenvio e acesso por perfil.
3. **Extrair módulos internos sem mudar comportamento.** Identidade, estrutura, catálogo, movimentos, consultas e auditoria; executar testes de contrato e fluxo vertical. Mudanças transacionais exigem PostgreSQL.
4. **Completar a operação individual.** Restrições, comprovantes, pendências, histórico de perfil, consulta por operador, baixa/anulação e modalidades/prazos após definição. Priorizar restrições antes de operação real que dependa dessa regra.
5. **Desbloquear estoque e inventário.** Resolver SIGAB-008/041 com a organização participante; implementar livro quantitativo antes de consumo/ajuste e sua integração ao inventário. Contagem individual pode avançar independentemente.
6. **Demonstrar continuidade e aceite.** Testar produção representativa, restauração, volume por turno e demonstração por cenário; registrar o que foi aceito, recusado ou permanece pendente.

Critério para declarar “100%”: todos os requisitos da **versão de escopo aprovada** possuem implementação verificável, testes adequados e aceite rastreável, ou foram formalmente substituídos/retirados com motivo. Não se obtém 100% apenas reescrevendo requisitos para coincidir com o código.

## 10. Índice de evidências

Referências por símbolo são fornecidas para facilitar nova verificação após mudanças de linha.

| Ref. | Arquivos e símbolos |
|---|---|
| E1 | [models.py](../../backend/sigab/models.py): Person, Membership, Account, Grant, EquipmentType, Item, Movement, AuditEvent; restrições e `clean()` |
| E2 | [services.py](../../backend/sigab/services.py): `checkout_item`, `return_item`, `create_grant`, `revoke_grant`, `incorporate_item`, `reverse_movement`, `audit` |
| E3 | [admin.py](../../backend/sigab/admin.py): AccountAdmin, AuditedAdmin, ItemAdmin, MovementAdmin, AuditEventAdmin |
| E4 | [authentication.py](../../backend/sigab/authentication.py), [permissions.py](../../backend/sigab/permissions.py), [set_organization_status.py](../../backend/sigab/management/commands/set_organization_status.py) |
| E5 | [PersonDetailPage](../../frontend/src/pages/PersonDetailPage.tsx), [CatalogPage](../../frontend/src/pages/CatalogPage.tsx), [ActionDialog](../../frontend/src/components/ActionDialog.tsx) |
| E6 | [api/views.py](../../backend/sigab/api/views.py): `item_events`, `_filter_items`, `search`, `activity_feed`, `audit_trail`, `_account_resource` |
| E7 | [api/urls.py](../../backend/sigab/api/urls.py), [App.tsx](../../frontend/src/App.tsx), [AppShell](../../frontend/src/components/AppShell.tsx) |
| E8 | [ItemsPage](../../frontend/src/pages/ItemsPage.tsx), [ItemDetailPage](../../frontend/src/pages/ItemDetailPage.tsx), [ActivityPage](../../frontend/src/pages/ActivityPage.tsx) |
| E9 | [test_audit](../../backend/sigab/tests/test_audit.py), [test_reversal](../../backend/sigab/tests/test_reversal.py), [test_concurrency](../../backend/sigab/tests/test_concurrency.py), [verify_audit_chain](../../backend/sigab/management/commands/verify_audit_chain.py) |
| E10 | [Decisões pendentes](../decisoes-pendentes.md), [estoque](../decisoes/0003-modelo-de-estoque-e-municao.md), [restrições](../decisoes/0005-restricao-operacional.md), [contingência](../adr/0004-conectividade-e-contingencia.md) |
| E11 | [test_isolation](../../backend/sigab/tests/test_isolation.py), [test_authorization](../../backend/sigab/tests/test_authorization.py), [test_activity_and_search](../../backend/sigab/tests/test_activity_and_search.py), [test_vertical_flow](../../backend/sigab/tests/test_vertical_flow.py), [test_contingency](../../backend/sigab/tests/test_contingency.py) |
| E12 | [Modelo de domínio](../modelo-de-dominio.md), [backup](../backup-e-restauracao.md), [política de dados](../politica-de-dados-pessoais.md), [validação anterior](tarefas-041-a-045.md), [backlog](../tarefas/tarefas-15-10-26/tarefas.csv) |

## 11. Alterações realizadas nesta revisão

Criado este relatório com matriz completa, prioridades, limites e proposta de módulos. Atualizado o índice de requisitos para remover a declaração desatualizada de que todas as outras capacidades estão fora do escopo. A fonte inicial foi preservada. A refatoração e as funcionalidades propostas são trabalho futuro; não foram apresentadas como já entregues.
