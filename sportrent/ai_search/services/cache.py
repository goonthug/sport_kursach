"""
Redis-кэш для результатов парсинга поисковых запросов.
TTL: 1 час. Ключ: md5 нормализованного запроса.
Graceful degradation: при падении Redis работаем без кэша.
"""

import hashlib
import logging

from django.core.cache import cache

logger = logging.getLogger('ai_search')

_PREFIX = 'ai_search:parsed:'
_TTL = 3600  # 1 час


def _make_key(query: str) -> str:
    normalized = ' '.join(query.lower().split())
    return _PREFIX + hashlib.md5(normalized.encode()).hexdigest()


def get_cached(query: str):
    """
    Возвращает ParsedSearchQuery из кэша или None.
    При ошибке Redis — логирует и возвращает None.
    """
    try:
        data = cache.get(_make_key(query))
        if data is None:
            return None
        from ai_search.services.llm import ParsedSearchQuery
        return ParsedSearchQuery.model_validate_json(data)
    except Exception as exc:
        logger.warning('cache.get ошибка, идём к LLM: %s', exc)
        return None


def set_cached(query: str, result) -> None:
    """
    Сохраняет ParsedSearchQuery в кэш на 1 час.
    При ошибке Redis — логирует и молчит.
    """
    try:
        cache.set(_make_key(query), result.model_dump_json(), timeout=_TTL)
    except Exception as exc:
        logger.warning('cache.set ошибка: %s', exc)
