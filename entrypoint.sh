#!/bin/sh
set -e

mkdir -p /app/sportrent/logs /app/sportrent/staticfiles /app/sportrent/media

echo "==> Применяем миграции..."
python manage.py migrate --noinput

echo "==> Проверяем наполненность БД..."
USER_COUNT=$(python manage.py shell -c \
  "from users.models import User; print(User.objects.count())" 2>/dev/null || echo "0")

if [ "$USER_COUNT" = "0" ]; then
    echo "==> База пустая — запускаем populate_db..."
    python manage.py populate_db
    echo "==> Демо-данные загружены."
else
    echo "==> В БД уже есть пользователи ($USER_COUNT) — populate_db пропускаем."
fi

echo "==> Собираем статику..."
python manage.py collectstatic --noinput -v 0

echo ""
echo "=========================================="
echo "  Проект доступен на http://localhost"
echo "  (откройте браузер через 5-10 секунд)"
echo "=========================================="
echo ""

exec daphne -b 0.0.0.0 -p 8000 config.asgi:application
