"""
Views для системы отзывов - ПОЛНАЯ РЕАЛИЗАЦИЯ.
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.core.paginator import Paginator

from .models import Review
from .forms import ReviewForm
from rentals.models import Rental
from inventory.models import Inventory
from users.decorators import role_required

logger = logging.getLogger('reviews')


@login_required
def review_list(request):
    """
    Список отзывов с фильтрацией.
    """
    user = request.user

    # В зависимости от роли показываем разные отзывы
    if user.role == 'client' and hasattr(user, 'client_profile'):
        reviews = Review.objects.filter(
            reviewer=user
        ).select_related('rental', 'rental__inventory').order_by('-review_date')

    elif user.role == 'owner' and hasattr(user, 'owner_profile'):
        # Отзывы на инвентарь владельца
        reviews = Review.objects.filter(
            rental__inventory__owner=user.owner_profile,
            target_type='inventory'
        ).select_related('rental', 'reviewer', 'rental__inventory').order_by('-review_date')

    elif user.role in ['manager', 'administrator']:
        reviews = Review.objects.all().select_related(
            'rental', 'reviewer', 'rental__inventory'
        ).order_by('-review_date')
    else:
        messages.error(request, 'Недостаточно прав')
        return redirect('core:home')

    # Фильтрация по статусу
    status = request.GET.get('status')
    if status:
        reviews = reviews.filter(status=status)

    # Пагинация
    paginator = Paginator(reviews, 15)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'selected_status': status,
        'status_choices': Review.STATUS_CHOICES,
    }

    return render(request, 'reviews/review_list.html', context)


@login_required
def review_create(request, rental_id):
    """
    Создание отзыва на завершенную аренду.
    """
    rental = get_object_or_404(
        Rental.objects.select_related('inventory', 'client'),
        pk=rental_id
    )

    # Проверка что аренда завершена
    if rental.status != 'completed':
        messages.error(request, 'Отзыв можно оставить только на завершенную аренду')
        return redirect('rentals:detail', pk=rental_id)

    # Проверка прав (только клиент может оставлять отзывы)
    if request.user.role != 'client' or not hasattr(request.user, 'client_profile'):
        messages.error(request, 'Только клиенты могут оставлять отзывы')
        return redirect('rentals:detail', pk=rental_id)

    if rental.client != request.user.client_profile:
        messages.error(request, 'Вы не можете оставить отзыв на чужую аренду')
        return redirect('rentals:detail', pk=rental_id)

    # Проверка что отзыв еще не оставлен
    existing_review = Review.objects.filter(
        rental=rental,
        reviewer=request.user,
        target_type='inventory'
    ).exists()

    if existing_review:
        messages.warning(request, 'Вы уже оставили отзыв на эту аренду')
        return redirect('rentals:detail', pk=rental_id)

    if request.method == 'POST':
        form = ReviewForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    review = form.save(commit=False)
                    review.rental = rental
                    review.reviewer = request.user
                    review.reviewed_id = rental.inventory.inventory_id
                    review.target_type = 'inventory'
                    review.status = 'pending'  # Модерация администратором
                    review.save()

                    logger.info(f'Создан отзыв: {review.review_id} от {request.user.email}')
                    messages.success(request, 'Отзыв отправлен на модерацию. Спасибо за ваше мнение!')
                    return redirect('rentals:detail', pk=rental_id)

            except Exception as e:
                logger.error(f'Ошибка при создании отзыва: {str(e)}')
                messages.error(request, 'Произошла ошибка при отправке отзыва')
    else:
        form = ReviewForm()

    context = {
        'form': form,
        'rental': rental,
    }

    return render(request, 'reviews/review_create.html', context)


@login_required
@role_required('administrator')
def review_approve(request, pk):
    """
    Одобрение отзыва администратором.
    """
    review = get_object_or_404(Review, pk=pk)

    if review.status != 'pending':
        messages.warning(request, 'Этот отзыв уже обработан')
        return redirect('reviews:list')

    if request.method == 'POST':
        try:
            review.status = 'published'
            review.save()  # сигнал post_save → recalculate_rating_on_review_save

            logger.info(f'Отзыв одобрен: {review.review_id} администратором {request.user.email}')
            messages.success(request, 'Отзыв опубликован')

        except Exception as e:
            logger.error(f'Ошибка при одобрении отзыва: {str(e)}')
            messages.error(request, 'Ошибка при одобрении')

    return redirect('reviews:list')


@login_required
@role_required('administrator')
def review_reject(request, pk):
    """
    Отклонение отзыва администратором.
    """
    review = get_object_or_404(Review, pk=pk)

    if review.status != 'pending':
        messages.warning(request, 'Этот отзыв уже обработан')
        return redirect('reviews:list')

    if request.method == 'POST':
        reason = request.POST.get('reason', '')

        try:
            review.status = 'rejected'
            review.rejection_reason = reason
            review.save()

            logger.info(f'Отзыв отклонен: {review.review_id} причина: {reason}')
            messages.info(request, 'Отзыв отклонен')

        except Exception as e:
            logger.error(f'Ошибка при отклонении отзыва: {str(e)}')
            messages.error(request, 'Ошибка при отклонении')

    return redirect('reviews:list')