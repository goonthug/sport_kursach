"""
Формы для регистрации и управления пользователями.
"""

import re
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator, MinValueValidator, MaxValueValidator
from django.utils import timezone
from .models import User, Client, Owner, Manager, OwnerAgreement, BankAccount


class UserRegistrationForm(UserCreationForm):
    """Форма регистрации нового пользователя с полной валидацией."""

    email = forms.EmailField(
        label='Email',
        validators=[EmailValidator(message='Введите корректный email адрес')],
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'example@mail.com'
        })
    )

    phone = forms.CharField(
        label='Телефон',
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+7 (999) 123-45-67',
            'maxlength': '18',  # +7 (999) 123-45-67
        })
    )

    role = forms.ChoiceField(
        label='Роль',
        choices=[('client', 'Клиент (арендатор)'), ('owner', 'Владелец инвентаря')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    full_name = forms.CharField(
        label='Полное имя',
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Иванов Иван Иванович'
        })
    )

    password1 = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Минимум 8 символов'
        }),
        help_text='Пароль должен содержать минимум 8 символов, включая заглавную букву, цифру и спецсимвол'
    )

    password2 = forms.CharField(
        label='Подтверждение пароля',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Повторите пароль'
        })
    )

    # Поля для владельца
    owner_percentage = forms.IntegerField(
        label='Процент владельцу',
        required=False,
        min_value=0,
        max_value=100,
        initial=70,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '70'
        })
    )

    store_percentage = forms.IntegerField(
        label='Процент магазину',
        required=False,
        min_value=0,
        max_value=100,
        initial=30,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '30'
        })
    )

    agreement_accepted = forms.BooleanField(
        label='Принимаю условия соглашения',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    # Банковские реквизиты
    bank_name = forms.CharField(
        label='Название банка',
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Например: Сбербанк'
        })
    )

    account_number = forms.CharField(
        label='Номер счета',
        required=False,
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '40702810100000000000'
        })
    )

    bik = forms.CharField(
        label='БИК',
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '044525225'
        })
    )

    recipient_name = forms.CharField(
        label='Получатель',
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Иванов Иван Иванович'
        })
    )

    class Meta:
        model = User
        fields = ('email', 'phone', 'role', 'password1', 'password2')

    def clean_email(self):
        """Проверка уникальности и корректности email."""
        email = self.cleaned_data.get('email', '').strip().lower()

        # Проверка формата email
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            raise ValidationError('Введите корректный email адрес (example@mail.com)')

        # Проверка уникальности
        if User.objects.filter(email=email).exists():
            raise ValidationError('Пользователь с таким email уже существует.')

        return email

    def clean_phone(self):
        """Валидация телефона."""
        phone = self.cleaned_data.get('phone', '').strip()

        if not phone:
            raise ValidationError('Телефон обязателен для заполнения')

        # Убираем все символы кроме цифр и +
        cleaned_phone = re.sub(r'[^\d+]', '', phone)

        # Ожидаем формат российского номера +7XXXXXXXXXX (11 цифр)
        if not re.match(r'^\+7[0-9]{10}$', cleaned_phone):
            raise ValidationError('Введите номер в формате +7XXXXXXXXXX')

        return cleaned_phone

    def clean_full_name(self):
        """Валидация полного имени."""
        full_name = self.cleaned_data.get('full_name', '').strip()

        if len(full_name) < 3:
            raise ValidationError('Имя должно содержать минимум 3 символа')

        # Проверка что имя содержит только буквы, пробелы и дефисы
        if not re.match(r'^[а-яёА-ЯЁa-zA-Z\s\-]+$', full_name):
            raise ValidationError('Имя должно содержать только буквы')

        return full_name

    def clean_password1(self):
        """Усиленная валидация пароля."""
        password = self.cleaned_data.get('password1')

        if len(password) < 8:
            raise ValidationError('Пароль должен содержать минимум 8 символов')

        # Проверка наличия заглавной буквы
        if not re.search(r'[A-ZА-Я]', password):
            raise ValidationError('Пароль должен содержать хотя бы одну заглавную букву')

        # Проверка наличия строчной буквы
        if not re.search(r'[a-zа-я]', password):
            raise ValidationError('Пароль должен содержать хотя бы одну строчную букву')

        # Проверка наличия цифры
        if not re.search(r'\d', password):
            raise ValidationError('Пароль должен содержать хотя бы одну цифру')

        # Проверка наличия спецсимвола
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password):
            raise ValidationError('Пароль должен содержать хотя бы один спецсимвол (!@#$%^&* и т.д.)')

        return password

    def clean(self):
        """Валидация полей для владельца."""
        cleaned_data = super().clean()
        role = cleaned_data.get('role')

        if role == 'owner':
            # Проверка соглашения
            agreement_accepted = cleaned_data.get('agreement_accepted')
            owner_percentage = cleaned_data.get('owner_percentage', 0)
            store_percentage = cleaned_data.get('store_percentage', 0)

            if not agreement_accepted:
                raise ValidationError('Необходимо принять условия соглашения')

            if owner_percentage + store_percentage != 100:
                raise ValidationError('Сумма процентов владельца и магазина должна равняться 100%')

            # Проверка банковских реквизитов
            bank_name = cleaned_data.get('bank_name', '').strip()
            account_number = cleaned_data.get('account_number', '').strip()
            recipient_name = cleaned_data.get('recipient_name', '').strip()

            if not bank_name or not account_number or not recipient_name:
                raise ValidationError('Необходимо заполнить все поля банковских реквизитов')

        return cleaned_data

    def save(self, commit=True):
        """Сохранение пользователя и создание профиля."""
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.phone = self.cleaned_data.get('phone')
        user.role = self.cleaned_data['role']

        if commit:
            user.save()

            # Создаем профиль в зависимости от роли
            full_name = self.cleaned_data['full_name']

            if user.role == 'client':
                Client.objects.create(
                    user=user,
                    full_name=full_name
                )
            elif user.role == 'owner':
                owner = Owner.objects.create(
                    user=user,
                    full_name=full_name
                )

                # Создаем соглашение
                owner_percentage = self.cleaned_data.get('owner_percentage', 70)
                store_percentage = self.cleaned_data.get('store_percentage', 30)
                agreement_text = f"Соглашение о выплатах: {owner_percentage}% владельцу, {store_percentage}% магазину"

                OwnerAgreement.objects.create(
                    owner=owner,
                    owner_percentage=owner_percentage,
                    store_percentage=store_percentage,
                    agreement_text=agreement_text,
                    is_accepted=True,
                    accepted_date=timezone.now()
                )

                # Создаем банковский счет
                BankAccount.objects.create(
                    owner=owner,
                    bank_name=self.cleaned_data.get('bank_name', ''),
                    account_number=self.cleaned_data.get('account_number', ''),
                    bik=self.cleaned_data.get('bik', ''),
                    recipient_name=self.cleaned_data.get('recipient_name', ''),
                    is_default=True
                )

        return user


