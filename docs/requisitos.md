# Requisitos e rastreabilidade

Os requisitos foram derivados de um documento inicial produzido após validação com o usuário-alvo. A transcrição desse documento está em [DOC-0011 v0.1](fontes/DOC-0011-analise-de-requisitos-v0.1.md). Permanecem no estado formal `proposto` quando ainda não possuem responsável, data e evidência individualmente rastreados no backlog; esse estado não significa ausência de validação da linha de base de domínio.

| Fatia | Requisitos | Implementação/teste |
|---|---|---|
| Tenancy e identidade | RF-01 a RF-04 | modelos, permissões, [matriz de autorização](decisoes/0002-papeis-e-escopos.md) e testes negativos de tenant/conta |
| Acervo individual | RF-10, RF-12, RF-14 a RF-16 | `EquipmentType`, `Item`, detalhe e histórico |
| Movimentação | RF-20 a RF-23 | serviços atômicos, confirmação, idempotência e CI PostgreSQL |
| Auditoria | RF-60, RF-62 | eventos append-only, admin somente leitura e separação de funções na [matriz de autorização](decisoes/0002-papeis-e-escopos.md) |

Os demais requisitos permanecem fora do escopo. O status do backlog indica planejamento e rastreabilidade individual, enquanto a validação da linha de base está registrada na decisão do segmento e no glossário.

A [nota regulatória 0001](notas-regulatorias/0001-guardas-municipais.md) registra a pesquisa preliminar da Seção 7 para o segmento inicial. Ela não certifica conformidade: requisitos locais, retenção, integrações e habilitação do fluxo real de armas dependem do Município, de validação jurídica e dos instrumentos vigentes com os órgãos competentes.

## Estado individual: ciclo de vida do item

Registrado na SIGAB-009 ([decisão 0004](decisoes/0004-ciclo-de-vida-do-item-individual.md), seção 11).

| Requisito | Estado | Evidência |
|---|---|---|
| RF-14 | validado | DOC-0011, reunião REU-0001 com o armeiro (2026-09-29) |
| RF-22 | validado | idem |
| RN-08 | validado | idem |
