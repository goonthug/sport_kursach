"""
Views оплаты через ЮКассу — создание платежа, обработка webhook, страница возврата.

Что здесь:
- create_payment(): создаёт PaymentIntent и редиректит клиента на ЮКассу
- payment_webhook(): принимает уведомление ЮКассы (POST), проверяет IP whitelist,
  переводит Rental в статус paid/overdue/extended
- payment_return(): страница после редиректа с ЮКассы — polling статуса
- _apply_payment_succeeded(): применяет успешный платёж к объекту аренды

Связано с:
- payments/services.py: YooKassaService — создание и проверка платежей
- payments/models.py: PaymentIntent — запись о каждом платеже
- rentals/models.py: Rental — обновление статуса после оплаты
- config/settings.py: TUNNEL_URL — нужен для build_absolute_uri за Tuna-прокси

Ключевые слова: оплата, платёж, webhook, ЮКасса, return_url, polling
"""

import json
import logging
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from rentals.models import PaymentHistory, Rental
from .models import PaymentIntent
from .services import YooKassaService

logger = logging.getLogger(__name__)

_VALID_PURPOSES = {'rental_main', 'extension', 'overdue'}


def _get_client_ip(request) -> str:
    """
    Извлекает реальный IP клиента из заголовков, выставляемых nginx после real_ip_module.
    Приоритет: X-Real-IP (ставит nginx) → X-Forwarded-For[0] → REMOTE_ADDR.
    """
    real_ip = request.META.get('HTTP_X_REAL_IP')
    if real_ip:
        return real_ip
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


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

    return_url = request.build_absolute_uri(
        reverse('payments:return') + f'?intent_id={intent.intent_id}'
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


@csrf_exempt
@require_POST
def payment_webhook(request):
    """
    Обработчик входящих уведомлений от ЮКассы.

    Проверяет IP отправителя, обновляет PaymentIntent и применяет
    бизнес-эффект при payment.succeeded. Всегда возвращает 200 OK
    если обработка прошла — иначе ЮКасса повторяет запрос до 24 ч.
    """
    client_ip = _get_client_ip(request)

    if not YooKassaService.verify_webhook_ip(client_ip):
        logger.warning('Webhook отклонён: IP %s не в whitelist ЮКассы', client_ip)
        return HttpResponse(status=403)

    logger.info('Webhook получен с IP %s', client_ip)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        logger.warning('Webhook: невалидный JSON в теле запроса')
        return HttpResponse(status=400)

    event_type = data.get('event', '')
    payment_obj = data.get('object', {})
    yookassa_payment_id = payment_obj.get('id', '')

    if not yookassa_payment_id:
        logger.warning('Webhook: отсутствует object.id в теле %s', data)
        return HttpResponse(status=400)

    # Найти PaymentIntent по ID платежа в ЮКассе
    try:
        intent = PaymentIntent.objects.select_related('rental__inventory').get(
            yookassa_payment_id=yookassa_payment_id
        )
    except PaymentIntent.DoesNotExist:
        logger.warning(
            'Webhook: PaymentIntent не найден для yookassa_payment_id=%s (event=%s)',
            yookassa_payment_id, event_type,
        )
        # Возвращаем 200 чтобы ЮКасса не повторяла — мы этот платёж не знаем
        return HttpResponse(status=200)

    # Idempotency: если webhook уже успешно обработан — пропустить
    if intent.status == 'succeeded' and event_type == 'payment.succeeded':
        logger.info('Webhook idempotent skip: intent %s уже succeeded', intent.intent_id)
        return HttpResponse(status=200)

    # Проверка суммы — расхождение может сигнализировать об атаке
    webhook_amount = Decimal(payment_obj.get('amount', {}).get('value', '0'))
    if event_type == 'payment.succeeded' and webhook_amount != intent.amount:
        logger.warning(
            'Webhook: расхождение суммы для intent %s: ожидали %s, получили %s',
            intent.intent_id, intent.amount, webhook_amount,
        )
        # Не прерываем обработку, но факт расхождения зафиксирован

    if event_type == 'payment.succeeded':
        try:
            with transaction.atomic():
                _apply_payment_succeeded(intent, data)
        except Exception as exc:
            logger.error(
                'Webhook: ошибка при обработке payment.succeeded для intent %s: %s',
                intent.intent_id, exc,
            )
            # 500 заставит ЮКассу повторить запрос
            return HttpResponse(status=500)

    elif event_type == 'payment.canceled':
        intent.status = 'canceled'
        intent.raw_webhook_data = data
        intent.save(update_fields=['status', 'raw_webhook_data', 'updated_at'])
        logger.info('PaymentIntent %s отменён через webhook', intent.intent_id)

    elif event_type == 'payment.waiting_for_capture':
        intent.status = 'waiting_for_capture'
        intent.raw_webhook_data = data
        intent.save(update_fields=['status', 'raw_webhook_data', 'updated_at'])
        logger.info('PaymentIntent %s ожидает подтверждения списания', intent.intent_id)

    else:
        logger.warning(
            'Webhook: неизвестный тип события "%s" для intent %s',
            event_type, intent.intent_id,
        )

    return HttpResponse(status=200)


@login_required
def payment_return(request):
    """
    Страница возврата после оплаты на ЮКассе.
    Если статус ещё pending — один раз опрашивает ЮКассу и обновляет БД.
    """
    intent_id = request.GET.get('intent_id')
    if not intent_id:
        return redirect('rentals:list')

    intent = get_object_or_404(
        PaymentIntent.objects.select_related('rental'),
        intent_id=intent_id,
        user=request.user,
    )

    if intent.status == 'pending' and intent.yookassa_payment_id:
        try:
            service = YooKassaService()
            info = service.get_payment(intent.yookassa_payment_id)
            new_status = info['status']
            if new_status in ('succeeded', 'canceled', 'waiting_for_capture'):
                if new_status == 'succeeded' and intent.status != 'succeeded':
                    with transaction.atomic():
                        _apply_payment_succeeded(intent, {'polled': True})
                else:
                    intent.status = new_status
                    intent.save(update_fields=['status', 'updated_at'])
        except Exception as exc:
            logger.warning('payment_return: не удалось опросить ЮКассу: %s', exc)

    intent.refresh_from_db()

    template_map = {
        'succeeded': 'payments/payment_success.html',
        'canceled': 'payments/payment_canceled.html',
    }
    template = template_map.get(intent.status, 'payments/payment_pending.html')
    return render(request, template, {'intent': intent, 'rental': intent.rental})


def _apply_payment_succeeded(intent: PaymentIntent, raw_data: dict) -> None:
    """
    Применяет бизнес-эффект успешной оплаты внутри уже открытой транзакции.
    Вызывается только из payment_webhook.
    """
    now = timezone.now()
    rental = intent.rental

    intent.status = 'succeeded'
    intent.raw_webhook_data = raw_data
    intent.save(update_fields=['status', 'raw_webhook_data', 'updated_at'])

    if intent.purpose == 'rental_main':
        rental.payment_status = 'paid'
        # Поля payment_date на Rental нет — статус оплаты отражается через payment_status
        rental.save(update_fields=['payment_status'])
        # PaymentHistory не имеет типа для rental_main — только extension/overdue
        # TODO: добавить тип 'rental_main_card' в PaymentHistory.PAYMENT_TYPE_CHOICES если понадобится история

    elif intent.purpose == 'extension':
        rental.additional_payment_paid = True
        # Если нет других долгов — итоговый статус тоже paid
        if rental.overdue_fee_unpaid <= 0:
            rental.payment_status = 'paid'
        rental.save(update_fields=['additional_payment_paid', 'payment_status'])
        PaymentHistory.objects.create(
            rental=rental,
            amount=intent.amount,
            payment_type='extension_card',
            paid_at=now,
        )

    elif intent.purpose == 'overdue':
        rental.overdue_fee_paid_at = now
        rental.overdue_fee_snapshot = intent.amount
        rental.save(update_fields=['overdue_fee_paid_at', 'overdue_fee_snapshot'])
        PaymentHistory.objects.create(
            rental=rental,
            amount=intent.amount,
            payment_type='overdue_card',
            paid_at=now,
        )

    logger.info(
        'Webhook processed: intent=%s purpose=%s аренда=%s сумма=%s',
        intent.intent_id, intent.purpose, rental.rental_id, intent.amount,
    )
