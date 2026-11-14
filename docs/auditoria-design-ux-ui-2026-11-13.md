# Auditoria de design, UX/UI e qualidade da interface do SIGAB

Data: 13/11/2026. Escopo: versão local disponível durante a revisão.

**Atualização após autorização de implementação:** consulte a [entrega com correções, testes e evidências](validacao/design-ux-ui-2026-11-13.md). Os achados abaixo registram o estado observado antes dessas correções.

## Diagnóstico

O SIGAB tem identidade visual coerente e uma base de componentes que permite evoluir sem redesenhar o produto inteiro. A prioridade é tornar a composição mais consistente e corrigir comportamentos que podem confundir a pessoa ou apresentar informação fora de contexto.

Direção recomendada: interface institucional de trabalho, com pouca variação visual, movimento discreto e densidade adaptada à tarefa. Preservar o verde, a navegação agrupada e os tokens existentes. Os critérios da taste-skill foram aplicados seletivamente: a própria skill exclui dashboards e fluxos complexos de seu escopo principal. Não se recomenda aplicar efeitos de landing page às áreas operacionais.

## Método e limites

- Inspeção visual de Cadastros, Atividade, Estoque, Acervo, Pessoas, cadastro de pessoa e Biometria na versão atual; a revisão anterior também observou Equipamentos, Início, detalhe de item e Termos. Nesta revisão, o código atualizado dessas áreas foi consultado novamente.
- Inspeção responsiva do Acervo a 400, 970 e 1000 px, e do cadastro de pessoa a 320 px pelo modo responsivo do Chrome.
- Verificação do foco inicial e do fechamento com Escape do cadastro de pessoa vazio. Ambos funcionaram na versão atual.
- Leitura dos estilos, componentes compartilhados, consultas, fluxos de atendimento, autosserviço, restrições, termos e template de login.
- Nenhum cadastro, exclusão, captura biométrica, concessão de acesso ou movimentação foi executado.
- Modo escuro, contraste calculado, leitor de tela, teclado virtual, impressão real e condições de rede degradada não foram validados em execução. Não há declaração de conformidade de acessibilidade nem medição de desempenho.
- A sessão visual era administrativa. As observações de autosserviço e etapas de atendimento sem acesso nessa sessão são baseadas no código, com necessidade de reprodução no respectivo perfil.

Legenda: **V** = observado visualmente; **C** = identificado no código; **R** = recomendação de design a validar com usuários. P1 = corrigir primeiro; P2 = próxima rodada; P3 = refinamento.

## Melhorias já presentes

Não devem ser reabertas como problemas atuais da auditoria anterior:

- Busca explícita com botão e rótulo associado em Acervo e Pessoas.
- Paginação, filtros aplicados e memória de consulta nessas duas áreas.
- Títulos funcionais nas telas centrais e cabeçalhos de colunas nas listas.
- Modal compartilhado com foco inicial, contenção de Tab, fundo inerte, Escape e retorno de foco.
- Separação de ações sensíveis em alguns módulos e variantes de botão de perigo.
- Página inicial com exceções antes do resumo, consultas acessíveis pelos indicadores e vazio secundário compacto.
- Formulário de pessoa mais largo e dividido em seções.
- Separação entre seletor de aparência e escolhas de formulário.

## Achados prioritários de comportamento e contexto

### 01. Biometria: pessoa selecionada sem identificação visual suficiente — P1 · V/C

Ao abrir “Gerenciar”, o painel mostra apenas “Biometria facial”, data, “Recadastrar” e “Excluir”. O nome da pessoa existe no `aria-label`, mas não aparece visualmente no painel. Não há botão para fechar a seleção nem indicação de linha selecionada.

**Melhoria:** mostrar nome e matrícula no cabeçalho; destacar a seleção; oferecer “Fechar painel”; levar o foco para o painel ou anunciar sua abertura. Toda confirmação deve repetir a pessoa afetada.

