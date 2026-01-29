#!/usr/bin/env bash
# Подготовка проекта для разработки:
# - создает виртуальное окружение
# - устанавливает зависимости
# - создает папку для логов
# - применяет миграции

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_DIR="$ROOT_DIR/sportrent"
VENV_DIR="$ROOT_DIR/.venv"

if [[ ! -f "$PROJECT_DIR/manage.py" ]]; then
  echo "Не найден manage.py в $PROJECT_DIR"
  exit 1
fi

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "Python не найден. Установите Python 3.10+."
  exit 1
fi

if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

if [[ -d "$VENV_DIR/Scripts" ]]; then
  VENV_PY="$VENV_DIR/Scripts/python.exe"
else
  VENV_PY="$VENV_DIR/bin/python"
fi

if [[ ! -x "$VENV_PY" ]]; then
  echo "Не удалось найти python в виртуальном окружении."
  exit 1
fi

"$VENV_PY" -m pip install --upgrade pip
"$VENV_PY" -m pip install -r "$ROOT_DIR/requirements.txt"

# Логи пишутся в BASE_DIR/logs, поэтому папку нужно создать заранее
mkdir -p "$PROJECT_DIR/logs"

cd "$PROJECT_DIR"
"$VENV_PY" manage.py migrate

echo "Готово. Окружение создано и миграции применены."
