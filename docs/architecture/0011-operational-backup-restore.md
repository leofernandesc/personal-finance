# ADR 0011 — Backup e restauração local do PostgreSQL

## Status

Aceito em 21/09/2026 para desenvolvimento local.

## Contexto

O PostgreSQL é a fonte de verdade financeira. Um dump criado sem testar a
restauração não comprova que o sistema pode recuperar o histórico de um usuário
ou o estado das migrations.

## Decisões

- `scripts/backup_postgres.sh` usa `pg_dump` em formato custom, com `umask 077`,
  e grava um checksum SHA-256 ao lado do arquivo.
- `scripts/check_postgres_backup.sh` restaura o dump em um banco temporário,
  verifica que a tabela de usuários e `alembic_version` podem ser consultadas e
  remove somente esse banco temporário ao terminar.
- `scripts/restore_postgres.sh` exige `--confirm`, valida o checksum quando
  disponível e usa `pg_restore --clean` somente no banco do serviço Compose.
- Dumps ficam em `backups/`, ignorado pelo Git; nenhum dado financeiro deve ser
  commitado.

## Consequências

O fluxo continua sem custo operacional e funciona com PostgreSQL local. A
restauração é deliberadamente explícita e destrutiva; em produção ainda será
necessário definir retenção, armazenamento cifrado e procedimento de backup
externo.
