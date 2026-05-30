"""
Модель PaymentIntent — аудит-запись о каждом платеже через ЮКассу.

Что здесь:
- PaymentIntent: создаётся до редиректа на ЮКассу, обновляется webhook'ом.
  Три типа (purpose): rental_main (основная аренда), extension (продление),
  overdue (штраф за просрочку по ст. 622 ГК РФ).
  Хранит yookassa_payment_id (idempotency), amount, статус (pending/succeeded/failed).

Связано с:
- payments/views.py: создаёт и читает PaymentIntent
- payments/services.py: yookassa_payment_id используется для запроса статуса
- rentals/models.py: Rental.payment_intents (reverse FK) — все платежи по аренде

Ключевые слова: PaymentIntent, платёж, ЮКасса, аудит, idempotency, статус
"""

import uuid

from django.db import models


class PaymentIntent(models.Model):
    """Запись о намерении оплаты — создаётся до редиректа на ЮКассу, обновляется webhook'ом."""

    PURPOSE_CHOICES = [
        ('rental_main', 'Основная оплата аренды'),
        ('extension',   'Доплата за продление'),
        ('overdue',     'Штраф за просрочку'),
    ]

    STATUS_CHOICES = [
        ('pending',              'Ожидает оплаты'),
        ('waiting_for_capture', 'Ожидает подтверждения'),
        ('succeeded',           'Оплачен'),
        ('canceled',            'Отменён'),
    ]

    intent_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID намерения',
    )
    rental = models.ForeignKey(
        'rentals.Rental',
        on_delete=models.CASCADE,
        related_name='payment_intents',
        verbose_name='Аренда',
    )
    user = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='payment_intents',
        verbose_name='Плательщик',
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Сумма (руб.)',
    )
    purpose = models.CharField(
        max_length=20,
        choices=PURPOSE_CHOICES,
        verbose_name='Назначение платежа',
    )
    yookassa_payment_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
        verbose_name='ID платежа в ЮКассе',
    )
    status = models.CharField(
        max_length=25,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Статус',
    )
    raw_webhook_data = models.JSONField(
        default=dict,
        verbose_name='Сырые данные webhook',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлён')

    class Meta:
        verbose_name = 'Намерение оплаты'
        verbose_name_plural = 'Намерения оплаты'
        ordering = ['-created_at']

    def __str__(self):
        return f'PaymentIntent {self.intent_id} [{self.get_purpose_display()}] — {self.get_status_display()}'
