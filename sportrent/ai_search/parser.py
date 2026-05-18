"""
Парсинг поисковых запросов.

Цепочка выполнения:
  1. Redis-кэш (1 ч TTL) — если есть, возвращаем сразу
  2. get_llm_provider() — GigaChat-2-Lite (основной) или regex (если DEBUG+флаг)
  3. При любой ошибке провайдера — автоматический fallback на RegexFallbackProvider
  4. Результат сохраняется в кэш
"""

import logging

from django.core.exceptions import ImproperlyConfigured

from ai_search.services.llm import ParsedSearchQuery, get_llm_provider, RegexFallbackProvider
from ai_search.services.cache import get_cached, set_cached

logger = logging.getLogger('ai_search')


def parse_query(query: str) -> ParsedSearchQuery:
    """
    Основная точка входа. Возвращает ParsedSearchQuery.

    ImproperlyConfigured (нет ключа) — пробрасывается наверх, не глотается.
    Runtime-ошибки GigaChat (timeout, rate limit) — fallback на regex.
    """
    if not query or not query.strip():
        return ParsedSearchQuery()

    # 1. Кэш
    cached = get_cached(query)
    if cached is not None:
        logger.debug('Кэш-хит: "%s"', query)
        return cached

    # 2. Основной провайдер
    # ImproperlyConfigured не перехватываем — это конфигурационная ошибка,
    # а не runtime-сбой; пусть долетит до view и вернёт 503.
    provider = get_llm_provider()
    try:
        result = provider.parse_query(query)
    except ImproperlyConfigured:
        raise
    except Exception as exc:
        # Runtime-ошибка GigaChat (сеть, rate limit, timeout) → тихий fallback
        logger.warning(
            '%s runtime-ошибка, fallback на RegexFallbackProvider: %s',
            type(provider).__name__, exc,
        )
        result = RegexFallbackProvider().parse_query(query)

    # 3. Кэшируем
    set_cached(query, result)

    return result
