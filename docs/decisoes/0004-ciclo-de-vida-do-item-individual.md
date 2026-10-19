# Decisão de domínio 0004 — Ciclo de vida do item individual

- Tarefa: SIGAB-009
- Data: 2026-10-19
- Estado: **validada** (2026-10-19)
- Responsável pela validação: Produto/Domínio
- Dependências: SIGAB-002 e SIGAB-003 concluídas ([glossário](../glossario.md)); papéis da [decisão 0002](0002-papeis-e-escopos.md); padrão de eventos do [ADR 0003](../adr/0003-eventos-idempotencia.md); obrigações OBR-01, OBR-02, OBR-08 e OBR-09 da [nota regulatória 0001](../notas-regulatorias/0001-guardas-municipais.md)
- Requisitos relacionados: RF-14, RF-22 e RN-08 do [DOC-0011 v0.1](../fontes/DOC-0011-analise-de-requisitos-v0.1.md), todos no estado `Proposto`; também RF-21, RF-23, RN-05, RN-07 e RN-09
- Alimenta: implementação da condição/liberação do item (ver seção 9) e as futuras tarefas de manutenção, transferência, sinistro e baixa

> Este documento define a máquina de estados exigida pelo critério de aceite. A validação está registrada na seção 11. Ela **não autoriza implementação** das transições marcadas como `futura`: tabelas, endpoints e telas de manutenção, transferência, sinistro e baixa continuam ausentes até existir tarefa própria no backlog.

## 1. Decisão

O estado de um item individual é descrito por **quatro dimensões independentes** e por uma **disponibilidade derivada**. Nenhuma dimensão é sinônimo de outra, e a disponibilidade nunca é alterada diretamente.

| Dimensão | Pergunta que responde | Valores |
|---|---|---|
| Situação administrativa | o item ainda pertence ao acervo controlado? | `ativo`, `baixado`, `anulado` |
| Condição física | o item pode ser usado com segurança? | `apto`, `inapto` (com motivo) |
| Localização | onde o item está, segundo o registro? | `reserva`, `posse operacional`, `manutenção externa`, `em trânsito`, `desconhecida`, `retido externamente` |
| Lotação | a qual unidade e local de guarda o item pertence? | unidade + local de guarda de referência |
| **Disponibilidade** (derivada) | o item pode sair agora? | `disponível` ou `indisponível` com motivo |

Regras centrais:

1. **Disponível** se e somente se: situação `ativo` ∧ condição `apto` ∧ localização `reserva` ∧ nenhum bloqueio pendente (seção 2.5). Qualquer outra combinação é `indisponível`, e o motivo exibido é a primeira condição violada.
2. Toda mudança de dimensão acontece por uma **transição confirmada** (seção 4), que gera movimentação ou evento imutável, auditoria e atualização da projeção do item na mesma transação ([ADR 0003](../adr/0003-eventos-idempotencia.md)).
3. Nenhuma transição é desfeita por edição. Desfazer é sempre uma **transição inversa** (fluxo normal) ou um **estorno compensatório** com motivo e referência ao fato original (RN-05).
4. `baixado` e `anulado` são **terminais** para a operação: o item e seu histórico permanecem para consulta, mas nenhuma transição operacional parte deles. A única saída é o estorno controlado da seção 4.4.

## 2. Dimensões

### 2.1 Situação administrativa

| Valor | Significado | Não confundir com |
|---|---|---|
| `ativo` | o item integra o acervo e responde ao controle patrimonial (OBR-01) | disponível |
| `baixado` | o item saiu do acervo por ato formal com motivo (RN-09): inservível, destruído, alienado, transferido a outro órgão, sinistro não recuperado | apagado; o item e o histórico permanecem |
| `anulado` | o registro foi criado por erro (duplicado ou incorporação indevida) e **nunca representou um bem distinto** | baixa; anulação não aparece em relatório patrimonial como saída de bem |

Sinistro, manutenção e transferência **não** mudam a situação administrativa: um item furtado continua `ativo` até a baixa ou a recuperação.

### 2.2 Condição física

| Valor | Significado |
|---|---|
| `apto` | pode ser entregue e usado |
| `inapto` | não pode ser entregue (RN-08). Exige **motivo** de uma lista curta: `defeito`, `aguardando manutenção`, `aguardando inspeção`, `vencido/fora de especificação`, `outro` (texto obrigatório) |

