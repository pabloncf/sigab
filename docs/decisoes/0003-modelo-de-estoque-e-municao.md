# Decisão de domínio 0003 — Modelo de estoque quantitativo e munição

- Tarefa: SIGAB-008
- Data: 2026-10-19
- Estado: **proposta — controle por calibre validado no sistema de referência; aguardando validação com a organização-alvo**
- Responsável pela validação: Produto/Domínio
- Dependências: SIGAB-002 concluída; SIGAB-005 com pesquisa federal preliminar ([nota regulatória 0001](../notas-regulatorias/0001-guardas-municipais.md), OBR-10); padrão de eventos da SIGAB-012 ([ADR 0003](../adr/0003-eventos-idempotencia.md))
- Requisitos relacionados: RF-13, RF-24 e RN-04 do documento inicial de requisitos ([DOC-0011 v0.1](../fontes/DOC-0011-analise-de-requisitos-v0.1.md), 2026-09-29). Todos estão no estado `Proposto`. A conferência está na seção 11.
- Bloqueia: SIGAB-041 (livro de estoque quantitativo)

> Este documento propõe o modelo exigido pelo critério de aceite. Ele **não autoriza implementação**: tabelas, endpoints e telas de estoque continuam ausentes até a validação registrada na seção 13. As questões da seção 12 precisam ser confirmadas com a Guarda participante.

## 1. Decisão proposta

Munição e demais materiais fungíveis ("item de estoque" no DOC-0011) serão controlados como **estoque quantitativo por tipo**, em um **livro de lançamentos imutável e de partidas dobradas**. Para munição, o tipo é definido pelo **calibre**. O saldo é uma projeção transacional desse livro e nunca é editado diretamente (RN-04).

1. Material quantitativo nunca usa `Item` nem o fluxo de item individual. Essa invariante já existe (RF-10, RN-03) e continua valendo.
2. A menor unidade controlada é um **inteiro na unidade base do tipo** (para munição, o cartucho). Não existem quantidades fracionárias.
3. **Não existe controle por lote.** Saldo, saída, devolução e consumo são por tipo (calibre). Essa regra foi validada no sistema de referência em 2026-10-19 e responde à pergunta 5 da seção 8 do DOC-0011. O número de lote, o fabricante e a validade podem ser registrados na entrada como **informação de procedência**, mas não criam saldo separado (seção 2.1).
4. Toda quantidade se move entre **posições de saldo**. A soma das quantidades de uma operação é sempre zero, e nenhuma posição física fica negativa.
5. Na saída, a munição passa a ficar **em posse operacional da pessoa responsável**, por tipo, até ser devolvida ou ter o consumo justificado. A devolução pode ser parcial. O que não foi devolvido nem justificado continua sendo **pendência** (glossário do DOC-0011, RF-24 e RF-27); o sistema nunca encerra uma pendência sem justificativa.
6. Correções são feitas por ajuste com motivo e aprovação separada ou por estorno compensatório (RN-04, RN-05 e RN-09; [decisão 0002](0002-papeis-e-escopos.md); [ADR 0003](../adr/0003-eventos-idempotencia.md)).

## 2. Conceitos

