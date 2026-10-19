# Glossário operacional v0.2

- Tarefa: SIGAB-003
- Segmento: Guardas Municipais brasileiras com acervo de armamentos e equipamentos operacionais
- Estado: aprovado
- Responsável pela aprovação: Produto/Domínio
- Dependências: SIGAB-001 decidida; SIGAB-002 concluída, com a validação de domínio incorporada ao documento inicial de requisitos

Este glossário fixa o vocabulário mínimo para a descoberta, a interface e a
documentação do SIGAB. As definições abaixo evitam usar como sinônimos termos que
representam evento, modalidade, situação, dever, estrutura organizacional ou
local físico diferentes.

## Termos críticos

### Saída

Movimentação confirmada que retira um item individual disponível de seu local de
guarda e o vincula a uma pessoa responsável, permanecendo aberta até a devolução
ou até outra movimentação de encerramento que venha a ser definida.

É o termo geral para o evento registrado pelo sistema. **Cautela** e
**consignação** são modalidades de saída; não são sinônimos de saída. O operador
que registra a movimentação não se torna, por esse ato, o responsável pelo item.

### Cautela

Modalidade de saída temporária com devolução esperada e prazo ou condição de
encerramento definidos no momento da entrega. Pode ultrapassar um turno e durar
dias ou meses.

Não designa toda saída e não se confunde com o documento ou comprovante que possa
formalizá-la. A retirada limitada ao turno é tratada separadamente e não deve ser
classificada automaticamente como cautela.

### Consignação

Modalidade de saída para uso continuado, sem data de devolução previamente
definida, encerrada por devolução, substituição, desligamento ou outro motivo
formalmente registrado.

Não transfere propriedade do bem. Neste glossário, consignação corresponde à
“atribuição sem data de devolução previamente definida” descrita na decisão do
segmento inicial.

### Posse operacional

Situação corrente em que um item está fora da reserva e vinculado, por uma saída
aberta, a uma pessoa responsável. É uma projeção do histórico de movimentações e
termina quando a saída é encerrada.

“Posse” no SIGAB é sempre posse operacional: não significa propriedade, porte ou
posse em sentido jurídico. A interface deve preferir a expressão completa quando
houver risco de ambiguidade.

### Custódia

Dever de guarda, conservação e controle físico do item. A custódia existe tanto
na reserva, sob o processo institucional de guarda, quanto durante uma saída, sob
o cuidado da pessoa responsável.

Custódia não é sinônimo de posse operacional. A primeira descreve um dever; a
segunda, a situação registrada que vincula item e pessoa. O estado técnico atual
`in_custody`, exibido como “Em posse”, representa **posse operacional**, não toda
forma de custódia.

### Responsável

Pessoa à qual o item está vinculado durante uma saída aberta e que responde por
sua guarda e devolução conforme a modalidade aplicável. No modelo técnico atual,
é o `current_holder` do item e o destinatário da saída.

Não é sinônimo de operador, autorizador, armeiro, chefe da unidade ou responsável
pela reserva. Uma mesma pessoa pode acumular funções, mas cada função deve ser
registrada e autorizada separadamente.

### Unidade

Subdivisão identificável de uma organização, usada para agrupar pessoas, itens,
locais e escopos de autorização. Exemplos dependem da estrutura da Guarda
Municipal participante e podem incluir comando, grupamento, base ou posto.

Não é sinônimo de organização, endereço, local de guarda nem unidade de medida.
Uma unidade pode possuir um ou mais locais de guarda.

### Reserva

Local ou setor de uma unidade no qual armamentos e equipamentos ficam guardados,
controlados e movimentados por pessoal autorizado. No modelo do SIGAB, uma
reserva é representada como **local de guarda** vinculado a uma unidade.

Não significa reserva de agenda, separação futura de item nem quantidade em
estoque. “Responsável pela reserva” é um papel operacional; “reserva” é o local
ou setor em que esse papel atua.

## Relações entre os termos

```text
Organização
└── Unidade
    └── Reserva (um local de guarda)

Saída
├── retirada por turno
├── cautela (retorno com prazo ou condição definida)
└── consignação (uso continuado, sem data final definida)

Saída aberta ── vincula ── Item ── a ── Responsável
                               └── situação: posse operacional
Custódia ── dever de guarda aplicável na reserva e durante a saída
```

## Convenções de uso

- Use **saída** para a movimentação genérica e a ação da interface.
- Use **cautela** ou **consignação** somente quando a modalidade estiver
  identificada; não deduza a modalidade apenas pela duração transcorrida.
- Use **posse operacional** para a situação atual do item e **custódia** para o
  dever de guarda.
- Use **responsável** para o destinatário atual do item e **operador** para quem
  registra a movimentação.
- Use **unidade** para a subdivisão organizacional e **reserva** ou **local de
  guarda** para o lugar/setor onde o item fica armazenado.
- Código e campos técnicos permanecem em inglês; interface e documentação de
  domínio usam os termos em português definidos aqui.

## Matriz de não sinonímia

| Termos | Distinção obrigatória |
|---|---|
| saída × cautela × consignação | saída é o evento geral; cautela e consignação são modalidades diferentes |
| posse operacional × custódia | posse é uma situação item–pessoa; custódia é um dever de guarda |
| responsável × operador | responsável recebe e guarda o item; operador registra a operação |
| unidade × reserva | unidade é estrutura organizacional; reserva é local ou setor subordinado |

## Validação e aprovação

O documento inicial de requisitos foi produzido após validação com o usuário-alvo
do segmento escolhido e já continha o vocabulário operacional consolidado nas
Seções 2 e 7. A versão 0.2 organiza essas definições e explicita as fronteiras
entre os termos sem alterar seu sentido operacional.

A proveniência dessa validação foi confirmada pelo responsável do projeto em
2026-10-19. Data, identidade do participante e artefato bruto da entrevista não
estão registrados neste repositório e não são inferidos por este documento.

| Termo | Decisão do usuário-alvo | Evidência |
|---|---|---|
| saída | aceito | documento inicial de requisitos, Seções 2 e 7 |
| cautela | aceito | documento inicial de requisitos, Seções 2 e 7 |
| consignação | aceito | documento inicial de requisitos, Seções 2 e 7 |
| posse operacional | aceito | documento inicial de requisitos, Seções 2 e 7 |
| custódia | aceito | documento inicial de requisitos, Seções 2 e 7 |
| responsável | aceito | documento inicial de requisitos, Seções 2 e 7 |
| unidade | aceito | documento inicial de requisitos, Seções 2 e 7 |
| reserva | aceito | documento inicial de requisitos, Seções 2 e 7 |

Com as definições individualizadas, a matriz de não sinonímia e a proveniência da
validação registradas, a SIGAB-003 satisfaz seu critério de aceite.

