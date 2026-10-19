# SIGAB — Análise de requisitos v0.1

> **Transcrição de fonte.** Transcrição fiel do documento DOC-0011 v0.1 (arquivo `requisitos.pdf`), adicionada ao repositório em 2026-10-19 para referência futura. O conteúdo não foi alterado. Não edite este arquivo para registrar decisões: o que foi decidido depois fica nos ADRs, em `docs/decisoes/` e em `docs/decisoes-pendentes.md`. Uma nova versão do documento deve entrar como um novo arquivo.

id: DOC-0011 · status: rascunho · confidencialidade: interno · criado: 2026-09-29 · atualizado: 2026-09-29 · responsavel: pablo

**Sistema Integrado de Gestão de Acervo Bélico** · versão 0.1 · 2026-09-29

## 1 Finalidade

Este documento reúne os requisitos iniciais do SIGAB, derivados de duas fontes:

- **V: vídeos do sistema de referência.** 15 vídeos de uso, analisados em `DOC-0010` (códigos OBS e REL).
- **R: reunião de 2026-09-29.** Validação com o David, autor do sistema de referência, e com um armeiro que o opera (`REU-0001`, dores D1 a D8). Quando a reunião corrige o que os vídeos mostravam, o requisito diz **"corrige"**.

Um terceiro tipo de origem aparece quando a necessidade não veio de nenhuma das duas fontes:

- **I: inferido por nós.** Necessário para o produto funcionar ou ser vendido, mas ninguém pediu. **Precisa de validação antes de virar escopo.**

O SIGAB é um sistema **novo**. Nenhum código, banco de dados ou documento interno do sistema de referência é usado. O sistema de referência mostra o que um sistema desse tipo faz; ele não é especificação.

### 1.1 Público-alvo

Órgãos que ainda controlam acervo sem sistema: guardas e polícias municipais, empresas de segurança privada e órgãos de segurança pública sem sistema.

> **Limite desta versão.** Todos os requisitos vêm de um sistema de referência que opera numa organização que **já tem sistema**. Nenhum órgão-alvo foi ouvido. Requisitos marcados "Proposto" estão prontos para o David e o armeiro validarem, não para desenvolver.

### 1.2 Status dos requisitos

| Status | Significado |
|---|---|
| Proposto | Escrito neste documento, ainda não revisado. |
| Validado (referência) | O David e o armeiro que opera o sistema de referência confirmaram regra e comportamento. |
| Validado (alvo) | Um órgão-alvo confirmou a necessidade. |
| Descartado | Fica no documento com o motivo. Nunca é apagado. |

Todos os requisitos desta versão estão como **Proposto**.

## 2 Glossário

| Termo | Definição proposta |
|---|---|
| Organização | Órgão ou empresa cliente do SIGAB. Os dados de uma organização não são visíveis para outra. |
| Unidade | Subdivisão da organização que guarda acervo (batalhão, base, posto). |
| Tipo de equipamento | Modelo ou categoria do material (ex.: pistola de um modelo, algema, colete). No sistema de referência: "equipamento geral". |
| Item com registro | Unidade física identificada individualmente por número (ex.: uma arma com número de série). **Registro é por item.** |
| Item de estoque | Material controlado por quantidade, sem identificação individual (ex.: munição). **Cadastro é por estoque.** |
| Pessoa | Quem recebe material ou opera o sistema. Identificada por matrícula. |
| Perfil | Nível de acesso da pessoa no sistema. É um atributo que muda, não um cadastro separado. |
| Saída | Entrega de material a uma pessoa. No sistema de referência: "consignação". `[VALIDAR TERMO COM O DAVID E COM O ALVO]` |
| Devolução | Retorno do material à reserva, com conferência. |
| Pendência | Material que saiu e não voltou nem teve o consumo justificado. |
| Inapto | Item que está na reserva mas não pode ser entregue (ex.: aguardando manutenção). |
| Restrição | Impedimento de uma pessoa receber material (judicial, saúde, administrativo, outro). |

## 3 Perfis e permissões

Hierarquia proposta: **Dev > Adm > Armeiro > Usuário**.

Nas anotações da reunião também aparecem "dono" e "gerente". Esta versão assume que **dono e gerente são o perfil Adm**. `[VALIDAR COM O DAVID: dono e gerente são níveis diferentes?]`

