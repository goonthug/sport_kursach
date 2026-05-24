from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Сбросить и пересоздать БД: flush → migrate → populate_db'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Подтвердить сброс (обязательно)',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(self.style.WARNING(
                'Добавьте --confirm для подтверждения. '
                'Все данные будут удалены!'
            ))
            return

        self.stdout.write('==> Очищаем базу данных...')
        call_command('flush', '--noinput')

        self.stdout.write('==> Применяем миграции...')
        call_command('migrate', '--noinput')

        self.stdout.write('==> Заполняем тестовыми данными...')
        call_command('populate_db')

        self.stdout.write(self.style.SUCCESS('==> База данных пересоздана успешно.'))
