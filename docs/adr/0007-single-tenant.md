# ADR 0007 — Produto single-tenant

Status: decidido pelo responsável pelo produto em 10/11/2026; implementação técnica nesta revisão. Substitui a tenancy compartilhada do ADR 0002 e o identificador de organização no login do contrato 049/Jira 73. Autorizações explícitas, segregação de funções, unidades, confirmação, idempotência e auditoria continuam vigentes.

## Decisão

Cada cliente tem instalação, banco, credenciais de banco, domínio/acesso e cópias de segurança próprios. Uma instalação contém **uma organização**, com várias unidades e locais de guarda internos. Um segundo cliente exige outro banco e implantação. Um servidor físico pode hospedar instalações distintas se seus recursos e credenciais forem isolados; compartilhar tabelas de clientes não faz parte do produto.

`Organization` permanece como cadastro institucional e referência dos registros históricos. A migração `0012_single_tenant_installation` acrescenta `installation_key`: valor obrigatório 1 por check constraint e único no banco. Essa combinação impede uma segunda organização, inclusive por escrita concorrente ou `bulk_create`. Não há configuração para reativar o modo compartilhado.

Não se removem UUIDs, FKs, escopos, cadeias de auditoria ou unicidades existentes: eles preservam a identidade dos fatos e a integridade referencial. Os filtros por organização são defesa adicional, não roteamento de tenants. A separação interna de acesso continua por concessão e unidade.

## Acesso e provisionamento

- Login por matrícula e senha na organização única, ou username e senha para conta técnica. Não existe campo de organização na tela.
- Matrícula depende de pessoa e vínculo ativos e de uma conta não revogada. Identificador ambíguo entre matrícula e usuário técnico é recusado com mensagem genérica; o administrador deve regularizar a colisão.
- O parâmetro de organização em chamadas antigas de autenticação só pode repetir o ID local; nunca escolhe outro cliente. O formulário não o utiliza. Variar esse parâmetro não cria outro limite de tentativas.
- Organização suspensa ou conta inativa/revogada continua sem acesso. Superusuário local de manutenção não recebe permissões operacionais automaticamente.
- `bootstrap_sigab` inicializa somente uma base sem organização. `seed_demo` cria uma organização com duas unidades e recusa base já inicializada.
- Os comandos de criação de conta e situação da organização usam a organização local. `--organization-id` é opcional por compatibilidade e, se informado, deve corresponder à organização local.

## Transição de dados

A migração recusa banco com mais de uma organização **antes de adicionar a restrição**, sem apagar, fundir, renomear ou reatribuir dados. Para uma base vazia ou com uma organização, preserva os IDs e registros existentes.

Antes de atualizar um banco antigo, levantar apenas a quantidade de organizações e os IDs institucionais. Se houver mais de uma, preparar instalações e bancos exclusivos e um procedimento revisado de exportação/restauração por cliente que preserve FKs, contas, movimentos e cadeias de auditoria. Conferir contagens, relações e hashes, além de acesso por unidade, em ambiente isolado antes da troca. Não selecionar arbitrariamente um cliente, truncar tabelas ou remapear histórico para fazer a migração passar.

Essa separação não é executada automaticamente por esta entrega. O ambiente antigo de demonstração com Alfa e Bravo também precisa dessa transição; se seus dados forem descartáveis, a criação de uma demonstração nova deve ser feita em outro banco vazio, preservando o antigo até decisão explícita de descarte.

Cada implantação deve apontar `DATABASE_URL` para seu banco exclusivo; compartilhar um mesmo banco entre duas implantações não cria dois clientes. Manter usuários de banco, diretórios de backup e gestão de chaves separados por instalação. As metas de recuperação e pendências de PITR continuam no procedimento de backup existente.

## Requisitos e rastreabilidade

A fonte DOC-0011 permanece intacta. A exigência multi-organização RF-01 e o isolamento por linha RNF-05 são substituídos por uma organização por instalação e isolamento físico entre bancos de clientes. RF-02 passa a matrícula/senha local sem código de cliente. Papéis, unidades e demais requisitos continuam com as evidências e pendências já registradas. Implementação técnica não substitui homologação de fluxo e decisões de domínio quantitativo.

## Verificação

- Banco rejeita segunda organização e chave diferente de 1.
- Migração recusa múltiplas organizações e preserva base de um cliente.
- Bootstrap e demonstração recusam segundo cliente.
- Login local dispensa UUID; tentativa de seleção externa não muda a organização; limitações de tentativas não são contornadas por parâmetro de organização.
- Testes de referências cruzadas continuam sobre fixtures explicitamente legadas e inválidas. O helper existe apenas nos testes e desabilita temporariamente o check dentro do banco descartável; não é caminho de provisionamento do produto.
- Registros de evidência anteriores a este ADR descrevem a arquitetura histórica.