**Aceite:** deve ser possível identificar a pessoa atendida olhando somente para o painel aberto.

Evidência: `frontend/src/features/identity/BiometricsPage.tsx`, `BiometricPanel.tsx`.

### 02. Biometria: estado anterior preservado ao trocar de pessoa — P1 · C

O painel é reutilizado sem `key` por pessoa. O efeito de mudança de `personId` busca o novo status, mas não limpa status anterior, modo de captura/exclusão, consentimento ou mensagens. Também não descarta respostas atrasadas. Isso permite exibir temporariamente contexto anterior e conservar uma etapa iniciada para outra pessoa.

**Melhoria:** reinicializar o painel por pessoa ou resetar explicitamente todos os estados, descartar respostas obsoletas e impedir troca enquanto houver envio. A confirmação de presença deve ser renovada a cada seleção.

**Aceite:** trocar de pessoa nunca reaproveita consentimento, formulário de exclusão, mensagem ou status da pessoa anterior. Este risco foi identificado no código; nenhuma alteração de biometria foi tentada.

### 03. Consultas: resposta antiga pode aparecer sob filtro novo — P1 · C

Acervo e Pessoas preservam as linhas anteriores durante recargas após a primeira consulta, sinalizando `aria-busy`. Isso ajuda a evitar saltos, mas falta uma indicação visual clara de atualização e proteção contra respostas fora de ordem. Filtros novos podem coexistir com dados antigos, e uma consulta lenta anterior pode sobrescrever a mais recente.

**Melhoria:** descartar respostas obsoletas, mostrar “Atualizando resultados…” e definir quando as ações sobre resultados anteriores ficam indisponíveis. Aplicar o mesmo padrão às demais consultas.

**Aceite:** ao alternar filtros rapidamente, somente a consulta mais recente pode definir os resultados; a interface informa quando os dados ainda estão sendo atualizados.

Evidência: `frontend/src/pages/ItemsPage.tsx`, `PeoplePage.tsx`; padrão semelhante em outras páginas de consulta.

### 04. Autosserviço: estrutura da linha do tempo incompatível com o CSS — P1 · C

O histórico de “Minha posse” usa `.timeline`, cuja grade espera marcador de 14 px e conteúdo. Seus itens renderizam apenas o bloco de conteúdo, sem marcador. Esse bloco ocupa a primeira coluna estreita. As linhas de materiais também usam `.item-row` sem a classe que atualmente fornece a grade no desktop.

**Melhoria:** criar componentes de linha do tempo e de lista com estrutura garantida, e revisar o autosserviço com dados preenchidos. A seção principal de materiais atuais deve aparecer antes do histórico e dos comprovantes.

**Aceite:** histórico legível, sem texto comprimido; materiais atuais prioritários e com colunas consistentes. Reproduzir com perfil de autosserviço antes de encerrar o ajuste.

Evidência: `frontend/src/features/self-service/MyPossessionsPage.tsx`; `.timeline li`, `.item-row`, `.item-columns` em `components.css`.

## Composição, alinhamento e espaçamento

### 05. Cadastros: coluna vazia permanente — P2 · V/C

“Estrutura da organização” usa `.detail-grid`, com duas colunas, mas renderiza apenas uma seção. O conteúdo fica comprimido à esquerda e sobra uma área extensa à direita. Botões de unidade e local competem dentro de um espaço desnecessariamente estreito.

**Melhoria:** usar coluna única com largura adequada; separar o cabeçalho de cada unidade de sua lista de locais. Colocar “Nova unidade” no cabeçalho da página e manter ações dos locais na própria linha.

Evidência: `frontend/src/pages/CatalogPage.tsx`; `.detail-grid` em `layout.css`.

### 06. Estoque: painéis encostados e títulos com margem residual — P2 · V/C

Os painéis de saldos e pendências aparecem consecutivos sem espaçamento. O `h2.list-summary` ainda recebe margens nativas de título, deixando uma faixa branca acima da área de cabeçalho.

