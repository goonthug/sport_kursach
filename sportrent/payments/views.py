import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from rentals.models import Rental
from .models import PaymentIntent
from .services import YooKassaService

logger = logging.getLogger(__name__)

_VALID_PURPOSES = {'rental_main', 'extension', 'overdue'}


@login_required
@require_POST
def create_payment(request, rental_id, purpose):
    """
    Создаёт PaymentIntent и перенаправляет на форму оплаты ЮКассы.
    purpose жёстко задан через kwargs маршрута — пользователь не может его подменить.
    """
    if purpose not in _VALID_PURPOSES:
        return HttpResponseBadRequest('Недопустимое назначение платежа.')

    rental = get_object_or_404(Rental.objects.select_related('client__user', 'inventory'), pk=rental_id)

    if rental.client.user != request.user:
        raise PermissionDenied('Это не ваша аренда.')

    # Защита от двойной оплаты: если уже succeeded — не создавать новый платёж
    already_paid = PaymentIntent.objects.filter(
        rental=rental, purpose=purpose, status='succeeded'
    ).exists()
    if already_paid:
        messages.info(request, 'Этот платёж уже был успешно выполнен.')
        return redirect('rentals:detail', pk=rental_id)

    # Сумма зависит от назначения
    if purpose == 'rental_main':
        amount = rental.total_price
        description = f'Оплата аренды «{rental.inventory.name}»'
    elif purpose == 'extension':
        amount = rental.additional_payment
        description = f'Доплата за продление аренды «{rental.inventory.name}»'
    else:  # overdue
        amount = rental.overdue_fee_unpaid
        description = f'Штраф за просрочку аренды «{rental.inventory.name}»'

    if not amount or amount <= 0:
        messages.error(request, 'Нет суммы к оплате.')
        return redirect('rentals:detail', pk=rental_id)

    # pending/waiting_for_capture — брошенные интенты остаются, ЮКасса их отменит сама (~10 мин)
    intent = PaymentIntent.objects.create(
        rental=rental,
        user=request.user,
        amount=amount,
        purpose=purpose,
    )

    return_url = (
        f'{settings.TUNNEL_URL}/api/payments/return/'
        f'?intent_id={intent.intent_id}'
    )
    metadata = {
        'intent_id': str(intent.intent_id),
        'rental_id': str(rental.rental_id),
        'purpose': purpose,
    }

    try:
        service = YooKassaService()
        confirmation_url, yookassa_payment_id = service.create_payment(
            amount=amount,
            description=description,
            return_url=return_url,
            metadata=metadata,
        )
    except Exception as exc:
        logger.error('Ошибка создания платежа ЮКасса, аренда %s: %s', rental_id, exc)
        intent.status = 'canceled'
        intent.save(update_fields=['status', 'updated_at'])
        messages.error(request, 'Не удалось создать платёж. Попробуйте позже.')
        return redirect('rentals:detail', pk=rental_id)

    intent.yookassa_payment_id = yookassa_payment_id
    intent.save(update_fields=['yookassa_payment_id', 'updated_at'])

    logger.info(
        'PaymentIntent %s создан: аренда=%s purpose=%s сумма=%s',
        intent.intent_id, rental_id, purpose, amount,
    )
    return redirect(confirmation_url)
