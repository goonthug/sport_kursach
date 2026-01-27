"""
Views для управления инвентарем.
Включает список, детали, создание, редактирование и удаление.
"""

import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Avg
from django.db import transaction

from .models import Inventory, SportCategory, InventoryPhoto
from .forms import InventoryForm, InventoryPhotoFormSet
from users.models import Owner

logger = logging.getLogger('inventory')


def inventory_list(request):
    """
    Список инвентаря с фильтрацией, поиском и сортировкой.
    """
    # Базовый queryset только для доступного инвентаря
    inventory_qs = Inventory.objects.filter(
        status='available'
    ).select_related('category', 'owner', 'owner__user').prefetch_related('photos')

    # Поиск
    search_query = request.GET.get('search', '').strip()
    if search_query:
        inventory_qs = inventory_qs.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(brand__icontains=search_query) |
            Q(model__icontains=search_query)
        )
        logger.info(f'Поиск инвентаря: {search_query}')

    # Фильтрация по категории
    category_id = request.GET.get('category')
    if category_id:
        inventory_qs = inventory_qs.filter(category_id=category_id)

    # Фильтрация по состоянию
    condition = request.GET.get('condition')
    if condition:
        inventory_qs = inventory_qs.filter(condition=condition)

    # Фильтрация по цене
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        inventory_qs = inventory_qs.filter(price_per_day__gte=min_price)
    if max_price:
        inventory_qs = inventory_qs.filter(price_per_day__lte=max_price)

    # Сортировка
    sort_by = request.GET.get('sort', '-added_date')
    valid_sorts = {
        'price_asc': 'price_per_day',
        'price_desc': '-price_per_day',
        'name': 'name',
        'newest': '-added_date',
        'rating': '-avg_rating',
    }

    if sort_by in valid_sorts:
        inventory_qs = inventory_qs.order_by(valid_sorts[sort_by])

    # Пагинация
    paginator = Paginator(inventory_qs, 12)  # 12 items per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Получаем категории для фильтра
    categories = SportCategory.objects.all()

    context = {
        'page_obj': page_obj,
        'categories': categories,
        'search_query': search_query,
        'selected_category': category_id,
        'selected_condition': condition,
        'min_price': min_price,
        'max_price': max_price,
        'current_sort': sort_by,
        'total_count': paginator.count,
    }

    return render(request, 'inventory/inventory_list.html', context)


def inventory_detail(request, pk):
    """
    Детальная страница инвентаря с отзывами.
    """
    inventory = get_object_or_404(
        Inventory.objects.select_related('category', 'owner', 'owner__user', 'manager'),
        pk=pk
    )

    # Получаем отзывы напрямую через Review модель
    from reviews.models import Review
    reviews = Review.objects.filter(
        reviewed_id=inventory.inventory_id,
        target_type='inventory',
        status='published'
    ).select_related('reviewer', 'rental').order_by('-review_date')[:10]

    context = {
        'inventory': inventory,
        'reviews': reviews,
    }

    return render(request, 'inventory/inventory_detail.html', context)


@login_required
def inventory_create(request):
    """
    Создание нового инвентаря (только для владельцев).
    """
    # Проверка роли пользователя
    if request.user.role != 'owner':
        messages.error(request, 'Только владельцы могут добавлять инвентарь.')
        return redirect('core:home')

    if not hasattr(request.user, 'owner_profile'):
        messages.error(request, 'Профиль владельца не найден.')
        return redirect('users:profile')

    owner = request.user.owner_profile

    if request.method == 'POST':
        form = InventoryForm(request.POST, request.FILES)
        photo_formset = InventoryPhotoFormSet(request.POST, request.FILES)

        if form.is_valid() and photo_formset.is_valid():
            try:
                with transaction.atomic():
                    inventory = form.save(commit=False)
                    inventory.owner = owner
                    inventory.status = 'pending'  # Ожидает проверки менеджером
                    inventory.save()

                    # Сохраняем фотографии
                    for photo_form in photo_formset:
                        if photo_form.cleaned_data and not photo_form.cleaned_data.get('DELETE'):
                            photo = photo_form.save(commit=False)
                            photo.inventory = inventory
                            photo.save()

                    logger.info(f'Новый инвентарь создан: {inventory.name} by {owner.full_name}')
                    messages.success(request, 'Инвентарь успешно добавлен и отправлен на модерацию.')
                    return redirect('inventory:detail', pk=inventory.inventory_id)

            except Exception as e:
                logger.error(f'Ошибка при создании инвентаря: {str(e)}')
                messages.error(request, 'Произошла ошибка при сохранении.')
    else:
        form = InventoryForm()
        photo_formset = InventoryPhotoFormSet(queryset=InventoryPhoto.objects.none())

    context = {
        'form': form,
        'photo_formset': photo_formset,
        'is_create': True,
    }

    return render(request, 'inventory/inventory_form.html', context)


