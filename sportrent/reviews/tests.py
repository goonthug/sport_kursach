"""
Тесты для приложения reviews.
Проверяет паттерн Наблюдатель: сигнал post_save на Review пересчитывает рейтинг инвентаря.
"""

from decimal import Decimal
from django.test import TestCase
from django.utils import timezone

from users.models import User, Client, Owner, Manager
from inventory.models import Inventory, SportCategory
from rentals.models import Rental
from reviews.models import Review


def _make_user(email, role):
    return User.objects.create_user(email=email, password='Pass1234!', role=role)


def _make_client(email='client@test.com'):
    user = _make_user(email, 'client')
    return Client.objects.create(user=user, full_name='Тест Клиент')


def _make_owner(email='owner@test.com'):
    user = _make_user(email, 'owner')
    return Owner.objects.create(user=user, full_name='Тест Владелец')


def _make_manager(email='manager@test.com'):
    user = _make_user(email, 'manager')
    return Manager.objects.create(user=user, full_name='Тест Менеджер')


def _make_inventory(owner):
    category = SportCategory.objects.create(name='Велосипеды')
    return Inventory.objects.create(
        owner=owner,
        category=category,
        name='Тестовый велосипед',
        description='Описание',
        price_per_day=Decimal('500.00'),
        status='available',
    )


def _make_rental(inventory, client, manager):
    now = timezone.now()
    return Rental.objects.create(
        inventory=inventory,
        client=client,
        manager=manager,
        start_date=now,
        end_date=now,
        total_price=Decimal('500.00'),
        status='completed',
    )


class RatingSignalTest(TestCase):
    """Паттерн Наблюдатель: рейтинг инвентаря пересчитывается при сохранении отзыва."""

    def setUp(self):
        self.client_profile = _make_client()
        self.owner = _make_owner()
        self.manager = _make_manager()
        self.inventory = _make_inventory(self.owner)
        self.rental = _make_rental(self.inventory, self.client_profile, self.manager)

    def test_rating_recalculated_on_review_publish(self):
        """После публикации отзыва avg_rating инвентаря обновляется."""
        Review.objects.create(
            rental=self.rental,
            reviewer=self.client_profile.user,
            reviewed_id=self.inventory.inventory_id,
            target_type='inventory',
            rating=4,
            comment='Хорошо',
            status='published',
        )
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.avg_rating, Decimal('4.00'))
        self.assertEqual(self.inventory.reviews_count, 1)

    def test_pending_review_does_not_update_rating(self):
        """Отзыв в статусе pending НЕ обновляет рейтинг."""
        Review.objects.create(
            rental=self.rental,
            reviewer=self.client_profile.user,
            reviewed_id=self.inventory.inventory_id,
            target_type='inventory',
            rating=1,
            comment='Плохо',
            status='pending',
        )
        self.inventory.refresh_from_db()
        self.assertIsNone(self.inventory.avg_rating)

    def test_average_across_multiple_reviews(self):
        """Средний рейтинг считается по всем опубликованным отзывам."""
        client2 = _make_client('client2@test.com')
        rental2 = _make_rental(self.inventory, client2, self.manager)

        Review.objects.create(
            rental=self.rental,
            reviewer=self.client_profile.user,
            reviewed_id=self.inventory.inventory_id,
            target_type='inventory',
            rating=3,
            comment='Нормально',
            status='published',
        )
        Review.objects.create(
            rental=rental2,
            reviewer=client2.user,
            reviewed_id=self.inventory.inventory_id,
            target_type='inventory',
            rating=5,
            comment='Отлично',
            status='published',
        )
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.avg_rating, Decimal('4.00'))
        self.assertEqual(self.inventory.reviews_count, 2)
