#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Uso: $0 backups/arquivo.dump" >&2
  exit 2
fi

backup_file="$1"
if [[ "$backup_file" != /* ]]; then
  backup_file="$(pwd)/$backup_file"
fi
if [[ ! -f "$backup_file" ]]; then
  echo "Backup não encontrado: $backup_file" >&2
  exit 2
fi

if [[ -f "$backup_file.sha256" ]]; then
  (cd "$(dirname -- "$backup_file")" && sha256sum --check "$(basename -- "$backup_file.sha256")")
fi

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

restore_db="personal_finance_restore_check_$(date -u +%Y%m%d%H%M%S)"
cleanup() {
  docker compose exec -T db sh -c 'dropdb --if-exists -U "$POSTGRES_USER" "$1"' sh "$restore_db" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker compose exec -T db sh -c 'createdb -U "$POSTGRES_USER" "$1"' sh "$restore_db"
docker compose exec -T db sh -c \
  'pg_restore --exit-on-error --no-owner --no-privileges -U "$POSTGRES_USER" -d "$1"' \
  sh "$restore_db" < "$backup_file"

printf 'restore_check_db=%s\n' "$restore_db"
printf 'users='
docker compose exec -T db sh -c \
  'psql -U "$POSTGRES_USER" -d "$1" -At -c "SELECT count(*) FROM users"' \
  sh "$restore_db"
printf 'alembic_head='
docker compose exec -T db sh -c \
  'psql -U "$POSTGRES_USER" -d "$1" -At -c "SELECT version_num FROM alembic_version"' \
  sh "$restore_db"
