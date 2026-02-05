"""
Модели пользователей системы SportRent.
Включает базовую модель User и расширенные модели для разных ролей.
"""

import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class UserManager(BaseUserManager):
    """Менеджер для кастомной модели пользователя."""

    def create_user(self, email, password=None, **extra_fields):
        """Создание обычного пользователя."""
        if not email:
            raise ValueError('Email обязателен для заполнения')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Создание суперпользователя."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'administrator')

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Базовая модель пользователя.
    Поддерживает различные роли: client, owner, manager, administrator.
    """

    ROLE_CHOICES = [
        ('client', 'Клиент'),
        ('owner', 'Владелец'),
        ('manager', 'Менеджер'),
        ('administrator', 'Администратор'),
    ]

    STATUS_CHOICES = [
        ('active', 'Активен'),
        ('blocked', 'Заблокирован'),
        ('pending', 'Ожидает проверки'),
    ]

    user_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(max_length=255, unique=True, verbose_name='Email')
    phone = models.CharField(max_length=15, blank=True, null=True, unique=True, verbose_name='Телефон')

    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='client', verbose_name='Роль')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name='Статус')

    registration_date = models.DateTimeField(default=timezone.now, verbose_name='Дата регистрации')
    avatar_url = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='Аватар')

    avg_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        verbose_name='Средний рейтинг'
    )
    loyalty_points = models.IntegerField(default=0, verbose_name='Баллы лояльности')

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'users'
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['-registration_date']

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"

    def get_full_name(self):
        """Получение полного имени из связанных моделей."""
        if self.role == 'client' and hasattr(self, 'client_profile'):
            return self.client_profile.full_name
        elif self.role == 'owner' and hasattr(self, 'owner_profile'):
            return self.owner_profile.full_name
        elif self.role == 'manager' and hasattr(self, 'manager_profile'):
            return self.manager_profile.full_name
        elif self.role == 'administrator' and hasattr(self, 'admin_profile'):
            return self.admin_profile.full_name
        return self.email


class Client(models.Model):
    """Профиль клиента (арендатора)."""

    PAYMENT_CHOICES = [
        ('card', 'Банковская карта'),
        ('cash', 'Наличные'),
        ('online', 'Онлайн-платеж'),
    ]

    client_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='client_profile')

    full_name = models.CharField(max_length=200, verbose_name='Полное имя')
    passport_data = models.TextField(blank=True, verbose_name='Паспортные данные')

    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        verbose_name='Рейтинг'
    )
    total_rentals = models.IntegerField(default=0, verbose_name='Всего аренд')
    verified = models.BooleanField(default=False, verbose_name='Верифицирован')
    loyalty_points = models.IntegerField(default=0, verbose_name='Баллы лояльности')
    preferred_payment = models.CharField(max_length=30, choices=PAYMENT_CHOICES, blank=True,
                                         verbose_name='Предпочитаемый способ оплаты')

    class Meta:
        db_table = 'clients'
        verbose_name = 'Клиент'
        verbose_name_plural = 'Клиенты'

    def __str__(self):
        return self.full_name


class Owner(models.Model):
    """Профиль владельца инвентаря."""

    owner_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='owner_profile')

    full_name = models.CharField(max_length=200, verbose_name='Полное имя')
    tax_number = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name='ИНН')
    bank_details = models.TextField(blank=True, verbose_name='Банковские реквизиты')

    total_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Общий заработок')
    active_items = models.IntegerField(default=0, verbose_name='Активных предметов')
    verified = models.BooleanField(default=False, verbose_name='Верифицирован')

    class Meta:
        db_table = 'owners'
        verbose_name = 'Владелец'
        verbose_name_plural = 'Владельцы'

    def __str__(self):
        return self.full_name


class OwnerAgreement(models.Model):
    """Соглашение владельца с условиями выплат."""

    agreement_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, related_name='agreements', verbose_name='Владелец')

    owner_percentage = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Процент владельцу'
    )
    store_percentage = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Процент магазину'
    )
    agreement_text = models.TextField(verbose_name='Текст соглашения')
    is_accepted = models.BooleanField(default=False, verbose_name='Принято')
    accepted_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата принятия')

    created_date = models.DateTimeField(default=timezone.now, verbose_name='Дата создания')

    class Meta:
        db_table = 'owner_agreements'
        verbose_name = 'Соглашение владельца'
        verbose_name_plural = 'Соглашения владельцев'
        ordering = ['-created_date']

    def __str__(self):
        return f"Соглашение {self.owner.full_name} - {self.owner_percentage}/{self.store_percentage}%"

    def save(self, *args, **kwargs):
        if self.is_accepted and not self.accepted_date:
            self.accepted_date = timezone.now()
        super().save(*args, **kwargs)


class BankAccount(models.Model):
    """Банковские реквизиты владельца."""

    account_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, related_name='bank_accounts', verbose_name='Владелец')

    bank_name = models.CharField(max_length=200, verbose_name='Название банка')
    account_number = models.CharField(max_length=50, verbose_name='Номер счета')
    bik = models.CharField(max_length=20, blank=True, verbose_name='БИК')
    correspondent_account = models.CharField(max_length=50, blank=True, verbose_name='Корреспондентский счет')
    recipient_name = models.CharField(max_length=200, verbose_name='Получатель')
    inn = models.CharField(max_length=20, blank=True, verbose_name='ИНН получателя')
    kpp = models.CharField(max_length=20, blank=True, verbose_name='КПП')

    is_default = models.BooleanField(default=False, verbose_name='По умолчанию')
    created_date = models.DateTimeField(default=timezone.now, verbose_name='Дата создания')

    class Meta:
        db_table = 'bank_accounts'
        verbose_name = 'Банковский счет'
        verbose_name_plural = 'Банковские счета'
        ordering = ['-is_default', '-created_date']

    def __str__(self):
        return f"{self.bank_name} - {self.account_number}"

    def save(self, *args, **kwargs):
        if self.is_default:
            # Убираем флаг is_default у других счетов этого владельца
            BankAccount.objects.filter(owner=self.owner, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class Manager(models.Model):
    """Профиль менеджера магазина."""

    manager_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='manager_profile')

    full_name = models.CharField(max_length=200, verbose_name='Полное имя')
    phone_work = models.CharField(max_length=15, blank=True, verbose_name='Рабочий телефон')
    email_work = models.EmailField(max_length=255, blank=True, verbose_name='Рабочий email')

    assigned_items = models.IntegerField(default=0, verbose_name='Назначенных предметов')
    active_chats = models.IntegerField(default=0, verbose_name='Активных чатов')

    class Meta:
        db_table = 'managers'
        verbose_name = 'Менеджер'
        verbose_name_plural = 'Менеджеры'

    def __str__(self):
        return self.full_name


class Administrator(models.Model):
    """Профиль администратора."""

    admin_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_profile')

    full_name = models.CharField(max_length=200, verbose_name='Полное имя')
    email_work = models.EmailField(max_length=255, verbose_name='Рабочий email')
    actions_logged = models.IntegerField(default=0, verbose_name='Количество действий')

    class Meta:
        db_table = 'administrators'
        verbose_name = 'Администратор'
        verbose_name_plural = 'Администраторы'

    def __str__(self):
        return self.full_name