| Conceito | Definição proposta | Não confundir com |
|---|---|---|
| Tipo quantitativo | `EquipmentType` com classificação `quantitativo` ("de estoque", RF-10); define o material e a unidade base | item individual |
| Tipo de munição | tipo quantitativo cujo atributo obrigatório é o **calibre**. Munições do mesmo tipo são intercambiáveis no saldo; calibres diferentes nunca se misturam | marca, fabricante ou lote |
| Unidade base | unidade inteira em que saldos e lançamentos são registrados (por exemplo, "cartucho") | **unidade** organizacional do RF-13 e do [glossário](../glossario.md#unidade) |
| Embalagem | fator de conversão informado somente na entrada (por exemplo, caixa = 50 cartuchos), convertido imediatamente para a unidade base | unidade base |
| Procedência | dados informativos de uma entrada: documento de aquisição e, quando houver, fabricante, número de lote e validade | saldo; posição |
| Posição de saldo | onde a quantidade está: local de guarda (disponível ou inapto) ou pessoa responsável (em posse) | localização de item individual |
| Contrapartida externa | origem ou destino fora do acervo (origem da entrada, consumo, ajuste). Não tem saldo físico e existe apenas para fechar a partida dobrada | local de guarda |
| Pendência | quantidade em posse de uma pessoa, vinculada a uma saída, que ainda não foi devolvida nem teve o consumo justificado | divergência de contagem (RF-42) |
| Lançamento | linha imutável do livro: operação, tipo, posição, quantidade com sinal, instante e ator | saldo |
| Operação de estoque | ato confirmado (entrada, saída, devolução etc.) que gera dois ou mais lançamentos de soma zero | evento de auditoria |

### 2.1 Onde fica cada atributo

| Atributo pedido na tarefa | Onde fica | Efeito no saldo |
|---|---|---|
| calibre | tipo de munição, obrigatório | define o saldo: um saldo por calibre e posição |
| lote | procedência da entrada, opcional | nenhum; só registra quais lotes entraram |
| fabricante | procedência da entrada, opcional | nenhum |
| validade | procedência da entrada, opcional | nenhum; o sistema não sabe quais cartuchos de uma posição estão vencidos (ver 12.4) |
| unidade de medida | tipo (unidade base) e entrada (embalagem) | o saldo é sempre na unidade base |
| unidade organizacional (RF-13) | derivada do local de guarda da posição | o local de guarda já pertence a uma unidade; não se duplica o vínculo |

O calibre e a unidade base seguem a mesma regra da classificação (RF-16, RN-03): **não mudam depois que o tipo tiver lançamentos**.

Este modelo admite a granularidade "só por calibre". Se cada calibre precisar se dividir em especificações não intercambiáveis (por exemplo, munição de treino e de serviço), cada especificação vira **outro tipo**. O modelo não muda; só o cadastro. Ver questão 12.9.

## 3. Posições de saldo

```text
Origem (externa) ──entrada──▶ Local de guarda: disponível
                                 │  ▲
                          saída  │  │ devolução apta
                                 ▼  │
                              Pessoa responsável: em posse  ← pendência enquanto > 0
                                 │        │
               consumo justificado        │ devolução inapta
                                 ▼        ▼
                       Consumo (externa)  Local de guarda: inapto
                                              │
                                              └─ ajuste/baixa (futuro) ─▶ externa

Ajuste aprovado (+/−) ◀──▶ Local de guarda (disponível ou inapto)
```

- As posições são identificadas por `(tipo, local de guarda, disponível | inapto)` e por `(tipo, pessoa, saída)`.
- Somente o **saldo disponível** de um local de guarda pode sair (RN-08).
- O **saldo inapto** guarda munição devolvida inapta, vencida ou suspeita. Ele não sai para uso. O destino final (descarte, devolução ao fabricante, baixa) é uma tarefa futura e fica fora deste escopo.
- O **saldo em posse** é verificável pelo livro, como a posse operacional do item. Enquanto for positivo, ele é a pendência listada no RF-27.
- As contrapartidas externas não têm saldo físico, por isso a regra de não negatividade não se aplica a elas.
- Por tipo, o painel do RF-40 é a soma das posições: total = disponível + em posse + inapto.

## 4. Operações

Toda operação tem confirmação explícita com resumo (RF-21), chave de idempotência única por organização, ator, unidade, instante UTC, motivo quando exigido (RN-09) e correlação. Toda operação gera lançamentos de soma zero.

| Operação | Débito (sai de) | Crédito (entra em) | Regras |
|---|---|---|---|
| **Entrada** (cadastro de estoque, RF-13) | externa: origem | local: disponível | tipo + quantidade + local de guarda (e, portanto, unidade); quantidade convertida da embalagem; procedência com referência ao documento de aquisição (número, órgão, data) e, opcionalmente, fabricante, lote e validade, sem anexo |
| **Saída** (RF-20) | local: disponível | pessoa: em posse | tipo e quantidade ≤ saldo disponível; pode compor a mesma saída que itens com registro (ver 4.2) |
| **Devolução apta** (RF-22) | pessoa: em posse | local: disponível | mesmo tipo que saiu; pode ser parcial; fica disponível no mesmo instante (RF-23) |
| **Devolução inapta** (RF-22) | pessoa: em posse | local: inapto | motivo obrigatório |
| **Consumo justificado** (RF-24) | pessoa: em posse | externa: consumo | justificativa obrigatória (RN-09) com finalidade (treinamento, ocorrência, outro) e referência textual ao registro externo quando houver; quem consumiu é a pessoa responsável e quem registra é o armeiro |
| **Ajuste** (RN-04) | posição ou externa | posição ou externa | solicitação e aprovação por atores distintos (decisão 0002); motivo obrigatório (contagem, dano, vencimento, erro de registro); aplicado de forma atômica na aprovação |
| **Estorno** (RN-05) | inverso da operação original | inverso da operação original | referencia a operação original e exige motivo; não pode deixar posição negativa; uma operação só pode ser estornada uma vez |

Não existe operação que encerre uma pendência sem devolução ou justificativa. A munição que nunca volta (extravio, furto, perda) pertence ao fluxo de sinistro, que está fora do escopo (DOC-0011, 4.8; OBR-09). Até esse fluxo existir, a quantidade continua como pendência visível.

### 4.1 Devolução parcial e pendência

Uma saída de munição continua com **pendência enquanto houver saldo em posse** vinculado a ela. Cada devolução ou consumo justificado reduz esse saldo. A pendência se encerra quando o saldo chega a zero, ou seja, "pelo que foi justificado" (RF-24). Para cada tipo da saída vale:

```text
entregue = devolvido apto + devolvido inapto + consumido justificado + pendência
```

Na devolução, o sistema mostra a quantidade em posse por tipo. O sistema não deduz consumo a partir da falta. A diferença não justificada permanece como pendência, e não como consumo. É exatamente esse problema que o D6 descreve ("pendência falsa de munição").

### 4.2 Saída conjunta com itens com registro (RF-20)

Uma mesma saída pode conter itens com registro e linhas de estoque com quantidade. Ela é confirmada **uma única vez** (RF-21), numa só transação, com uma chave de idempotência e uma correlação comuns. Se qualquer linha falhar (item indisponível ou saldo insuficiente), nada é gravado.

Os registros de domínio continuam separados: movimentação de item para cada item e operação de estoque para cada tipo. As devoluções também são independentes: devolver a arma não encerra a pendência de munição, nem o contrário. Ver questão 12.3.

## 5. Saldo

- O saldo de cada posição física é `soma(lançamentos)` da posição. Uma tabela de projeção (`saldo por tipo e posição`) é atualizada **na mesma transação** que grava os lançamentos.
- O saldo agregado por tipo, local ou unidade (RF-40) é sempre derivado das projeções.
- O histórico de um tipo de estoque (RF-54: saídas, devoluções e consumos) é a consulta ao livro filtrado por tipo.
- Uma rotina de reconciliação compara a projeção com a soma do livro. Uma divergência é tratada como incidente técnico e nunca corrigida por edição.
- Saldo zero não apaga a linha. O histórico continua consultável.

## 6. Prevenção de saldo negativo

São camadas complementares, e nenhuma depende só da interface:

1. **Restrição de banco**: `CHECK (quantidade >= 0)` na projeção de toda posição física e `CHECK (quantidade <> 0)` em cada lançamento.
2. **Bloqueio**: a operação faz `select_for_update` nas linhas de projeção envolvidas, **sempre na mesma ordem determinística** (por exemplo, por UUID), para evitar deadlock.
3. **Atualização condicional**: o débito usa `UPDATE … SET quantidade = quantidade - n WHERE … AND quantidade >= n`. Se nenhuma linha for afetada, a operação inteira é rejeitada e nada é gravado.
4. **Atomicidade**: lançamentos, projeção, evento de domínio e auditoria ficam numa única `transaction.atomic`.
5. **Idempotência**: a chave é única no banco. Repetir a confirmação (o duplo clique do D7) devolve a operação original e não cria lançamento novo.
6. **Testes**: confirmações concorrentes em PostgreSQL com conexões independentes. Duas saídas que, somadas, excedem o saldo resultam em exatamente uma aceita.

Um ajuste negativo ou um estorno que deixaria uma posição física negativa também é rejeitado.

## 7. Contingência (ADR 0004 e SIGAB-046)

Movimentações de munição registradas em papel durante a contingência são lançadas depois com o **instante do fato** e a referência ao documento. Elas entram na ordem de registro, e a regra de não negatividade vale no momento do lançamento. Se o lançamento tardio deixaria uma posição negativa, ele é rejeitado e a diferença é resolvida por um ajuste aprovado com motivo. O sistema nunca reordena nem reescreve lançamentos anteriores.

## 8. Autorização e auditoria

- O tenant vem da conta autenticada. Tipo, local e pessoa precisam pertencer à mesma organização, e uma referência cruzada falha sem revelar se o registro existe.
- Mapeamento proposto para a matriz 0002, a detalhar na SIGAB-022. É coerente com a seção 3 do DOC-0011, em que o armeiro registra consumo e devolução parcial e o Adm cadastra estoque:
  - entrada: cadastro de acervo (Gestor de acervo; Operador de reserva se a organização conceder);
  - saída, devolução e consumo justificado: execução (Operador de reserva);
  - ajuste e estorno: solicitação pelo Operador e aprovação pelo Aprovador ou Gestor, nunca pelo mesmo ator.
- Bloqueio da organização (RN-07): devolução e consumo justificado nunca são bloqueados; só novas saídas e entradas são.
- O evento de domínio guarda a operação, o tipo, as posições e as quantidades. A auditoria guarda o ator, a ação, o objeto, o instante UTC e a correlação (RF-60). Nenhum dos dois replica dados pessoais além do identificador da pessoa responsável.
- Metadados seguem schema versionado (por exemplo, `stock.checkout.v1`), sem JSON genérico.

## 9. Fora deste modelo

- **Saldo por lote, regra de vencimento por lote e rastreio de qual lote foi entregue a quem.**
- **Anexo do consumo (RF-24):** o requisito prevê anexo opcional (documento ou foto), mas anexos dependem de política aprovada. Por enquanto, o consumo guarda apenas uma referência textual ao registro externo (ver questão 12.5).
- **Contagem guiada e ocorrência (RF-41, RF-42):** a contagem só gera ajustes. A ocorrência com responsável e status é tarefa própria.
- **Retirada em nome de terceiro (RF-25, RN-10):** a posse de munição fica sempre em nome de quem usa, mas a retirada por terceiro depende da SIGAB-007.
- **Outros fluxos:** sinistro (extravio, furto, perda), recarga, transferência entre unidades, descarte e baixa, integração com SINARM, SisFPC ou sistema patrimonial, relatórios e exportações (RF-56).

Os itens acima exigem tarefa e decisão próprias. Nenhuma tabela ou endpoint vazio deve ser criado para eles.

### 9.1 Consequências do controle sem lote

- **Rastreabilidade regulatória:** a OBR-10 exige identificação de lote e adquirente nas **compras**. A procedência da entrada registra o lote adquirido, mas o SIGAB não consegue dizer em que lote estava a munição entregue a uma pessoa, consumida ou extraviada. Se o Município, a PF ou o Exército exigirem essa rastreabilidade, o modelo terá de mudar. O impacto precisa ser confirmado na validação jurídica da SIGAB-005.
- **Validade:** como o saldo não separa lotes, munição vencida só sai do disponível por ajuste aprovado para a posição inapta. O sistema não bloqueia automaticamente a saída de munição vencida.
- **Reversibilidade:** acrescentar a dimensão de lote depois exige migração. Os saldos existentes passariam a um "lote não identificado" por tipo e posição, e o livro anterior continuaria sem lote. A mudança é possível, mas não é barata. Por isso a decisão deve ser confirmada com a organização-alvo antes da SIGAB-041.

## 10. Divergências entre a proposta e o DOC-0011

| Tema | DOC-0011 | Proposta | Tratamento |
|---|---|---|---|
| lote | RF-13 não pede lote; a seção 7 deixa "munição por lote" fora | controle só por calibre, com lote apenas como procedência | alinhado; validado no sistema de referência em 2026-10-19; falta a organização-alvo |
| anexo do consumo | RF-24 prevê anexo opcional | apenas referência textual | conflito com a política de anexos do projeto; questão 12.5 |
| hierarquia de perfis | Dev > Adm > Armeiro > Usuário | papéis sem hierarquia e com escopo (decisão 0002) | já decidido na SIGAB-004; o mapeamento da seção 8 preserva quem faz o quê |

## 11. Conformidade com os requisitos relacionados

| Requisito (DOC-0011 v0.1) | Texto resumido | Como o modelo atende |
|---|---|---|
| RF-13 | cadastro de item de estoque: tipo + quantidade + unidade | entrada na posição disponível de um local de guarda, que pertence a uma unidade (seções 2.1 e 4) |
| RF-24 | consumo e devolução parcial com justificativa e anexo opcional; a pendência se encerra pelo que foi justificado | consumo justificado e devolução parcial; a pendência só cai por devolução ou justificativa (seções 4 e 4.1); anexo pendente (seção 9) |
| RN-04 | saldo não é editado diretamente; só muda por movimentação, consumo ou ajuste com motivo | saldo derivado do livro, sem operação de edição; ajuste com motivo e aprovação (seções 1, 4, 5 e 6) |
| RF-20, RF-21 | saída conjunta e confirmação explícita | seção 4.2 |
| RF-22, RF-23 | conferência apto/inapto; apto disponível no mesmo instante | seção 4 (Devolução apta e inapta) |
| RF-27, RF-40, RF-54 | pendências, painel por tipo, histórico de estoque | seções 3 e 5 |
| RN-05, RN-07, RN-08, RN-09 | estorno, bloqueio por inadimplência, inapto não sai, motivos | seções 3, 4 e 8 |

| Critério de aceite da SIGAB-008 | Onde está explicado |
|---|---|
| entrada | 4 (Entrada), 2.1 |
| saldo | 3, 5 |
| saída | 4 (Saída), 4.2 |
| consumo | 4 (Consumo justificado), 4.1 |
| devolução | 4 (Devolução apta e inapta), 4.1 |
| ajuste | 4 (Ajuste, Estorno), 8 |
| lote | 1, 2.1, 9.1 (controle sem lote, lote como procedência) |
| prevenção de saldo negativo | 6, 7 |

| Atributo da descrição da tarefa | Onde está explicado |
|---|---|
| calibre, lote, fabricante, validade, unidade de medida | 2.1 |
| consumo, devolução parcial | 4.1 |

## 12. Questões para validar com a Guarda participante

As respostas podem mudar o modelo e precisam ser registradas com responsável e data na seção 13.

1. **Controle por calibre**: ~~quantidade simples, lote ou calibre?~~ Respondido no sistema de referência: **só por calibre, sem lote** (2026-10-19). Falta confirmar com a Guarda participante que ela também não controla lote na reserva.
2. **Unidade base**: algum material de estoque do acervo real é medido em fração (spray, agente químico em ml ou g)? O modelo proposto aceita apenas inteiros.
3. **Arma e munição**: munição é entregue sempre junto com a arma, ou existe entrega isolada (treinamento, por exemplo)? Na devolução da arma, a munição precisa ser devolvida na mesma hora?
4. **Validade**: como a reserva separa hoje a munição vencida? Basta o ajuste manual para a posição inapta?
5. **Justificativa de consumo**: que comprovação a Guarda exige para disparo em serviço ou em treinamento (número de ocorrência, relatório, testemunha)? A referência textual basta até existir política de anexos?
6. **Pendência**: a munição fica com o guarda entre turnos? Depois de quanto tempo uma pendência vira alerta? Quando a munição não volta e não é justificada, a quem a Guarda comunica hoje?
7. **Estojos**: a devolução de estojos deflagrados é controlada? Se for, eles contam como material separado ou como evidência de consumo?
8. **Locais**: munição fica em local de guarda separado do armamento (paiol)? Existe transferência entre reservas?
9. **Granularidade**: um tipo por calibre basta, ou o mesmo calibre se divide em especificações que não podem se misturar (treino e serviço, por exemplo)?
10. **Aprovação**: que tamanho de ajuste exige aprovação do Comando, e não apenas do Aprovador da unidade?

## 13. Validação

| Item | Decisão | Responsável | Data | Evidência |
|---|---|---|---|---|
| conferência técnica com RF-13, RF-24 e RN-04 | feita; divergências na seção 10 | Tech Lead | 2026-10-19 | DOC-0011 v0.1 (requisitos em estado `Proposto`) |
| controle por calibre, sem lote (12.1) | Validado (referência) | Produto/Domínio | 2026-10-19 | confirmação do autor e do armeiro do sistema de referência, informada pelo responsável do projeto; registro bruto não versionado |
| controle por calibre na organização-alvo (12.1) | pendente | Produto/Domínio com a Guarda | — | — |
| impacto da OBR-10 no controle sem lote (9.1) | pendente | Jurídico/Produto (SIGAB-005) | — | — |
| modelo de livro, posições e pendência (1, 3, 4) | pendente | Produto/Domínio | — | — |
| questões 12.2 a 12.10 | pendentes | Produto/Domínio com a Guarda | — | — |

A conferência técnica e a validação no sistema de referência não validam o modelo para a organização-alvo. Pelo DOC-0011 (seção 1.2), a referência é uma organização que já tem sistema. Enquanto esta tabela tiver itens pendentes, a SIGAB-008 não satisfaz o critério de aceite ("modelo de estoque validado") e a SIGAB-041 continua bloqueada.
