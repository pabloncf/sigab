# Segurança e privacidade

Controles presentes: hash de senha do Django, sessão HTTP-only expiráveis, CSRF, escaping de templates, negação por padrão, escopo no servidor, UUIDs não sequenciais, transações, bloqueio pessimista e atualização condicional, idempotência, auditoria minimizada, correlação de requisição e log técnico estruturado com mascaramento de CPF e segredos ([observabilidade](observabilidade.md)). Eventos não têm rotas de escrita e são somente leitura no admin.

O CPF é opcional e não aparece em telas operacionais, eventos ou logs. Não há biometria, laudo, anexo ou exportação. Nunca habilite `DEBUG` em produção. TLS, gestão de segredos, rate limiting no proxy/IdP, criptografia de disco/backup, retenção, resposta a incidentes e revisão de infraestrutura são responsabilidades de implantação ainda abertas.

Limite conhecido: “append-only” é garantido na aplicação, não contra administrador do banco. Políticas de banco, segregação operacional, retenção e verificação criptográfica exigem desenho posterior. Administradores Django têm finalidade de implantação controlada e não devem ser concedidos a operadores comuns.

## Modelo de ameaças

Ameaças, controles, responsáveis e testes previstos estão no [modelo de ameaças](modelo-de-ameacas.md) (SIGAB-013).
