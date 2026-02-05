"""
Views для управления арендой - ПОЛНАЯ РЕАЛИЗАЦИЯ.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import Rental, Payment, Contract
from .forms import RentalCreateForm, RentalUpdateForm, RentalBankAccountForm
from inventory.models import Inventory
from users.models import Client, Manager

logger = logging.getLogger('rentals')


@login_required
def rental_list(request):
    """
    Список аренд пользователя с фильтрацией по статусу.
    """
    user = request.user

    # Определяем queryset в зависимости от роли
    if user.role == 'client':
        if not hasattr(user, 'client_profile'):
            messages.error(request, 'Профиль клиента не найден')
            return redirect('users:profile')

        rentals = Rental.objects.filter(
            client=user.client_profile
        ).select_related('inventory', 'inventory__category', 'manager').order_by('-created_date')
        status_choices = Rental.STATUS_CHOICES

    elif user.role == 'manager':
        if not hasattr(user, 'manager_profile'):
            messages.error(request, 'Профиль менеджера не найден')
            return redirect('users:profile')

        rentals = Rental.objects.filter(
            manager=user.manager_profile
        ).select_related('inventory', 'client', 'client__user').order_by('-created_date')
        status_choices = Rental.STATUS_CHOICES

    elif user.role == 'owner':
        if not hasattr(user, 'owner_profile'):
            messages.error(request, 'Профиль владельца не найден')
            return redirect('users:profile')

        rentals = Rental.objects.filter(
            inventory__owner=user.owner_profile
        ).select_related('inventory', 'client', 'client__user', 'manager').order_by('-created_date')
        rentals = rentals.exclude(status='inquiry')
        status_choices = [choice for choice in Rental.STATUS_CHOICES if choice[0] != 'inquiry']

    elif user.role == 'administrator':
        rentals = Rental.objects.all().select_related(
            'inventory', 'client', 'client__user', 'manager'
        ).order_by('-created_date')
        status_choices = Rental.STATUS_CHOICES
    else:
        messages.error(request, 'Недостаточно прав для просмотра аренд')
        return redirect('core:home')

    # Поиск для менеджера
    search_query = request.GET.get('search', '').strip()
    if search_query and user.role == 'manager':
        rentals = rentals.filter(
            Q(client__full_name__icontains=search_query) |
            Q(inventory__name__icontains=search_query)
        )
    
    # Фильтрация по статусу
    status = request.GET.get('status')
    if status:
        rentals = rentals.filter(status=status)

    # Пагинация
    paginator = Paginator(rentals, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'selected_status': status,
        'status_choices': status_choices,
        'search_query': search_query,
    }

    return render(request, 'rentals/rental_list.html', context)


@login_required
def rental_detail(request, pk):
    """
    Детальная информация об аренде.
    """
    rental = get_object_or_404(
        Rental.objects.select_related('inventory', 'client', 'client__user', 'manager'),
        pk=pk
    )

    # Проверка прав доступа
    user = request.user
    has_access = False

    if user.role == 'client' and hasattr(user, 'client_profile'):
        has_access = rental.client == user.client_profile
    elif user.role == 'manager' and hasattr(user, 'manager_profile'):
        has_access = rental.manager == user.manager_profile
    elif user.role == 'owner' and hasattr(user, 'owner_profile'):
        has_access = rental.inventory.owner == user.owner_profile
    elif user.role == 'administrator':
        has_access = True

    if not has_access:
        messages.error(request, 'У вас нет доступа к этой аренде')
        return redirect('rentals:list')

    if user.role == 'owner' and rental.status == 'inquiry':
        messages.info(request, 'Запросы по инвентарю отображаются только в чатах')
        return redirect('rentals:list')

    # Получаем связанные данные
    payments = rental.payments.all().order_by('-payment_date')
    contract = getattr(rental, 'contract', None)

    # Может ли клиент оставить отзыв (аренда завершена и отзыв еще не оставлен)
    can_leave_review = False
    if user.role == 'client' and hasattr(user, 'client_profile') and rental.client == user.client_profile:
        if rental.status == 'completed' and rental.total_price > 0:
            from reviews.models import Review
            has_review = Review.objects.filter(
                rental=rental,
                reviewer=user,
                target_type='inventory'
            ).exists()
            can_leave_review = not has_review

    context = {
        'rental': rental,
        'payments': payments,
        'contract': contract,
        'can_leave_review': can_leave_review,
    }

    return render(request, 'rentals/rental_detail.html', context)


@login_required
def rental_create(request, inventory_id):
    """
    Создание новой заявки на аренду (только для клиентов).
    """
    # Проверка роли
    if request.user.role != 'client':
        messages.error(request, 'Только клиенты могут создавать заявки на аренду')
        return redirect('inventory:detail', pk=inventory_id)

    if not hasattr(request.user, 'client_profile'):
        messages.error(request, 'Профиль клиента не найден')
        return redirect('users:profile')

    client = request.user.client_profile
    inventory = get_object_or_404(Inventory, pk=inventory_id)

    # Проверка доступности
    if inventory.status != 'available':
        messages.error(request, 'Этот инвентарь недоступен для аренды')
        return redirect('inventory:detail', pk=inventory_id)

    if request.method == 'POST':
        form = RentalCreateForm(request.POST, inventory=inventory)

        if form.is_valid():
            try:
                with transaction.atomic():
                    rental = form.save(commit=False)
                    rental.client = client
                    rental.inventory = inventory

                    # Назначаем менеджера (если есть)
                    if inventory.manager:
                        rental.manager = inventory.manager

                    # Рассчитываем стоимость
                    rental_days = (rental.end_date - rental.start_date).days
                    rental.total_price = inventory.price_per_day * rental_days
                    rental.deposit_paid = inventory.deposit_amount

                    rental.status = 'pending'
                    rental.payment_status = 'pending'
                    rental.save()

                    # Создаем платеж
                    Payment.objects.create(
                        rental=rental,
                        amount=rental.total_price + rental.deposit_paid,
                        payment_method='online',
                        status='pending'
                    )

                    logger.info(f'Создана заявка на аренду: {rental.rental_id} для {client.full_name}')
                    messages.success(request, 'Заявка создана. Перейдите к оплате.')
                    return redirect('rentals:pay', pk=rental.rental_id)

            except Exception as e:
                logger.error(f'Ошибка при создании аренды: {str(e)}')
                messages.error(request, 'Произошла ошибка при создании заявки')
    else:
        # Предзаполняем форму
        initial = {
            'start_date': timezone.now().date(),
            'end_date': (timezone.now() + timedelta(days=inventory.min_rental_days)).date(),
        }
        form = RentalCreateForm(initial=initial, inventory=inventory)

    context = {
        'form': form,
        'inventory': inventory,
    }

    return render(request, 'rentals/rental_create.html', context)


@login_required
def rental_confirm(request, pk):
    """
    Подтверждение аренды менеджером. Доступно только после оплаты клиентом.
    """
    rental = get_object_or_404(Rental, pk=pk)

    if request.user.role != 'manager':
        messages.error(request, 'Недостаточно прав')
        return redirect('rentals:detail', pk=pk)

    if not hasattr(request.user, 'manager_profile'):
        messages.error(request, 'Профиль менеджера не найден')
        return redirect('rentals:list')

    if rental.status != 'pending':
        messages.warning(request, 'Эта аренда уже обработана')
        return redirect('rentals:detail', pk=pk)

    if rental.payment_status != 'paid':
        messages.warning(request, 'Подтверждение возможно только после оплаты заявки клиентом.')
        return redirect('rentals:detail', pk=pk)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                rental.status = 'confirmed'
                rental.manager = request.user.manager_profile
                rental.save()

                inventory = rental.inventory
                inventory.status = 'rented'
                inventory.save()

                logger.info(f'Аренда подтверждена: {rental.rental_id} менеджером {request.user.email}')
                messages.success(request, 'Аренда успешно подтверждена')

        except Exception as e:
            logger.error(f'Ошибка при подтверждении аренды: {str(e)}')
            messages.error(request, 'Ошибка при подтверждении')

    return redirect('rentals:detail', pk=pk)


@login_required
def rental_pay(request, pk):
    """
    Условная оплата аренды (имитация онлайн-оплаты).
    После подтверждения оплаты статус платежа и аренды обновляется.
    """
    rental = get_object_or_404(
        Rental.objects.select_related('inventory', 'client', 'client__user'),
        pk=pk
    )

    if request.user.role != 'client' or not hasattr(request.user, 'client_profile'):
        messages.error(request, 'Оплата доступна только клиенту')
        return redirect('rentals:detail', pk=pk)

    if rental.client != request.user.client_profile:
        messages.error(request, 'У вас нет доступа к этой аренде')
        return redirect('rentals:list')

    if rental.payment_status == 'paid':
        messages.info(request, 'Оплата уже произведена')
        return redirect('rentals:detail', pk=pk)

    if rental.status != 'pending':
        messages.warning(request, 'Оплата недоступна для этой аренды')
        return redirect('rentals:detail', pk=pk)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                payment = rental.payments.filter(status='pending').first()
                if payment:
                    payment.status = 'completed'
                    payment.payment_date = timezone.now()
                    payment.save()
                rental.payment_status = 'paid'
                rental.save()

                logger.info(f'Оплата произведена: аренда {rental.rental_id}, клиент {request.user.email}')
                messages.success(request, 'Оплата прошла успешно. Ожидайте подтверждения менеджером.')
                return redirect('rentals:detail', pk=pk)
        except Exception as e:
            logger.error(f'Ошибка при оплате: {str(e)}')
            messages.error(request, 'Ошибка при проведении оплаты')

    total = rental.total_price + (rental.deposit_paid or 0)
    context = {
        'rental': rental,
        'total': total,
    }
    return render(request, 'rentals/rental_pay.html', context)


@login_required
def rental_reject(request, pk):
    """
    Отклонение аренды менеджером.
    """
    rental = get_object_or_404(Rental, pk=pk)

    # Только менеджер может отклонять
    if request.user.role != 'manager':
        messages.error(request, 'Недостаточно прав')
        return redirect('rentals:detail', pk=pk)

    if rental.status != 'pending':
        messages.warning(request, 'Эта аренда уже обработана')
        return redirect('rentals:detail', pk=pk)

    if request.method == 'POST':
        reason = request.POST.get('reason', '')

        try:
            with transaction.atomic():
                rental.status = 'rejected'
                rental.rejection_reason = reason
                rental.save()

                logger.info(f'Аренда отклонена: {rental.rental_id} причина: {reason}')
                messages.info(request, 'Аренда отклонена')

        except Exception as e:
            logger.error(f'Ошибка при отклонении аренды: {str(e)}')
            messages.error(request, 'Ошибка при отклонении')

    return redirect('rentals:detail', pk=pk)


@login_required
def rental_complete(request, pk):
    """
    Завершение аренды (возврат инвентаря) с возможностью выплаты владельцу.
    """
    rental = get_object_or_404(
        Rental.objects.select_related('inventory', 'inventory__owner', 'bank_account'),
        pk=pk
    )

    # Только менеджер может завершать
    if request.user.role != 'manager':
        messages.error(request, 'Недостаточно прав')
        return redirect('rentals:detail', pk=pk)

    if rental.status not in ['confirmed', 'active']:
        messages.warning(request, 'Эта аренда не может быть завершена')
        return redirect('rentals:detail', pk=pk)

    if request.method == 'POST':
        pay_owner = True
        
        try:
            with transaction.atomic():
                rental.status = 'completed'
                rental.actual_return_date = timezone.now()
                rental.save()

                # Возвращаем инвентарь в доступные
                inventory = rental.inventory
                inventory.status = 'available'
                inventory.total_rentals += 1
                inventory.save()

                # Начисляем баллы клиенту
                client = rental.client
                client.total_rentals += 1
                client.loyalty_points += 10  # 10 баллов за аренду
                client.save()

                # Выплата владельцу
                if pay_owner and inventory.bank_account:
                    from users.models import OwnerAgreement
                    # Получаем актуальное соглашение владельца
                    agreement = OwnerAgreement.objects.filter(
                        owner=inventory.owner,
                        is_accepted=True
                    ).order_by('-created_date').first()
                    
                    if agreement:
                        owner_amount = (rental.total_price * agreement.owner_percentage) / 100
                        owner = inventory.owner
                        owner.total_earnings += owner_amount
                        owner.save()
                        
                        logger.info(f'Выплата владельцу: {owner_amount} руб. для {owner.full_name}')
                        messages.success(request, f'Аренда завершена. Владельцу выплачено {owner_amount:.2f} ₽ на счет {inventory.bank_account.bank_name}.')
                    else:
                        messages.warning(request, 'Аренда завершена, но соглашение владельца не найдено')
                elif pay_owner and not inventory.bank_account:
                    messages.warning(request, 'Аренда завершена, но банковский счет не указан в инвентаре')
                else:
                    logger.info(f'Аренда завершена: {rental.rental_id}')
                    messages.success(request, 'Аренда успешно завершена')

        except Exception as e:
            logger.error(f'Ошибка при завершении аренды: {str(e)}')
            messages.error(request, 'Ошибка при завершении')

    return redirect('rentals:detail', pk=pk)


@login_required
def rental_extend(request, pk):
    """
    Продление аренды менеджером (если инвентарь задержан).
    """
    rental = get_object_or_404(Rental, pk=pk)

    # Только менеджер может продлевать
    if request.user.role != 'manager':
        messages.error(request, 'Недостаточно прав')
        return redirect('rentals:detail', pk=pk)

    if rental.status in ['completed', 'cancelled', 'rejected']:
        messages.warning(request, 'Нельзя продлевать завершенную или отмененную аренду')
        return redirect('rentals:detail', pk=pk)

    if request.method == 'POST':
        additional_days = int(request.POST.get('additional_days', 0))
        
        if additional_days <= 0:
            messages.error(request, 'Количество дней должно быть больше 0')
            return redirect('rentals:detail', pk=pk)

        try:
            with transaction.atomic():
                from datetime import timedelta
                # Продлеваем дату окончания
                rental.end_date = rental.end_date + timedelta(days=additional_days)
                
                # Рассчитываем стоимость доплаты
                additional_price = rental.inventory.price_per_day * additional_days
                rental.additional_payment += additional_price
                rental.payment_status = 'delayed'
                rental.save()

                logger.info(f'Аренда продлена на {additional_days} дней: {rental.rental_id}')
                messages.success(request, f'Аренда продлена на {additional_days} дней. Доплата: {additional_price:.2f} ₽')

        except Exception as e:
            logger.error(f'Ошибка при продлении аренды: {str(e)}')
            messages.error(request, 'Ошибка при продлении')

    return redirect('rentals:detail', pk=pk)


@login_required
def rental_cancel(request, pk):
    """
    Отмена аренды клиентом.
    """
    rental = get_object_or_404(Rental, pk=pk)

    # Проверка прав
    if request.user.role == 'client':
        if not hasattr(request.user, 'client_profile') or rental.client != request.user.client_profile:
            messages.error(request, 'У вас нет прав на отмену этой аренды')
            return redirect('rentals:detail', pk=pk)
    elif request.user.role not in ['manager', 'administrator']:
        messages.error(request, 'Недостаточно прав')
        return redirect('rentals:detail', pk=pk)

    # Можно отменить только pending или confirmed
    if rental.status not in ['pending', 'confirmed']:
        messages.warning(request, 'Эту аренду нельзя отменить')
        return redirect('rentals:detail', pk=pk)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                rental.status = 'cancelled'
                rental.save()

                # Если инвентарь был заблокирован, освобождаем
                if rental.inventory.status == 'rented':
                    rental.inventory.status = 'available'
                    rental.inventory.save()

                logger.info(f'Аренда отменена: {rental.rental_id} пользователем {request.user.email}')
                messages.success(request, 'Аренда отменена')

        except Exception as e:
            logger.error(f'Ошибка при отмене аренды: {str(e)}')
            messages.error(request, 'Ошибка при отмене')

    return redirect('rentals:detail', pk=pk)