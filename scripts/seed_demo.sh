#!/usr/bin/env bash
# Заполняет БД демо-данными для презентации и тестов.
# Использует management-команду populate_db.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_DIR="$ROOT_DIR/sportrent"
VENV_DIR="$ROOT_DIR/.venv"

if [[ ! -f "$PROJECT_DIR/manage.py" ]]; then
  echo "Не найден manage.py в $PROJECT_DIR"
  exit 1
fi

if [[ -d "$VENV_DIR/Scripts" ]]; then
  VENV_PY="$VENV_DIR/Scripts/python.exe"
elif [[ -d "$VENV_DIR/bin" ]]; then
  VENV_PY="$VENV_DIR/bin/python"
else
  VENV_PY=""
fi

if [[ -z "$VENV_PY" || ! -x "$VENV_PY" ]]; then
  echo "Виртуальное окружение не найдено. Запустите scripts/bootstrap_dev.sh."
  exit 1
fi

cd "$PROJECT_DIR"
"$VENV_PY" manage.py migrate
"$VENV_PY" manage.py populate_db

echo "База данных заполнена демо-данными."
