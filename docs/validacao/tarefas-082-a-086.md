# Entrega técnica — tarefas originais 082–086

Data: 13/11/2026. Origem: [lote de tarefas de 12/11](../tarefas/tarefas-12-11-26/README.md). Os números abaixo são IDs originais de planejamento, não chaves reais do Jira. Nenhum registro externo foi alterado. Nenhum aceite de produto é presumido.

## Entrega por tarefa

| ID original | Estado técnico local | Entrega e evidência |
|---|---|---|
| SIGAB-082 | Concluído tecnicamente | Atendimento passa a se chamar **Retirada e devolução**, com três abas exibidas conforme a permissão: Retirada (cesta atual), Devolução e Registro de movimentações. Detalhes nas seções abaixo. |
| SIGAB-083 | Proposta registrada; **aguarda aprovação** | [ADR 0008](../adr/0008-biometria-facial.md) com status "proposto". A obrigatoriedade já foi decidida pelo produto em 13/11/2026: validação biométrica obrigatória na retirada e na devolução, quando a biometria não for possível, termo assinado pelo servidor e aprovado só pelo administrador do acervo; com o servidor fora do ar, contingência em papel. O ADR também cobre: verificação 1:1, prova de vida, equipamento, processamento local, armazenamento só do modelo criptografado, retenção e exclusão, base legal proposta, RIPD e o que entra na auditoria. A [política de dados pessoais](../politica-de-dados-pessoais.md) recebeu o rascunho da linha de biometria, marcado como não vigente. A aprovação técnica e jurídica é de Produto, Segurança e Jurídico. |
| SIGAB-084 | Parcial: comparação documental entregue; medição prática pendente | [Pesquisa 0002](../pesquisas/0002-verificacao-facial-no-balcao.md) compara quatro opções e descarta o Azure Face. Critérios: licença para revenda, prova de vida, funcionamento sem internet, local de processamento, retenção pelo fornecedor, custo e risco. Recomenda processamento local 1:1. As taxas de falsa aceitação e falsa rejeição e o tempo por verificação exigem voluntários com consentimento e câmera de balcão; o protocolo está na seção 6 e os números ficam "a medir". Nenhum código entrou no produto e nenhuma imagem foi coletada. |
| SIGAB-085 | Concluído tecnicamente; produção depende de aprovação jurídica | Módulo **Biometria** (Gestor de acervo, `biometric.manage`) e painel na ficha da pessoa: cadastro, recadastro e exclusão por captura da webcam, mostrando só "cadastrada/não cadastrada" e a data. Guarda só o vetor, criptografado com Fernet e chave fora do banco; nenhuma imagem é persistida. A exclusão é física e auditada sem o dado, e ocorre também ao encerrar o último vínculo ativo. Motor isolado (`sigab.biometrics`) com adaptador OpenCV YuNet + SFace, opcional por `uv sync --extra face`; sem motor ou chave, a API responde 503. |
| SIGAB-086 | Concluído tecnicamente; produção depende de aprovação jurídica e da medição da 084 | Retirada e devolução exigem verificação facial 1:1 aprovada, com conferência visual do operador. A verificação é de uso único, vale 2 minutos, fica vinculada a pessoa, operador, operação e organização e é consumida na transação do lote. Quando a biometria não é possível: o sistema gera o termo, o servidor assina, o operador registra o termo assinado e só o administrador do acervo (`movement.exception.approve`, diferente de quem registrou) aprova. Nada se movimenta antes da aprovação, que revalida o estado. O registro de movimentações exibe o método. Fora da contingência, a ficha do item só aceita o lançamento do livro de contingência. |

## SIGAB-082 em detalhe

### Devolução

- O operador seleciona a pessoa e vê a posse atual dentro do seu escopo de `movement.return`, com e sem registro.
- Confere item a item: marca apto, ou inapto com motivo. Para material sem registro, informa a quantidade devolvida.
- Revisa o resumo e confirma de forma explícita.
- A confirmação é uma operação única (`return_basket`): todos os materiais voltam juntos ou nenhum volta.
- O novo modelo `ReturnBatch` (migração 0013) tem chave de idempotência única por organização, hash do conteúdo e comprovante `DV-…`. As linhas apontam para as movimentações e os lançamentos imutáveis criados pela devolução.
- Reenvio com a mesma chave devolve o mesmo lote. A mesma chave com conteúdo diferente é recusada.
- Duas devoluções concorrentes da mesma pessoa se serializam no bloqueio da pessoa e só uma é aceita (teste PostgreSQL).
- A devolução aceita pessoa inativa (RN-07).
- Material sem registro só é devolvido como apto. Consumo justificado continua no Estoque, e o inapto depende da SIGAB-008.
- No navegador, o lote usa a mesma proteção contra resposta perdida da retirada.