@login_required
def inventory_update(request, pk):
    """
    Редактирование инвентаря (только для владельца или менеджера).
    """
    inventory = get_object_or_404(Inventory, pk=pk)

    # Проверка прав доступа
    if request.user.role == 'owner':
        if not hasattr(request.user, 'owner_profile') or inventory.owner != request.user.owner_profile:
            messages.error(request, 'У вас нет прав на редактирование этого инвентаря.')
            return redirect('inventory:detail', pk=pk)
    elif request.user.role not in ['manager', 'administrator']:
        messages.error(request, 'У вас нет прав на редактирование.')
        return redirect('inventory:detail', pk=pk)

    if request.method == 'POST':
        form = InventoryForm(request.POST, request.FILES, instance=inventory)
        photo_formset = InventoryPhotoFormSet(request.POST, request.FILES, queryset=inventory.photos.all())

        if form.is_valid() and photo_formset.is_valid():
            try:
                with transaction.atomic():
                    inventory = form.save()

                    # Обработка фотографий
                    for photo_form in photo_formset:
                        if photo_form.cleaned_data:
                            if photo_form.cleaned_data.get('DELETE'):
                                if photo_form.instance.pk:
                                    photo_form.instance.delete()
                            else:
                                photo = photo_form.save(commit=False)
                                photo.inventory = inventory
                                photo.save()

                    logger.info(f'Инвентарь обновлен: {inventory.name}')
                    messages.success(request, 'Инвентарь успешно обновлен.')
                    return redirect('inventory:detail', pk=inventory.inventory_id)

            except Exception as e:
                logger.error(f'Ошибка при обновлении инвентаря: {str(e)}')
                messages.error(request, 'Произошла ошибка при сохранении.')
    else:
        form = InventoryForm(instance=inventory)
        photo_formset = InventoryPhotoFormSet(queryset=inventory.photos.all())

    context = {
        'form': form,
        'photo_formset': photo_formset,
        'inventory': inventory,
        'is_create': False,
    }

    return render(request, 'inventory/inventory_form.html', context)


@login_required
def inventory_delete(request, pk):
    """
    Удаление инвентаря (только для владельца или администратора).
    """
    inventory = get_object_or_404(Inventory, pk=pk)

    # Проверка прав доступа
    if request.user.role == 'owner':
        if not hasattr(request.user, 'owner_profile') or inventory.owner != request.user.owner_profile:
            messages.error(request, 'У вас нет прав на удаление этого инвентаря.')
            return redirect('inventory:detail', pk=pk)
    elif request.user.role != 'administrator':
        messages.error(request, 'У вас нет прав на удаление.')
        return redirect('inventory:detail', pk=pk)

    if request.method == 'POST':
        inventory_name = inventory.name
        inventory.delete()
        logger.info(f'Инвентарь удален: {inventory_name}')
        messages.success(request, f'Инвентарь "{inventory_name}" успешно удален.')
        return redirect('inventory:list')

    return render(request, 'inventory/inventory_confirm_delete.html', {'inventory': inventory})


@login_required
def my_inventory(request):
    """
    Мой инвентарь (для владельцев).
    """
    if request.user.role != 'owner':
        messages.error(request, 'Эта страница доступна только владельцам инвентаря')
        return redirect('inventory:list')

    if not hasattr(request.user, 'owner_profile'):
        messages.error(request, 'Профиль владельца не найден')
        return redirect('users:profile')

    owner = request.user.owner_profile

    # Фильтрация по статусу
    status = request.GET.get('status')

    inventory_qs = Inventory.objects.filter(
        owner=owner
    ).select_related('category', 'manager').prefetch_related('photos').order_by('-added_date')

    if status:
        inventory_qs = inventory_qs.filter(status=status)

    # Пагинация
    paginator = Paginator(inventory_qs, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'selected_status': status,
        'is_my_inventory': True,
    }

    return render(request, 'inventory/my_inventory.html', context)