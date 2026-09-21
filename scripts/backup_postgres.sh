#!/usr/bin/env bash
set -euo pipefail

umask 077
PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

BACKUP_DIR="${PERSONAL_FINANCE_BACKUP_DIR:-$PROJECT_ROOT/backups}"
mkdir -p "$BACKUP_DIR"

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_file="$BACKUP_DIR/personal_finance_${timestamp}.dump"

docker compose exec -T db sh -c \
  'pg_dump --format=custom --no-owner --no-privileges -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  > "$backup_file"
sha256sum "$backup_file" > "$backup_file.sha256"

printf 'backup=%s\nchecksum=%s\n' "$backup_file" "$backup_file.sha256"