### Registro de movimentações

- Lista retiradas, devoluções e consumos, com e sem registro, mostrando: material, quem retirou ou devolveu, quem entregou ou recebeu, unidade, data e hora, condição na devolução, origem em contingência e código do comprovante (`AT-…` ou `DV-…`).
- Filtra por pessoa, operador, material, tipo de movimento, natureza e período.
- As opções de filtro saem só das movimentações que o leitor já pode ver. O escopo é `item.view`.
- APIs novas: `GET/POST /api/v1/return-batches/options/` e `return-batches/`, `GET /api/v1/movements/` e `movements/options/`.
- O Início passou a mostrar o código do comprovante, o atalho Devolução aponta para `/atendimento/devolucao` e há link para o registro completo.

### Fora do escopo desta entrega

- Página própria do comprovante de devolução. O código aparece na confirmação e no registro.
- Retirada em nome de terceiro (RF-25), que segue dependendo da SIGAB-007.

## Verificações

- Suíte SQLite: **262 passaram, 15 ignorados**. Suíte PostgreSQL 17: **275 passaram, 2 ignorados**, incluindo:
  - duas devoluções em lote simultâneas da mesma pessoa, com exatamente uma aceita;
  - corrida com a mesma chave, registrando uma única vez.
- `test_requirements_082.py`:
  - atomicidade, apto e inapto, replay, chave reutilizada com outro conteúdo e rollback quando qualquer linha falha;
  - confirmação, condição, posse da pessoa e quantidade;
  - pessoa inativa e permissão;
  - API de opções e registro com filtros e paginação;
  - escopo por unidade.
- Isolamento: quatro rotas novas registradas na guarda. Há teste negativo de acesso cruzado no registro e nas opções, e um teste de devolução com pessoa, item ou retirada de outra organização (400, sem vazamento e sem alteração).
- Playwright com API simulada: **23 jornadas passaram**, 3 delas novas:
  - devolução em lote com apto e inapto, resposta perdida, recarga e duplo clique sem duplicar;
  - registro com papéis e filtros;
  - abas por permissão.
- Ruff, `manage.py check`, `makemigrations --check`, TypeScript e build aprovados.
- A migração 0013 foi aplicada apenas nos bancos de teste. O banco de desenvolvimento precisa de `migrate`.

## SIGAB-085/086: decisões de implementação

- **Administrador do acervo:** é o papel Gestor de acervo da matriz 0002, que passou à versão 1.4.0 com `biometric.manage` e `movement.exception.approve`. A regra nova `identity_exception_four_eyes` impede que quem registrou aprove o próprio termo; ela também é uma restrição no banco.
- **Quem consta como operador:** na aprovação, a movimentação é executada em nome do operador que atendeu no balcão. A aprovação é um ato separado, auditado com o administrador.
- **Termo em aberto:** o material de um termo de devolução em aberto aparece como "aguardando aprovação" e não pode ser devolvido por outro caminho.
- **Ativação:** `SIGAB_REQUIRE_IDENTITY_CHECK` vem ligado por padrão. Os testes das regras de movimentação anteriores rodam com a exigência desligada; os testes da biometria usam o marcador `identity_check`.
- **Termo em papel:** o termo é impresso e assinado à mão. Digitalização, anexo e assinatura eletrônica ficam fora do escopo.

## SIGAB-085/086: verificações

- Suíte SQLite: **279 passaram, 17 ignorados**. Suíte PostgreSQL 17: **294 passaram, 2 ignorados**, incluindo:
  - a mesma verificação usada por duas retiradas simultâneas, com exatamente uma aceita;
  - dois administradores aprovando o mesmo termo, com uma única execução.
