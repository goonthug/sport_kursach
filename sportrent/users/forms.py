"""
Формы для регистрации и управления пользователями.
"""

import re
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from .models import User, Client, Owner, Manager


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
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+7 (999) 123-45-67'
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

        if phone:
            # Убираем все символы кроме цифр и +
            cleaned_phone = re.sub(r'[^\d+]', '', phone)

            # Проверка формата (должно быть 11-12 цифр)
            if not re.match(r'^\+?[0-9]{10,12}$', cleaned_phone):
                raise ValidationError('Введите корректный номер телефона (например, +79991234567)')

            return cleaned_phone

        return phone

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
                Owner.objects.create(
                    user=user,
                    full_name=full_name
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
