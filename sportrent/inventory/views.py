"""
Views для управления инвентарем.
Включает список, детали, создание, редактирование и удаление.
"""

import json
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.conf import settings
from datetime import datetime, timedelta
from decimal import Decimal

from django.core.paginator import Paginator
from django.db.models import Q, Avg, Sum, Count
from django.db.models.functions import TruncDate
from django.db import transaction
from django.utils import timezone

from .models import Inventory, SportCategory, InventoryPhoto, Favorite, City, PickupPoint
from .forms import InventoryForm, InventoryPhotoFormSet
from users.models import Owner

logger = logging.getLogger('inventory')


def _save_pickup_point(inventory, form, owner):
    """Создаёт или обновляет точку выдачи по данным из формы."""
    city_name = form.cleaned_data.get('city_name', '').strip()
    pickup_address = form.cleaned_data.get('pickup_address', '').strip()
    pickup_phone = form.cleaned_data.get('pickup_phone', '').strip()

    if not city_name or not pickup_address:
        return

    # Найти или создать город
    city, city_created = City.objects.get_or_create(name=city_name)
    if city_created or (not city.lat and not city.lon):
        try:
            from ai_search.geocoder import get_city_coordinates
            coords = get_city_coordinates(city_name)
            if coords:
                city.lat, city.lon = coords
                city.save(update_fields=['lat', 'lon'])
        except Exception:
            pass

    lat = city.lat or 0
    lon = city.lon or 0

    if inventory.pickup_point_id:
        # Обновляем существующую точку
        pp = inventory.pickup_point
        pp.city = city
        pp.address = pickup_address
        pp.phone = pickup_phone
        pp.lat = lat
        pp.lon = lon
        pp.save()
    else:
        pp = PickupPoint.objects.create(
            city=city,
            owner=owner,
            name=f'{city_name} — {owner.full_name}',
            address=pickup_address,
            lat=lat,
            lon=lon,
            phone=pickup_phone,
        )
        inventory.pickup_point = pp
        inventory.save(update_fields=['pickup_point'])