- `test_requirements_085_086.py` (18 testes), com motor sintético determinístico e sem imagem real:
  - criptografia, auditoria sem dado e recadastro;
  - permissão, vínculo ativo e captura sem rosto ou com formato inválido;
  - motor ou chave ausentes respondendo 503;
  - exclusão manual e automática;
  - verificação recusada, de uso único, expirada, de outra pessoa, de outro operador ou de outra operação;
  - devolução facial com o método no registro;
  - contingência ainda aceita;
  - termo de devolução e de retirada: assinatura, quem registrou não aprova, aprovação, recusa, cancelamento, revalidação e linha sem registro;
  - aprovador com escopo de outra unidade.
- Isolamento: dez rotas novas registradas na guarda, mais um teste de biometria e termos sem alcance a outra organização.
- Adaptador OpenCV real (4.14, modelos YuNet e SFace do OpenCV Zoo, ambiente temporário):
  - carrega os modelos;
  - recusa imagem sem rosto e imagem ilegível;
  - a similaridade de um vetor com ele mesmo dá 1,0.
  - **As taxas de acerto com rostos reais não foram medidas** (protocolo da pesquisa 0002).
- Playwright com câmera falsa do Chromium: **28 jornadas passaram**, 5 delas novas:
  - retirada com verificação aprovada;
  - recusa, geração do termo e registro da assinatura;
  - aprovação pelo administrador;
  - cadastro no módulo Biometria;
  - ficha do item limitada à contingência.
- Ruff, `manage.py check`, `makemigrations --check`, TypeScript e build aprovados. Migrações novas: `0013_return_batch` e `0014_facial_biometrics`.

## Revisão de 13/11/2026: Início com entrada e saída e cadastro facial na pessoa

- **Início:** os atalhos de retirada, devolução, estoque e cadastro de equipamento saíram; ficou um único botão "Entrada e saída". Ele pede a matrícula, identifica a pessoa (`GET /api/v1/counter/identify/`, busca exata) e abre o painel de reconhecimento facial com a escolha entre saída (retirada) e entrada (devolução). Aprovada a face, a operação abre com a pessoa fixada e confirma sem nova captura; sem biometria, segue para a operação e o termo.
- **Pessoas:** o cadastro aceita matrícula, unidade e posto (vínculo criado na mesma transação) e, para quem tem `biometric.manage`, a captura facial.
- **Validade da verificação:** 10 minutos (antes 2), configurável; segue de uso único.
- Testes: 5 novos no backend (identificação por matrícula, recusas, validade após a escolha de materiais, cadastro atômico com vínculo, isolamento) e 4 jornadas Playwright novas. SQLite **284 passaram, 17 ignorados**; PostgreSQL **299 passaram, 2 ignorados**; Playwright **32 passaram**.
- **Cancelar após a identidade confirmada:** botão "Cancelar operação" na retirada e na devolução abertas pela entrada; pede confirmação, invalida a verificação (`POST /face-verifications/<id>/cancel/`) e volta ao Início. Testes: cancelamento, confirmação exigida, outro operador, verificação usada, isolamento e uma jornada Playwright.
- **Retirada e devolução pela matrícula e por digitação (13/11):**
  - as telas começam pela identificação (matrícula, depois reconhecimento facial); o cartão "Retirada por" / "Devolução por" mostra nome, matrícula e como a identidade foi confirmada;
  - os materiais são digitados: com registro pelo número de série ou patrimônio (as opções trazem `codes`), sem registro pelo nome e quantidade, com sugestões;
  - com e sem registro ficam sempre em seções e listas separadas;
  - concluída a operação, o balcão volta a pedir a próxima matrícula.
  - Testes: SQLite **289 passaram**, PostgreSQL **304 passaram**, Playwright **34 passaram** (jornadas de retirada, devolução, recuperação e termo reescritas para o novo fluxo).
- **Operador não atende a si mesmo (13/11):** a biometria verificada é sempre a do servidor que retira ou devolve; a do operador só é usada quando ele próprio retira ou devolve, e então outro operador registra. Recusa em todos os caminhos (cesta, devolução, verificação, termo, contingência) e aviso na identificação. SQLite **290 passaram**, PostgreSQL **305 passaram**, Playwright **35 passaram**.
