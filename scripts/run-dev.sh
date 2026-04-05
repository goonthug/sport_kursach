#!/usr/bin/env bash
# Запуск SportRent на Linux/macOS.
#
# Делает: venv → pip install → .env из примера (если нет) → migrate → (опционально) populate_db → runserver.
#
# Требуется заранее: PostgreSQL, созданная БД, корректный sportrent/.env
#
# Использование:
#   chmod +x scripts/run-dev.sh
#   ./scripts/run-dev.sh
#
# С тестовыми данными:
#   ./scripts/run-dev.sh --seed
#
# Только подготовка без сервера:
#   ./scripts/run-dev.sh --no-server

set -euo pipefail

SEED=0
NO_SERVER=0

for arg in "$@"; do
  case "$arg" in
    --seed) SEED=1 ;;
    --no-server) NO_SERVER=1 ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SPORTRENT_DIR="$REPO_ROOT/sportrent"
VENV_DIR="$REPO_ROOT/venv"
ENV_EXAMPLE="$REPO_ROOT/.env.example"
ENV_TARGET="$SPORTRENT_DIR/.env"

echo "==> Репозиторий: $REPO_ROOT"

if [[ ! -d "$SPORTRENT_DIR" ]]; then
  echo "Не найден каталог sportrent: $SPORTRENT_DIR" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Установите python3" >&2
  exit 1
fi

PY="python3"
echo "==> Python: $($PY --version)"

if [[ ! -d "$VENV_DIR" ]]; then
  echo "==> Создаю venv: $VENV_DIR"
  "$PY" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "==> pip install -r requirements.txt"
python -m pip install --upgrade pip -q
python -m pip install -r "$REPO_ROOT/requirements.txt"
python -m pip install "python-docx" -q 2>/dev/null || true

if [[ ! -f "$ENV_TARGET" ]]; then
  if [[ -f "$ENV_EXAMPLE" ]]; then
    echo "==> Копирую .env.example -> sportrent/.env (проверьте DB_*!)"
    cp "$ENV_EXAMPLE" "$ENV_TARGET"
  else
    echo "==> ВНИМАНИЕ: нет sportrent/.env и нет .env.example" >&2
  fi
else
  echo "==> Найден sportrent/.env"
fi

cd "$SPORTRENT_DIR"
mkdir -p logs

echo "==> django migrate"
python manage.py migrate

if [[ "$SEED" -eq 1 ]]; then
  echo "==> populate_db (тестовые данные)"
  python manage.py populate_db
fi

if [[ "$NO_SERVER" -eq 0 ]]; then
  echo "==> Запуск сервера http://127.0.0.1:8000/ (Ctrl+C — остановить)"
  python manage.py runserver
else
  echo "==> Готово (--no-server)"
fi