**Melhoria:** envolver as seções em um agrupamento com gap de 24 px e fornecer um componente de cabeçalho que zere margens de títulos. O espaçamento deve pertencer ao layout, não depender da combinação de tags.

Evidência: `frontend/src/features/operations/StockPage.tsx`; `.list-summary` em `components.css`.

### 07. Cabeçalhos de contagem separam número e significado — P2 · V/C

Em Atividade, “30” aparece à esquerda e “registros” à direita. Em Biometria, “7”, “pessoas ativas”, “6” e “sem cadastro” se distribuem pelo painel. A causa é `justify-content: space-between` aplicado a fragmentos que deveriam formar uma frase.

**Melhoria:** agrupar cada número com seu rótulo. Exemplo: “7 pessoas ativas · 6 sem biometria”. Reservar a distribuição entre extremos para resumo de um lado e ações do outro.

Evidência: `ActivityPage.tsx`, `BiometricsPage.tsx`, `TermsPage.tsx`, `MovementRegisterPage.tsx`; `.list-summary`.

### 08. Separadores removidos de todas as linhas — P2 · V/C

O seletor `.item-row:last-child` corresponde a cada link quando ele é o único filho de seu `li`. Por isso, a lista de Acervo perde os separadores internos; os arredondamentos inferiores também são aplicados a linhas intermediárias.

**Melhoria:** limitar o tratamento da última linha ao último item da lista. Verificar também a variante de autosserviço, que usa outra estrutura.

Evidência: `frontend/src/styles/components.css:137`.

### 09. Estados vazios não têm escala por contexto — P2 · V/C

O vazio global usa 64 px de padding vertical. No Estoque, duas mensagens curtas ocupam dois painéis altos. A página inicial já possui uma alternativa compacta, mas o padrão não foi estendido.

**Melhoria:** definir vazio de página, vazio de seção e ausência de resultados. Usar aproximadamente 16–24 px de padding em vazios secundários e 40–64 px apenas quando o vazio for o conteúdo principal. Oferecer próximo passo quando houver ação possível.

### 10. Filtros antigos e novos têm aparência diferente — P2 · V/C

Acervo e Pessoas usam componentes novos; Atividade, Registro de movimentações e Termos ainda usam rótulos diretamente no formulário. As regras de fonte, largura e posicionamento se aplicam principalmente a `.field`, gerando diferenças e pequenos desalinhamentos. Em Atividade, o botão Filtrar fica abaixo da linha superior dos controles.

**Melhoria:** migrar os filtros para uma estrutura única, alinhando controles por sua caixa, com dicas abaixo. Usar grid responsivo para filtros numerosos, sem margens calculadas para simular a altura do rótulo.

### 11. Cabeçalho ocupa espaço demais no celular — P2 · V/R

No Acervo a 400 px, marca, organização, título, descrição, cadastro, abas e filtros consomem grande parte da altura de 749 px antes do primeiro resultado. A adaptação preserva os elementos, mas não reavalia sua prioridade.

**Melhoria:** encurtar a descrição, mostrar o escopo de forma compacta e reduzir os intervalos entre blocos relacionados. Avaliar se o cadastro precisa de botão de largura total nessa consulta. Manter busca e situação acessíveis perto dos resultados.

### 12. Formulários estreitos e textos de botão longos — P2 · V/C

No cadastro a 320 px, as camadas de padding do backdrop, modal e fieldset comprimem o formulário; a grade mantém mínimo de 220 px, maior que o espaço interno disponível em algumas combinações. Nos fluxos de identidade, botões longos usam `white-space: nowrap` e podem exceder a largura dos cards.

**Melhoria:** permitir que colunas encolham até a largura disponível, reduzir um nível de recuo no celular e permitir quebra controlada em ações longas. Para formulários extensos, avaliar modal em tela inteira em larguras pequenas, com ações sempre localizáveis.

