"""
Модели для системы отзывов и рейтингов.
"""

import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from users.models import User
from rentals.models import Rental


class Review(models.Model):
    """Отзывы пользователей."""

    TARGET_TYPE_CHOICES = [
        ('inventory', 'Инвентарь'),
        ('user', 'Пользователь'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Ожидает проверки'),
        ('published', 'Опубликован'),
        ('rejected', 'Отклонен'),
    ]

    review_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rental = models.ForeignKey(Rental, on_delete=models.CASCADE, related_name='reviews', verbose_name='Аренда')
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_reviews',
                                 verbose_name='Автор отзыва')

    # Универсальное поле для цели отзыва (может быть инвентарь или пользователь)
    reviewed_id = models.UUIDField(verbose_name='ID объекта отзыва')
    target_type = models.CharField(max_length=20, choices=TARGET_TYPE_CHOICES, verbose_name='Тип объекта')

    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Оценка'
    )
    comment = models.TextField(verbose_name='Комментарий')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Статус')
    review_date = models.DateTimeField(default=timezone.now, verbose_name='Дата отзыва')
    rejection_reason = models.TextField(blank=True, verbose_name='Причина отклонения')

    # Дополнительные критерии оценки
    punctuality_rating = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Оценка пунктуальности'
    )
    condition_rating = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Оценка состояния'
    )
    communication_rating = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Оценка общения'
    )

    class Meta:
        db_table = 'reviews'
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ['-review_date']
        indexes = [
            models.Index(fields=['reviewed_id', 'target_type', 'status']),
            models.Index(fields=['reviewer', 'status']),
        ]
        # Ограничение: один отзыв от пользователя на одну аренду
        constraints = [
            models.UniqueConstraint(
                fields=['rental', 'reviewer', 'target_type'],
                name='unique_review_per_rental_reviewer_target'
            )
        ]

    def __str__(self):
        return f"Отзыв от {self.reviewer.email} - {self.rating}/5"

    @property
    def average_detailed_rating(self):
        """Средняя оценка по детальным критериям."""
        ratings = [
            r for r in [self.punctuality_rating, self.condition_rating, self.communication_rating]
            if r is not None
        ]
        return sum(ratings) / len(ratings) if ratings else None