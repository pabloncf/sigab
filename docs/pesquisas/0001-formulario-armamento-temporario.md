# Pesquisa 0001 — Formulário de armamento temporário

- Tarefa: SIGAB-007
- Requisito relacionado: RF-25
- Dependências: SIGAB-002 concluída; [nota regulatória 0001](../notas-regulatorias/0001-guardas-municipais.md) e [glossário](../glossario.md)
- Responsável: Produto
- Versão: 0.2.0
- Data-base da pesquisa: 2026-10-19
- Estado: **análise preliminar com base em modelos públicos de outros Municípios; o formulário da organização-alvo ainda não foi obtido**
- Bloqueia: retirada em nome de terceiro

> O responsável pelo projeto informou que não há outra documentação disponível. Por isso, esta versão analisa modelos de formulário e regras **publicados oficialmente por Municípios que não são a organização-alvo**. A matriz descreve o padrão encontrado nesses atos, não a regra da Guarda que vai usar o SIGAB. O critério de aceite da SIGAB-007 só fica atendido quando o modelo local for confrontado com esta matriz (seção 8).

## 1. Conclusões

1. **Não existe modelo federal de formulário de cautela.** A IN DG/PF nº 310/2025 trata do TAD e do porte funcional, e cada Município institui seus termos por decreto local. Os campos, as assinaturas e as vias variam de um Município para outro.
2. **"Armamento temporário" cobre mais de uma modalidade.** Todas as fontes separam pelo menos dois instrumentos:
   - **retirada por turno** (chamada de "empréstimo diário" ou "cautela diária"), registrada em **livro de carga/controle**, sem termo individual;
   - **cautela por prazo ou fixa**, formalizada por **Termo de Responsabilidade e Cautela**, assinado antes da saída.

   Essas modalidades correspondem a termos que o glossário já separa: retirada por turno, cautela e consignação. A correspondência está na seção 3.
3. **Nenhuma fonte autoriza retirada em nome de terceiro.** Dois termos dizem textualmente que a cautela é "pessoal e intransferível". Outro ato atribui a responsabilidade "a um único servidor". Nenhum ato prevê procuração, preposto ou retirada por colega. **Não há evidência que sustente o RF-25 como retirada por terceiro**, e esta pesquisa recomenda manter a funcionalidade bloqueada (seção 6).
4. **Nenhuma fonte fixa prazo de retenção.** Só existem regras de arquivamento ("arquivada e controlada pelo setor Administrativo"). A retenção continua dependendo da tabela de temporalidade municipal (OBR-11, SIGAB-039).
5. **Os termos coletam mais dados pessoais do que a movimentação precisa.** CPF, endereço, telefone e e-mail aparecem no termo de cautela. Para identificar o responsável, a matrícula basta. O SIGAB não deve replicar esses dados no registro da movimentação.

## 2. Fontes analisadas