| Ação | Usuário | Armeiro | Adm | Dev |
|---|---|---|---|---|
| Consultar a própria posse e o próprio histórico | ✔ | ✔ | ✔ | — |
| Registrar saída e devolução | — | ✔ | ✔ | — |
| Registrar consumo ou devolução parcial | — | ✔ | ✔ | — |
| Consultar históricos e relatórios da organização | — | ✔ | ✔ | — |
| Cadastrar tipo de equipamento, item com registro e item de estoque | — | — | ✔ | — |
| Retirar item do acervo (baixa), sempre com motivo | — | — | ✔ | — |
| Marcar item como inapto ou apto | — | ✔ `[VALIDAR]` | ✔ | — |
| Cadastrar pessoas e alterar perfil | — | — | ✔ | — |
| Registrar e encerrar restrição | — | — | ✔ | — |
| Criar organização e o primeiro Adm | — | — | — | ✔ |
| Bloquear organização por inadimplência | — | — | — | ✔ |

**Dev** é a equipe da C&E. Proposta: o Dev administra organizações, mas **não opera o acervo** nem vê dados pessoais sem necessidade de suporte registrada. Motivo: o cliente precisa confiar que o fornecedor não mexe no acervo dele. Origem: I. `[VALIDAR]`

## 4 Requisitos funcionais

### 4.1 Organização, pessoas e acesso

| ID | Requisito | Origem |
|---|---|---|
| RF-01 | O sistema atende várias organizações, com dados isolados entre elas. | I |
| RF-02 | O acesso é por matrícula e senha. | V: OBS 01 |
| RF-03 | Cadastro de pessoa com: nome, nome funcional, matrícula, CPF, celular, posto/graduação, unidade, perfil. | V: OBS 02 |
| RF-04 | O Adm altera o perfil de uma pessoa **sem novo cadastro**. A alteração fica no histórico da pessoa, com quem alterou, quando e o motivo. | R: D1 — **corrige** OBS 01 e 2.1, em que o perfil admin era um cadastro separado |
| RF-05 | A biometria pode ser vinculada à pessoa, mas é **opcional**. Toda operação precisa de uma alternativa sem biometria. | V: OBS 03, OBS 08. Opcional: I — o alvo pode não ter leitor biométrico `[VALIDAR]` |
| RF-06 | O Dev pode bloquear uma organização por inadimplência, respeitando RN-07. | R: David |

### 4.2 Acervo

| ID | Requisito | Origem |
|---|---|---|
| RF-10 | Cadastro de tipo de equipamento, classificado como **com registro** (controle por item) ou **de estoque** (controle por quantidade). | V: OBS 04; R: "registro ≠ cadastro" |
| RF-11 | Ao cadastrar um tipo, o sistema sugere modelos de uma base pré-carregada de armamentos e acessórios. | R. Fonte da base: `[DEFINIR]` |
| RF-12 | Cadastro de item com registro: tipo + número de identificação + unidade. | V: OBS 06 |
| RF-13 | Cadastro de item de estoque: tipo + quantidade + unidade. | V: OBS 04 |
| RF-14 | Cada item tem um estado: **disponível**, **em posse** (com quem), **inapto** (com motivo) ou **baixado**. | R: D8 (inapto). "Baixado": I |
| RF-15 | Ao clicar num item, o sistema mostra seu detalhe: estado atual, quem tem a posse, histórico completo de movimentações e alterações. | R |
| RF-16 | A edição de tipo de equipamento **não permite trocar a classificação** (com registro ou de estoque). | R: Pablo — **corrige** OBS 05 |

### 4.3 Movimentação

| ID | Requisito | Origem |
|---|---|---|
| RF-20 | Saída: o armeiro seleciona a pessoa, adiciona itens com registro e itens de estoque (com quantidade) e confirma. | V: OBS 08 |
| RF-21 | Antes de confirmar qualquer saída, devolução ou alteração de acervo, o sistema mostra o resumo e pede confirmação explícita. **Nenhuma ação acontece com um clique ou duplo clique.** | R: D7, Plínio — **corrige** OBS 08 |
| RF-22 | Devolução com conferência: o armeiro confirma item por item o que voltou e marca cada item como apto ou inapto. | R: conferência de recebimento |
| RF-23 | Um item devolvido e marcado apto fica disponível **no mesmo instante** para nova saída. | R |
| RF-24 | Consumo e devolução parcial de item de estoque: o armeiro registra a quantidade consumida com justificativa e, se houver, anexo (documento ou foto). A pendência se encerra pelo que foi justificado. | R: D6 |
| RF-25 | Retirada em nome de outra pessoa: o sistema registra **quem retirou** e **quem vai usar**. A posse fica em nome de quem usa. | R: D4. Precisa do formulário padrão de armamento temporário para desenhar os campos `[OBTER CÓPIA]` |
| RF-26 | Comprovante imprimível da saída e da devolução. | V: OBS 08 |
| RF-27 | Lista de pendências por pessoa, por unidade e da organização. | R: D3, D6 |