class UserLoginForm(AuthenticationForm):
    """Форма входа в систему."""

    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'example@mail.com',
            'autofocus': True
        })
    )

    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите пароль'
        })
    )


class ClientProfileForm(forms.ModelForm):
    """Форма редактирования профиля клиента. На сайте только онлайн-оплата."""

    class Meta:
        model = Client
        fields = ['full_name', 'passport_data']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'passport_data': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'full_name': 'Полное имя',
            'passport_data': 'Паспортные данные',
        }


class OwnerProfileForm(forms.ModelForm):
    """Форма редактирования профиля владельца."""

    class Meta:
        model = Owner
        fields = ['full_name', 'tax_number', 'bank_details']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'tax_number': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'full_name': 'Полное имя',
            'tax_number': 'ИНН',
            'bank_details': 'Банковские реквизиты',
        }


class UserUpdateForm(forms.ModelForm):
    """Форма обновления данных пользователя."""

    class Meta:
        model = User
        fields = ['email', 'phone', 'avatar_url']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'avatar_url': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'email': 'Email',
            'phone': 'Телефон',
            'avatar_url': 'Аватар',
        }


class BankAccountForm(forms.ModelForm):
    """Форма для добавления/редактирования банковского счета."""

    class Meta:
        model = BankAccount
        fields = ['bank_name', 'account_number', 'bik', 'correspondent_account', 'recipient_name', 'inn', 'kpp', 'is_default']
        widgets = {
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'bik': forms.TextInput(attrs={'class': 'form-control'}),
            'correspondent_account': forms.TextInput(attrs={'class': 'form-control'}),
            'recipient_name': forms.TextInput(attrs={'class': 'form-control'}),
            'inn': forms.TextInput(attrs={'class': 'form-control'}),
            'kpp': forms.TextInput(attrs={'class': 'form-control'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'bank_name': 'Название банка',
            'account_number': 'Номер счета',
            'bik': 'БИК',
            'correspondent_account': 'Корреспондентский счет',
            'recipient_name': 'Получатель',
            'inn': 'ИНН получателя',
            'kpp': 'КПП',
            'is_default': 'По умолчанию',
        }
