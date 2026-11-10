# ADR 0002 — Tenancy compartilhada e autorização explícita

Status: tenancy compartilhada substituída em 10/11/2026 pelo [ADR 0007 — single-tenant](0007-single-tenant.md), por definição do responsável pelo produto. As regras de autorização explícita e escopo de unidade continuam vigentes. O texto abaixo é histórico.

Cada registro de negócio carrega ou deriva `organization_id`; Pessoa também é tenant-local. Toda entrada usa a organização da conta autenticada, nunca um tenant fornecido pelo navegador. Papéis contêm permissões explícitas e concessões têm escopo de organização ou unidade, sem hierarquia implícita.

Essa abordagem é simples e reversível para o MVP, mas exige disciplina em toda nova consulta. Cada módulo novo deve adicionar teste negativo cruzado. Isolamento físico por banco/schema poderá ser reconsiderado quando escala, contrato e operação forem conhecidos.