Evidência: `.form-grid`, `.form-section`, `.dialog`, `.button`; `PeoplePage.tsx`, `CounterEntry.tsx`, `IdentityCheck.tsx`.

## Organização da informação e textos

### 13. Biometria começa com um parágrafo de treinamento — P2 · V/R

O cabeçalho mistura regra geral, caso do operador, exceção e aprovação. O usuário precisa ler várias linhas antes da consulta.

**Melhoria:** manter uma frase de propósito no topo e colocar detalhes em ajuda contextual. Sugestão: “Consulte e cadastre a biometria das pessoas da organização.” A regra de atendimento por outro operador deve aparecer quando esse caso ocorrer.

### 14. Vocabulário varia entre telas — P2 · C/R

“Saída”, “retirada” e “entrada” coexistem; entrada pode significar devolução ou recebimento de estoque. “Minha posse” é menos direto que “Materiais comigo”. “Sem registro” pode ser entendido como ausência de cadastro, embora signifique controle por quantidade.

**Melhoria:** adotar glossário por tarefa: retirada, devolução e entrada em estoque. Preservar termos exigidos pelo negócio, com explicação curta: “Com registro — item a item” e “Sem registro — por quantidade”. Mudanças nos rótulos da navegação devem ser planejadas para preservar familiaridade.

### 15. Página inicial ainda repete números e exagera a abrangência de uma mensagem — P2 · C/R

“Em posse” aparece no grupo de posse e no resumo de itens. “Nada exige atenção agora” é calculado apenas por prazos vencidos de material quantitativo e itens indisponíveis; a frase pode sugerir cobertura de outras filas, como termos.

**Melhoria:** reduzir duplicação e limitar a afirmação ao que foi verificado: “Nenhum prazo vencido de material sem registro e nenhum item inapto.” Se houver outras filas relevantes, apresentá-las separadamente.

Os cartões de retiradas em aberto e vencidas levam à aba genérica de material sem registro. O destino deve aplicar o filtro correspondente ou usar um rótulo que descreva a consulta realmente aberta.

Evidência: `frontend/src/features/home/HomePage.tsx`.

### 16. Controles de consulta não seguem uma política única — P2 · C

Acervo e Pessoas preservam filtros na URL; Registro e Atividade mantêm grande parte do estado apenas em memória. Algumas opções são aplicadas imediatamente e outras dependem de Filtrar. O componente de URL também usa `replaceState`, sem representar cada alteração no histórico de navegação.

**Melhoria:** definir comportamento comum: edição de filtros, aplicação, limpeza, retorno do detalhe, recarga e uso do botão Voltar. Usar histórico deliberadamente e preservar parâmetros relevantes de autenticação e consulta.

### 17. Cadastro e edição divergem na marcação de campos — P2 · C

O cadastro de pessoa informa que campos sem marcação são obrigatórios, mas Matrícula e Unidade não exibem indicação individual de opcionalidade/condição. A seção é opcional, e a unidade só se torna obrigatória quando há matrícula. Já a edição ainda usa controles antigos e omite a marcação de opcionais em vários campos.

**Melhoria:** aplicar `Field` nas telas restantes e comunicar condições no próprio campo: “Unidade — obrigatória ao informar matrícula”. Usar erros próximos do controle e um resumo navegável no topo em formulários longos.

### 18. Ações de alto impacto ainda têm tratamento desigual — P1/P2 · C

Existe variante de perigo em parte do produto, mas “Excluir biometria” confirma com botão primário verde; na ficha da pessoa, desativar ou revogar ainda aparece como ação neutra em vários pontos. Os textos de envio frequentemente mostram “Registrando…” para tarefas distintas.

**Melhoria:** padronizar ação sensível, contexto e consequência. Exemplos de envio: “Salvando dados…”, “Excluindo biometria…”, “Desativando unidade…”. Nome e matrícula devem acompanhar a exclusão biométrica. Separar visualmente ações de conta, vínculo e pessoa.

