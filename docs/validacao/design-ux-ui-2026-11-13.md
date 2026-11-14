# Entrega de design, UX/UI e qualidade da interface

Data: 13/11/2026. Referência: [auditoria](../auditoria-design-ux-ui-2026-11-13.md).

## Resultado

Implementadas as correções de contexto, composição e interação identificadas na auditoria. A identidade verde e os rótulos principais da navegação foram preservados. A revisão reaproveitou os componentes existentes e não acrescentou dependências.

### Confiabilidade

- Biometria mostra nome/matrícula, destaca a seleção, oferece fechamento e gerencia foco. Cada pessoa recebe uma instância nova do conteúdo, sem reaproveitar consentimento, modo ou mensagens.
- Seleção e fechamento ficam indisponíveis durante envio. Exclusão tem apresentação de perigo e identifica a pessoa afetada.
- Leituras usam `useLatestRequest` para impedir que respostas obsoletas ou posteriores à desmontagem alterem a tela. O mecanismo não é usado para descartar resultados de comandos.
- Acervo e Pessoas mantêm resultados anteriores inertes e indicam atualização visualmente.
- Falha de comprovante permanece local e repete a abertura correspondente. Falha nas opções de filtros é exibida com nova tentativa.
- A câmera exige ativação explícita após a confirmação do formulário. Há orientações distintas para acesso negado, câmera ausente e falha temporária, além de nova tentativa e desativação.

### Composição e apresentação

- Cadastros utiliza uma coluna com unidades e locais, e criação de unidade no cabeçalho.
- Estoque possui distância entre painéis; cabeçalhos não acumulam margens nativas de títulos.
- Contagens permanecem junto dos substantivos. Separadores e arredondamentos respeitam a última linha real da lista.
- Seletores de listas deixaram de atingir indiscriminadamente os componentes internos.
- Vazios mais compactos, botões longos com quebra, grades de formulário que cabem em 320 px e cabeçalho móvel com altura previsível.
- Textos auxiliares mais legíveis, bordas e foco mais visíveis e contraste de botões adaptado à cor institucional.
- Autosserviço prioriza os materiais atuais, apresenta histórico com marcador e coluna de conteúdo corretos e mantém comprovantes em seção própria.

### Consistência

- Filtros e consultas preservam estado na URL, com histórico do navegador e restauração por Voltar/Avançar.
- Mais formulários usam `Field`, com rótulo associado, indicação de opcionalidade e erro por campo. Resumo de erro recebe foco e oferece acesso ao primeiro campo inválido.
- Menu móvel contém o foco, isola o conteúdo e devolve o foco ao fechar. Aparência usa rádios nativos, incluindo navegação por setas.
- Página inicial elimina repetição de posse e limita a mensagem de ausência de atenção ao que realmente foi verificado. O acesso a pendências descreve a consulta que será aberta.
- Login Django consome a identidade da instalação e preferência de tema pela origem local, com fallback padrão. O build inclui `login-theme.js`; a publicação precisa servir esse arquivo junto dos demais arquivos públicos.

## Rastreabilidade dos 24 achados

| Achado | Tratamento |
|---|---|
| 01–02: contexto biométrico | Identificação visual, seleção, foco, instância por pessoa e bloqueio durante envio |
| 03: respostas antigas | Guarda de leitura e indicador de atualização com resultados inertes |
| 04: autosserviço | Linha do tempo, grade de materiais, prioridade das seções e erro local |
| 05: coluna vazia | Layout de uma coluna em Cadastros |
| 06: painéis encostados | Espaço de seção e reset de margem dos cabeçalhos |
| 07: contagens fragmentadas | Número e significado agrupados |
| 08: separadores | Seletor limitado ao último item da lista |
| 09: vazios | Altura reduzida e variante compacta já existente preservada |
| 10: filtros diferentes | Estrutura e tipografia de campos alinhadas; recuperação das opções |
| 11: excesso no celular | Cabeçalho com altura correta, descrição menor e intervalos reduzidos |
| 12: largura dos formulários | Grade limitada ao espaço disponível e botões com quebra |
| 13: texto de treinamento | Descrição de Biometria reduzida ao propósito da página; regras mantidas nos fluxos pertinentes |
| 14: vocabulário | Descrições e contextos mais diretos; rótulos principais mantidos para preservar familiaridade |
| 15: resumo inicial | Duplicação removida e mensagem limitada aos indicadores consultados |
| 16: política de consulta | Histórico e estado na URL nas consultas revisadas |
| 17: obrigatoriedade | Campos padronizados e condição da unidade comunicada no cadastro |
| 18: ações sensíveis | Variantes de perigo, identificação e bloqueio durante envio |
| 19: erros locais | Comprovantes e carregamento de opções com recuperação específica |
| 20: câmera | Ativação explícita, recuperação e desativação |
| 21: teclado | Drawer com foco contido e rádios nativos |
| 22: efeitos cruzados | Seletores restritos à estrutura da lista |
| 23: densidade/tipografia | Rótulos e dicas maiores; espaçamento continua derivado dos tokens de densidade |
| 24: marca/login | Marca local e tema no login, escolha de primeiro plano e contraste verificado |

