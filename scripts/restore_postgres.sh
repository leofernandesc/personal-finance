#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 || "$1" != "--confirm" ]]; then
  echo "Uso destrutivo: $0 --confirm backups/arquivo.dump" >&2
  exit 2
fi

backup_file="$2"
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

echo "ATENÇÃO: o banco PostgreSQL do Compose será sobrescrito por $backup_file." >&2
echo "A confirmação explícita --confirm foi fornecida; iniciando restauração." >&2

docker compose exec -T db sh -c \
  'pg_restore --exit-on-error --clean --if-exists --no-owner --no-privileges -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  < "$backup_file"

echo "Restauração concluída. Execute 'make migrate' para conferir o schema."
