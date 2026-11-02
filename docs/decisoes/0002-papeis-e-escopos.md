# Decisão de produto e segurança 0002 — Papéis e escopos

- Tarefa: SIGAB-004
- Data: 2026-10-19
- Estado: aprovada para a linha de base
- Responsáveis pela decisão: Produto/Segurança
- Dependências: SIGAB-002 e SIGAB-003 concluídas
- Matriz canônica: [`0002-papeis-e-escopos.json`](0002-papeis-e-escopos.json), versão 1.1.0

## Decisão

O SIGAB usará **papéis como conjuntos nomeados de permissões**, concessões
explícitas e três classes de escopo: global, organização e unidade. Papéis
não herdam uns dos outros e nomes como “administrador”, “gestor” ou
“supervisor” não concedem poderes implícitos.

O acesso efetivo depende simultaneamente de permissão, recurso, organização,
unidade quando aplicável, vigência da concessão e regras de separação de
funções. Ausência de autorização explícita resulta em negação.

## Semântica dos escopos

| Escopo | Alcança | Não alcança |
|---|---|---|
| global | cadastro e operação do plano de controle da plataforma | dados de acervo, pessoas, movimentações ou auditoria de uma organização |
| organização | a organização indicada e suas unidades, somente para cada permissão concedida | outra organização; poderes não listados no papel |
| unidade | a unidade indicada e os recursos inequivocamente vinculados a ela | outra unidade, ainda que pertença à mesma organização |

Escopo mais amplo não implica papel superior. Uma permissão concedida no
escopo da organização pode atuar nas unidades daquela organização; uma
permissão ausente continua negada. Quando um objeto relaciona duas unidades, a
operação exige autorização explícita para ambas ou uma permissão de
organização apropriada.

## Papéis aprovados

| Papel | Escopo permitido | Finalidade |
|---|---|---|
| Administrador da plataforma | global | criar/suspender organizações e administrar configurações globais, sem ler dados de negócio |
| Analista de suporte | global | consultar telemetria sem conteúdo e solicitar sessão temporária de suporte |
| Administrador de acesso | organização | gerir contas, papéis e concessões da organização |
| Gestor de acervo | organização | gerir cadastro do acervo e aprovar ajustes, baixas e exceções operacionais |
| Gestor de restrições | organização | registrar, encerrar e consultar restrições operacionais com dados minimizados |
| Auditor | organização ou unidade | consultar acervo e trilhas imutáveis, sem mutação |
| Operador de reserva | unidade | consultar/cadastrar itens e executar saída, devolução e solicitações corretivas |
| Aprovador de acervo | unidade | aprovar ajustes, baixas e exceções da unidade, sem executar saída ou devolução |
| Leitor | unidade | consulta operacional somente leitura |

Os papéis são modelos iniciais reversíveis. Uma organização pode criar
outro conjunto de permissões, desde que preserve os conflitos obrigatórios
desta decisão. A interface deve mostrar permissões e escopo efetivos, e não
inferi-los apenas pelo nome do papel.

## Matriz resumida de autorização

Legenda: `L` leitura operacional; `C` cadastro de acervo; `I` identidades e
acessos; `E` execução; `S` solicitação; `A` aprovação e aplicação atômica;
`G` gestão; `T` trilha de auditoria; `D` diagnóstico sem conteúdo; `J` sessão
temporária autorizada. `—` significa negado.

| Papel | Leitura | Cadastro | Saída | Devolução | Ajuste | Baixa | Restrição | Auditoria | Suporte |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Administrador da plataforma | — | organização | — | — | — | — | — | metadados globais | — |
| Analista de suporte | — | — | — | — | — | — | — | próprias sessões | D/J |
| Administrador de acesso | L mínima | I | — | — | — | — | — | acessos | autoriza J |
| Gestor de acervo | L | C | — | — | A | A | aprova exceção | T operacional | — |
| Gestor de restrições | L mínima | — | — | — | — | — | G | T de restrições | — |
| Auditor | L | — | — | — | — | — | L minimizada | T | — |
| Operador de reserva | L | C | E | E | S | S | consulta decisão | T própria | — |
| Aprovador de acervo | L | — | — | — | A | A | aprova exceção | T operacional | — |
| Leitor | L | — | — | — | — | — | — | — | — |

A matriz JSON detalha as permissões atômicas que sustentam cada célula.

## Separação de funções e conflitos resolvidos

1. **Ajuste:** quem solicita não aprova a mesma solicitação. A aprovação
   aplica o ajuste de forma atômica e registra ambos os atores.
2. **Baixa:** quem solicita não aprova nem aplica a mesma baixa. Baixa nunca é
   exclusão do item ou de seu histórico.
3. **Restrição:** o gestor que cria ou encerra uma restrição não aprova
   exceção para o mesmo caso. O executor da saída também não aprova a
   exceção que usa. A saída permanece negada enquanto houver restrição ativa
   sem exceção válida.
4. **Auditoria independente:** o papel Auditor não pode coexistir, na mesma
   conta e no mesmo escopo, com papel que altere acervo, movimento, restrição,
   acesso ou sessão de suporte.
5. **Administração de acesso:** uma pessoa não concede, amplia, reativa ou
   revoga a própria concessão. O primeiro administrador continua sendo criado
   pelo fluxo controlado de bootstrap; alterações posteriores exigem outro
   administrador de acesso.
6. **Suporte:** suporte global não recebe acesso implícito a nenhum tenant. Uma
   sessão com conteúdo exige chamado, motivo, aprovação de administrador da
   organização, escopo mínimo, expiração máxima de 60 minutos e auditoria.
   Ela é somente leitura e mascara dados pessoais por padrão. Emergência sem
   aprovador da organização exige dois atores globais distintos e notificação
   posterior à organização.
