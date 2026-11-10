# Transição técnica para single-tenant — 10/11/2026

Definição do responsável pelo produto: o SIGAB deve ser **single-tenant**. A implementação desta revisão adota uma instalação e banco exclusivos por cliente, uma organização e várias unidades internas. Decisão registrada no [ADR 0007](../adr/0007-single-tenant.md), que substitui a tenancy compartilhada anterior sem reescrever a fonte DOC-0011.

## Alterações

- Migração `0012_single_tenant_installation` adiciona chave institucional única, fixada em 1 por restrição de banco. Segunda organização e tentativa de escolher outra chave são recusadas pelo banco.
- Pré-verificação da migração recusa bases com várias organizações antes de alterar sua estrutura. Nenhum cliente é escolhido, excluído ou fundido automaticamente.
- Login recebe somente matrícula/usuário técnico e senha. A organização não aparece como campo nem pode ser escolhida por parâmetro externo. Autenticação, auditoria de login, suspensão e limitação de tentativas foram ajustadas ao identificador local.
- `bootstrap_sigab` inicializa apenas uma instalação vazia. `seed_demo` cria uma organização com duas unidades; não cria outro cliente.
- Comandos de criação de conta e suspensão usam a organização local; ID explícito é apenas compatibilidade e deve coincidir com o local.
- FKs, UUIDs, permissões por unidade, histórico e hashes existentes permanecem. Os testes de referências cruzadas continuam como cenários adversariais de dados legados, sem habilitar múltiplos clientes no produto.
- README, instruções para agentes, requisitos, visão, domínio, segurança e contrato de login apontam para a definição atual. Evidências anteriores são históricas.

## Verificação

- Suíte completa PostgreSQL: **256 passaram, 2 ignorados**, em 78,92 s. Os ignorados são o ensaio opcional de desempenho e a integração de navegador opt-in, executada separadamente.
- Testes específicos SQLite de singleton, provisionamento, autenticação, suspensão e migrações: **7 passaram**.
- Playwright: **14 jornadas passaram**.
- Navegador + Django + PostgreSQL reais: **1 jornada passou**, agora incluindo login sem organização, entrada, saída com resposta perdida após commit, recarga/reenvio, devolução parcial e consumo.
- Ruff, Django check, ausência de migrações faltantes, typecheck e build: aprovados.
- Graphify atualizado por AST local; os dois JSONs que não produziram nós continuam fora do grafo estrutural e não foram tratados como documentos analisados semanticamente.

Os bancos de teste são separados: `test_sigab_single_tenant_validation` e `test_sigab_single_tenant_browser`, criados e removidos pelo Django. Não houve alteração de dados do banco de desenvolvimento ou produção.

## Situação do banco local

Consulta somente leitura em 10/11/2026 encontrou **3 organizações** em `sigab_organization` no banco local `sigab`. A migração 0012 não foi aplicada a ele. A implantação atual ainda depende da separação desses dados em instalações exclusivas, conforme o ADR 0007; este relatório não declara que a base existente já foi convertida.

A separação exige conferir, por organização, referências, contas, permissões, contagens e cadeia de auditoria em bancos de destino. Não há autorização de descarte presumida e não foi executada exclusão, fusão ou transferência automática de dados. O fluxo single-tenant foi validado em bancos temporários novos e em ensaios de migração de base com um cliente.


## Recuperação do Docker local no mesmo dia

Após a tentativa de inicialização da base antiga, o responsável escolheu uma demonstração single-tenant nova, preservando a base existente. O ambiente local passou a usar `sigab_single_tenant_demo_20261110`, selecionado por `SIGAB_DATABASE_NAME` no `.env` da raiz. O Compose agora aceita essa variável tanto no PostgreSQL quanto na conexão do backend.

Na base nova foram aplicadas todas as migrações, incluindo 0011/0012, e executado `seed_demo`: uma organização, duas unidades, 16 itens e duas contas. O backend iniciou em `localhost:8000`, e o frontend continua em `localhost:5173`. A cadeia de auditoria da demonstração foi verificada e está íntegra. Login real pelo navegador, via frontend Docker, validado para `alfa.admin` e matrícula `1001`, ambos com sessão HTTP 200 e sem campo de organização.

A consulta à base anterior `sigab` confirmou que suas três organizações continuam presentes. A restrição da 0012 não foi removida, e a base antiga não foi apagada, fundida ou reutilizada como instalação nova. Para os próximos inícios locais, usar `docker compose up -d`, mantendo o `.env`; o procedimento está no README.
