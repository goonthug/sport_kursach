"""
Views для системы чата - ПОЛНАЯ РЕАЛИЗАЦИЯ.
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Max
from datetime import timedelta
from django.utils import timezone

from .models import ChatMessage
from .forms import ChatMessageForm
from rentals.models import Rental
from users.models import User

logger = logging.getLogger('chat')


@login_required
def chat_list(request):
    """
    Список чатов пользователя (сгруппированных по арендам).
    """
    user = request.user

    # Получаем все чаты где пользователь участвует
    chats_qs = ChatMessage.objects.filter(
        Q(sender=user) | Q(receiver=user)
    ).select_related('rental', 'rental__inventory', 'sender', 'receiver').order_by('rental', '-sent_date')

    # Группируем по rental_id и берем последнее сообщение
    chat_groups = {}
    for message in chats_qs:
        rental_id = str(message.rental.rental_id)
        if rental_id not in chat_groups:
            # Определяем собеседника
            other_user = message.receiver if message.sender == user else message.sender

            # Подсчитываем непрочитанные
            unread_count = ChatMessage.objects.filter(
                rental=message.rental,
                receiver=user,
                is_read=False
            ).count()

            chat_groups[rental_id] = {
                'rental': message.rental,
                'last_message': message,
                'other_user': other_user,
                'unread_count': unread_count,
            }

    context = {
        'chat_groups': chat_groups.values(),
    }

    return render(request, 'chat/chat_list.html', context)


@login_required
def chat_detail(request, rental_id):
    """
    Детальный просмотр чата по конкретной аренде.
    """
    rental = get_object_or_404(Rental, pk=rental_id)
    user = request.user

    # Проверка прав доступа
    has_access = False
    other_user = None

    if user.role == 'client' and hasattr(user, 'client_profile'):
        if rental.client == user.client_profile:
            has_access = True
            other_user = rental.manager.user if rental.manager else None

    elif user.role == 'manager' and hasattr(user, 'manager_profile'):
        if rental.manager == user.manager_profile:
            has_access = True
            other_user = rental.client.user

    elif user.role == 'administrator':
        has_access = True
        # Админ может видеть все

    if not has_access:
        messages.error(request, 'У вас нет доступа к этому чату')
        return redirect('chat:list')

    # Получаем все сообщения
    messages_qs = ChatMessage.objects.filter(
        rental=rental
    ).select_related('sender', 'receiver').order_by('sent_date')

    # Отмечаем сообщения как прочитанные
    ChatMessage.objects.filter(
        rental=rental,
        receiver=user,
        is_read=False
    ).update(is_read=True, read_date=timezone.now())

    # Обработка отправки нового сообщения
    if request.method == 'POST':
        form = ChatMessageForm(request.POST, request.FILES)
        if form.is_valid():
            if not other_user:
                messages.error(request, 'Невозможно отправить сообщение - получатель не определен')
            else:
                message = form.save(commit=False)
                message.rental = rental
                message.sender = user
                message.receiver = other_user
                message.save()

                logger.info(f'Сообщение отправлено в чате аренды {rental_id}: {user.email} -> {other_user.email}')
                return redirect('chat:detail', rental_id=rental_id)
    else:
        form = ChatMessageForm()

    context = {
        'rental': rental,
        'messages': messages_qs,
        'form': form,
        'other_user': other_user,
    }

    return render(request, 'chat/chat_detail.html', context)


@login_required
def start_chat(request, rental_id):
    """
    Начать чат по аренде (создает первое сообщение если чата нет).
    """
    rental = get_object_or_404(Rental, pk=rental_id)
    user = request.user

    # Проверка прав
    has_access = False
    if user.role == 'client' and hasattr(user, 'client_profile'):
        has_access = rental.client == user.client_profile
    elif user.role == 'manager' and hasattr(user, 'manager_profile'):
        has_access = rental.manager == user.manager_profile

    if not has_access:
        messages.error(request, 'У вас нет доступа к этому чату')
        return redirect('rentals:detail', pk=rental_id)

    # Перенаправляем на страницу чата
    return redirect('chat:detail', rental_id=rental_id)


@login_required
def start_chat_by_inventory(request, inventory_id):
    """
    Начать чат с менеджером по инвентарю (без бронирования).
    Создает аренду со статусом inquiry для связи чата с инвентарем.
    """
    from inventory.models import Inventory

    if request.user.role != 'client' or not hasattr(request.user, 'client_profile'):
        messages.error(request, 'Чат доступен только клиентам')
        return redirect('inventory:detail', pk=inventory_id)

    inventory = get_object_or_404(
        Inventory.objects.select_related('manager'),
        pk=inventory_id,
        status='available'
    )
    if not inventory.manager:
        messages.error(request, 'По этому инвентарю пока нельзя написать. Обратитесь в поддержку.')
        return redirect('inventory:detail', pk=inventory_id)

    client = request.user.client_profile
    rental = Rental.objects.filter(
        inventory=inventory,
        client=client,
        status='inquiry'
    ).first()

    if not rental:
        start = timezone.now()
        end = start + timedelta(days=1)
        rental = Rental.objects.create(
            inventory=inventory,
            client=client,
            manager=inventory.manager,
            status='inquiry',
            start_date=start,
            end_date=end,
            total_price=0,
            deposit_paid=0,
            payment_status='pending',
        )
        logger.info(f'Создан чат-запрос по инвентарю {inventory.name} для клиента {client.full_name}')

    return redirect('chat:detail', rental_id=rental.rental_id)