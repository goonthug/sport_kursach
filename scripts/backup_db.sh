#!/usr/bin/env bash
# Делает безопасную копию базы данных SQLite.
# Копия сохраняется в папку sportrent/backups с временной меткой.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_DIR="$ROOT_DIR/sportrent"
DB_FILE="$PROJECT_DIR/db.sqlite3"
BACKUP_DIR="$PROJECT_DIR/backups"

if [[ ! -f "$DB_FILE" ]]; then
  echo "Файл базы не найден: $DB_FILE"
  exit 1
fi

mkdir -p "$BACKUP_DIR"

TIMESTAMP="$(date +"%Y%m%d-%H%M%S")"
BACKUP_FILE="$BACKUP_DIR/db-$TIMESTAMP.sqlite3"

cp "$DB_FILE" "$BACKUP_FILE"

echo "Резервная копия создана: $BACKUP_FILE"
