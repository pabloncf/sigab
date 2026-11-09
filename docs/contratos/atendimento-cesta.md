# Contrato de atendimento com cesta

Estado: aprovado para implementação no incremento de 06/11/2026 (SIGAB-067).

## Decisões

- O atendimento começa pela pessoa e confirma, em uma única transação, zero ou mais itens individuais e zero ou mais linhas quantitativas. Uma cesta vazia é inválida.
- A falha de qualquer linha desfaz toda a cesta. Itens são bloqueados em ordem estável e saldos quantitativos nunca podem ficar negativos.
- A chave de idempotência identifica a cesta completa. Repetir a mesma chave e conteúdo retorna o atendimento original; reutilizá-la com conteúdo diferente é conflito.
- As modalidades são: por turno, prazo determinado e prazo indeterminado. Prazo determinado exige instante futuro com fuso; as demais não aceitam prazo.
- O comprovante possui código estável, destinatário, operador, modalidade, prazo e todas as linhas confirmadas.
- Devolução e consumo quantitativos são parciais e encerram somente a quantidade informada. Consumo exige justificativa.
- **Retirada por terceiro não está autorizada neste incremento.** O modelo mantém o campo separado do operador para evolução futura, mas serviço e interface rejeitam seu preenchimento. RF-25/RN-10 permanecem pendentes de evidência externa específica.

## Segurança e escopo

- Organização vem exclusivamente da conta autenticada.
- O destinatário precisa estar ativo e possuir vínculo ativo na organização.
- Cada linha exige permissão de saída na unidade correspondente.
- A consulta de autosserviço deriva a pessoa de `Account.person`; não recebe UUID de pessoa, unidade ou organização do navegador.

## Encerramento de pendência

- Item individual deixa de estar pendente quando uma devolução válida ou estorno do fato correspondente recompõe seu estado.
- Linha quantitativa encerra quando `open_quantity` chega a zero por devolução, consumo justificado ou estorno autorizado.
- Prazo vencido é apresentado separadamente de posse válida sem prazo.

## Evidência automatizada

- `backend/sigab/tests/test_requirements_063_070.py`
- `frontend/e2e/journeys.spec.ts`
