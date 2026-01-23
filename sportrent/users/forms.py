"""
Формы для регистрации и управления пользователями.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from .models import User, Client, Owner, Manager


class UserRegistrationForm(UserCreationForm):
    """Форма регистрации нового пользователя."""

    email = forms.EmailField(
        label='Email',
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
        })
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
        """Проверка уникальности email."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('Пользователь с таким email уже существует.')
        return email

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
    """Форма редактирования профиля клиента."""

    class Meta:
        model = Client
        fields = ['full_name', 'passport_data', 'preferred_payment']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'passport_data': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'preferred_payment': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'full_name': 'Полное имя',
            'passport_data': 'Паспортные данные',
            'preferred_payment': 'Предпочитаемый способ оплаты',
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