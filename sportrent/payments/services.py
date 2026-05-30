"""
Сервисный слой для интеграции с ЮКассой (онлайн-оплата аренды).

Что здесь:
- YooKassaService.create_payment(): создаёт платёж в ЮКассе, возвращает confirmation_url
- YooKassaService.get_payment(): запрашивает актуальный статус платежа по payment_id
- YooKassaService.is_valid_webhook_ip(): проверяет IP webhook'а по whitelist ЮКассы

Связано с:
- payments/views.py: вызывает YooKassaService для create/webhook/return
- payments/models.py: PaymentIntent хранит yookassa_payment_id и статус
- config/settings.py: YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY, YOOKASSA_MODE (test/live)

Ключевые слова: ЮКасса, YooKassa, оплата, webhook, IP whitelist
"""

import ipaddress
import logging
from decimal import Decimal

from django.conf import settings
from yookassa import Configuration, Payment
from yookassa.domain.exceptions import ApiError

logger = logging.getLogger(__name__)

# IP-адреса и подсети серверов ЮКассы, с которых приходят webhook'и.
# Источник: https://yookassa.ru/developers/using-api/webhooks
# Обновлено: 2026-05-25
# При изменении списка ЮКассой — обновить здесь и поставить новую дату.
YOOKASSA_WEBHOOK_IPS = [
    ipaddress.ip_network('185.71.76.0/27'),
    ipaddress.ip_network('185.71.77.0/27'),
    ipaddress.ip_network('77.75.153.0/25'),
    ipaddress.ip_network('77.75.156.11/32'),
    ipaddress.ip_network('77.75.156.35/32'),
    ipaddress.ip_network('77.75.154.128/25'),
    ipaddress.ip_network('2a02:5180::/32'),
]


class YooKassaService:
    """Обёртка над SDK ЮКассы для создания и проверки платежей."""

    def __init__(self):
        Configuration.account_id = settings.YOOKASSA_SHOP_ID
        Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

    def create_payment(
        self,
        amount: Decimal,
        description: str,
        return_url: str,
        metadata: dict,
    ) -> tuple[str, str]:
        """
        Создаёт платёж в ЮКассе.

        Возвращает (confirmation_url, payment_id).
        idempotency_key = str(metadata['intent_id']) — защита от дубля при повторном запросе.
        """
        payment_data = {
            'amount': {
                'value': f'{amount:.2f}',
                'currency': 'RUB',
            },
            'confirmation': {
                'type': 'redirect',
                'return_url': return_url,
            },
            'description': description,
            'metadata': metadata,
            'capture': True,
        }

        try:
            response = Payment.create(payment_data, idempotency_key=str(metadata['intent_id']))
        except ApiError as exc:
            logger.error('YooKassa create_payment failed: %s', exc)
            raise

        return response.confirmation.confirmation_url, response.id

    def get_payment(self, payment_id: str) -> dict:
        """
        Запрашивает актуальный статус платежа из ЮКассы.

        Используется на return_url для однократной сверки когда webhook ещё не дошёл.
        Возвращает словарь с ключами: status, amount, paid, cancellation_details.
        """
        try:
            response = Payment.find_one(payment_id)
        except ApiError as exc:
            logger.error('YooKassa get_payment failed for %s: %s', payment_id, exc)
            raise

        return {
            'status': response.status,
            'amount': Decimal(response.amount.value),
            'paid': response.paid,
            'cancellation_details': (
                {
                    'party': response.cancellation_details.party,
                    'reason': response.cancellation_details.reason,
                }
                if response.cancellation_details
                else None
            ),
        }

    @staticmethod
    def verify_webhook_ip(request_ip: str) -> bool:
        """
        Проверяет, входит ли IP-адрес в whitelist серверов ЮКассы.

        Источник списка: https://yookassa.ru/developers/using-api/webhooks
        Дата обновления: 2026-05-25

        ЮКасса рекомендует проверку по IP как способ верификации подлинности
        входящих webhook-уведомлений. Список содержит CIDR-подсети и одиночные
        адреса (приведены к /32), проверка выполняется через модуль ipaddress.
        """
        try:
            addr = ipaddress.ip_address(request_ip)
        except ValueError:
            logger.warning('verify_webhook_ip: некорректный IP "%s"', request_ip)
            return False

        return any(addr in network for network in YOOKASSA_WEBHOOK_IPS)
