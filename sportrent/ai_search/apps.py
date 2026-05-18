import logging

from django.apps import AppConfig
from django.core.checks import Error, register

logger = logging.getLogger('ai_search')

_MIN_CREDS_LEN = 50


class AiSearchConfig(AppConfig):
    name = 'ai_search'
    verbose_name = 'AI-поиск'

    def ready(self):
        """
        Проверяем наличие GIGACHAT_CREDENTIALS при старте Django.
        Регистрируем system check (Error-уровень), видимый в runserver/manage.py check.
        """
        @register()
        def check_gigachat_credentials(app_configs, **kwargs):
            from django.conf import settings

            # Если USE_REGEX_FALLBACK_IN_DEBUG=True — GigaChat намеренно отключён
            if settings.DEBUG and getattr(settings, 'USE_REGEX_FALLBACK_IN_DEBUG', False):
                return []
            if getattr(settings, 'LLM_PROVIDER', 'gigachat') != 'gigachat':
                return []

            creds = getattr(settings, 'GIGACHAT_CREDENTIALS', '') or ''
            if not creds or len(creds) < _MIN_CREDS_LEN:
                logger.critical(
                    'GIGACHAT_CREDENTIALS не настроен или слишком короткий '
                    '(< %d символов). AI-поиск не будет работать.',
                    _MIN_CREDS_LEN,
                )
                return [Error(
                    'GIGACHAT_CREDENTIALS не настроен в .env. AI-поиск не будет работать.',
                    hint=(
                        'Проверьте файл .env в корне проекта и перезапустите docker-compose. '
                        'Получить ключ: https://developers.sber.ru/studio'
                    ),
                    obj=AiSearchConfig,
                    id='ai_search.E001',
                )]
            return []
