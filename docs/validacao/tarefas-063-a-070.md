# Entrega e validação das tarefas 063 a 070

## Rastreabilidade

| Tarefa | Evidência principal |
|---|---|
| SIGAB-063 | `InventorySession`, `InventoryCount`, `InventoryDivergence`; serviços e endpoints de contagem, investigação, resolução e fechamento auditado |
| SIGAB-064 | módulos em `backend/sigab/domain/` e APIs por domínio; mapa em `docs/arquitetura/modulos-por-dominio.md` |
| SIGAB-065 | áreas em `frontend/src/features/`, navegação por permissão e páginas de atendimento/autosserviço |
| SIGAB-066 | Playwright em `frontend/e2e/journeys.spec.ts` executado no CI |
| SIGAB-067 | contrato `docs/contratos/atendimento-cesta.md`; terceiro retirante explicitamente não autorizado |
| SIGAB-068 | `checkout_basket`, comprovante, cesta mista atômica e interface de seleção |
| SIGAB-069 | `StockLoan`, livro quantitativo, devolução/consumo parcial, consultas consolidadas e CSV sem paginação |
| SIGAB-070 | `/api/v1/me/possessions/`, `/me/history/` e comprovante limitado a `Account.person` |

## Garantias verificadas

- Idempotência da cesta e do livro quantitativo.
- Bloqueio transacional de itens e saldos; saldo quantitativo não negativo.
- Divergência não encerra sem resolução ou justificativa autorizada.
- Mudanças de divergência entram na trilha encadeada de auditoria.
- Autosserviço não aceita identificador de outra pessoa e não concede leitura da unidade.
- Navegador cobre navegação por permissão, autosserviço, cesta, saída, contingência, devolução e estorno.

## Limites explícitos

- Retirada por terceiro permanece desabilitada até validação externa.
- A fachada `sigab.services` continua existindo para compatibilidade; a extração dos módulos antigos é incremental.
- Aceite operacional com organização-alvo e volume real continua pertencendo à SIGAB-073.
