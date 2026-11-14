# Padrões de interface do frontend

Padrões adotados após a auditoria de UX de 13/11/2026. Componentes em `frontend/src/components/`; estilos em `frontend/src/styles/components.css`, sempre a partir dos tokens de `tokens.css`.

## Cabeçalho de página

- `h1` é o nome da funcionalidade (Início, Acervo, Pessoas, Equipamentos).
- O rótulo de contexto acima do título (`.context-label`) traz a organização ou o objeto pai (ex.: tipo do item no detalhe).
- A descrição nomeia o escopo consultado com `scopeLabel(session)` ("na unidade U1 · Sede", "em todas as unidades de …"), nunca "no seu escopo". O escopo vem de `session.item_scope`.

## Consulta (busca, filtros, paginação)

- `SearchForm`: rótulo associado ao campo, botão **Buscar** visível, **Limpar** e dica sob o campo. Enter continua funcionando. Mínimo de caracteres é comunicado na dica e validado antes do envio.
- Filtros com `<label for>` (componente `Field` ou `label` explícito).
- `AppliedFilters` lista cada filtro ativo com botão de remoção.
- `Pager` mostra "Exibindo X–Y de Z" e Anterior/Próxima; página de 50 registros. A ordenação é a do servidor, estável (`… , id`).
- `useUrlQuery` guarda busca, filtros e página na URL; `useListMemory` guarda a última consulta e a rolagem para o link "Voltar" do detalhe (`lastListUrl`).
- Alterações aplicadas entram no histórico do navegador; `popstate` restaura a consulta, inclusive um filtro vazio que difere do padrão.
- Leituras concorrentes usam `useLatestRequest`: só a resposta mais recente pode alterar a tela. Não usar esse descarte para comandos de escrita, cujo resultado precisa ser recuperável.
- Acervo e Pessoas preservam a altura durante atualização, com mensagem visível e resultados anteriores inertes até a resposta.

## Listas

- Desktop: colunas com cabeçalho (`.data-list-head` + `.item-columns`/`.person-columns`), sem rótulo repetido por linha.
- Celular (≤ 760 px): cabeçalho oculto; o rótulo da célula (`.cell-label`) aparece inline. No desktop ele fica só para leitor de tela.
- O menu vira drawer em 1080 px, antes de faltar largura para as colunas de consulta. O drawer isola o conteúdo, contém Tab, fecha com Escape e devolve o foco.
- Resumos agrupam número e substantivo no mesmo elemento. Não distribuir fragmentos de uma frase com `space-between`.
- Regras de lista devem atingir a estrutura direta, sem alterar todos os `span` descendentes. O marcador e o conteúdo da linha do tempo são filhos separados.
- A altura das linhas segue `--density`; não reduzir texto abaixo de `--text-sm` nem alvo de toque abaixo de 44 px no celular.

## Ações

- Uma ação principal por contexto (`button-primary` na página; `button-secondary` por linha).
- Consulta/navegação como link (`.text-link`).
- Alteração de maior consequência separada visualmente: `button-danger-quiet` na lista ou `.danger-zone` no detalhe; a confirmação usa `tone="danger"` (`button-danger`).
- Confirmações nomeiam o registro afetado no título, explicam o resultado na descrição e usam verbo específico no botão ("Desativar tipo", "Estornar registro"), não "Confirmar".

## Diálogos

- Sempre via `Modal` (ou `ActionDialog`, que o usa): foco no primeiro campo ao abrir, Tab preso no diálogo, Esc fecha, foco volta ao botão de origem, fundo `inert`.
- Com dados preenchidos, clique fora não fecha e Esc pede segunda confirmação.
- Durante o envio, Cancelar fica desabilitado e o diálogo não fecha: fechar não cancela a requisição e deixaria a operação em dúvida. O resultado (sucesso ou erro) é sempre mostrado.
- Formulários longos usam `size="wide"` e seções numeradas (`.form-section`).

## Formulários e mensagens

- Campos sem marcação são obrigatórios; opcionais levam "(opcional)". Use `Field` com `optional`.
- Erros do servidor por campo (`ApiError.details`) aparecem junto do campo (`aria-invalid` + `.field-error`); o resumo no topo traz a mensagem geral e erros sem campo correspondente.
- O resumo recebe foco e oferece acesso ao primeiro campo inválido. Uma falha de comprovante ou de opções de filtro fica no bloco afetado e repete a ação exata.
- Mensagens de falha usam `describeError()`: orientam a recuperação (conexão, recarregar, suporte), nunca "Erro inesperado".

## Variantes por finalidade

- `.theme-switch`: seletor de aparência na navegação escura.
- `.choice-group`: escolha exclusiva em formulário (rádios), com `legend`.
- Aparência usa rádios nativos, permitindo navegação por setas. A cor de texto de botões primários é escolhida pelo contraste com a marca; o login Django lê a mesma marca por `public/login-theme.js`.

## Biometria e câmera

- O painel mostra pessoa e matrícula; seleção visível, foco no painel e retorno ao botão ao fechar.
- `BiometricPanel` recria o conteúdo por `personId`, sem reaproveitar consentimento, modo ou mensagens. Durante envio, a seleção e o fechamento ficam indisponíveis.
- Câmera só é solicitada ao acionar **Ativar câmera**, depois da confirmação exigida pelo formulário. Permissão negada, dispositivo ausente e falha temporária têm orientação e nova tentativa. Desativar ou desmontar encerra as trilhas.
- Nunca usar rosto real nos testes automatizados: vídeo sintético do Chromium ou simulação de falha da API de mídia.

## Ritmo visual

- Referência: 6–8 px entre rótulo e controle, 16 px entre campos, 24 px entre seções, padding de card de 24 px no desktop e 16 px no celular.
- Vazios secundários compactos; o vazio principal pode ter mais espaço. Não somar margem nativa de título ao padding do cabeçalho.
- Grades internas devem caber na largura disponível, mesmo abaixo do mínimo nominal de uma coluna; botões longos podem quebrar linha.
- Cada layout explicita o espaço entre seus painéis. Uma grade de duas colunas não deve conter uma única seção sem justificativa.

## Validação visual

A cada mudança de layout, conferir em 390 px e 1280 px, nos temas claro e escuro, com textos longos, zoom de 200% e navegação completa por teclado. A suíte `frontend/e2e/ux-audit.spec.ts` cobre foco de modal, busca, paginação e hierarquia de ações.

`frontend/e2e/ux-quality.spec.ts` acrescenta respostas fora de ordem, contexto biométrico, câmera explícita, erro local, histórico, contraste renderizado, impressão e geometria em 320, 400, 768, 970, 1024 e 1440 px nos dois temas. `frontend/integration/stock-journey.mjs` é o roteiro de navegador contra Django/PostgreSQL reais em base de teste descartável.
