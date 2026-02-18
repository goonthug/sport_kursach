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
            'placeholder': '917 922 54 66',
            'maxlength': '15',
            'id': 'id_phone',
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

    # Паспортные данные для клиента
    passport_series = forms.CharField(
        label='Серия паспорта',
        required=False,
        max_length=4,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '0000',
            'id': 'id_passport_series',
            'maxlength': '4',
        })
    )

    passport_number = forms.CharField(
        label='Номер паспорта',
        required=False,
        max_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '000000',
            'id': 'id_passport_number',
            'maxlength': '6',
        })
    )

    passport_issue_date = forms.DateField(
        label='Дата выдачи паспорта',
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'id': 'id_passport_issue_date',
        })
    )

    passport_department_code = forms.CharField(
        label='Код подразделения',
        required=False,
        max_length=7,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '000-000',
            'id': 'id_passport_department_code',
            'maxlength': '7',
        })
    )

    # Поля для владельца
    agreement_accepted = forms.BooleanField(
        label='Принимаю условия соглашения (70% владельцу, 30% магазину)',
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
        max_length=19,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '2222-2222-2222-2222',
            'id': 'id_account_number_reg',
        })
    )

    recipient_name = forms.CharField(
        label='Получатель',
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Иванов Иван Иванович',
            'id': 'id_recipient_name_reg',
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

        # Убираем все символы кроме цифр
        cleaned_phone = re.sub(r'[^\d]', '', phone)

        # Ожидаем формат российского номера 10 цифр (без +7)
        if len(cleaned_phone) != 10 or not cleaned_phone.isdigit():
            raise ValidationError('Введите 10 цифр номера телефона (например: 9179225466)')

        # Возвращаем в формате +7XXXXXXXXXX
        return '+7' + cleaned_phone

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

    def clean_passport_series(self):
        """Серия паспорта: только 4 цифры."""
        series = (self.cleaned_data.get('passport_series') or '').strip()
        role = self.cleaned_data.get('role')

        if role == 'client':
            if not series:
                raise ValidationError('Серия паспорта обязательна для клиента')
            if not series.isdigit() or len(series) != 4:
                raise ValidationError('Серия паспорта должна содержать 4 цифры')
        elif not series:
            return series

        if series and (not series.isdigit() or len(series) != 4):
            raise ValidationError('Серия паспорта должна содержать 4 цифры')

        return series

    def clean_passport_number(self):
        """Номер паспорта: только 6 цифр."""
        number = (self.cleaned_data.get('passport_number') or '').strip()
        role = self.cleaned_data.get('role')

        if role == 'client':
            if not number:
                raise ValidationError('Номер паспорта обязателен для клиента')
            if not number.isdigit() or len(number) != 6:
                raise ValidationError('Номер паспорта должен содержать 6 цифр')
        elif not number:
            return number

        if number and (not number.isdigit() or len(number) != 6):
            raise ValidationError('Номер паспорта должен содержать 6 цифр')

        return number

    def clean_passport_department_code(self):
        """Код подразделения: формат 000-000, только цифры."""
        code = (self.cleaned_data.get('passport_department_code') or '').strip()
        role = self.cleaned_data.get('role')

        if role == 'client':
            if not code:
                raise ValidationError('Код подразделения обязателен для клиента')

        if not code:
            return code

        # Убираем все, кроме цифр
        digits_only = re.sub(r'[^\d]', '', code)
        if len(digits_only) != 6:
            raise ValidationError('Код подразделения должен содержать 6 цифр (например: 123-456)')

        # Возвращаем в формате 000-000
        return f'{digits_only[:3]}-{digits_only[3:]}'

    def clean_passport_issue_date(self):
        """Дата выдачи паспорта: обязательна для клиента и не может быть в будущем."""
        issue_date = self.cleaned_data.get('passport_issue_date')
        role = self.cleaned_data.get('role')

        if role == 'client' and not issue_date:
            raise ValidationError('Дата выдачи паспорта обязательна для клиента')

        if issue_date and issue_date > timezone.now().date():
            raise ValidationError('Дата выдачи паспорта не может быть в будущем')

        return issue_date

    def clean_account_number(self):
        """Валидация номера счета."""
        account_number = self.cleaned_data.get('account_number', '').strip()
        role = self.cleaned_data.get('role')
        
        if role == 'owner':
            if not account_number:
                raise ValidationError('Номер счета обязателен для владельца')
            
            # Убираем дефисы и проверяем что только цифры
            cleaned = re.sub(r'[^\d]', '', account_number)
            if len(cleaned) != 16:
                raise ValidationError('Номер счета должен содержать 16 цифр в формате 2222-2222-2222-2222')
            
            # Возвращаем в формате с дефисами
            return f"{cleaned[:4]}-{cleaned[4:8]}-{cleaned[8:12]}-{cleaned[12:16]}"
        
        return account_number

    def clean_recipient_name(self):
        """Валидация имени получателя - только буквы."""
        recipient_name = self.cleaned_data.get('recipient_name', '').strip()
        role = self.cleaned_data.get('role')
        
        if role == 'owner':
            if not recipient_name:
                raise ValidationError('Имя получателя обязательно для владельца')
            
            # Проверяем что только буквы, пробелы и дефисы
            if not re.match(r'^[а-яёА-ЯЁa-zA-Z\s\-]+$', recipient_name):
                raise ValidationError('Имя получателя должно содержать только буквы')
        
        return recipient_name

    def clean(self):
        """Валидация полей для владельца и клиента."""
        cleaned_data = super().clean()
        role = cleaned_data.get('role')

        if role == 'owner':
            # Проверка соглашения
            agreement_accepted = cleaned_data.get('agreement_accepted')

            if not agreement_accepted:
                raise ValidationError('Необходимо принять условия соглашения')

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
                    full_name=full_name,
                    passport_series=self.cleaned_data.get('passport_series') or None,
                    passport_number=self.cleaned_data.get('passport_number') or None,
                    passport_issue_date=self.cleaned_data.get('passport_issue_date'),
                    passport_department_code=self.cleaned_data.get('passport_department_code') or None,
                )
            elif user.role == 'owner':
                owner = Owner.objects.create(
                    user=user,
                    full_name=full_name
                )

                # Создаем соглашение с фиксированными процентами 70/30
                OwnerAgreement.objects.create(
                    owner=owner,
                    owner_percentage=70,
                    store_percentage=30,
                    agreement_text="Соглашение о выплатах: 70% владельцу, 30% магазину",
                    is_accepted=True,
                    accepted_date=timezone.now()
                )

                # Создаем банковский счет
                BankAccount.objects.create(
                    owner=owner,
                    bank_name=self.cleaned_data.get('bank_name', ''),
                    account_number=self.cleaned_data.get('account_number', ''),
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
    """Форма редактирования профиля клиента. На сайте только онлайн-оплата. Без паспортных данных."""

    class Meta:
        model = Client
        fields = ['full_name']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'full_name': 'Полное имя',
        }


