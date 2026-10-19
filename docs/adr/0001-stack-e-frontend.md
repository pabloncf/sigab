# ADR 0001 — Monólito Django e templates server-side

Status: aceito para a primeira base, 2026-10-15.

Usaremos Python 3.12+ e Django 5.2 LTS, PostgreSQL em produção/CI e SQLite apenas no desenvolvimento simples. A interface operacional usa templates Django e HTML progressivo. Foram consideradas SPA separada e HTMX; ambas adicionariam pipeline, contratos e/ou dependência sem benefício comprovado nesta fatia.

Templates renderizados no servidor atendem computadores comuns, teclado e leitores de tela, reduzem latência de balcão e mantêm autenticação por sessão, CSRF, escaping XSS, validação, autorização e mensagens de erro no backend. Formulários POST exigem resumo e confirmação explícita. Testes unitários e de integração cobrem serviços e views; o fluxo HTTP é exercitado com o cliente Django, e concorrência no PostgreSQL do CI. Uma camada mais interativa poderá ser adicionada sem mover regras ao navegador.

Consequência: implantação é um processo web e um banco. Offline não é suportado; conectividade e contingência estão no [ADR 0004](0004-conectividade-e-contingencia.md).