A condição só é afirmada por uma pessoa autorizada que conferiu o item. Quando o item está em localização `desconhecida` ou `retido externamente`, a condição registrada é a **última conhecida** e não é atualizada até a recuperação.

### 2.3 Localização

| Valor | Significado | Fase |
|---|---|---|
| `reserva` | no local de guarda de referência (lotação) | implementada |
| `posse operacional` | com o responsável, vinculado a uma saída aberta ([glossário](../glossario.md#posse-operacional)) | implementada |
| `manutenção externa` | com oficina, fabricante ou fornecedor, sob ordem de serviço | futura |
| `em trânsito` | transferido entre unidades da mesma organização, ainda não recebido no destino | futura |
| `desconhecida` | extraviado, furtado ou roubado | futura |
| `retido externamente` | apreendido ou retido por autoridade (perícia, inquérito, processo) | futura |

Manutenção feita **na própria reserva** pelo armeiro não muda a localização: é apenas condição `inapto` com motivo `aguardando manutenção` e, depois, liberação (T06).

### 2.4 Lotação

Unidade e local de guarda de referência (`unit` e `storage_location` no modelo atual). Muda somente por remanejamento (T11) ou transferência recebida (T10). A devolução sempre retorna o item à sua lotação; devolução em outra unidade não existe nesta versão (questão 10.4).

### 2.5 Bloqueios que tornam o item indisponível

Além das dimensões, um item `ativo`, `apto` e na `reserva` fica indisponível enquanto houver:

- solicitação de baixa pendente (T16);
- transferência solicitada e ainda não enviada (T09, se a Guarda exigir aprovação prévia — questão 10.6).

Bloqueios são fatos com início e fim registrados, não um quinto estado editável.

## 3. Combinações válidas

| Situação | Condição | Localização | Disponibilidade | Válida? |
|---|---|---|---|---|
| ativo | apto | reserva | disponível (se sem bloqueio) | sim |
| ativo | inapto | reserva | indisponível: inapto | sim |
| ativo | apto ou inapto | posse operacional | indisponível: em posse | sim; condição inapta só se declarada durante a posse por sinistro de dano (T13) |
| ativo | qualquer | manutenção externa, em trânsito | indisponível | sim (futura) |
| ativo | última conhecida | desconhecida, retido externamente | indisponível: sinistro | sim (futura) |
| baixado ou anulado | última conhecida | reserva ou destino final informado | indisponível: fora do acervo | sim |
| baixado ou anulado | qualquer | posse operacional, em trânsito, manutenção externa | — | **não** |
| qualquer | qualquer | posse operacional sem saída aberta, ou saída aberta fora de posse operacional | — | **não** |

Invariantes derivadas, a garantir no banco ou no serviço:

- `posse operacional` ⇔ existe exatamente uma saída aberta ⇔ `current_holder` preenchido.
- Item com saída aberta não recebe outra saída (já implementado).
- Baixa, anulação, transferência e envio à manutenção exigem localização `reserva`.
- A disponibilidade gravada no item é projeção das demais dimensões e nunca é escrita isoladamente.

## 4. Transições

Legenda de fase: **impl.** já implementada; **MVP** necessária para o fluxo atual não ficar inconsistente; **futura** prevista, fora do MVP, sem implementação autorizada.

Toda transição que altera estado exige confirmação explícita (RF-21), chave de idempotência única na organização e autorização no backend para a unidade de lotação do item. Todas geram evento de domínio com schema versionado e evento de auditoria com organização, ator, objeto, instante UTC e correlação. Essas exigências comuns não se repetem nas linhas abaixo.

Permissões entre aspas existem na matriz da [decisão 0002](0002-papeis-e-escopos.md). Permissões marcadas *(nova)* não existem e precisam entrar na matriz antes da implementação (questão 10.1).

### 4.1 Entrada e uso diário

| ID | Transição | Origem → destino | Ator e permissão | Pré-condições | Efeito | Reversão | Fase |
|---|---|---|---|---|---|---|---|
| T01 | Incorporação | inexistente → `ativo`, condição declarada, `reserva` na lotação | Operador de reserva ou Gestor de acervo, `item.create` | tipo individual ativo da organização; local de guarda pertence à unidade; série e patrimônio únicos quando preenchidos | cria o item, movimentação `incorporation`, evento `item.incorporated` | registro errado → **anulação** (T20); dado cadastral errado → correção cadastral auditada com valor anterior e novo (RF-60), sem mudar estado | impl. (condição declarada: MVP) |
| T02 | Saída | `reserva` disponível → `posse operacional` | Operador de reserva, `movement.checkout` | item disponível (seção 1, regra 1); destinatário ativo com vínculo ativo; futuramente sem restrição ativa (RN-06) e organização não bloqueada (RN-07) | movimentação `checkout`, `current_holder` = destinatário, evento `item.checked_out` | normal: devolução (T03/T04). Erro (item não saiu): **estorno da saída** com motivo, que encerra a saída e restaura `reserva` sem registrar devolução | impl. (estorno: ver 9.4) |
| T03 | Devolução apta | `posse operacional` → `reserva`, `apto` | Operador de reserva, `movement.return` | saída aberta; conferência do item (RF-22) | movimentação `return` vinculada à saída, limpa `current_holder`, condição `apto`; item disponível no mesmo instante (RF-23) | condição errada → T05; devolução registrada por engano → **estorno da devolução**, que reabre a mesma saída | impl. |
| T04 | Devolução inapta | `posse operacional` → `reserva`, `inapto` | Operador de reserva, `movement.return` | igual a T03; **motivo de inapto obrigatório** | igual a T03, com condição `inapto` e motivo | liberação (T06); estorno da devolução, como em T03 | impl. (motivo: MVP) |
| T05 | Declarar inapto | `reserva`, `apto` → `reserva`, `inapto` | Operador de reserva, `item.condition.set` *(nova)* | item `ativo` na `reserva`, sem saída aberta; motivo obrigatório | evento `item.condition_changed` com condição anterior, nova e motivo; item indisponível | T06 | MVP |
| T06 | Liberar (declarar apto) | `reserva`, `inapto` → `reserva`, `apto` | Operador de reserva, `item.condition.set` *(nova)*; separação de quem declarou inapto: questão 10.2 | item `ativo` na `reserva`; referência da conferência ou manutenção (texto curto) | evento `item.condition_changed`; item disponível se não houver bloqueio | T05 | MVP |

Durante a `posse operacional`, a condição não é alterada por T05/T06: o responsável está com o item e a conferência acontece na devolução. A exceção é o sinistro de dano (T13).

### 4.2 Manutenção externa, remanejamento e transferência

| ID | Transição | Origem → destino | Ator e permissão | Pré-condições | Efeito | Reversão | Fase |
|---|---|---|---|---|---|---|---|
| T07 | Envio à manutenção externa | `reserva` → `manutenção externa` | Operador de reserva, `item.maintenance.send` *(nova)* | `ativo`, sem saída aberta; destinatário externo e ordem de serviço informados | movimentação `maintenance_out`; condição passa a `inapto` (`aguardando manutenção`) se ainda não estava | estorno do envio, se o item não saiu fisicamente | futura |
| T08 | Retorno da manutenção | `manutenção externa` → `reserva`, condição conferida | Operador de reserva, `item.maintenance.receive` *(nova)* | envio aberto; conferência apto/inapto, como em T03/T04; identificação conferida contra o cadastro | movimentação `maintenance_in` vinculada ao envio | condição errada → T05/T06; estorno do retorno reabre o envio | futura |
| T11 | Remanejamento de local | `reserva` no local A → `reserva` no local B **da mesma unidade** | Operador de reserva, `item.relocate` *(nova)* | sem saída aberta; local B ativo e da mesma unidade | muda o local de guarda de referência; evento `item.relocated` | novo remanejamento | futura |
| T09 | Envio de transferência | `reserva` na unidade A → `em trânsito` | Operador da unidade A; autorização para A e B ou permissão de organização (decisão 0002, “dois recursos”), `item.transfer.send` *(nova)* | `ativo`, sem saída aberta; unidade de destino da mesma organização | movimentação `transfer_out`; lotação continua em A até o recebimento | cancelamento antes do recebimento, que devolve à `reserva` em A | futura |
| T10 | Recebimento de transferência | `em trânsito` → `reserva` na unidade B | Operador da unidade B, `item.transfer.receive` *(nova)* | envio aberto; conferência de identidade e condição | movimentação `transfer_in` vinculada; lotação passa a B; condição conferida | nova transferência; erro material → estorno do recebimento com motivo | futura |

Transferência para **outra organização ou outro órgão** não é transferência interna: para a organização de origem é uma baixa (T17, motivo `transferido a outro órgão`) e depende do fluxo oficial (OBR-02, OBR-03). O SIGAB não move itens entre tenants.

### 4.3 Sinistro

| ID | Transição | Origem → destino | Ator e permissão | Pré-condições | Efeito | Reversão | Fase |
|---|---|---|---|---|---|---|---|
| T12 | Registro de extravio, furto ou roubo | `reserva` ou `posse operacional` → `desconhecida` | Operador de reserva ou Gestor de acervo, `item.incident.register` *(nova)* | `ativo`; natureza, data/hora do fato e relato mínimo | abre ocorrência com prazo de comunicação (OBR-09); item indisponível na hora; se havia saída aberta, a saída é **encerrada pelo sinistro**, e o responsável no momento fica registrado na ocorrência | recuperação (T14); registro errado → estorno do sinistro, que restaura a localização e reabre a saída encerrada | futura |
| T13 | Registro de dano | localização inalterada; condição → `inapto` | igual a T12 | `ativo`; descrição do dano | abre ocorrência; condição `inapto` (`defeito`); na posse, a devolução posterior (T04) mantém o item inapto | liberação (T06) após reparo | futura |
| T15 | Retenção externa | `reserva` ou `posse operacional` → `retido externamente` | igual a T12 | `ativo`; autoridade e número do procedimento | abre ocorrência; encerra saída aberta como em T12 | recuperação (T14) | futura |
| T14 | Recuperação ou restituição | `desconhecida` ou `retido externamente` → `reserva`, `inapto` (`aguardando inspeção`) | Operador de reserva, `item.incident.resolve` *(nova)* | ocorrência aberta; identificação conferida contra o cadastro | encerra a localização desconhecida/retida; a ocorrência segue aberta até as comunicações serem registradas | liberação (T06) após inspeção; estorno se a identificação estava errada | futura |

O registro interno de sinistro **não** comprova comunicação à PF, à polícia ou ao SINARM (OBR-02, OBR-09). O sistema guarda as referências dessas comunicações e o prazo, mas não declara a obrigação cumprida.

### 4.4 Saída do acervo

| ID | Transição | Origem → destino | Ator e permissão | Pré-condições | Efeito | Reversão | Fase |
|---|---|---|---|---|---|---|---|
| T16 | Solicitação de baixa | `ativo` (sem mudança de dimensão) → bloqueio pendente | Operador de reserva, `item.retire.request` | localização `reserva` ou `desconhecida`/`retido externamente` com ocorrência; sem saída aberta; motivo (RN-09) | registra solicitação; item indisponível enquanto pendente | rejeição ou desistência remove o bloqueio | futura |
| T17 | Aprovação e aplicação da baixa | `ativo` → `baixado` | Gestor ou Aprovador de acervo, `item.retire.approve`; **nunca** quem solicitou (decisão 0002, regra 2) | solicitação pendente; referência ao processo patrimonial (OBR-01) e, para arma de fogo, ao procedimento oficial (OBR-02), sem inferir que foi concluído | evento `item.retired`; item sai de contagens e disponibilidade; histórico preservado | **estorno de baixa** somente por erro material, com motivo e aprovador diferente de quem aplicou; item recuperado após baixa por sinistro: questão 10.8 | futura |
| T18 | Rejeição da baixa | bloqueio pendente → sem bloqueio | Gestor ou Aprovador de acervo, `item.retire.approve` | solicitação pendente; motivo | encerra a solicitação | nova solicitação | futura |
| T20 | Anulação de registro | `ativo` → `anulado` | Gestor de acervo, `item.retire.approve`; quem incorporou não anula sozinho | **nenhuma movimentação além da incorporação**; motivo (`duplicado` ou `incorporação indevida`), referência ao registro correto quando duplicado | evento `item.voided`; identificadores liberados para reuso: questão 10.9 | estorno da anulação por aprovador diferente | MVP |

### 4.5 Contingência

Saídas e devoluções lançadas depois do fato, a partir do registro em papel (SIGAB-046, [ADR 0004](../adr/0004-conectividade-e-contingencia.md)), seguem **as mesmas transições** T02, T03 e T04. A diferença é que registram o instante do fato separado do instante da confirmação. Lançamentos de contingência que conflitem com o estado atual (por exemplo, devolução de item que o sistema já mostra na reserva) não são aplicados automaticamente: viram divergência para tratamento manual.

## 5. Diagrama da localização

```text
                         T01 incorporação
                                │
                                ▼
          ┌─────────────────► RESERVA ◄──────────────── T11 remanejamento
          │                   │  │  │  │                   (mesma unidade)
          │       T02 saída   │  │  │  │ T12/T15 sinistro
          │    ┌──────────────┘  │  │  └───────────────────────┐
          │    ▼                 │  │                          ▼
  T03/T04 │  POSSE OPERACIONAL   │  │               DESCONHECIDA ou
devolução └──┘    │              │  │               RETIDO EXTERNAMENTE
                  │ T12/T15      │  │                          │
                  └──────────────┼──┼──────────────────────────┤
                                 │  │                          │ T14 recuperação
                   T07 envio     │  │ T09 envio                │ (volta inapto,
                                 ▼  ▼                          │  aguardando inspeção)
                  MANUTENÇÃO EXTERNA   EM TRÂNSITO             ▼
                         │                   │              RESERVA
                         └── T08 retorno     └── T10 recebimento
                             à RESERVA           na RESERVA da unidade B

Situação administrativa (independente da localização):
  ativo ──T16 solicitação + T17 aprovação──► baixado   (terminal)
  ativo ──T20 anulação──────────────────────► anulado   (terminal)

Condição física (muda na reserva ou por T04/T13/T14):
  apto ──T04/T05/T13──► inapto ──T06──► apto
```

## 6. Estornos

Cada transição confirmada pode ser estornada **uma vez**, por evento compensatório com motivo, referência ao fato original, ator e instante (RN-05, RN-09, ADR 0003). O estorno:

- só é aceito se o item ainda estiver no estado produzido pelo fato estornado. Se houve fato posterior, estorna-se primeiro o mais recente;
- nunca apaga nem edita o fato original, que continua visível no histórico com a marca de estornado;
- exige confirmação explícita e chave de idempotência, como qualquer transição;
- para baixa e anulação, exige aprovador diferente de quem aplicou o ato original.

Estorno corrige **erro de registro**. Um fato real posterior, como item recuperado depois de furto, é registrado pela transição normal (T14), não por estorno.

## 7. Conferência com o modelo atual

| Conceito desta decisão | Modelo atual (`sigab/models.py`) | Diferença |
|---|---|---|
| situação administrativa | `Item.administrative_status`: `active`, `inactive` | `inactive` não tem semântica, nenhum fluxo o define e **a saída não verifica a situação**. Proposta: substituir por `retired` (baixado) e `voided` (anulado) |
| condição | `Item.condition`: `fit`, `unfit` | compatível; falta o **motivo** de inapto (RF-14) |
| localização | implícita em `availability = in_custody` | o valor mistura localização e disponibilidade; sem lugar para manutenção, trânsito ou sinistro |
| lotação | `Item.unit` e `Item.storage_location` | compatível; hoje também representa a localização física quando o item está na reserva |
| disponibilidade | `Item.availability` gravada: `available`, `in_custody`, `unavailable` | compatível como projeção. A regra 1 (seção 1) passa a ser a única fórmula; `unavailable` hoje significa apenas “inapto na reserva” |
| T02 | `checkout_item` verifica `available` e `fit` | falta verificar `administrative_status` |
| T04 | `return_item` aceita `unfit` | não captura motivo |
| T06 | inexistente | **item devolvido inapto fica indisponível para sempre**: não há liberação |

Manter `availability` como coluna gravada é compatível com esta decisão e preserva a atualização condicional que garante a exclusão mútua da saída (CI com PostgreSQL). A migração de `in_custody` para uma coluna de localização separada fica a critério da tarefa de implementação e não é exigida no MVP.

## 8. Rastreabilidade

| Exigência | Onde |
|---|---|
| separar condição, disponibilidade, localização e situação administrativa | 1, 2 |
| origem e destino de cada transição | 4 (coluna “Origem → destino”), 5 |
| ator | 4 (coluna “Ator e permissão”) |
| pré-condição | 4 |
| efeito | 4 |
| possibilidade de reversão | 4 (coluna “Reversão”), 6 |
| prever manutenção, sinistro, transferência e baixa | 4.2, 4.3, 4.4 |
| RF-14 (disponível, em posse, inapto com motivo, baixado) | 2.1, 2.2, 3; motivo de inapto em T04/T05 |
| RF-22 (devolução com conferência apto/inapto) | T03, T04 |
| RN-08 (inapto não conta como disponível e não sai) | regra 1 da seção 1; T02 |

## 9. Consequências para implementação

Esta decisão não altera código. Ela orienta:

1. **Corrigir a saída** para exigir `administrative_status = active` (defeito atual; exige teste que reproduza a falha).
2. **Motivo de inapto** em T04 e T05, com lista fechada e texto em `outro`.
3. **T05/T06** (declarar inapto e liberar) como serviço transacional, evento `item.condition_changed.v1` e permissão nova na matriz (SIGAB-022).
4. **Estorno** de saída e devolução. A SIGAB-034 está como `Done` no backlog, mas o código não tem fluxo de estorno e o ADR 0003 registra que “estorno não foi exposto nesta entrega”. O backlog precisa ser conferido.
5. **T20 (anulação)** e a substituição de `inactive` por `retired`/`voided`, com migração nova.

As transições `futura` precisam de tarefas próprias (manutenção, transferência, sinistro, baixa), que hoje não existem no backlog. Pelas regras do projeto, não se criam tabelas nem endpoints vazios para elas.

## 10. Questões de detalhamento

Estas questões não bloqueiam a decisão validada. Elas refinam regras de transições específicas e devem ser respondidas na tarefa que implementar cada transição. Enquanto não houver resposta, vale o que está escrito na seção 4.

1. **Quem altera a condição?** O DOC-0011 propõe que o armeiro marque apto/inapto `[VALIDAR]`. Basta o Operador de reserva, ou a liberação exige outro papel (armeiro habilitado, inspeção)?
2. **Separação na liberação:** quem declarou o item inapto pode liberá-lo, ou é preciso uma segunda pessoa?
3. **Motivos de inapto:** a lista da seção 2.2 cobre o uso real?
4. **Devolução em outra unidade:** um guarda pode devolver em reserva diferente daquela em que retirou? Se sim, isso vira transferência implícita?
5. **Manutenção:** existe manutenção externa (fabricante, oficina) ou tudo é resolvido na reserva? Quem autoriza o envio?
6. **Transferência entre unidades:** exige aprovação prévia (Comando) ou basta o envio e o recebimento pelos operadores?
7. **Sinistro na posse:** quando a arma é furtada com o guarda, a Guarda encerra a cautela, ou a mantém aberta até a apuração?
8. **Recuperação após baixa:** item baixado por furto e recuperado anos depois volta como o mesmo item (estorno de baixa) ou é reincorporado com novo processo patrimonial?
9. **Anulação:** o número de série e o patrimônio de um registro anulado podem ser reutilizados no registro correto?
10. **Apreensão:** arma envolvida em ocorrência é retida por perícia ou inquérito com que frequência? É necessário distinguir `retido externamente` de `desconhecida`?

## 11. Validação

| Item | Decisão | Responsável | Data | Evidência |
|---|---|---|---|---|
| conferência técnica com o código atual | feita; divergências na seção 7 | Tech Lead | 2026-10-19 | `sigab/models.py`, `sigab/services.py` |
| conferência com RF-14, RF-22 e RN-08 | feita; seção 8 | Tech Lead | 2026-10-19 | DOC-0011 v0.1 (requisitos em estado `Proposto`) |
| quatro dimensões e disponibilidade derivada (1, 2, 3) | validada | Produto/Domínio | 2026-10-19 | confirmação informada pelo responsável do projeto; registro bruto não versionado |
| transições T01–T18 e T20, reversões e estornos (4, 5, 6) | validadas | Produto/Domínio | 2026-10-19 | idem |
| novas permissões *(nova)* na matriz da decisão 0002 | pendente; não bloqueia esta decisão | Produto/Segurança (SIGAB-022) | — | — |
| questões de detalhamento 10.1 a 10.10 | abertas; não bloqueiam esta decisão | Produto/Domínio com a Guarda | — | — |

Com a máquina de estados validada, a SIGAB-009 satisfaz seu critério de aceite. Isso não valida os requisitos RF-14, RF-22 e RN-08 individualmente, que continuam `Proposto` no DOC-0011. Também não autoriza a implementação das transições `futura`. A data, a identidade de quem validou e o artefato bruto da validação não estão no repositório, e este documento não os deduz.