class OwnerProfileForm(forms.ModelForm):
    """Форма редактирования профиля владельца."""

    class Meta:
        model = Owner
        fields = ['full_name']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'full_name': 'Полное имя',
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
        fields = ['bank_name', 'account_number', 'recipient_name', 'is_default']
        widgets = {
            'bank_name': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_bank_name_profile'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '2222-2222-2222-2222', 'id': 'id_account_number_profile'}),
            'recipient_name': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_recipient_name_profile'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'bank_name': 'Название банка',
            'account_number': 'Номер счета',
            'recipient_name': 'Получатель',
            'is_default': 'По умолчанию',
        }

    def clean_account_number(self):
        """Валидация номера счета."""
        account_number = self.cleaned_data.get('account_number', '').strip()
        
        if not account_number:
            raise ValidationError('Номер счета обязателен')
        
        # Убираем дефисы и проверяем что только цифры
        cleaned = re.sub(r'[^\d]', '', account_number)
        if len(cleaned) != 16:
            raise ValidationError('Номер счета должен содержать 16 цифр в формате 2222-2222-2222-2222')
        
        # Возвращаем в формате с дефисами
        return f"{cleaned[:4]}-{cleaned[4:8]}-{cleaned[8:12]}-{cleaned[12:16]}"

    def clean_recipient_name(self):
        """Валидация имени получателя - только буквы."""
        recipient_name = self.cleaned_data.get('recipient_name', '').strip()
        
        if not recipient_name:
            raise ValidationError('Имя получателя обязательно')
        
        # Проверяем что только буквы, пробелы и дефисы
        if not re.match(r'^[а-яёА-ЯЁa-zA-Z\s\-]+$', recipient_name):
            raise ValidationError('Имя получателя должно содержать только буквы')
        
        return recipient_name