| Id | Município/UF | Ato | O que contém | Acesso |
|---|---|---|---|---|
| F1 | Pedro Avelino/RN | [Decreto nº 231, de 01/11/2022](https://getpublic.inf.br/uploads/PMPA/pdf/20221101124440/getpub-view.pdf) | arts. 7º–20 e 26; Anexo I (Termo de Cautelamento), Anexo II (Termo de Responsabilidade e Cautela), Anexo III (autorização de desconto) | texto integral lido |
| F2 | Piedade/SP | [Decreto nº 8.192, de 28/06/2021](https://www.piedade.sp.gov.br/portal/leis_decretos/7734/) | arts. 7º–14 e 20; Anexos I e II com a mesma estrutura de F1 | texto integral lido |
| F3 | Cícero Dantas/BA | [Decreto nº 823, de 19/04/2022](https://www.cicerodantas.ba.gov.br/Handler.ashx?f=f&query=84bf2b6a-c1cc-4abf-a907-93893c814d2e.pdf) | arts. 6º–12; norma de procedimento anexa (itens 6.1.3–6.1.10, 6.3, 6.4.4) com os campos do registro de cautela | texto integral lido |
| F4 | Salto de Pirapora/SP | [Decreto nº 7.297, de 19/06/2025](https://www.dosp.com.br/leituratexto?p=MjE5MTQwNQ%3D%3D) | arts. 11–23 e 43: cautela fixa, diária e emergencial; campos do livro de cautelas; arquivamento | texto lido por resumo de ferramenta; conferir no original |
| F5 | Corumbá/MS | Decreto nº 2.430/2020 (via [reportagem](https://diarionline.com.br/index.php?id=120790&s=noticia)) | definição de cautela fixa, diária e emergencial | fonte secundária |

Limitações:

- F1 e F2 têm o mesmo texto-base. Por isso não contam como duas evidências independentes.
- Não consegui acessar os textos de Pontal do Paraná/PR, Barra dos Coqueiros/SE (PDF digitalizado, sem camada de texto) e Sapucaia do Sul/RS (acesso negado).
- Nenhuma fonte é da organização-alvo.

## 3. Modalidades e correspondência com o glossário

| Modalidade nas fontes | Instrumento | Prazo | Autoriza | Termo no glossário (hipótese) |
|---|---|---|---|---|
| Empréstimo/cautela diária (F1 art. 8º; F2 art. 8º; F4 art. 13; F5) | registro no livro de carga e controle | início ao fim do serviço | não identificado (F1, F2); setor Administrativo (F4) | retirada por turno |
| Empréstimo por cautela (F1 art. 7º, II: até 3 meses, prorrogável) | Termo de Responsabilidade e Cautela (Anexo II) | determinado | Inspetor Geral prorroga (F1) | cautela |
| Cautela fixa (F4 art. 12; F5) | cautela + termo de responsabilidade, arquivados | sem prazo | Secretário de Segurança (F4) | consignação |
| Cautela emergencial (F4 art. 14; F5) | justificativa + autorização | até 15 dias úteis, prorrogável; cancelamento automático (F4) | Secretário de Segurança (F4) | cautela com motivo "emergencial" |
| Cautela no serviço (F3 art. 6º) | livro + termo + registro em sistema ou planilha | enquanto em serviço | Comando habilita quem pode cautelar (F3 6.1.3) | retirada por turno |

A "cautela emergencial" é a reposição de uma arma perdida ou apreendida em ocorrência. Ela é feita ao próprio guarda e não é retirada por terceiro.

## 4. Pessoas e responsabilidades

| Papel nas fontes | Atribuição | Fonte |
|---|---|---|
| Guarda cautelado | assina o termo; responde pela guarda e manutenção; repara ou repõe em caso de dano, extravio, furto ou roubo (com ressalvas); comunica BO em até 24 h | F1 arts. 10, 14 e Anexo II; F3 art. 9º; F4 art. 18 |
| Responsável pela reserva de armamento (armeiro, paioleiro, cautelador) | registra entrada e saída; só entrega depois de o termo ser assinado; inspeção mensal; confere e dá baixa na devolução | F1 arts. 19–20; F2 arts. 13–14; F3 5.1 e 6.1.10 |
| Supervisor de dia | acompanha a cautela "sempre que possível" | F3 6.1.8 |
| Inspetor Geral, Comandante ou Secretário | autoriza cautela fixa, emergencial ou prorrogação; suspende ou retira a cautela; é o detentor legal da carga | F1 arts. 7º e 12; F4 arts. 11, 12, 14 e 20 |
| Corregedoria | recebe comunicação de extravio; registra no SINARM via PF; apura responsabilidade | F1 art. 12; F3 6.3.3 |
| Setor administrativo | arquiva e controla os termos de cautela fixa e emergencial | F4 arts. 12, §1º e 14, §2º |
| Chefia imediata | recolhe a arma se o guarda não devolver depois de a cautela ser retirada; faz relatório | F4 art. 21 |

Nas fontes, **quem autoriza** é uma autoridade de comando, diferente de **quem entrega** (a reserva). Na retirada por turno, nenhuma fonte identifica um autorizador para cada retirada além da habilitação geral.

## 5. Matriz de campos

Legenda:

- **Obrigatório?**: `sempre`, `condicional`, `opcional` ou `n/d` (a fonte não diz).
- **Emissor**: quem preenche ou assina.
- **Receptor**: quem recebe, confere ou arquiva.
- **Retenção**: nenhuma fonte fixa prazo. `tabela municipal` significa que o prazo depende da SIGAB-039.

### 5.1 Termo de Responsabilidade e Cautela (F1 Anexo II; F2 Anexo II)

| # | Campo/assinatura | Finalidade | Obrigatório? | Emissor | Receptor | Retenção | Dado pessoal? |
|---|---|---|---|---|---|---|---|
| T1 | Nome do guarda | identificar o responsável | sempre | guarda cautelado | reserva; setor administrativo | tabela municipal | sim |
| T2 | Matrícula | identificar o servidor de forma inequívoca | sempre | guarda cautelado | reserva; setor administrativo | tabela municipal | sim |
| T3 | CPF | identificação civil | sempre no modelo | guarda cautelado | reserva; setor administrativo | tabela municipal | sim; **não replicar no SIGAB** |
| T4 | Declaração de cautela "pessoal e intransferível" | fixar a responsabilidade individual e vedar a transferência | sempre (texto fixo) | órgão (modelo) | guarda cautelado | tabela municipal | não |
| T5 | Dever de comunicar furto/roubo/extravio em até 24 h, com BO | cumprir a comunicação à PF/SINARM | sempre (texto fixo) | órgão (modelo) | guarda cautelado; Corregedoria | tabela municipal | não |
| T6 | Declaração de conhecimento da legislação | ciência formal | sempre (texto fixo) | guarda cautelado | órgão | tabela municipal | não |
| T7 | Armamento: tipo, calibre, nº de série, quantidade | individualizar o bem cautelado | sempre | reserva | guarda cautelado; setor administrativo | tabela municipal | não |
| T8 | Munição: tipo, calibre, quantidade, identificação | controlar a munição entregue | condicional (quando houver) | reserva | guarda cautelado | tabela municipal | não (fora do escopo; SIGAB-008) |
| T9 | Endereço, telefone e e-mail ("informações complementares") | localizar o servidor | n/d | guarda cautelado | setor administrativo | tabela municipal | sim; **não replicar no SIGAB** |
| T10 | Atestado de veracidade | responsabilizar o declarante | sempre | guarda cautelado | órgão | tabela municipal | não |
| T11 | Local e data | datar o ato | sempre | guarda cautelado | órgão | tabela municipal | não |
| T12 | Assinatura do guarda | aceite da cautela; condição para a saída (F1 arts. 19–20) | sempre | guarda cautelado | reserva; setor administrativo | tabela municipal | sim |

Neste termo **não existe** assinatura de quem entrega nem de quem autoriza, campo de prazo de devolução ou campo de estado do item.

### 5.2 Termo de Cautelamento, documento de porte (F1 Anexo I; F2 Anexo I)

| # | Campo/assinatura | Finalidade | Obrigatório? | Emissor | Receptor | Retenção | Dado pessoal? |
|---|---|---|---|---|---|---|---|
| C1 | Material: tipo (pistola, revólver, espingarda, munição, algema, colete, tonfa, rádio), marca, calibre, nº de série, quantidade | provar a posse legítima do material durante o porte | sempre | reserva | guarda cautelado (porta consigo) | enquanto durar a cautela; a cópia arquivada segue a tabela municipal | não |
| C2 | Base legal (Lei 10.826/2003, art. 6º, III e §1º) | fundamento do porte | sempre (texto fixo) | órgão | — | — | não |
| C3 | Assinatura do responsável pela reserva | atestar a entrega | sempre | reserva | guarda cautelado | idem C1 | sim |
| C4 | Assinatura do guarda | atestar o recebimento | sempre | guarda cautelado | reserva | idem C1 | sim |
| C5 | Validade condicionada à carteira funcional | vincular o documento ao portador | sempre (texto fixo) | órgão | fiscalização | — | não |

### 5.3 Registro de cautela no livro, planilha ou sistema (F3 6.1.6 e 6.1.10; F4 art. 43; F1 e F2 art. 8º)

| # | Campo | Finalidade | Obrigatório? | Emissor | Receptor | Retenção | Dado pessoal? |
|---|---|---|---|---|---|---|---|
| L1 | Matrícula e nome do guarda | responsável | sempre | reserva | SME/reserva; Comando | tabela municipal | sim |
| L2 | Tipo e nº de série da arma | individualizar | sempre | reserva | SME/reserva | tabela municipal | não |
| L3 | Estado da arma e dos acessórios na entrega | base da conferência na devolução | sempre (F4) | reserva | guarda (ciência) | tabela municipal | não |
| L4 | Acessórios e carregadores (quantidade e estado) | controlar componentes | sempre (F3, F4) | reserva | SME/reserva | tabela municipal | não |
| L5 | Munição: quantidade, descrição, lote | rastrear munição | condicional | reserva | SME/reserva | tabela municipal | não (fora do escopo) |
| L6 | Data e hora da retirada | início da posse | sempre | reserva | SME/reserva | tabela municipal | não |
| L7 | Data e hora da devolução | fim da posse | sempre | reserva | SME/reserva | tabela municipal | não |
| L8 | Estado na devolução, alterações e ciência do guarda | apurar dano e responsabilidade | sempre (F4); conferência obrigatória (F3 6.1.10) | reserva (paioleiro) | guarda (ciência); Comando, se houver alteração | tabela municipal | não |
| L9 | Observações e ocorrências relacionadas | vincular disparo, dano ou extravio | condicional | reserva | Comando; Corregedoria | tabela municipal e enquanto houver apuração | pode conter |
| L10 | Assinaturas de entrega e recebimento (acautelamento no fim do expediente) | provar a transferência de guarda | sempre (F4 art. 23) | guarda e setor administrativo | um ao outro | tabela municipal | sim |

### 5.4 Documentos acessórios encontrados

- **Autorização de desconto em folha** (F1 Anexo III): só existe depois de extravio com culpa provada. Contém dados pessoais e financeiros e está fora do escopo do SIGAB.
- **Justificativa e autorização de cautela emergencial** (F4 art. 14): nenhuma das fontes lidas traz modelo.
- **Relatório de disparo e formulário de ocorrência** (F1 art. 24; F3 6.2.12–6.3.5): pertencem ao fluxo de incidente, fora do escopo atual.

## 6. Retirada em nome de terceiro (RF-25)

| Evidência | Fonte |
|---|---|
| A cautela é "pessoal e intransferível" | F1 e F2, Anexo II |
| A responsabilidade cabe "a um único servidor" | F4 art. 18 |
| Só GCMs habilitados e com porte válido realizam carga, guarda e descautela | F3 6.1.3 |
| A saída depende da assinatura do próprio guarda | F1 art. 19, parágrafo único; F2 art. 13 |
| Hipótese de recolhimento por outra pessoa: só pela chefia, depois de a cautela ser retirada | F4 art. 21 |

Recomendação: **não implementar retirada em nome de terceiro** com base nas fontes disponíveis. Os atos analisados vedam a transferência ou não preveem a hipótese, e a regra contrária teria impacto jurídico (OBR-03, OBR-08). Antes de qualquer modelagem, o RF-25 precisa de decisão de produto que defina se existe de fato um caso de uso local e qual ato normativo o autoriza. Dois candidatos aparecem nas fontes, e nenhum é retirada por terceiro: o recolhimento pela chefia (F4 art. 21) e a cautela emergencial (F4 art. 14). A retirada em nome de terceiro continua fora do escopo, conforme o CLAUDE.md e a [decisão 0001](../decisoes/0001-segmento-inicial.md).

## 7. Comparação com o modelo atual do SIGAB

Esta seção apenas aponta lacunas. Não implemente nada antes da decisão correspondente.

| Informação nas fontes | Situação no SIGAB | Observação |
|---|---|---|
| Responsável (matrícula/nome) | `Movement.recipient` → `Person` | atende; matrícula vem de `Membership` |
| Quem entrega | `Movement.operator` → `Account` | atende |
| Item: tipo, série, patrimônio | `Item.equipment_type`, `serial_number`, `asset_number`, `official_identifier` | atende |
| Data e hora da retirada e da devolução | `Movement.confirmed_at` | atende |
| Estado na devolução | `Movement.condition_on_return` (apto/inapto) | atende parcialmente: sem descrição das alterações nem ciência do guarda |
| Estado na entrega | ausente | lacuna; depende da SIGAB-009 |
| Modalidade (turno, cautela, consignação, emergencial) | ausente | lacuna; exige decisão de modelagem |
| Prazo ou condição de devolução | ausente | lacuna; necessário para cautela por prazo |
| Autorizador diferente do operador | ausente | lacuna; relacionada à dupla aprovação (pendência futura) |
| Acessórios e carregadores | ausente | lacuna; avaliar se são itens individuais ou atributos |
| Referência ao termo em papel (número/via) | ausente | relacionada à SIGAB-046 (registro de contingência) |
| Aceite ou assinatura do guarda | ausente | fora do escopo ("Prova/assinatura e comprovantes" em decisões pendentes) |
| Munição | ausente | fora do escopo (SIGAB-008) |
| CPF, endereço, telefone, e-mail | `Person` tem CPF opcional | **não levar para a movimentação** |

## 8. Pendências para concluir a SIGAB-007

| Pendência | Responsável | Estado |
|---|---|---|
| Obter o modelo da organização-alvo e confrontá-lo com as seções 3 a 5 | Produto | pendente; sem documentação disponível em 2026-10-19 |
| Confirmar no original o texto de F4 (lido por resumo) | Produto | pendente |
| Decidir se o RF-25 se mantém, é reescrito ou é descartado (seção 6) | Produto/Domínio | pendente |
| Decidir como modelar a modalidade da saída e o prazo de devolução | Produto + ADR | pendente |
| Regra de retenção dos termos e registros (SIGAB-039) | Produto/Jurídico/Arquivo | pendente |

Roteiro para quando o modelo local for obtido:

1. Para que serve o formulário? Que modalidades da seção 3 ele cobre?
2. Que ato institui o formulário? Ele tem vias? Quem fica com cada uma?
3. Quem autoriza, quem entrega, quem recebe? Existe dupla autorização?
4. Os campos T1–T12, C1–C5 e L1–L10 existem no modelo local? Que campos existem lá e não aparecem aqui?
5. Existe alguma hipótese local de retirada por pessoa diferente do responsável? Com base em qual ato?
6. Como uma via é corrigida ou anulada?
7. Qual é a tabela de temporalidade aplicável aos termos e aos livros?

## 9. Histórico de versões

| Versão | Data | Alteração |
|---|---|---|
| 0.1.0 | 2026-10-19 | Instrumento de coleta e matriz vazia. |
| 0.2.0 | 2026-10-19 | Análise de modelos públicos (F1–F5): modalidades, responsabilidades, matriz de campos, retirada por terceiro e comparação com o modelo atual. |
