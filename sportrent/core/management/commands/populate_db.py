"""
Management команда для заполнения БД тестовыми данными.
Использование: python manage.py populate_db
"""

from django.core.management.base import BaseCommand
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

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Начинаем заполнение БД...'))

        # Создаем пользователей
        self.create_users()

        # Создаем категории
        self.create_categories()

        # Создаем инвентарь
        self.create_inventory()

        # Создаем аренды
        self.create_rentals()

        # Создаем отзывы
        self.create_reviews()

        self.stdout.write(self.style.SUCCESS('База данных успешно заполнена!'))

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
        manager_data = [
            ('manager1@sportrent.ru', 'Петров Петр Петрович'),
            ('manager2@sportrent.ru', 'Сидорова Анна Ивановна'),
        ]

        for index, (email, name) in enumerate(manager_data, start=1):
            user, created = User.objects.get_or_create(
                email=email,
                defaults={'role': 'manager', 'is_staff': True}
            )
            if created:
                user.set_password('manager123')
                user.save()
            Manager.objects.get_or_create(
                user=user,
                defaults={
                    'full_name': name,
                    'phone_work': f'+7(999)222-33-4{index}',
                    'email_work': email
                }
            )

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
            user, created = User.objects.get_or_create(
                email=email,
                defaults={'role': 'client'}
            )
            if created:
                user.set_password('client123')
                user.save()
            if not user.phone:
                user.phone = f'+7{9100000000 + index}'
                user.save(update_fields=['phone'])
            Client.objects.get_or_create(
                user=user,
                defaults={
                    'full_name': name,
                    'verified': random.choice([True, False]),
                    'preferred_payment': random.choice(['card', 'cash', 'online'])
                }
            )

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

        owners = Owner.objects.all()
        managers = Manager.objects.all()
        categories = SportCategory.objects.all()

        inventory_data = [
            # Велосипеды
            ('Горный велосипед Trek Marlin 7', 'Отличный горный велосипед для трейлов', 'Trek', 'Marlin 7',
             Decimal('800'), 'excellent'),
            ('Шоссейный велосипед Giant TCR', 'Легкий шоссейный велосипед', 'Giant', 'TCR Advanced', Decimal('1200'),
             'excellent'),
            ('Городской велосипед Stels Navigator', 'Удобный городской велосипед', 'Stels', 'Navigator 300',
             Decimal('500'), 'good'),

            # Лыжи
            ('Горные лыжи Atomic Redster', 'Профессиональные горные лыжи', 'Atomic', 'Redster G9', Decimal('1500'),
             'excellent'),
            ('Беговые лыжи Fischer Speedmax', 'Быстрые беговые лыжи', 'Fischer', 'Speedmax', Decimal('900'), 'good'),

            # Сноуборды
            ('Сноуборд Burton Custom', 'Универсальный фристайл сноуборд', 'Burton', 'Custom', Decimal('1100'),
             'excellent'),
            ('Сноуборд Ride Agenda', 'Сноуборд для начинающих', 'Ride', 'Agenda', Decimal('700'), 'good'),

            # Ролики
            ('Роликовые коньки Rollerblade', 'Комфортные фитнес ролики', 'Rollerblade', 'Zetrablade', Decimal('400'),
             'good'),

            # Самокаты
            ('Электросамокат Xiaomi Pro 2', 'Мощный электросамокат', 'Xiaomi', 'Mi Pro 2', Decimal('600'), 'excellent'),
            ('Самокат Razor A5 Lux', 'Складной самокат для взрослых', 'Razor', 'A5 Lux', Decimal('300'), 'good'),

            # Туристическое снаряжение
            ('Палатка Quechua Arpenaz 3', 'Трехместная палатка', 'Quechua', 'Arpenaz 3', Decimal('450'), 'good'),
            ('Рюкзак Osprey Atmos 65', 'Походный рюкзак 65л', 'Osprey', 'Atmos 65', Decimal('350'), 'excellent'),

            # Водный спорт
            ('SUP-борд Starboard', 'Надувной SUP для прогулок', 'Starboard', 'iGO Zen', Decimal('800'), 'excellent'),
            ('Каяк Intex Explorer', 'Надувной каяк', 'Intex', 'Explorer K2', Decimal('500'), 'good'),
        ]

        for i, (name, desc, brand, model, price, condition) in enumerate(inventory_data):
            owner = random.choice(owners)
            category = random.choice(categories)
            manager = random.choice(managers)

            # Создаем с разными статусами
            status = random.choices(
                ['available', 'pending', 'rented'],
                weights=[0.6, 0.2, 0.2]
            )[0]

            inventory, _ = Inventory.objects.get_or_create(
                name=name,
                defaults={
                    'owner': owner,
                    'manager': manager if status == 'available' else None,
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

        clients = Client.objects.all()
        available_inventory = Inventory.objects.filter(status='available')
        managers = Manager.objects.all()

        for i in range(10):
            client = random.choice(clients)
            inventory = random.choice(available_inventory)
            manager = random.choice(managers)

            start_date = timezone.now() - timedelta(days=random.randint(5, 30))
            end_date = start_date + timedelta(days=random.randint(2, 10))

            rental_days = (end_date - start_date).days
            total_price = inventory.price_per_day * rental_days

            status = random.choice(['completed', 'active', 'confirmed'])

            rental = Rental.objects.create(
                inventory=inventory,
                client=client,
                manager=manager,
                start_date=start_date,
                end_date=end_date,
                total_price=total_price,
                deposit_paid=inventory.deposit_amount,
                status=status,
                payment_status='paid' if status != 'pending' else 'pending'
            )

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
        from reviews.views import update_inventory_rating
        for inventory in Inventory.objects.all():
            update_inventory_rating(inventory)

        self.stdout.write(self.style.SUCCESS(f'Создано отзывов: {Review.objects.count()}'))