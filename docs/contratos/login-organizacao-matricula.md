# Login por organização e matrícula — original 049 / Jira 73

O formulário `/entrar/` recebe organização (UUID institucional), matrícula e senha. O administrador informa o UUID da organização ao provisionar o acesso. A matrícula é resolvida em `Membership` ativa na organização e deve identificar uma pessoa ativa com uma conta ativa e não revogada. Duas organizações podem usar a mesma matrícula e senhas independentes.

Contas técnicas sem pessoa continuam usando username global e organização vazia. Uma conta vinculada a pessoa não autentica por esse caminho. Não existe seleção pública de organizações ou recuperação que confirme a existência de outra conta.

As tentativas são limitadas por organização/matrícula e IP. Identificadores tentados ficam em HMAC, sem senha nos registros. Sessões continuam revogáveis e organizações suspensas não autenticam.

## Migração e rollback

Não se renomeiam usernames nem matrículas existentes. Antes de disponibilizar o novo formulário, conferir pessoas com conta mas sem vínculo ativo e organizar sua regularização pelo administrador do cliente. Novas contas que colidam com um username de outro tenant recebem identificador interno derivado de UUID; isso não muda a matrícula usada no login.

Não converter automaticamente conta de pessoa em conta técnica. Contas sem pessoa são credenciais técnicas e devem ser revisadas pelo administrador. Contas vinculadas sem matrícula ficam sem login até regularização; seus fatos históricos são preservados.

Rollback do código de autenticação preserva hashes e usernames antigos. Contas novas com identificadores internos precisam desses identificadores no rollback. A migração 0010 acrescenta restrições e não altera dados de login. Não reverter essa migração em banco com restrições registradas: isso apagaria evidência; preferir rollback de código compatível com o esquema.

Aceite institucional dos identificadores e homologação de login continuam pendentes de Produto; os testes automatizados são evidência técnica.
