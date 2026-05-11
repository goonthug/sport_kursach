"""
Management команда для заполнения БД тестовыми данными.
Использование: python manage.py populate_db
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.utils import OperationalError
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import random

from users.models import User, Client, Owner, Manager, Administrator, BankAccount, OwnerAgreement
from inventory.models import SportCategory, Inventory, InventoryPhoto
from rentals.models import Rental, Payment, Contract
from reviews.models import Review


class Command(BaseCommand):
    help = 'Заполняет базу данных тестовыми данными'

    def add_arguments(self, parser):
        parser.add_argument(
            '--flush',
            action='store_true',
            help='Очистить аренды/отзывы перед созданием (для повторного запуска на чистом листе)',
        )

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Начинаем заполнение БД...'))

        try:
            connection.ensure_connection()
        except OperationalError as exc:
            raise CommandError(
                'Не удалось подключиться к PostgreSQL. Запустите службу PostgreSQL и '
                'проверьте sportrent/.env: DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT.\n'
                f'Детали: {exc}'
            ) from exc

        if kwargs['flush']:
            self.stdout.write('--flush: удаляем аренды, платежи и отзывы...')
            from reviews.models import Review
            from rentals.models import Payment
            Review.objects.all().delete()
            Payment.objects.all().delete()
            Rental.objects.all().delete()
            self.stdout.write(self.style.WARNING('Аренды, платежи и отзывы удалены.'))

        # Создаем пользователей
        self.create_users()

        # Создаем категории
        self.create_categories()

        # Создаем инвентарь
        self.create_inventory()

        # Создаем аренды (только если их ещё нет — для идемпотентности)
        if Rental.objects.exists() and not kwargs['flush']:
            self.stdout.write(self.style.WARNING(
                f'Аренды уже существуют ({Rental.objects.count()} шт.) — пропуск. '
                'Используй --flush для пересоздания.'
            ))
        else:
            self.create_rentals()

        # Создаем отзывы
        self.create_reviews()

        self.stdout.write(self.style.SUCCESS('База данных успешно заполнена!'))
        self.stdout.write(self.style.SUCCESS('Открыть сайт: http://localhost/'))
        self.stdout.write('Тестовые аккаунты:')
        self.stdout.write('  admin@sportrent.ru   / admin123')
        self.stdout.write('  manager1@sportrent.ru / manager123')
        self.stdout.write('  owner1@mail.ru        / owner123')
        self.stdout.write('  client1@mail.ru       / client123')

    def create_users(self):
        """Создание тестовых пользователей."""
        self.stdout.write('Создаем пользователей...')

        # Администратор
        admin_user, created = User.objects.get_or_create(
            email='admin@sportrent.ru',
            defaults={'role': 'administrator'}
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.is_staff = True
            admin_user.save()
        Administrator.objects.get_or_create(
            user=admin_user,
            defaults={
                'full_name': 'Администратор Системы',
                'email_work': 'admin@sportrent.ru'
            }
        )

        # Менеджеры
        primary_manager_email = 'manager1@sportrent.ru'
        primary_manager_name = 'Петров Петр Петрович'

        primary_user, created = User.objects.get_or_create(
            email=primary_manager_email,
            defaults={'role': 'manager', 'is_staff': True}
        )
        if created:
            primary_user.set_password('manager123')
            primary_user.save()
        primary_manager, _ = Manager.objects.get_or_create(
            user=primary_user,
            defaults={
                'full_name': primary_manager_name,
                'phone_work': '+7(999)222-33-41',
                'email_work': primary_manager_email,
            }
        )

        # Если в БД уже есть второй менеджер от прошлых запусков, делаем его неиспользуемым:
        # 1) Переназначаем инвентарь/аренды первому менеджеру
        # 2) Удаляем лишние профили менеджеров
        other_managers = Manager.objects.exclude(user__email=primary_manager_email)
        if other_managers.exists():
            Inventory.objects.filter(status='available', manager__in=other_managers).update(manager=primary_manager)
            Rental.objects.filter(manager__in=other_managers).update(manager=primary_manager)

            # Удаляем пользователей (Manager удалится каскадно). Список id до любых дальнейших запросов.
            other_managers_user_ids = list(other_managers.values_list('user_id', flat=True))
            User.objects.filter(user_id__in=other_managers_user_ids).delete()

        # Владельцы
        owner_data = [
            ('owner1@mail.ru', 'Владимиров Владимир Владимирович'),
            ('owner2@mail.ru', 'Александрова Мария Сергеевна'),
            ('owner3@mail.ru', 'Николаев Николай Николаевич'),
        ]

        for index, (email, name) in enumerate(owner_data, start=1):
            user, created = User.objects.get_or_create(
                email=email,
                defaults={'role': 'owner'}
            )
            if created:
                user.set_password('owner123')
                user.save()
            if not user.phone:
                user.phone = f'+7{9000000000 + index}'
                user.save(update_fields=['phone'])
            owner, _ = Owner.objects.get_or_create(
                user=user,
                defaults={'full_name': name, 'verified': random.choice([True, False])}
            )
            if not OwnerAgreement.objects.filter(owner=owner, is_accepted=True).exists():
                OwnerAgreement.objects.create(
                    owner=owner,
                    owner_percentage=70,
                    store_percentage=30,
                    agreement_text="Соглашение о выплатах: 70% владельцу, 30% магазину",
                    is_accepted=True,
                    accepted_date=timezone.now()
                )
            if not BankAccount.objects.filter(owner=owner).exists():
                BankAccount.objects.create(
                    owner=owner,
                    bank_name='Сбербанк',
                    account_number=f'2222-2222-2222-{str(1110 + index)}',
                    recipient_name=owner.full_name,
                    is_default=True
                )

        # Клиенты
        client_data = [
            ('client1@mail.ru', 'Иванов Иван Иванович'),
            ('client2@mail.ru', 'Смирнова Елена Александровна'),
            ('client3@mail.ru', 'Кузнецов Дмитрий Павлович'),
            ('client4@mail.ru', 'Морозова Ольга Викторовна'),
            ('client5@mail.ru', 'Федоров Андрей Михайлович'),
        ]

        for index, (email, name) in enumerate(client_data, start=1):
            user, created_user = User.objects.get_or_create(
                email=email,
                defaults={'role': 'client'}
            )
            if created_user:
                user.set_password('client123')
                user.save()
            if not user.phone:
                user.phone = f'+7{9100000000 + index}'
                user.save(update_fields=['phone'])

            # Генерируем реалистичные паспортные данные
            passport_series = f"{4500 + index:04d}"
            passport_number = f"{120000 + index:06d}"
            passport_issue_date = (timezone.now() - timedelta(days=365 * random.randint(3, 15))).date()
            passport_department_code = f"{random.randint(100, 899):03d}-{random.randint(100, 899):03d}"

            client, created_client = Client.objects.get_or_create(
                user=user,
                defaults={
                    'full_name': name,
                    'verified': random.choice([True, False]),
                    'preferred_payment': random.choice(['card', 'cash', 'online']),
                    'passport_series': passport_series,
                    'passport_number': passport_number,
                    'passport_issue_date': passport_issue_date,
                    'passport_department_code': passport_department_code,
                }
            )

            # Если клиент уже существовал ранее без паспортных данных — дополним их
            if not created_client:
                updated = False
                if not getattr(client, 'passport_series', None):
                    client.passport_series = passport_series
                    updated = True
                if not getattr(client, 'passport_number', None):
                    client.passport_number = passport_number
                    updated = True
                if not getattr(client, 'passport_issue_date', None):
                    client.passport_issue_date = passport_issue_date
                    updated = True
                if not getattr(client, 'passport_department_code', None):
                    client.passport_department_code = passport_department_code
                    updated = True
                if updated:
                    client.save()

        self.stdout.write(self.style.SUCCESS(f'Создано пользователей: {User.objects.count()}'))

    def create_categories(self):
        """Создание категорий спортивного инвентаря."""
        self.stdout.write('Создаем категории...')

        categories = [
            {'name': 'Велосипеды', 'description': 'Горные, шоссейные, городские велосипеды', 'icon': 'bi-bicycle'},
            {'name': 'Лыжи', 'description': 'Горные и беговые лыжи', 'icon': 'bi-snow'},
            {'name': 'Сноуборды', 'description': 'Сноуборды для разных стилей катания', 'icon': 'bi-snow2'},
            {'name': 'Ролики', 'description': 'Роликовые коньки', 'icon': 'bi-badge-vo'},
            {'name': 'Самокаты', 'description': 'Электросамокаты и обычные самокаты', 'icon': 'bi-scooter'},
            {'name': 'Туристическое снаряжение', 'description': 'Палатки, рюкзаки, спальники', 'icon': 'bi-backpack'},
            {'name': 'Водный спорт', 'description': 'SUP-борды, каяки, серфы', 'icon': 'bi-water'},
        ]

        for cat_data in categories:
            SportCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults=cat_data
            )

        self.stdout.write(self.style.SUCCESS(f'Создано категорий: {SportCategory.objects.count()}'))

    def create_inventory(self):
        """Создание инвентаря."""
        self.stdout.write('Создаем инвентарь...')

        owners = list(Owner.objects.all())
        primary_manager = Manager.objects.filter(user__email='manager1@sportrent.ru').first()
        if not primary_manager:
            raise RuntimeError('Первый менеджер (manager1@sportrent.ru) не найден. Сначала запустите populate_db.')
        categories = list(SportCategory.objects.all())
        if not owners:
            raise RuntimeError('Нет владельцев в БД. Сначала выполните create_users.')
        if not categories:
            raise RuntimeError('Нет категорий. Сначала выполните create_categories.')

        inventory_data = [
            # Велосипеды
            ('Горный велосипед Trek Marlin 7', 'Отличный горный велосипед для трейлов', 'Trek', 'Marlin 7',
             Decimal('800'), 'excellent'),
            ('Шоссейный велосипед Giant TCR', 'Легкий шоссейный велосипед', 'Giant', 'TCR Advanced', Decimal('1200'),
             'excellent'),
            ('Городской велосипед Stels Navigator', 'Удобный городской велосипед', 'Stels', 'Navigator 300',
             Decimal('500'), 'good'),
            ('Горный велосипед Specialized Rockhopper', 'Надёжный хардтейл для трасс', 'Specialized', 'Rockhopper', Decimal('750'), 'good'),
            ('Городской велосипед Trek FX', 'Гибрид для города и парка', 'Trek', 'FX 2', Decimal('520'), 'good'),

            # Лыжи
            ('Горные лыжи Atomic Redster', 'Профессиональные горные лыжи', 'Atomic', 'Redster G9', Decimal('1500'),
             'excellent'),
            ('Беговые лыжи Fischer Speedmax', 'Быстрые беговые лыжи', 'Fischer', 'Speedmax', Decimal('900'), 'good'),
            ('Горные лыжи Rossignol Hero', 'Карвинговые лыжи для склона', 'Rossignol', 'Hero Elite', Decimal('1300'), 'excellent'),

            # Сноуборды
            ('Сноуборд Burton Custom', 'Универсальный фристайл сноуборд', 'Burton', 'Custom', Decimal('1100'),
             'excellent'),
            ('Сноуборд Ride Agenda', 'Сноуборд для начинающих', 'Ride', 'Agenda', Decimal('700'), 'good'),
            ('Сноуборд Salomon Assassin', 'Для парка и пайпа', 'Salomon', 'Assassin', Decimal('1000'), 'excellent'),

            # Ролики
            ('Роликовые коньки Rollerblade', 'Комфортные фитнес ролики', 'Rollerblade', 'Zetrablade', Decimal('400'),
             'good'),
            ('Ролики K2 F.I.T. 84', 'Фитнес для взрослых', 'K2', 'F.I.T. 84', Decimal('450'), 'good'),

            # Самокаты
            ('Электросамокат Xiaomi Pro 2', 'Мощный электросамокат', 'Xiaomi', 'Mi Pro 2', Decimal('600'), 'excellent'),
            ('Самокат Razor A5 Lux', 'Складной самокат для взрослых', 'Razor', 'A5 Lux', Decimal('300'), 'good'),
            ('Электросамокат Ninebot Max', 'Максимальная дальность', 'Ninebot', 'Max G30', Decimal('750'), 'excellent'),

            # Туристическое снаряжение
            ('Палатка Quechua Arpenaz 3', 'Трехместная палатка', 'Quechua', 'Arpenaz 3', Decimal('450'), 'good'),
            ('Рюкзак Osprey Atmos 65', 'Походный рюкзак 65л', 'Osprey', 'Atmos 65', Decimal('350'), 'excellent'),
            ('Палатка Nordway Sphinx', 'Двухместная трёхсезонная', 'Nordway', 'Sphinx 2', Decimal('380'), 'good'),
            ('Рюкзак Deuter Aircontact', 'С системой вентиляции', 'Deuter', 'Aircontact 55', Decimal('480'), 'excellent'),

            # Водный спорт
            ('SUP-борд Starboard', 'Надувной SUP для прогулок', 'Starboard', 'iGO Zen', Decimal('800'), 'excellent'),
            ('Каяк Intex Explorer', 'Надувной каяк', 'Intex', 'Explorer K2', Decimal('500'), 'good'),
            ('SUP-борд Red Paddle Co', 'Жёсткий для волн', 'Red Paddle Co', 'Ride 10.6', Decimal('950'), 'excellent'),
            ('Каяк надувной Sevylor Colorado', 'Двухместный', 'Sevylor', 'Colorado', Decimal('450'), 'good'),
        ]

        for i, (name, desc, brand, model, price, condition) in enumerate(inventory_data):
            owner = random.choice(owners)
            category = random.choice(categories)  # list, не QuerySet — для random.choice

            # Создаем с разными статусами
            status = random.choices(
                ['available', 'pending', 'rented'],
                weights=[0.6, 0.2, 0.2]
            )[0]

            inventory, _ = Inventory.objects.get_or_create(
                name=name,
                defaults={
                    'owner': owner,
                    'manager': primary_manager if status == 'available' else None,
                    'category': category,
                    'description': desc,
                    'brand': brand,
                    'model': model,
                    'price_per_day': price,
                    'condition': condition,
                    'status': status,
                    'min_rental_days': random.randint(1, 3),
                    'max_rental_days': random.randint(7, 30),
                    'deposit_amount': price * Decimal('0.3'),
                }
            )
            # На повторном запуске populate_db обновляем менеджера в соответствии с текущим статусом.
            if inventory.status == 'available':
                if inventory.manager_id != primary_manager.manager_id:
                    inventory.manager = primary_manager
                    inventory.save(update_fields=['manager'])
            else:
                if inventory.manager_id is not None:
                    inventory.manager = None
                    inventory.save(update_fields=['manager'])
            if not inventory.bank_account:
                owner_account = BankAccount.objects.filter(owner=owner, is_default=True).first()
                if not owner_account:
                    owner_account = BankAccount.objects.filter(owner=owner).first()
                if owner_account:
                    inventory.bank_account = owner_account
                    inventory.save(update_fields=['bank_account'])

        self.stdout.write(self.style.SUCCESS(f'Создано инвентаря: {Inventory.objects.count()}'))

    def create_rentals(self):
        """Создание тестовых аренд."""
        self.stdout.write('Создаем аренды...')

        clients = list(Client.objects.all())
        available_inventory = list(Inventory.objects.filter(status='available'))
        primary_manager = Manager.objects.filter(user__email='manager1@sportrent.ru').first()
        if not primary_manager:
            raise RuntimeError('Первый менеджер (manager1@sportrent.ru) не найден. Сначала запустите populate_db.')

        if not clients:
            self.stdout.write(self.style.WARNING('Нет клиентов — пропуск создания аренд.'))
            return
        if not available_inventory:
            self.stdout.write(
                self.style.WARNING(
                    'Нет инвентаря со статусом «доступен» — пропуск создания аренд. '
                    'Запустите populate_db на чистой БД или добавьте доступные позиции.'
                )
            )
            return

        for i in range(10):
            client = random.choice(clients)
            inventory = random.choice(available_inventory)

            start_date = timezone.now() - timedelta(days=random.randint(5, 30))
            end_date = start_date + timedelta(days=random.randint(2, 10))

            rental_days = (end_date - start_date).days
            total_price = inventory.price_per_day * rental_days

            status = random.choice(['completed', 'active', 'confirmed'])

            rental = Rental.objects.create(
                inventory=inventory,
                client=client,
                manager=primary_manager,
                start_date=start_date,
                end_date=end_date,
                total_price=total_price,
                deposit_paid=inventory.deposit_amount,
                status=status,
                payment_status='paid' if status != 'pending' else 'pending',
                actual_return_date=end_date if status == 'completed' else None,
            )

            # Для завершённых аренд обновляем заработок владельца, чтобы аналитика не ломалась
            if status == 'completed':
                agreement = OwnerAgreement.objects.filter(
                    owner=inventory.owner,
                    is_accepted=True
                ).order_by('-created_date').first()
                owner_pct = (agreement.owner_percentage if agreement else 70) / 100
                owner_amount = total_price * Decimal(str(owner_pct))
                owner = inventory.owner
                owner.total_earnings += owner_amount
                owner.save(update_fields=['total_earnings'])

            # Создаем платеж
            Payment.objects.create(
                rental=rental,
                amount=total_price,
                payment_method=random.choice(['card', 'online']),
                status='completed' if status != 'pending' else 'pending',
                payment_date=start_date if status != 'pending' else None
            )

        self.stdout.write(self.style.SUCCESS(f'Создано аренд: {Rental.objects.count()}'))

    def create_reviews(self):
        """Создание тестовых отзывов."""
        self.stdout.write('Создаем отзывы...')

        completed_rentals = Rental.objects.filter(status='completed')

        comments = [
            'Отличное состояние, все понравилось!',
            'Хороший инвентарь, рекомендую.',
            'Все прошло гладко, спасибо!',
            'Качественное оборудование.',
            'Приятное обслуживание.',
        ]

        for rental in completed_rentals[:15]:
            Review.objects.get_or_create(
                rental=rental,
                reviewer=rental.client.user,
                target_type='inventory',
                defaults={
                    'reviewed_id': rental.inventory.inventory_id,
                    'rating': random.randint(4, 5),
                    'comment': random.choice(comments),
                    'status': 'published',
                    'punctuality_rating': random.randint(4, 5),
                    'condition_rating': random.randint(4, 5),
                    'communication_rating': random.randint(4, 5),
                }
            )

        # Обновляем рейтинг по всем отзывам
        from reviews.utils import update_inventory_rating

        for inventory in Inventory.objects.all():
            update_inventory_rating(inventory)

        self.stdout.write(self.style.SUCCESS(f'Создано отзывов: {Review.objects.count()}'))