def inventory_list(request):
    """
    Список инвентаря с фильтрацией, поиском и сортировкой.
    """
    # Базовый queryset только для доступного инвентаря
    inventory_qs = Inventory.objects.filter(
        status='available'
    ).select_related('category', 'owner', 'owner__user', 'pickup_point__city').prefetch_related('photos')

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
    paginator = Paginator(inventory_qs, 9)  # 9 items per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Обновляем рейтинги для инвентаря на текущей странице
    from reviews.utils import update_inventory_rating
    for item in page_obj.object_list:
        if item.reviews_count > 0:
            update_inventory_rating(item)

    favorite_ids = set()
    if request.user.is_authenticated and request.user.role == 'client' and hasattr(request.user, 'client_profile'):
        favorite_ids = set(
            Favorite.objects.filter(
                client=request.user.client_profile,
                inventory__in=page_obj.object_list
            ).values_list('inventory_id', flat=True)
        )

    # Получаем категории и города для фильтров
    categories = SportCategory.objects.all()
    cities = list(City.objects.filter(pickup_points__is_active=True).distinct().values('name').order_by('name'))

    context = {
        'page_obj': page_obj,
        'categories': categories,
        'cities': cities,
        'search_query': search_query,
        'selected_category': category_id,
        'selected_condition': condition,
        'min_price': min_price,
        'max_price': max_price,
        'current_sort': sort_by,
        'total_count': paginator.count,
        'favorite_ids': favorite_ids,
        'yandex_maps_key': settings.YANDEX_MAPS_KEY,
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

    is_favorite = False
    if request.user.is_authenticated and request.user.role == 'client' and hasattr(request.user, 'client_profile'):
        is_favorite = Favorite.objects.filter(
            client=request.user.client_profile,
            inventory=inventory
        ).exists()

    context = {
        'inventory': inventory,
        'reviews': reviews,
        'is_favorite': is_favorite,
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
        form = InventoryForm(request.POST, request.FILES, owner=owner)
        photo_formset = InventoryPhotoFormSet(request.POST, request.FILES)

        if form.is_valid() and photo_formset.is_valid():
            try:
                with transaction.atomic():
                    inventory = form.save(commit=False)
                    inventory.owner = owner
                    inventory.status = 'pending'  # Ожидает проверки менеджером
                    inventory.save()

                    # Сохраняем точку выдачи
                    _save_pickup_point(inventory, form, owner)

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
        form = InventoryForm(owner=owner)
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
        if inventory.status not in ['pending', 'rejected']:
            messages.error(request, 'Редактирование доступно только до одобрения менеджером.')
            return redirect('inventory:detail', pk=pk)
    elif request.user.role not in ['manager', 'administrator']:
        messages.error(request, 'У вас нет прав на редактирование.')
        return redirect('inventory:detail', pk=pk)

    if request.method == 'POST':
        form = InventoryForm(request.POST, request.FILES, instance=inventory, owner=inventory.owner)
        photo_formset = InventoryPhotoFormSet(request.POST, request.FILES, queryset=inventory.photos.all())

        if form.is_valid() and photo_formset.is_valid():
            try:
                with transaction.atomic():
                    inventory = form.save()

                    # Обновляем точку выдачи
                    _save_pickup_point(inventory, form, inventory.owner)

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
        form = InventoryForm(instance=inventory, owner=inventory.owner)
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


@login_required
def owner_earnings_analytics(request):
    """
    Аналитика заработка владельца: по дням, за период, топ и аутсайдеры по инвентарю.
    """
    if request.user.role != 'owner' or not hasattr(request.user, 'owner_profile'):
        messages.error(request, 'Доступно только владельцам инвентаря')
        return redirect('core:home')

    owner = request.user.owner_profile
    owner_pct = Decimal('0.70')  # 70% владельцу по умолчанию

    # Период из GET или по умолчанию последние 30 дней
    today = timezone.now().date()
    try:
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        if date_from:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        else:
            date_from = today - timedelta(days=30)
        if date_to:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        else:
            date_to = today
        if date_from > date_to:
            date_from, date_to = date_to, date_from
    except (ValueError, TypeError):
        date_from = today - timedelta(days=30)
        date_to = today

    from rentals.models import Rental

    # Заработок по дням (завершённые аренды, дата = actual_return_date)
    rentals_completed = Rental.objects.filter(
        inventory__owner=owner,
        status='completed',
        actual_return_date__isnull=False,
        actual_return_date__date__gte=date_from,
        actual_return_date__date__lte=date_to,
    )
    earnings_by_day_qs = rentals_completed.annotate(
        day=TruncDate('actual_return_date')
    ).values('day').annotate(
        total=Sum('total_price')
    ).order_by('day')
    earnings_by_day = []
    for row in earnings_by_day_qs:
        earnings_by_day.append({
            'day': row['day'],
            'earnings': (row['total'] or Decimal('0')) * owner_pct,
            'rentals_count': None,
        })
    # Количество аренд по дням
    from django.db.models import Count
    count_by_day = rentals_completed.annotate(
        day=TruncDate('actual_return_date')
    ).values('day').annotate(
        cnt=Count('rental_id')
    )
    count_map = {r['day']: r['cnt'] for r in count_by_day}
    for row in earnings_by_day:
        row['rentals_count'] = count_map.get(row['day'], 0)

    # Итого за период
    period_total = sum((r['earnings'] for r in earnings_by_day), Decimal('0'))

    # Фильтр по периоду для топ/аутсайдеров (те же даты, что и «Итого за период»)
    period_filter = (
        Q(rentals__status='completed') &
        Q(rentals__actual_return_date__isnull=False) &
        Q(rentals__actual_return_date__date__gte=date_from) &
        Q(rentals__actual_return_date__date__lte=date_to)
    )

    # По инвентарю за выбранный период: кто приносит больше всего и меньше всего
    inventory_with_stats = Inventory.objects.filter(
        owner=owner
    ).annotate(
        completed_rentals=Count('rentals', filter=period_filter),
        total_revenue=Sum('rentals__total_price', filter=period_filter),
    ).filter(
        completed_rentals__gt=0
    ).order_by('-total_revenue')
    top_inventory = []
    for inv in inventory_with_stats[:10]:
        total_rev = inv.total_revenue or Decimal('0')
        top_inventory.append({
            'inventory': inv,
            'rentals_count': inv.completed_rentals,
            'earnings': total_rev * owner_pct,
        })
    # Меньше всего спроса за период (по количеству аренд или по сумме)
    least_inventory = list(
        Inventory.objects.filter(owner=owner).annotate(
            completed_rentals=Count('rentals', filter=period_filter),
            total_revenue=Sum('rentals__total_price', filter=period_filter),
        ).order_by('completed_rentals', 'total_revenue')[:10]
    )
    least_inventory_with_earnings = []
    for inv in least_inventory:
        rev = getattr(inv, 'total_revenue', None) or Decimal('0')
        cnt = getattr(inv, 'completed_rentals', 0)
        least_inventory_with_earnings.append({
            'inventory': inv,
            'rentals_count': cnt,
            'earnings': rev * owner_pct,
        })

    context = {
        'date_from': date_from,
        'date_to': date_to,
        'earnings_by_day': earnings_by_day,
        'period_total': period_total,
        'top_inventory': top_inventory,
        'least_inventory': least_inventory_with_earnings,
        'owner_pct': owner_pct,
    }
    return render(request, 'inventory/owner_earnings.html', context)


@login_required
def favorites_list(request):
    """
    Избранный инвентарь клиента.
    """
    if request.user.role != 'client' or not hasattr(request.user, 'client_profile'):
        messages.error(request, 'Избранное доступно только клиентам')
        return redirect('inventory:list')

    favorites_qs = Favorite.objects.filter(
        client=request.user.client_profile
    ).select_related('inventory', 'inventory__category').prefetch_related('inventory__photos').order_by('-created_date')

    paginator = Paginator(favorites_qs, 9)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'total_count': paginator.count,
    }

    return render(request, 'inventory/favorites.html', context)


@login_required
def favorite_toggle(request, pk):
    """
    Добавить или удалить инвентарь из избранного.
    """
    if request.user.role != 'client' or not hasattr(request.user, 'client_profile'):
        messages.error(request, 'Избранное доступно только клиентам')
        return redirect('inventory:detail', pk=pk)

    if request.method != 'POST':
        return redirect('inventory:detail', pk=pk)

    inventory = get_object_or_404(Inventory, pk=pk, status='available')
    client = request.user.client_profile

    favorite = Favorite.objects.filter(client=client, inventory=inventory).first()
    if favorite:
        favorite.delete()
        messages.info(request, 'Удалено из избранного')
    else:
        Favorite.objects.create(client=client, inventory=inventory)
        messages.success(request, 'Добавлено в избранное')

    next_url = request.GET.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('inventory:detail', pk=pk)


@require_POST
def ai_search_view(request):
    """
    AJAX-эндпоинт AI-поиска. Принимает JSON с полем "q",
    возвращает список инвентаря с координатами точек выдачи.
    """
    try:
        body = json.loads(request.body)
        query = body.get('q', '').strip()
    except (json.JSONDecodeError, AttributeError):
        query = request.POST.get('q', '').strip()

    if not query:
        return JsonResponse({'error': 'Запрос не может быть пустым'}, status=400)

    try:
        from ai_search.parser import parse_query
        from ai_search.search import search_inventory

        parsed = parse_query(query)
        results_qs = search_inventory(parsed)

        items = []
        for item in results_qs:
            photo = item.photos.first()
            pp = item.pickup_point
            items.append({
                'id': str(item.inventory_id),
                'name': item.name,
                'brand': item.brand or '',
                'price_per_day': float(item.price_per_day),
                'category': item.category.name if item.category else '',
                'condition': item.condition,
                'avg_rating': float(item.avg_rating) if item.avg_rating else None,
                'photo_url': photo.photo_url.url if photo and photo.photo_url else '',
                'url': f'/inventory/{item.inventory_id}/',
                'pickup_point': {
                    'name': pp.name,
                    'address': pp.address,
                    'city': pp.city.name,
                    'lat': float(pp.lat),
                    'lon': float(pp.lon),
                    'phone': pp.phone or '',
                } if pp else None,
            })

        parsed_info = {
            'category_query': parsed.category_query,
            'city_name': parsed.city_name,
            'max_price': parsed.max_price,
            'start_date': parsed.start_date,
            'end_date': parsed.end_date,
        }

        logger.info('AI-поиск "%s": найдено %d', query, len(items))
        return JsonResponse({'results': items, 'count': len(items), 'parsed': parsed_info})

    except Exception as exc:
        logger.error('Ошибка AI-поиска: %s', exc)
        return JsonResponse({'error': 'Ошибка поиска, попробуйте позже'}, status=500)