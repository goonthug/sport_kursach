"""
Модели для управления арендой инвентаря.
"""

import uuid
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from users.models import Client, Manager, BankAccount
from inventory.models import Inventory


class Rental(models.Model):
    """Аренда инвентаря."""

    STATUS_CHOICES = [
        ('inquiry', 'Вопрос по инвентарю'),
        ('pending', 'Ожидает подтверждения'),
        ('confirmed', 'Подтверждена'),
        ('active', 'Активна'),
        ('completed', 'Завершена'),
        ('cancelled', 'Отменена'),
        ('rejected', 'Отклонена'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Ожидает оплаты'),
        ('paid', 'Оплачено'),
        ('refunded', 'Возвращено'),
        ('failed', 'Ошибка оплаты'),
    ]

    rental_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inventory = models.ForeignKey(Inventory, on_delete=models.PROTECT, related_name='rentals', verbose_name='Инвентарь')
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='rentals', verbose_name='Клиент')
    manager = models.ForeignKey(Manager, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='managed_rentals', verbose_name='Менеджер')

    start_date = models.DateTimeField(verbose_name='Дата начала')
    end_date = models.DateTimeField(verbose_name='Дата окончания')
    actual_return_date = models.DateTimeField(null=True, blank=True, verbose_name='Фактическая дата возврата')

    total_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)],
                                      verbose_name='Общая стоимость')
    deposit_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Внесенный залог')

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending', verbose_name='Статус')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending',
                                      verbose_name='Статус оплаты')

    created_date = models.DateTimeField(default=timezone.now, verbose_name='Дата создания')
    notes = models.TextField(blank=True, verbose_name='Примечания')
    rejection_reason = models.TextField(blank=True, verbose_name='Причина отклонения')
    
    # Банковский счет для выплаты владельцу
    bank_account = models.ForeignKey(BankAccount, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='rentals', verbose_name='Банковский счет для выплаты')

    class Meta:
        db_table = 'rentals'
        verbose_name = 'Аренда'
        verbose_name_plural = 'Аренды'
        ordering = ['-created_date']
        indexes = [
            models.Index(fields=['client', 'status']),
            models.Index(fields=['inventory', 'status']),
            models.Index(fields=['start_date', 'end_date']),
        ]

    def __str__(self):
        return f"Аренда {self.inventory.name} - {self.client.full_name}"

    @property
    def rental_days(self):
        """Количество дней аренды."""
        return (self.end_date - self.start_date).days

    def is_overdue(self):
        """Проверка просрочки возврата."""
        if self.status == 'active' and not self.actual_return_date:
            return timezone.now() > self.end_date
        return False


class Payment(models.Model):
    """Платежи за аренду."""

    PAYMENT_METHOD_CHOICES = [
        ('card', 'Банковская карта'),
        ('cash', 'Наличные'),
        ('online', 'Онлайн-платеж'),
        ('transfer', 'Банковский перевод'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Ожидает обработки'),
        ('completed', 'Завершен'),
        ('failed', 'Ошибка'),
        ('refunded', 'Возвращен'),
    ]

    payment_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rental = models.ForeignKey(Rental, on_delete=models.PROTECT, related_name='payments', verbose_name='Аренда')

    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)],
                                 verbose_name='Сумма')
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES, verbose_name='Способ оплаты')
    transaction_id = models.CharField(max_length=100, unique=True, blank=True, null=True, verbose_name='ID транзакции')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Статус')
    payment_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата платежа')

    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Сумма возврата')
    refund_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата возврата')

    class Meta:
        db_table = 'payments'
        verbose_name = 'Платеж'
        verbose_name_plural = 'Платежи'
        ordering = ['-payment_date']

    def __str__(self):
        return f"Платеж {self.amount} руб. - {self.rental}"


class Contract(models.Model):
    """Договоры аренды."""

    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('active', 'Активен'),
        ('completed', 'Завершен'),
        ('cancelled', 'Отменен'),
    ]

    contract_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rental = models.OneToOneField(Rental, on_delete=models.CASCADE, related_name='contract', verbose_name='Аренда')

    contract_number = models.CharField(max_length=50, unique=True, verbose_name='Номер договора')
    terms = models.TextField(verbose_name='Условия договора')

    start_date = models.DateField(verbose_name='Дата начала')
    end_date = models.DateField(verbose_name='Дата окончания')
    signed_date = models.DateField(null=True, blank=True, verbose_name='Дата подписания')

    pdf_url = models.FileField(upload_to='contracts/', blank=True, null=True, verbose_name='PDF договора')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='Статус')

    class Meta:
        db_table = 'contracts'
        verbose_name = 'Договор'
        verbose_name_plural = 'Договоры'
        ordering = ['-signed_date']

    def __str__(self):
        return f"Договор {self.contract_number}"


class DamageReport(models.Model):
    """Отчеты о повреждениях."""

    DAMAGE_TYPE_CHOICES = [
        ('minor', 'Незначительное'),
        ('moderate', 'Среднее'),
        ('major', 'Серьезное'),
        ('critical', 'Критическое'),
    ]

    STATUS_CHOICES = [
        ('reported', 'Сообщено'),
        ('reviewing', 'На рассмотрении'),
        ('resolved', 'Решено'),
        ('disputed', 'Оспаривается'),
    ]

    report_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rental = models.ForeignKey(Rental, on_delete=models.CASCADE, related_name='damage_reports', verbose_name='Аренда')
    inventory = models.ForeignKey(Inventory, on_delete=models.CASCADE, related_name='damage_reports',
                                  verbose_name='Инвентарь')
    reporter = models.ForeignKey('users.User', on_delete=models.CASCADE, verbose_name='Сообщивший')

    damage_type = models.CharField(max_length=50, choices=DAMAGE_TYPE_CHOICES, verbose_name='Тип повреждения')
    description = models.TextField(verbose_name='Описание')
    photos = models.ImageField(upload_to='damage_reports/', blank=True, null=True, verbose_name='Фото повреждений')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='reported', verbose_name='Статус')
    repair_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                      verbose_name='Стоимость ремонта')

    reported_date = models.DateTimeField(default=timezone.now, verbose_name='Дата сообщения')
    resolved_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата решения')

    class Meta:
        db_table = 'damage_reports'
        verbose_name = 'Отчет о повреждении'
        verbose_name_plural = 'Отчеты о повреждениях'
        ordering = ['-reported_date']

    def __str__(self):
        return f"Повреждение {self.inventory.name} - {self.damage_type}"