## Verificações executadas

| Verificação | Resultado |
|---|---|
| Frontend: build de produção e TypeScript | Aprovados |
| Playwright completo | **66 testes aprovados**, incluindo os 42 testes existentes e 24 de qualidade/UX |
| Matriz de layout | 320, 400, 768, 970, 1024 e 1440 px; claro/escuro; oito páginas e formulário de pessoa |
| Textos longos | Nomes compostos, descrição longa e matrícula de 64 caracteres sem rolagem horizontal indevida |
| Contraste renderizado | Textos verificados ≥ 4,5:1 e borda de input ≥ 3:1; claro/escuro e quatro marcas, incluindo branco e preto |
| Impressão | Identificação e assinaturas mantidas; navegação e ações ocultas; PDF sintético gerado pelo Chromium |
| Backend em SQLite | **291 aprovados, 17 opt-in/concorrência não executados nesse banco** |
| Backend em PostgreSQL isolado | **306 aprovados**, dois ensaios opt-in executados separadamente |
| Ensaio de volume opt-in | **1 aprovado**: busca com 5.000 itens e 2.000 pessoas, dentro do orçamento do teste existente |
| Navegador real + Django + PostgreSQL | **1 aprovado**: login, entrada de estoque, identificação por matrícula, retirada, resposta perdida, recarga, recuperação, devolução parcial e consumo |
| Ruff, formatação Python e `manage.py check` | Aprovados |
| Migrações | Nenhuma mudança detectada |
| `git diff --check` | Aprovado |
| Graphify | Atualização AST executada |

Os 308 testes distintos do backend foram cobertos somando a suíte PostgreSQL e os dois ensaios opcionais. A base de teste `test_sigab_design_validation_20261113` foi criada e destruída pelo Django; as jornadas de escrita não utilizaram a base da demonstração.

O roteiro de integração existente estava desatualizado: procurava a seleção antiga de destinatário e atendimento. Foi atualizado para a identificação por matrícula e os seletores atuais; a nova execução usou API e transações reais.

Os testes de contraste apontaram e permitiram corrigir combinações insuficientes em marcas extremas. A revisão humana das capturas também encontrou o crescimento indevido do cabeçalho móvel e um botão de fechar visível no desktop; ambos foram corrigidos e receberam verificações de geometria/visibilidade.

## Evidências visuais sintéticas

- [Acervo claro, 1440 px](design-ux-ui-2026-11-13/acervo-light-1440.png)
- [Acervo escuro, 1440 px](design-ux-ui-2026-11-13/acervo-dark-1440.png)
- [Cadastros claro, 400 px](design-ux-ui-2026-11-13/cadastros-light-400.png)
- [Cadastros escuro, 400 px](design-ux-ui-2026-11-13/cadastros-dark-400.png)

Também foi feita conferência no Chrome da aplicação local, incluindo abertura do painel biométrico e identificação visual da pessoa, sem captura, exclusão ou alteração de cadastro real.

## Reprodução

Na pasta `frontend/`:

```sh
bun run build
bun run test:e2e
```

Na pasta `backend/`, com PostgreSQL local disponível e URL apontando para um nome exclusivo para o teste:

```sh
DATABASE_URL=postgresql://sigab:local-only@127.0.0.1:5432/sigab_design_validation_20261113 .venv/bin/pytest -q
DATABASE_URL=postgresql://sigab:local-only@127.0.0.1:5432/sigab_design_validation_20261113 SIGAB_BROWSER_INTEGRATION=1 SIGAB_PERF=1 .venv/bin/pytest -q sigab/tests/test_browser_integration.py sigab/tests/test_activity_and_search.py::test_search_response_time_with_test_volume
```

As credenciais acima são exclusivas do Compose de desenvolvimento, já documentadas no projeto.

## Limites da validação

- Chromium foi o navegador automatizado. Safari/Firefox e tecnologias assistivas específicas ainda dependem de homologação nos equipamentos de uso.
- Captura facial foi exercitada com vídeo sintético e simulação de falhas de permissão/dispositivo. Não houve homologação de reconhecimento facial com pessoas reais.
- O teste de impressão verifica o documento renderizado, sem ensaio de impressora física.
- As medições de contraste cobrem componentes e combinações representativas; não constituem certificação integral de acessibilidade.
- A suíte de layout cobre a faixa de larguras documentada. Zoom de navegador a 200% com teclado virtual real não foi automatizado.
- Graphify avisou sobre três JSON sem nós AST e diferença de versão da skill; o grafo de código foi atualizado sem chamadas a modelo. Não foi solicitada rotulagem semântica paga.

Nenhuma implantação ou commit foi realizado. As alterações anteriores do workspace foram preservadas.
