"""
Views для управления пользователями.
"""

import logging
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction

from .forms import UserRegistrationForm, UserLoginForm, UserUpdateForm, ClientProfileForm, OwnerProfileForm
from .models import User

logger = logging.getLogger('users')


def register(request):
    """
    Регистрация нового пользователя с созданием соответствующего профиля.
    """
    if request.user.is_authenticated:
        return redirect('core:home')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save()
                    logger.info(f'Новый пользователь зарегистрирован: {user.email}, роль: {user.role}')

                    # Автоматический вход после регистрации
                    login(request, user)
                    messages.success(request, f'Добро пожаловать, {user.get_full_name()}! Регистрация прошла успешно.')
                    return redirect('core:home')

            except Exception as e:
                logger.error(f'Ошибка при регистрации пользователя: {str(e)}')
                messages.error(request, 'Произошла ошибка при регистрации. Пожалуйста, попробуйте снова.')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{form.fields.get(field).label if field != "__all__" else ""}: {error}')
    else:
        form = UserRegistrationForm()

    return render(request, 'users/register.html', {'form': form})


def user_login(request):
    """
    Вход пользователя в систему.
    """
    if request.user.is_authenticated:
        return redirect('core:home')

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)

        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            user = authenticate(request, username=email, password=password)

            if user is not None:
                if user.status == 'blocked':
                    messages.error(request, 'Ваш аккаунт заблокирован. Обратитесь в поддержку.')
                    logger.warning(f'Попытка входа заблокированного пользователя: {email}')
                else:
                    login(request, user)
                    logger.info(f'Пользователь вошел в систему: {user.email}')
                    messages.success(request, f'Добро пожаловать, {user.get_full_name()}!')

                    # Перенаправление в зависимости от роли
                    next_url = request.GET.get('next')
                    if next_url:
                        return redirect(next_url)
                    elif user.role in ['manager', 'administrator']:
                        return redirect('custom_admin:dashboard')
                    else:
                        return redirect('core:home')
            else:
                messages.error(request, 'Неверный email или пароль.')
        else:
            messages.error(request, 'Неверный email или пароль.')
    else:
        form = UserLoginForm()

    return render(request, 'users/login.html', {'form': form})


@login_required
def user_logout(request):
    """
    Выход пользователя из системы.
    """
    user_email = request.user.email
    logout(request)
    logger.info(f'Пользователь вышел из системы: {user_email}')
    messages.info(request, 'Вы успешно вышли из системы.')
    return redirect('core:home')


@login_required
def profile(request):
    """
    Просмотр и редактирование профиля пользователя.
    """
    user = request.user
    profile_form = None

    # Определяем форму профиля в зависимости от роли
    if user.role == 'client' and hasattr(user, 'client_profile'):
        profile_model = user.client_profile
        ProfileFormClass = ClientProfileForm
    elif user.role == 'owner' and hasattr(user, 'owner_profile'):
        profile_model = user.owner_profile
        ProfileFormClass = OwnerProfileForm
    else:
        profile_model = None
        ProfileFormClass = None

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, request.FILES, instance=user)

        if ProfileFormClass and profile_model:
            profile_form = ProfileFormClass(request.POST, instance=profile_model)

        if user_form.is_valid() and (profile_form is None or profile_form.is_valid()):
            try:
                with transaction.atomic():
                    user_form.save()
                    if profile_form:
                        profile_form.save()

                    logger.info(f'Профиль обновлен: {user.email}')
                    messages.success(request, 'Профиль успешно обновлен.')
                    return redirect('users:profile')
            except Exception as e:
                logger.error(f'Ошибка при обновлении профиля: {str(e)}')
                messages.error(request, 'Произошла ошибка при сохранении.')
    else:
        user_form = UserUpdateForm(instance=user)
        if ProfileFormClass and profile_model:
            profile_form = ProfileFormClass(instance=profile_model)

    # Получаем статистику пользователя
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
    }

    # Добавляем статистику в зависимости от роли
    if user.role == 'client' and hasattr(user, 'client_profile'):
        from rentals.models import Rental
        context['total_rentals'] = Rental.objects.filter(client=user.client_profile).count()
        context['active_rentals'] = Rental.objects.filter(client=user.client_profile, status='active').count()

    elif user.role == 'owner' and hasattr(user, 'owner_profile'):
        from inventory.models import Inventory
        context['total_items'] = Inventory.objects.filter(owner=user.owner_profile).count()
        context['active_items'] = Inventory.objects.filter(owner=user.owner_profile, status='available').count()

    return render(request, 'users/profile.html', context)