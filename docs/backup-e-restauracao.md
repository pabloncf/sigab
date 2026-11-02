# Backup e ensaio de restauração — SIGAB-042

Estado: rotina técnica implementada; aceite operacional pendente. Metas do [ADR 0004](adr/0004-conectividade-e-contingencia.md): RPO ≤ 15 min e RTO ≤ 4 h. O ensaio de dump mede recuperação do banco, não a recuperação completa do serviço nem o RPO de produção.

## Cópia protegida

`ops/backup/backup.sh` usa PostgreSQL 17 (`pg_dump` custom) e age. O dump segue por pipe diretamente para criptografia; não há arquivo intermediário em claro. O diretório é 0700, arquivos 0600 e uma falha em qualquer estágio impede publicar a cópia. O manifesto identifica o início conservador do snapshot, término e SHA-256 do ciphertext. O hash detecta corrupção acidental; a autenticação criptográfica vem do age. Proteja também o manifesto contra alteração.

Pré-requisitos no host: Bash, Python ≥ 3.11, cliente PostgreSQL 17 e age. Para o ensaio Django: uv, Python 3.12 e dependências travadas. Há uma imagem de ferramentas em `ops/backup/Dockerfile`; ela não é a imagem de produção da aplicação.

1. Na máquina de recuperação, execute `umask 077; age-keygen -o recovery.agekey`. Guarde a chave privada em cofre separado das cópias e teste seu acesso durante o ensaio. Não a instale no host de backup. Extraia apenas a chave pública com `age-keygen -y recovery.agekey`.
2. Crie usuário de sistema `sigab-backup`, diretório `/var/backups/sigab` de sua propriedade e modo 0700. Instale o repositório em `/opt/sigab`. Use uma conta PostgreSQL de backup com leitura suficiente para todas as tabelas; ela não precisa criar/apagar bancos.
3. Crie `/etc/sigab/backup.env` protegido (root, 0600), com `PGHOST`, `PGPORT`, `PGUSER`, `PGDATABASE`, `PGPASSFILE=/etc/sigab/backup.pgpass`, `BACKUP_DIR=/var/backups/sigab` e `AGE_RECIPIENT=age1...`. O arquivo pgpass deve ser legível apenas pelo usuário de backup (0600). TLS/`PGSSLMODE=verify-full` e CA devem ser configurados para conexões remotas. Não passe senhas em linha de comando.
4. Instale `ops/backup/sigab-backup.service` e `.timer` em `/etc/systemd/system/`; rode `systemctl daemon-reload` e `systemctl enable --now sigab-backup.timer`. O timer executa diariamente às 02:00 UTC e recupera execuções perdidas. Teste com `systemctl start sigab-backup.service` e confira `journalctl -u sigab-backup.service`.
5. Copie cada diretório publicado para armazenamento fora do host, criptografado, com acesso restrito e proteção contra exclusão. Só considere uma cópia disponível após verificar o upload. O transporte e as credenciais dependem do provedor da implantação e não estão configurados por este repositório.

Não há descarte automático: prazo e destinação dependem da tabela de temporalidade e da [política de dados](politica-de-dados-pessoais.md). Monitore espaço, última cópia concluída, transferência externa e falhas do timer. Registre responsáveis e canal de alerta na implantação.

## Ensaio isolado

Use servidor PostgreSQL separado, sem dados operacionais, e diretório temporário sobre disco criptografado ou tmpfs. A restauração precisa materializar o dump autenticado em claro antes de executá-lo. Restaure apenas backups da sua própria origem confiável: dumps podem conter código SQL.

Configure `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD` (ou `PGPASSFILE`) **do servidor isolado**, `BACKUP_PATH` para um diretório de cópia, `AGE_IDENTITY` para a chave privada 0600, `REPORT_PATH` para um arquivo novo em diretório protegido e `RESTORE_TEST_ISOLATED=yes`. Use caminho absoluto para backup, chave e relatório. Execute:

```bash
./ops/backup/restore-test.sh
```

O script verifica checksum e descriptografia, cria um banco com nome aleatório (nunca restaura sobre banco existente), restaura em uma transação, verifica configuração Django, migrações, cadeia de auditoria e contagens. Apaga somente o banco que criou, inclusive em falhas, e elimina o dump temporário. Uma falha de limpeza resulta em código de saída não zero; investigue o nome indicado no erro. Uma interrupção não capturável, como falta de energia/SIGKILL, exige limpar manualmente os resíduos no host isolado.

O JSON preserva o manifesto original, contagens, resultados e duração. Não sobrescreve relatório existente. A duração considera descriptografia, criação, restore e verificações; o resultado `database_rto_within_4h` é exclusivo do banco. A cadeia de hashes não detecta toda exclusão de cauda: compare também contagens e evidências externas conhecidas do snapshot.

Execute mensalmente e após mudanças de schema/chaves; uma automação do ambiente deve agendar o ensaio e alertar por saída não zero. Para um exercício completo, meça também provisionamento, acesso às chaves, recuperação do armazenamento externo, implantação da mesma revisão, login, saída/devolução sintética, reconexão do frontend e aprovação operacional. Registre início da indisponibilidade, recuperação efetiva e último evento recuperado.

## Teste reproduzível

No cluster descartável do CI, `ops/backup/test-backup.sh` cria uma organização, item, saída e devolução sintéticos; faz cópia e restauração real; compara contagens; rejeita chave errada, ciphertext alterado e dump falho; verifica limpeza dos bancos temporários. Nunca execute esse teste em um cluster compartilhado com produção.

```bash
docker build -f ops/backup/Dockerfile -t sigab-backup-test .
# PGHOST/PGPORT/PGUSER/PGPASSWORD devem apontar para PostgreSQL 17 descartável.
docker run --rm --network host \
  -e PGHOST -e PGPORT -e PGUSER -e PGPASSWORD \
  sigab-backup-test /app/ops/backup/test-backup.sh
```

`--network host` é destinado ao runner Linux; em Docker Desktop use rede Docker dedicada e o nome do container PostgreSQL como `PGHOST`.

## Critérios ainda pendentes

- Provedor e configuração de WAL/PITR com armazenamento externo e monitoramento do atraso ≤ 15 min; dump diário sozinho não atende ao RPO.
- Ensaio PITR em volume representativo, com recuperação até um instante alvo e medição do último evento recuperado.
- Recuperação completa do serviço ≤ 4 h, incluindo infraestrutura, aplicação, frontend, segredos e acesso humano.
- Aprovação de retenção, responsáveis, cofre de chaves, alertas e armazenamento externo.

A SIGAB-042 permanece em andamento até essas evidências existirem. Não houve implantação nem alteração de banco de produção.
