#!/usr/bin/env bash
# Резервная копия PostgreSQL (pg_dump custom format).
# Читает DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT из .env в корне репозитория.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"
BACKUP_DIR="$ROOT_DIR/sportrent/backups"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Нет файла .env: $ENV_FILE"
  exit 1
fi

# Безопасная подстановка переменных из .env (только строки DB_*)
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

: "${DB_NAME:?В .env задайте DB_NAME}"
: "${DB_USER:?В .env задайте DB_USER}"

DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-5432}"

mkdir -p "$BACKUP_DIR"
TIMESTAMP="$(date +"%Y%m%d-%H%M%S")"
BACKUP_FILE="$BACKUP_DIR/pg-$DB_NAME-$TIMESTAMP.dump"

export PGPASSWORD="${DB_PASSWORD:-}"

pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -F c -f "$BACKUP_FILE"

echo "Резервная копия PostgreSQL создана: $BACKUP_FILE"

unset PGPASSWORD