### 4.4 Restrições

| ID | Requisito | Origem |
|---|---|---|
| RF-30 | O Adm registra uma restrição para uma pessoa com: categoria (judicial, saúde, administrativa, outra), motivo, data de início, data de fim (opcional) e anexo (opcional). | R: David, restrição administrativa |
| RF-31 | Uma pessoa com restrição ativa não recebe material. O sistema bloqueia a saída e mostra que existe restrição, **sem mostrar o motivo** ao armeiro. | R + I (ocultar o motivo) `[VALIDAR]` |
| RF-32 | Encerrar ou alterar uma restrição exige motivo e fica no histórico. | R |

### 4.5 Conferência do acervo

| ID | Requisito | Origem |
|---|---|---|
| RF-40 | Painel por tipo de equipamento: total, disponível, em posse, inapto. | V: REL 07; R: D8 |
| RF-41 | Contagem guiada: o armeiro informa o que contou, tipo por tipo ou item por item, e o sistema compara com o esperado. | R: D5 |
| RF-42 | Divergência na contagem gera uma ocorrência com responsável e status, até ser resolvida. | R: D3, D5. Ocorrência: V, 2.1 (apenas citada) |

### 4.6 Busca, consulta e relatórios

| ID | Requisito | Origem |
|---|---|---|
| RF-50 | Busca única por qualquer referência: nome, matrícula, número do item, tipo, unidade. Com filtros por período, estado, unidade e tipo. | R: D2 — **corrige** REL 02–08, que só buscavam por título ou lista |
| RF-51 | Posse atual de uma pessoa. | V: OBS 09 |
| RF-52 | Histórico de uma pessoa: tudo que recebeu e devolveu, com datas e armeiros. | V: REL 01 |
| RF-53 | Histórico de um item com registro: todas as saídas e devoluções. | V: REL 02, REL 03, REL 08 |
| RF-54 | Histórico de um tipo de estoque: saídas, devoluções e consumos. | V: REL 04, REL 05 |
| RF-55 | Histórico de um armeiro: tudo que ele entregou e recebeu. | V: REL 06 |
| RF-56 | Todo relatório pode ser impresso e exportado em PDF. | V: REL 01–07 |

### 4.7 Auditoria e atividade

| ID | Requisito | Origem |
|---|---|---|
| RF-60 | Todo evento fica registrado com: quem fez, o quê, quando, valor anterior e novo, e motivo (quando exigido). | R: detalhamento máximo; Plínio |
| RF-61 | Feed de atividade da organização, em ordem cronológica, filtrável por pessoa, item e tipo de ação. | R: Plínio ("atividade" do Instagram) |
| RF-62 | O registro de auditoria não pode ser alterado nem apagado por nenhum perfil, inclusive Dev. | I — necessário para RF-60 ter valor |

> **Conflito a resolver com o David.** A reunião pediu um "grid de histórico com opções de editar e excluir". Isso entra em conflito com RF-62. Proposta: **corrigir** é permitido, mas vira um novo evento (estorno com motivo); o original continua visível. Nada é apagado (RN-05).

### 4.8 Citados na referência, ainda não detalhados

Aparecem no menu do sistema de referência sem fluxo descrito (`DOC-0010`, 2.1 e 6.1). Ficam fora desta versão até o David descrever o uso real:

- Registro de sinistro de equipamento (perda, dano, furto)
- Avisos e mensagens aos usuários
- Fotografia da pessoa
- Cadastro de unidades e de postos/graduações (necessário, mas não detalhado)

## 5 Regras de negócio

| ID | Regra | Origem |
|---|---|---|
| RN-01 | Uma pessoa tem um único cadastro por organização. O perfil é um atributo com histórico. | R: D1 |
| RN-02 | O número de um item com registro é único dentro da organização. | I `[VALIDAR]` |
| RN-03 | A classificação de um tipo de equipamento (com registro ou de estoque) não muda depois de criada. | R: Pablo |
| RN-04 | O saldo de estoque não é editado diretamente. Só muda por movimentação, consumo ou ajuste com motivo. | I — **corrige** OBS 05, que tinha estoque em campo aberto |
| RN-05 | Nenhuma movimentação é apagada. Uma correção é um estorno com motivo. | R + I |
| RN-06 | Pessoa com restrição ativa não recebe material. | R: David |
| RN-07 | O bloqueio por inadimplência **nunca** impede registrar devolução, consultar posse e exportar dados. Só impede novas saídas e cadastros. | I — sem isso, o bloqueio deixa arma na rua sem registro |
| RN-08 | Item inapto não conta como disponível e não pode sair. | R: D8 |
| RN-09 | Exigem motivo: baixa de item, ajuste de estoque, consumo, alteração de perfil, restrição (registro, alteração e encerramento), estorno. | R ("sempre com um motivo") `[VALIDAR LISTA]` |
| RN-10 | A posse fica em nome de quem usa o material, mesmo quando outra pessoa retirou. | R: D4 |