### 19. Erros locais podem substituir a página inteira — P2 · C

Em Minha posse, a falha ao abrir um comprovante usa o mesmo erro do carregamento principal, substituindo toda a tela por erro. A recuperação chama o carregamento geral, em vez de repetir a abertura daquele comprovante. No Registro, a falha ao carregar opções é convertida em listas vazias silenciosamente.

**Melhoria:** manter erros no bloco afetado; oferecer repetição da ação exata; distinguir ausência de opções de falha no carregamento. Preservar conteúdo e formulário sempre que possível.

### 20. Câmera pede acesso antes de uma ativação explícita — P2 · C

`FaceCapture` solicita a câmera ao montar. O estado `disabled` bloqueia o botão de captura, mas não a solicitação da câmera. No cadastro, ela pode ser montada após preencher vínculo, antes de marcar a confirmação.

**Melhoria:** apresentar “Ativar câmera” com explicação; só então solicitar permissão. Separar acesso negado, dispositivo ausente e falha temporária; oferecer orientação de recuperação e nova tentativa. Não confundir câmera ativa com imagem capturada ou cadastro concluído.

## Acessibilidade, consistência e manutenção

### 21. Menu móvel não tem o mesmo tratamento do modal — P2 · C

O menu recebe foco e fecha com Escape, mas o código não isola o conteúdo ao fundo, não contém Tab e não devolve explicitamente o foco ao botão de abertura. O seletor de aparência usa papéis de radio em botões sem navegação por setas implementada.

**Melhoria:** aplicar um contrato completo de drawer; usar rádios nativos ou implementar o comportamento de teclado esperado para o seletor de aparência. Validar com teclado e leitor de tela.

### 22. Seletores genéricos provocam efeitos cruzados — P2 · V/C

`.sub-list span` aplica grid a qualquer span descendente. Isso sobrescreve o layout de badges e de números dentro das listas; em Atividade, o badge “estornado” aparece quebrado, com o ponto em linha separada.

**Melhoria:** limitar as regras à estrutura direta ou usar classes explícitas de conteúdo. Criar componentes para resumo, lista, formulário e linha do tempo com variantes declaradas. Evitar que tags genéricas determinem o layout de componentes internos.

### 23. Tipografia e densidade precisam de uma segunda escala — P3 · C/R

Os tokens usam 12 px para informações auxiliares, 13 px para muitos rótulos e 15 px para texto base. Isso pode funcionar em consultas densas, mas orientações de erro e consequências não devem herdar automaticamente a escala menor. O modo compacto reduz gaps, mas quase não reduz a altura dos controles: de 44 para 43,2 px.

**Melhoria:** definir densidade por linhas e seções; manter legibilidade e alvos adequados. Usar aproximadamente 14–16 px nos textos de trabalho e reservar 12 px para metadados secundários, validando zoom e monitores reais. Não é necessário trocar a fonte do produto.

### 24. Personalização e login usam contratos visuais diferentes — P2/P3 · C

O login possui fonte, cores e marca próprias em CSS literal, sem consumir a personalização `brand.json` do frontend; também declara apenas esquema claro. O tema aceita cores de marca válidas sintaticamente, mas não garante contraste com texto branco ou foco derivado do acento.

**Melhoria:** alinhar o contrato da marca entre login e área autenticada; validar combinações de cores, foco, erro e estados desabilitados. Manter uma paleta validada ou calcular uma cor de texto apropriada. A revisão não mediu as razões de contraste atuais.

## Régua de espaçamento proposta

Valores de referência para consolidar os tokens existentes; não são medições de defeito nem exigência de aplicar o mesmo espaço a todo contexto.

