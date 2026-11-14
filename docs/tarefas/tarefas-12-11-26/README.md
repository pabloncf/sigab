# Navegação, cadastro de equipamentos e identificação na entrega — lote de 12/11/2026

[CSV das tarefas novas](tarefas.csv) · [Guia de importação](../IMPORTAR-NO-JIRA.md)

Registradas **8 tarefas novas, IDs originais SIGAB-079 a SIGAB-086**, e um épico com ID local `4001`. O registro é local: nada foi criado no Jira.

## Origem

A revisão da interface feita em 12/11/2026 comparou o sistema com o sistema de referência (DOC-0010) e com os requisitos (DOC-0011):

| Observação | Situação encontrada no código |
|---|---|
| Não há área principal | `/` abre direto a lista de itens individuais (`frontend/src/app/modules.tsx`). Não há painel (RF-40, SIGAB-059 em aberto) nem visão de pendências (RF-27). |
| Não há área de cadastro de equipamento com e sem registro | O tipo fica em Cadastros, junto de unidades e locais. O item com registro é incorporado por um botão dentro do Acervo. A entrada de material sem registro fica no Estoque. A interface usa "Individual/Quantitativo", e não "com registro/sem registro". |
| O que o Acervo faz | Lista e busca **apenas itens com registro**, filtra por situação, mostra a posse por pessoa (`?holder=`), abre a ficha do item e incorpora item. Material sem registro (munição) não aparece. |
| Não aparece o registro de retirada e entrada | O backend registra operador e recebedor em cada `Movement`. A retirada está em Atendimento. A devolução de item com registro só existe item a item, dentro da ficha. Não há tela de registro de movimentações por pessoa ou operador. |
| Biometria facial | Não implementada nem registrada. DOC-0011 (RF-05) fala de biometria opcional, sem tipo. A biometria segue como "futura" em `decisoes-pendentes.md` e depende da SIGAB-071. |

## Novas tarefas

| ID original | Tarefa | Prioridade | Bloqueada por |
|---|---|---|---|
| SIGAB-079 | Criar página inicial do sistema separada do acervo | Highest | 059, 069 (lote anterior) |
| SIGAB-080 | Criar módulo de cadastro de equipamentos com e sem registro | Highest | 078, 008 (lote anterior) |
| SIGAB-081 | Separar o acervo em material com registro e sem registro | High | 008, 041, 078 (lote anterior) |
| SIGAB-082 | Tornar retirada e devolução visíveis e rastreáveis no balcão | Highest | 058, 076, 077 (lote anterior) |
| SIGAB-083 | Registrar decisão de biometria facial na retirada e devolução | Highest | 071, 039 (lote anterior) |
| SIGAB-084 | Prova de conceito técnica de verificação facial no balcão | High | em paralelo à 083 |
| SIGAB-085 | Cadastrar biometria facial da pessoa | High | 083, 084 |
| SIGAB-086 | Verificar identidade facial do recebedor na retirada e devolução | High | 085, 082 |

## Ordem sugerida

1. **079, 080 e 082**: só reorganizam o que o backend já faz. Entregam a página inicial, o cadastro de equipamentos e a retirada/devolução visíveis.
2. **081**: depende da decisão quantitativa (SIGAB-008) para disponível e inapto de material sem registro.
3. **083 e 084 em paralelo**. A biometria facial é dado pessoal sensível. Nenhum código de biometria entra antes do ADR e da política aprovados.
4. **085 e depois 086**.

## Importação

- Mesmo formato dos lotes anteriores: 18 colunas, quatro `Labels`, seis `Is Blocked By`.
- `Is Blocked By` aponta só para registros deste lote (85 ← 83, 84; 86 ← 85, 82). As dependências de lotes anteriores estão em "Dependências originais" e devem ser vinculadas às chaves reais.
- Os IDs originais 079–086 não são as chaves Jira SIGAB-79 a SIGAB-86.
- Validados: cabeçalho, quantidade de campos, unicidade dos IDs entre todos os lotes e referências internas.