7. **Plano de controle:** Administrador da plataforma e Analista de suporte não
   podem coexistir na mesma conta. Nenhum dos dois pode usar uma conta tenant
   para contornar o fluxo de suporte.

Combinações de papéis não conflitantes somam somente suas permissões
explícitas. As restrições acima prevalecem sobre essa união.

## Regras de aplicação

- Toda decisão é feita no backend a partir da conta autenticada; organização
  ou unidade enviada pelo cliente nunca é fonte de autoridade.
- Uma negação entre tenants não revela a existência do recurso externo.
- Concessões inativas, revogadas, ainda não vigentes ou expiradas não contam.
- Saída, devolução, ajuste, baixa, restrição, concessão e suporte geram
  auditoria com ator, escopo, objeto, instante UTC, resultado e correlação.
- Eventos e movimentos confirmados não são editados nem excluídos; correções
  são compensatórias.
- Dados de restrição seguem minimização: o operador recebe apenas a decisão
  necessária para permitir ou negar a saída, não o fundamento sensível.

## Compatibilidade e implementação

A implementação atual é parcial: `identity.manage`, `item.view` e `audit.view`
já são permissões separadas, mas `inventory.manage` e `movement.execute` ainda
agrupam operações que esta decisão separa. O modelo `Grant` aceita apenas
organização ou unidade e, portanto, não deve representar atores globais.

A SIGAB-022 deve:

- substituir as permissões agregadas pelas permissões atômicas da matriz;
- validar conflitos na criação e no uso da concessão;
- manter identidades globais em plano de controle separado das contas tenant;
- implementar sessões de suporte como autorizações temporárias, não como
  papel tenant permanente;
- adicionar testes de negação por tenant, unidade, permissão, vigência e
  conflito de função.

A matriz define autorização, não antecipa os fluxos de ajuste, baixa ou
restrição. Essas operações continuam indisponíveis até suas tarefas de domínio
serem aprovadas e implementadas.

## Rastreabilidade do critério de aceite

| Cobertura exigida | Evidência |
|---|---|
| papéis globais, da organização e da unidade | seções “Semântica dos escopos” e “Papéis aprovados” |
| leitura e cadastro | matriz resumida e permissões `*.view`, `catalog.manage`, `item.create`, `identity.manage` |
| saída e devolução | `movement.checkout` e `movement.return` |
| ajuste e baixa | pares `request`/`approve`, com autoaprovação proibida |
| restrição | gestão separada de exceção e dados minimizados |
| auditoria | consulta/exportação imutável e papel independente |
| suporte | diagnóstico sem conteúdo e sessão temporária controlada |
| conflitos resolvidos | sete regras obrigatórias de separação de funções |

Com essa cobertura e a matriz JSON versionada, a SIGAB-004 satisfaz seu critério
de aceite. Mudanças futuras exigem nova versão da matriz e registro da decisão.

## Revisão 1.1.0 — SIGAB-009

Data: 2026-10-19. A [decisão 0004](0004-ciclo-de-vida-do-item-individual.md)
acrescenta a permissão atômica `item.condition.set`, que permite declarar o
item inapto (com motivo) ou liberá-lo como apto enquanto ele está na reserva.

| Papel | `item.condition.set` |
|---|---|
| Operador de reserva | sim, na unidade |
| Gestor de acervo | sim, na organização |
| demais papéis | não |

A base é a seção 3 do [DOC-0011](../fontes/DOC-0011-analise-de-requisitos-v0.1.md),
que dá a ação “Marcar item como inapto ou apto” ao Armeiro e ao Adm. A
permissão não tem separação de funções: quem declara inapto pode liberar,
e a auditoria registra o ator de cada ato. Mudar a condição durante a posse
operacional continua sendo papel da devolução (`movement.return`).

## Revisão 1.2.0 — SIGAB-022 e SIGAB-024

Data: 2026-11-02. Os papéis e as permissões não mudam; esta revisão registra
um esclarecimento de alcance e o estado da implementação.

**Esclarecimento.** `catalog.manage` abrange, além dos tipos de equipamento,
o cadastro de unidades e locais de guarda da organização. A matriz não tinha
permissão própria para a estrutura física, e o Gestor de acervo é o papel que
“gere o cadastro do acervo”. Uma permissão separada só será criada se uma
organização precisar dividir essas funções.

**Implementado** (`backend/sigab/permissions.py`, `services.py`, `roles.py`):

- permissões atômicas no lugar de `inventory.manage` e `movement.execute`
  (migração `0005` converte papéis existentes: `inventory.manage` →
  `catalog.manage` + `item.create`; `movement.execute` → `movement.checkout` +
  `movement.return`);
- papel só aceita códigos da matriz e só é concedido nos escopos permitidos;
- concessão vigente: ativa, não revogada, `valid_from` ≤ agora < `valid_until`;
- superusuário e identidades da plataforma não recebem permissão de tenant;
- organização suspensa não recebe permissão alguma;
- conflitos verificados na concessão: `no_self_grant` (conta não concede nem
  revoga para si mesma) e `independent_auditor` (papel com `audit.export` não
  acumula permissão que altera dados em escopo sobreposto);
- toda organização nova recebe os papéis de tenant desta matriz; o primeiro
  administrador recebe Administrador de acesso e Gestor de acervo, ambos na
  organização. Ele não executa saída nem devolução: essas exigem Operador de
  reserva, concedido a outra conta.

**Ainda não implementado**, por dependerem de fluxos inexistentes: as regras
`different_actor_same_case` de ajuste, baixa, exceção de restrição e suporte;
a sessão temporária de suporte; o plano de controle separado para identidades
globais (hoje, o superusuário do Django Admin, de uso transitório).