| Relação | Referência inicial |
|---|---:|
| Rótulo → controle | 6–8 px |
| Controle → dica/erro | 4–6 px |
| Campos relacionados | 16 px |
| Blocos dentro de uma seção | 16–24 px |
| Seções independentes | 24–32 px |
| Título → descrição | 8 px |
| Cabeçalho → filtros/conteúdo | 24 px desktop; 16 px celular |
| Padding de card | 24 px desktop; 16 px celular |
| Ações relacionadas | 8–12 px |
| Separação de ações sensíveis | 24 px ou área própria |
| Linha de consulta | aproximadamente 52–64 px, adaptável ao conteúdo |

Usar mais espaço entre seções do que entre elementos da mesma tarefa. Evitar acumular gap, margem de parágrafo e padding para produzir o mesmo intervalo. Controlar margens nativas de títulos. Não reduzir todos os espaços para resolver telas longas: remover repetição e melhorar a prioridade também é necessário.

## Propostas de texto

| Atual | Proposta / regra |
|---|---|
| “Entrada e saída” no balcão | “Iniciar atendimento”, com escolha “Retirada” ou “Devolução” |
| “Biometria não foi possível: seguir com termo” | Botão “Continuar com termo”; consequência em texto próximo |
| “Fatos confirmados do acervo…” | “Consulte as movimentações registradas nas unidades permitidas.” |
| “A trilha de auditoria completa é separada.” | Informar onde consultá-la se o usuário tiver acesso; caso contrário, retirar essa frase do cabeçalho |
| “Sem nome funcional” repetido | Mostrar nome completo; reservar o aviso para edição cadastral |
| “Nenhum saldo registrado.” | “Nenhum saldo disponível para consulta.” + ação pertinente, distinguindo inexistência de cadastro e saldo zero conforme a API |
| “7 pessoas ativas · 6 sem cadastro” | “7 pessoas ativas · 6 sem biometria”, em um grupo legível |
| “Cadastrar” / “Gerenciar” repetidos | Nome acessível com contexto: “Gerenciar biometria de [pessoa]” |
| “Campos sem marcação são obrigatórios.” | Manter somente se todos os campos e condições seguirem essa regra |

Textos de consentimento, exclusão e aprovação devem manter suas informações de negócio. Encurtar o botão e reposicionar a explicação não significa remover consequências importantes.

## Sequência de implementação

1. **Confiabilidade:** contexto e reset da Biometria; respostas obsoletas; apresentação do autosserviço; consistência das confirmações sensíveis.
2. **Composição:** contagens agrupadas, separadores, seletores de listas, coluna vazia em Cadastros, margens de títulos e distância entre painéis de Estoque.
3. **Padrões de interação:** filtros, preservação de contexto, estados locais de erro, ativação de câmera e identificação de ações.
4. **Refinamento:** textos, prioridade do conteúdo no celular, densidade, marca do login e contraste em temas.

## Critérios de validação

- Testar 320, 400, 768, 970, 1024 e 1440 px, com nomes e códigos longos; verificar ausência de rolagem horizontal indesejada.
- Conferir tema claro, escuro e marca alternativa; medir contraste de texto, placeholder, foco, bordas necessárias e botões.
- Percorrer por teclado: navegação, drawer, modal, filtros, paginação e retorno do detalhe.
- Validar estados vazio, sem resultados, falha, atualização, envio, sucesso e resultado ainda não confirmado.
- Simular respostas fora de ordem e troca de pessoa com painel aberto, sem reutilização de contexto anterior.
- Confirmar que toda ação de perigo identifica pessoa/registro e apresenta a consequência antes do envio.
- Exercitar o autosserviço com histórico e posses reais de demonstração, e cada etapa do balcão com o perfil autorizado.
- Validar impressão dos termos e comprovantes, sem navegação nem botões no documento impresso.
- Manter verificações automatizadas de comportamento para riscos concretos e capturas visuais representativas por componente. Complementar com avaliação humana de hierarquia, legibilidade e compreensão.

Esta entrega registra a auditoria e as recomendações. Nenhuma correção de interface foi implementada nesta rodada.
