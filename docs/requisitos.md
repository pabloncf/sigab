# Requisitos e rastreabilidade

**Definição vigente em 10/11/2026:** produto single-tenant, uma instalação e banco exclusivos por cliente. RF-01 e RNF-05 da fonte original são substituídos pelo isolamento entre instalações e pela autorização entre unidades; login não recebe organização. Ver [ADR 0007](adr/0007-single-tenant.md). As fotografias anteriores abaixo permanecem históricas.

O documento inicial está preservado em [DOC-0011 v0.1](fontes/DOC-0011-analise-de-requisitos-v0.1.md). As decisões posteriores refinam seu escopo e domínio; não alteram retroativamente a fonte. Validação de referência, validação com organização-alvo, implementação e aceite do fluxo são estados distintos e precisam de evidência própria.

## Fotografia atual — 2026-11-06

A [auditoria de alinhamento e módulos](validacao/alinhamento-requisitos-2026-11-06.md) compara individualmente os **37 requisitos funcionais, 10 regras de negócio e 8 requisitos não funcionais** com o código atual, registra lacunas e propõe a divisão dos módulos. **O produto atual não atende integralmente ao documento inicial.**

| Fatia | Requisitos | Implementação/teste |
|---|---|---|
| Tenancy e identidade | RF-01 a RF-04 | modelos, permissões, [matriz de autorização](decisoes/0002-papeis-e-escopos.md) e testes negativos de tenant/conta |
| Acervo individual | RF-10, RF-12, RF-14 a RF-16 | `EquipmentType`, `Item`, detalhe e histórico |
| Movimentação | RF-20 a RF-23 | serviços atômicos, confirmação, idempotência e CI PostgreSQL |
| Auditoria | RF-60, RF-62 | eventos append-only, registros de auditoria somente leitura no Admin e separação de funções na [matriz de autorização](decisoes/0002-papeis-e-escopos.md); proteção contra SQL privilegiado ainda incompleta |
| Consultas e atividade | RF-27, RF-50 a RF-53, RF-55, RF-61 | busca, posse por pessoa, histórico paginado e feed; cobertura parcial conforme matriz da auditoria |
| Correção e contingência | RN-05, RN-09, RNF-01 | estorno de saída/devolução/condição e lançamento posterior de fatos registrados em papel; sem operação digital offline |

As fatias acima indicam capacidades existentes, não atendimento integral de todos os requisitos associados. Estoque quantitativo, restrições pessoais, inventário físico, comprovantes, exportação PDF, biometria e retirada por terceiro ainda não possuem os fluxos previstos na fonte. Baixa, bloqueio comercial e atualização automática entre balcões também permanecem lacunas. O status do backlog não substitui evidência de implementação ou aceite.

Para atualizar o estado de um requisito, registrar separadamente: decisão de escopo (mantido, substituído, adiado ou retirado), implementação (ausente, parcial ou implementado), testes, validação/aceite, responsável, data e evidência. Ver a proposta de módulos e os critérios de correção no relatório.

A [nota regulatória 0001](notas-regulatorias/0001-guardas-municipais.md) registra a pesquisa preliminar da Seção 7 para o segmento inicial. Ela não certifica conformidade: requisitos locais, retenção, integrações e habilitação do fluxo real de armas dependem do Município, de validação jurídica e dos instrumentos vigentes com os órgãos competentes.

## Estado individual: ciclo de vida do item

Registrado na SIGAB-009 ([decisão 0004](decisoes/0004-ciclo-de-vida-do-item-individual.md), seção 11).

| Requisito | Estado | Evidência |
|---|---|---|
| RF-14 | validado | DOC-0011, reunião REU-0001 com o armeiro (2026-09-29) |
| RF-22 | validado | idem |
| RN-08 | validado | idem |
