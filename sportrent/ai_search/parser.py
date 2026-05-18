"""
Парсинг поисковых запросов.

Цепочка выполнения:
  1. Redis-кэш (1 ч TTL) — если есть, возвращаем сразу
  2. get_llm_provider() — GigaChat-2-Lite (основной) или regex (если DEBUG+флаг)
  3. При любой ошибке провайдера — автоматический fallback на RegexFallbackProvider
  4. Результат сохраняется в кэш
"""

import logging

from ai_search.services.llm import ParsedSearchQuery, get_llm_provider, RegexFallbackProvider
from ai_search.services.cache import get_cached, set_cached

logger = logging.getLogger('ai_search')


def parse_query(query: str) -> ParsedSearchQuery:
    """
    Основная точка входа. Возвращает ParsedSearchQuery.
    Никогда не поднимает исключение наружу.
    """
    if not query or not query.strip():
        return ParsedSearchQuery()

    # 1. Кэш
    cached = get_cached(query)
    if cached is not None:
        logger.debug('Кэш-хит: "%s"', query)
        return cached

    # 2. Основной провайдер с автоматическим fallback
    provider = get_llm_provider()
    try:
        result = provider.parse_query(query)
    except Exception as exc:
        logger.warning(
            '%s упал, fallback на RegexFallbackProvider: %s',
            type(provider).__name__, exc,
        )
        result = RegexFallbackProvider().parse_query(query)

    # 3. Кэшируем
    set_cached(query, result)

    return result