## 6 Requisitos não funcionais

| ID | Requisito | Origem |
|---|---|---|
| RNF-01 | **Disponibilidade.** A operação de saída e devolução não pode parar quando cai a internet ou o servidor. Web, local ou híbrido: **decisão em aberto** (ver 7). | R: David |
| RNF-02 | **Atualização imediata.** Uma devolução confirmada aparece para todos os armeiros da unidade no mesmo instante. | R |
| RNF-03 | **Integridade da auditoria.** RF-62. | I |
| RNF-04 | **Dados pessoais.** CPF, biometria e motivo de restrição de saúde são dados pessoais. Os dois últimos provavelmente são dados sensíveis. Acesso mínimo, registro de acesso, política de retenção. `[CONFIRMAR COM JURÍDICO]` | R + I |
| RNF-05 | **Isolamento entre organizações.** Nenhuma consulta retorna dado de outra organização. | I |
| RNF-06 | **Uso no balcão.** Saída e devolução com o menor número possível de campos obrigatórios. O detalhamento vem do registro automático (RF-60), não de digitação do armeiro. | R: preocupação do David com excesso de detalhe |
| RNF-07 | **Cópia de segurança e recuperação.** Frequência e tempo de recuperação: `[DEFINIR]`. | I |
| RNF-08 | **Desempenho.** Volume de movimentações por turno: `[FALTA DADO]`. Sem esse número, não há meta de desempenho. | I |

## 7 Decisões em aberto

| Decisão | O que falta para decidir |
|---|---|
| Web, local ou híbrido (RNF-01) | Conectividade real nas reservas dos órgãos-alvo; o que acontece hoje quando o sistema de referência cai; volume por turno. É decisão difícil de reverter. |
| Nomes dos perfis e se dono e gerente são níveis diferentes | Validar com o David |
| Termo para "saída" (consignação, cautela, outro) | Validar com o David e com o alvo |
| Biometria obrigatória, opcional ou fora | Custo do leitor para o alvo; o que o alvo usa hoje |
| Regulação aplicável a cada segmento (municipal, privado, público) e se existe sistema oficial obrigatório com o qual o SIGAB precise se integrar | `[CONFIRMAR COM FONTE OFICIAL]` — não levantado |
| Fora do escopo por falta de informação: munição por lote, manutenção, transferência entre unidades, integração com outros sistemas | Uso real no alvo |

## 8 Perguntas para o David e o armeiro

Em ordem de impacto no desenho. As perguntas 2, 3, 6 e 7 são do balcão — o armeiro responde melhor:

1. Dono e gerente são níveis diferentes? O armeiro pode marcar item como inapto?
2. Como o formulário de armamento temporário funciona hoje? Dá para obter um modelo em branco?
3. "Editar e excluir" no histórico: o que precisa ser corrigido na prática, e com que frequência?
4. Quais ações exigem motivo (RN-09)? A lista está completa?
5. Como a munição é controlada: por quantidade simples, por lote ou por calibre?
6. O que acontece hoje quando o sistema cai? Existe procedimento em papel?
7. Quantas saídas e devoluções acontecem num turno numa reserva típica?
8. Quais itens do menu citados em 4.8 são usados de verdade?

## 9 Rastreabilidade

| Fonte | Requisitos |
|---|---|
| OBS 01–03 | RF-02, RF-03, RF-05 |
| OBS 04–07 | RF-10, RF-12, RF-13, RF-16, RN-04 |
| OBS 08–09 | RF-20, RF-21, RF-26, RF-51 |
| REL 01–08 | RF-40, RF-50, RF-52 a RF-56 |
| D1 perfil exige novo cadastro | RF-04, RN-01 |
| D2 busca só por título | RF-50 |
| D3 material some | RF-22, RF-27, RF-42 |
| D4 retirada por terceiro | RF-25, RN-10 |
| D5 erro de contagem | RF-41, RF-42 |
| D6 pendência falsa de munição | RF-24, RF-27 |
| D7 duplo clique | RF-21 |
| D8 sem estado inapto | RF-14, RF-40, RN-08 |
