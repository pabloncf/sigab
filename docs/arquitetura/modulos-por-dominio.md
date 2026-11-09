# Módulos por domínio — SIGAB-064/065

O backend preserva `sigab.services` como fachada de compatibilidade. Novos consumidores usam:

- `sigab.domain.identity`: pessoas, vínculos, contas e concessões;
- `sigab.domain.catalog`: estrutura, catálogo e incorporação;
- `sigab.domain.movements`: movimentações individuais;
- `sigab.domain.operations`: cesta e estoque quantitativo;
- `sigab.domain.inventory`: contagens e divergências;
- `sigab.domain.queries`: posse e histórico.

A API segue a mesma fronteira: `api.views` mantém os contratos existentes, enquanto `api.operations`, `api.inventory` e `api.self_service` recebem as capacidades novas. A migração dos endpoints antigos pode continuar incrementalmente sem alterar URLs ou formatos públicos.

O frontend expõe as áreas por `src/features/{inventory,identity,catalog,audit,operations,self-service}`. As páginas antigas continuam reexportadas durante a migração, preservando URLs e reduzindo risco de regressão.

Regras de domínio, autorização e transações permanecem no servidor; o React apenas coleta intenção, confirma e apresenta respostas.
