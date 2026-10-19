# Decisão de produto 0001 — Segmento inicial

- Tarefa: SIGAB-001
- Data: 2026-10-16
- Estado: decidida e validada para a linha de base do produto
- Responsável pela validação: Produto

## Decisão

O primeiro segmento atendido pelo SIGAB será o de **Guardas Municipais brasileiras que mantêm acervo de armamentos e equipamentos operacionais e realizam a entrega temporária ou continuada desses bens aos seus integrantes**.

Essa escolha define o foco inicial de descoberta, linguagem operacional, levantamento regulatório e validação dos fluxos. Não limita o SIGAB permanentemente a Guardas Municipais: a base de organizações, pessoas, papéis, equipamentos e movimentações deve permanecer genérica para permitir a avaliação futura de outros segmentos.

## Justificativa

- Existe acesso a uma Guarda Municipal e a pessoas capazes de explicar e validar o processo real.
- O controle atual da unidade é realizado em papel, sem sistema próprio para manter a situação corrente e o histórico do acervo.
- Há material de descoberta produzido a partir de vídeos de um sistema institucional semelhante, não comercializável.
- O problema observado corresponde ao fluxo vertical já modelado: item individual, responsável atual, saída, devolução e auditoria.
- A proximidade com usuários reais reduz o risco de consolidar regras e termos apenas por suposição.

Os vídeos e o sistema de referência são insumos de descoberta, não fontes normativas nem autorização para reproduzir sua interface ou implementação.

## Público inicial

- **Armeiro ou responsável pela reserva:** operador cotidiano que cadastra ou consulta itens e registra entregas e devoluções conforme suas permissões.
- **Administrador da organização:** administra contas, concessões de acesso e o cadastro de novos armeiros.
- **Integrante da Guarda Municipal:** destinatário e responsável operacional pelo equipamento recebido, ainda que não utilize diretamente o sistema no primeiro incremento.
- **Gestor ou auditor autorizado:** consulta a situação do acervo e seu histórico dentro do escopo permitido.

## Problema inicial

O controle em papel dificulta determinar com segurança quais itens existem, onde estão, quem está responsável por eles, quando foram retirados ou devolvidos e quem realizou ou autorizou cada operação.

O produto deverá admitir ao menos três modalidades operacionais consolidadas no levantamento inicial:

1. retirada durante um turno, tratada como o caso mais frequente;
2. cautela por prazo determinado, que pode durar dias ou meses;
3. atribuição sem data de devolução previamente definida, comum para determinados equipamentos de uso continuado, como rádios.

## Premissas validadas no levantamento inicial

1. O papel é a fonte principal do controle operacional na unidade observada.
2. O armeiro é o principal operador cotidiano do fluxo de entrega e devolução.
3. Um administrador com poderes separados controla contas, permissões e o cadastro de armeiros.
4. Cada item individual precisa ter situação, localização e responsável atual identificáveis.
5. Retiradas por turno, cautelas por prazo determinado e atribuições sem data final exigem regras e apresentações distintas.
6. O SIGAB pode operar como sistema independente, sem integração obrigatória para o primeiro incremento.
7. O histórico confirmado deve ser preservado, e correções futuras devem manter a rastreabilidade dos fatos anteriores.
8. A linguagem do produto corresponde à linguagem usada pelos armeiros e gestores das Guardas Municipais.

## Escopo e exclusões iniciais

A visão do produto contempla armamentos e diferentes equipamentos operacionais. O primeiro incremento, porém, permanece limitado a **itens físicos individualizáveis**, identificados por UUID interno e, quando existentes, número de série, patrimônio ou outro identificador institucional.

Permanecem fora desta decisão e dependem de pesquisa ou decisão própria:

- estoque quantitativo, munição, lotes, consumo e devolução parcial;
- integrações com sistemas oficiais ou de terceiros;
- biometria, assinatura definitiva e anexos sensíveis;
- restrições médicas, judiciais ou administrativas;
- retirada em nome de terceiro;
- inventário, manutenção, transferência, sinistro e baixa;
- operação offline e sincronização;
- afirmação de conformidade regulatória, jurídica ou com a LGPD antes dos levantamentos correspondentes;
- regras específicas de outros segmentos antes que eles sejam pesquisados e priorizados.

## Validação

O documento inicial de requisitos foi produzido após validação com o usuário-alvo da Guarda Municipal e consolida o processo, o público e a linguagem operacional usados nesta decisão. Para fins de rastreabilidade, ele é o entregável consolidado da SIGAB-002. A proveniência foi confirmada pelo responsável do projeto em 2026-10-19; a data e a identidade do participante não estão registradas neste repositório.

Entrevistas, demonstrações do processo e amostras autorizadas podem ampliar a descoberta e revelar variações entre unidades, mas não constituem pendência para a aprovação desta linha de base ou do glossário v0.2. Obrigações regulatórias permanecem pendentes da SIGAB-005.

## Consequências

- Entrevistas, glossário, papéis e pesquisa regulatória devem usar a Guarda Municipal como contexto inicial.
- A interface pode adotar termos validados nesse segmento, mas o modelo técnico não deve codificar a Guarda Municipal como o único tipo possível de organização.
- A expansão para polícias, sistema penitenciário, Forças Armadas, segurança privada ou outros segmentos exigirá descoberta e decisão específicas.
- Esta decisão deve ser revista se evidências posteriores mostrarem que o processo real não corresponde ao fluxo de itens individuais.
