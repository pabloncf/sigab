# ADR 0003 — Eventos, projeção atual e idempotência

Status: aceito para a base, 2026-10-15. Formato dos eventos, contrato da auditoria e estorno: [ADR 0006](0006-eventos-auditoria-e-estornos.md).

Movimentações confirmadas e seus eventos não são editados nem apagados por fluxos normais. O item mantém uma projeção atual (disponibilidade, condição e responsável) atualizada na mesma transação do evento. Metadados usam nome de schema e versão; dados críticos permanecem em campos estruturados.

Escritas críticas exigem UUID de idempotência único na organização. A saída bloqueia o item no banco e faz atualização condicional. Correções futuras serão eventos compensatórios com referência e motivo; estorno não foi exposto nesta entrega.

