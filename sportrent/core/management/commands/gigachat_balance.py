"""
Management-команда: python manage.py gigachat_balance

Показывает:
  1. Баланс через GigaChat API (только для prepaid-клиентов; free tier → 403)
  2. Расход токенов из Redis-счётчиков (накапливается через _track_tokens)
"""

from datetime import date, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Показывает баланс и расход токенов GigaChat-2-Lite.'

    def handle(self, *args, **options):
        credentials = getattr(settings, 'GIGACHAT_CREDENTIALS', '')

        self.stdout.write('\n=== GigaChat токены ===\n')

        # 1. Попытка получить баланс через API
        if credentials:
            try:
                from gigachat import GigaChat
                with GigaChat(credentials=credentials, verify_ssl_certs=False) as client:
                    balance = client.get_balance()
                self.stdout.write(self.style.SUCCESS(f'Баланс API: {balance}'))
            except Exception as exc:
                # get_balance() возвращает 403 на free tier — это ожидаемо
                self.stdout.write(self.style.WARNING(
                    f'Баланс API недоступен (free tier не поддерживает): {exc}'
                ))
                self.stdout.write(
                    'Проверяй остаток вручную: https://developers.sber.ru/studio\n'
                )
        else:
            self.stdout.write(self.style.ERROR('GIGACHAT_CREDENTIALS не задан в .env'))

        # 2. Расход токенов из Redis
        self.stdout.write('\n--- Расход токенов (Redis счётчики) ---')
        try:
            from django.core.cache import cache

            today = date.today()
            today_tokens = cache.get(f'gigachat:tokens:{today.isoformat()}', 0)

            # Считаем за последние 7 дней
            week_tokens = sum(
                cache.get(f'gigachat:tokens:{(today - timedelta(days=i)).isoformat()}', 0)
                for i in range(7)
            )

            total_tokens = cache.get('gigachat:tokens:total', 0)

            self.stdout.write(f'  Сегодня ({today.isoformat()}):  {today_tokens} токенов')
            self.stdout.write(f'  Последние 7 дней:              {week_tokens} токенов')
            self.stdout.write(f'  Всего (с последнего redis flush): {total_tokens} токенов')
            self.stdout.write('')
            self.stdout.write('  Лимит free tier: 1 000 000 токенов / 12 мес')
            self.stdout.write(f'  Средняя стоимость запроса: ~23 токена')
            if total_tokens:
                remaining = max(0, 1_000_000 - total_tokens)
                approx_queries = remaining // 23
                self.stdout.write(
                    f'  Осталось примерно: ~{remaining:,} токенов '
                    f'(~{approx_queries:,} запросов)'
                )

        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'Ошибка чтения Redis: {exc}'))
            self.stdout.write('Убедись что Redis запущен (docker-compose up)')

        self.stdout.write('')
