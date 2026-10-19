# Segurança e privacidade

Controles presentes: hash de senha do Django, sessão HTTP-only expiráveis, CSRF, escaping de templates, negação por padrão, escopo no servidor, UUIDs não sequenciais, transações, bloqueio pessimista e atualização condicional, idempotência, auditoria minimizada e correlação de requisição. Eventos não têm rotas de escrita e são somente leitura no admin.

O CPF é opcional e não aparece em telas operacionais, eventos ou logs. Não há biometria, laudo, anexo ou exportação. Nunca habilite `DEBUG` em produção. TLS, gestão de segredos, rate limiting no proxy/IdP, criptografia de disco/backup, retenção, resposta a incidentes e revisão de infraestrutura são responsabilidades de implantação ainda abertas.

Limite conhecido: “append-only” é garantido na aplicação, não contra administrador do banco. Políticas de banco, segregação operacional, retenção e verificação criptográfica exigem desenho posterior. Administradores Django têm finalidade de implantação controlada e não devem ser concedidos a operadores comuns.

## Modelo de ameaças inicial

| Ameaça P0 | Controle | Evidência |
|---|---|---|
| acesso entre organizações | FKs validadas, filtros por tenant, 404 e testes negativos | `test_flow.py` |
| dupla saída | transação, `select_for_update`, atualização condicional | teste concorrente PostgreSQL |
| repetição de rede | chave única por organização | testes de idempotência |
| operador sem permissão | concessão explícita e escopo por unidade | testes de negação |
| adulteração por UI | eventos/movimentos sem update/delete no admin | teste de imutabilidade |
| exposição de dados pessoais | minimização; CPF ausente de eventos/UI | inspeção e política |

