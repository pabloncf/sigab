# Decisão de domínio 0005 — Restrição operacional da pessoa

- Tarefa: SIGAB-040
- Data: 2026-11-02
- Estado: **implementação técnica parcial** nas tarefas originais 050/051 (Jira 74/75); homologação, anexos, classes agregadas e recolhimento automático continuam pendentes. Evidências em [Jira 71–75](../validacao/jira-071-a-075.md).
- Requisitos: RF-30, RF-31, RF-32, RN-06 e RN-09 do [DOC-0011 v0.1](../fontes/DOC-0011-analise-de-requisitos-v0.1.md)
- Base: OBR-07 e OBR-12 da [nota regulatória 0001](../notas-regulatorias/0001-guardas-municipais.md), [matriz de papéis 0002](0002-papeis-e-escopos.md), [política de dados pessoais](../politica-de-dados-pessoais.md), [contrato da saída](../contratos/saida-individual.md)

## 1. Decisão

Uma **restrição operacional** é um impedimento, com vigência, de uma pessoa receber material. Ela é registrada por quem tem `restriction.manage` e consultada na saída apenas como **decisão**: permitido ou impedido. O fundamento (motivo, documento, diagnóstico, processo) nunca chega ao armeiro (RF-31) e o SIGAB não armazena laudo, diagnóstico nem inteiro teor de decisão (OBR-07, OBR-12).

## 2. Dados

| Campo | Regra | Quem vê |
|---|---|---|
| pessoa | da organização | `restriction.manage`, `restriction.view_decision` (só a existência) |
| categoria | `judicial`, `saude`, `administrativa`, `outra` (RF-30) | `restriction.manage` |
| escopo por material | todos os materiais, ou lista de tipos de equipamento, ou classe (armas de fogo) | `restriction.manage`; a decisão na saída já considera o escopo |
| início | data e hora; pode ser futura | `restriction.manage` |
| fim | opcional; sem fim = até encerramento | `restriction.manage` |
| fonte | quem informou: Corregedoria, RH, Comando, Judiciário, Junta Médica, outra | `restriction.manage` |
| autoridade e referência | órgão e número do processo ou documento oficial, **sem** o conteúdo | `restriction.manage` |
| motivo resumido | texto curto, sem diagnóstico, CID ou teor de decisão; obrigatório (RN-09) | `restriction.manage` |
| anexo | **não** é armazenado. RF-30 prevê anexo opcional; fica bloqueado até política aprovada para anexos sensíveis | — |

## 3. Vigência e decisão na saída

Restrição **ativa** no instante `t`: `início ≤ t` e (`fim` vazio ou `t < fim`) e não encerrada.

Na saída (pré-condição adicional do contrato da saída, dentro da mesma transação):

1. busca restrições ativas da pessoa cujo escopo inclua o tipo do item;
2. se houver e não existir exceção válida (seção 5), a saída falha com `409` e a mensagem “Saída bloqueada: existe restrição ativa para esta pessoa. Procure a chefia.”;
3. a resposta **não** informa categoria, motivo, fonte nem datas;
4. a tentativa bloqueada gera auditoria `restriction.blocked_checkout` com pessoa, item e restrição.

Restrição com início futuro não bloqueia antes do início. Restrição que começa durante uma posse em aberto **não** desfaz a saída: gera pendência de recolhimento (seção 6).

A devolução nunca é bloqueada por restrição.

## 4. Registro, alteração e encerramento

| Ato | Permissão | Exige | Efeito |
|---|---|---|---|
| registrar | `restriction.manage` | motivo resumido, categoria, início, escopo, fonte | evento `restriction.registered`; auditoria com categoria, sem motivo |
| alterar fim ou escopo | `restriction.manage` | motivo (RF-32) | novo evento com valor anterior e novo; o registro anterior permanece |
| encerrar antecipadamente | `restriction.manage` | motivo (RF-32) | evento `restriction.closed`; a restrição deixa de ser ativa; o fato histórico permanece (OBR-07) |
| registrar com erro | `restriction.manage` | motivo | estorno compensatório, como no ADR 0006 |

Nada é apagado. Restrição expirada pela data de fim não precisa de ato.

## 5. Exceção

Uma **exceção** autoriza uma saída específica (ou um período curto) apesar de restrição ativa, por exemplo para ato de serviço determinado pela chefia.

- Aprovada por `restriction.exception.approve`, com motivo, validade máxima e escopo (item ou tipo).
- Separação de funções da matriz 0002 (`restriction_exception_independence`): quem registrou a restrição, quem aprova a exceção e quem executa a saída são contas diferentes.
- A saída com exceção registra a exceção usada; a auditoria liga restrição, exceção e saída.
- Restrição de categoria `saude` ou `judicial` não admite exceção sem decisão de produto e jurídica (o risco é de segurança da pessoa e de terceiros).

## 6. Recolhimento

Quando uma restrição se torna ativa e a pessoa tem itens em posse (`/api/v1/items/?holder=`), o sistema cria uma pendência de recolhimento visível a quem tem `restriction.manage` e `movement.return` na unidade dos itens. O prazo de 48 h do TAD (OBR-07) para eventos funcionais é exibido; comunicação externa (PF) continua fora do sistema.

## 7. Privacidade e auditoria

- O armeiro (`restriction.view_decision`) só vê: “impedido” ou “liberado”. Busca, ficha e histórico do item não mostram restrições.
- Consulta ao detalhe de uma restrição por `restriction.manage` gera auditoria de leitura (`restriction.viewed`), por envolver dado potencialmente sensível (RNF-04).
- Auditoria de registro e alteração guarda categoria, datas e escopo; o motivo resumido fica só no registro da restrição.
- Retenção: histórica, conforme a política de dados pessoais e a tabela municipal; nunca eliminada ao encerrar.

## 8. Fora desta decisão

Integração automática com RH, Corregedoria ou Judiciário; habilitação de porte (validade de CRAF, EQP, avaliação psicológica), que é outro tipo de elegibilidade com fonte oficial própria; restrição a grupos de pessoas.

## 9. Pendências antes de implementar

- Validar com o alvo a lista de categorias e se “saúde” e “judicial” admitem exceção.
- Política de anexos sensíveis (bloqueia o anexo de RF-30).
- Decidir quem cria a pendência de recolhimento e com que escalonamento.
- Validar o texto exibido ao armeiro (RF-31 está marcado `[VALIDAR]` no DOC-0011).
