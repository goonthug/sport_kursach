"""
Абстракция LLMProvider для парсинга поисковых запросов.

Провайдеры:
  GigaChatProvider    — основной, GigaChat-2-Lite, max_tokens=250
  RegexFallbackProvider — резервный, pure Python, без сети

Выбор провайдера: get_llm_provider() читает LLM_PROVIDER из settings.
Счётчик токенов:  _track_tokens() пишет в Redis (не в БД).
"""

import re
import logging
from abc import ABC, abstractmethod
from datetime import date, timedelta
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger('ai_search')


# ── Схема результата парсинга ──────────────────────────────────────────────

class ParsedSearchQuery(BaseModel):
    """Структурированный результат разбора поискового запроса."""
    category_query: Optional[str] = Field(None, description='Тип инвентаря')
    city_name: Optional[str] = Field(None, description='Название города в России')
    start_date: Optional[str] = Field(None, description='Дата начала YYYY-MM-DD')
    end_date: Optional[str] = Field(None, description='Дата окончания YYYY-MM-DD')
    max_price: Optional[float] = Field(None, description='Максимальная цена руб/день')
    keywords: Optional[str] = Field(None, description='Дополнительные ключевые слова')


# ── Синонимы городов — загружаются один раз при старте ────────────────────

CITY_SYNONYMS: dict[str, list[str]] = {
    'Москва': ['москва', 'москве', 'москву', 'москвы', 'мск', 'moscow'],
    'Санкт-Петербург': [
        'санкт-петербург', 'санкт петербург', 'спб', 'петербург',
        'питер', 'питере', 'петербурге', 'spb',
    ],
    'Казань': ['казань', 'казани', 'казанью', 'kazan'],
    'Екатеринбург': ['екатеринбург', 'екатеринбурге', 'екб', 'екате'],
    'Новосибирск': ['новосибирск', 'новосибирске', 'нск', 'новосиб'],
    'Красноярск': ['красноярск', 'красноярске', 'красноярска'],
    'Омск': ['омск', 'омске', 'омска'],
    'Тюмень': ['тюмень', 'тюмени', 'тюменью'],
    'Челябинск': ['челябинск', 'челябинске', 'чел'],
    'Уфа': ['уфа', 'уфе', 'уфу', 'уфы'],
    'Самара': ['самара', 'самаре', 'самару', 'самары'],
    'Нижний Новгород': [
        'нижний новгород', 'нижнем новгороде', 'нижнего новгорода',
        'нижний', 'ннов', 'нн',
    ],
    'Ростов-на-Дону': ['ростов-на-дону', 'ростов на дону', 'ростов', 'ростове'],
    'Краснодар': ['краснодар', 'краснодаре', 'краснодара'],
    'Сочи': ['сочи', 'сочах'],
    'Воронеж': ['воронеж', 'воронеже', 'воронежа'],
    'Пермь': ['пермь', 'перми', 'пермью'],
    'Волгоград': ['волгоград', 'волгограде', 'волгограда'],
    'Ижевск': ['ижевск', 'ижевске', 'ижевска'],
    'Альметьевск': ['альметьевск', 'альметьевске', 'альметьевска'],
}

# Инвертированный индекс: синоним → каноническое имя города
_SYNONYM_INDEX: dict[str, str] = {
    syn: city
    for city, synonyms in CITY_SYNONYMS.items()
    for syn in synonyms
}

# ── Ключевые слова категорий ───────────────────────────────────────────────

# Список пар (каноническое имя, [ключевые слова]).
# Порядок важен: более специфичные категории — раньше.
CATEGORY_KEYWORDS: list[tuple[str, list[str]]] = [
    ('беговые лыжи', ['беговые лыжи', 'лыжи беговые', 'беговая лыжа', 'лыжа беговая']),
    ('горные лыжи', ['горные лыжи', 'лыжи горные', 'горнолыжный', 'горнолыжные']),
    ('лыжи', ['лыжи', 'лыжа', 'лыжный']),
    ('сноуборд', ['сноуборд', 'сноубординг', 'сноуборды']),
    ('велосипед', ['велосипед', 'велосипеды', 'велосипедный', 'велик', 'байк']),
    ('ролики', ['ролики', 'роликовые коньки', 'ролик']),
    ('коньки', ['коньки', 'конек', 'коньках']),
    ('скейт', ['скейт', 'скейтборд', 'скейтборды']),
    ('каяк', ['каяк', 'каяки', 'каякинг']),
    ('байдарка', ['байдарка', 'байдарки', 'байдарочный']),
    ('сап', ['сап', 'sup', 'сапборд', 'гребля на доске']),
    ('палатка', ['палатка', 'палатки', 'палаточный']),
    ('рюкзак', ['рюкзак', 'рюкзаки']),
    ('туризм', ['поход', 'походный', 'треккинг', 'туристический']),
]


# ── Абстрактный провайдер ─────────────────────────────────────────────────

class LLMProvider(ABC):
    """Интерфейс парсера поисковых запросов."""

    @abstractmethod
    def parse_query(self, query: str) -> ParsedSearchQuery:
        ...


# ── GigaChatProvider ──────────────────────────────────────────────────────

class GigaChatProvider(LLMProvider):
    """
    Парсинг через GigaChat (free tier).
    Поднимает исключение при любой ошибке — вызывающий код делает fallback.
    """

    MODEL = 'GigaChat'
    MAX_TOKENS = 300

    def __init__(self, credentials: str) -> None:
        self._credentials = credentials

    def parse_query(self, query: str) -> ParsedSearchQuery:
        import json
        import re as _re
        from gigachat import GigaChat
        from gigachat.models import Chat, Messages, MessagesRole

        today = date.today().isoformat()
        # chat_parse (structured output) не поддерживается на free tier →
        # используем обычный chat() с явным JSON-примером в промпте.
        prompt = (
            f'Сегодня {today}. Разбери запрос аренды спортивного инвентаря: "{query}". '
            'Извлеки поля: category_query (тип инвентаря или null), '
            'city_name (город России или null), '
            'start_date (YYYY-MM-DD или null), end_date (YYYY-MM-DD или null), '
            'max_price (число руб/день или null), keywords (прочие слова или null). '
            'Поля, не упомянутые в запросе, — null. '
            'Верни ТОЛЬКО валидный JSON без markdown и пояснений. '
            'Пример: {"category_query":"лыжи","city_name":"Казань","start_date":"2026-05-19",'
            '"end_date":null,"max_price":500.0,"keywords":null}'
        )

        with GigaChat(
            credentials=self._credentials,
            model=self.MODEL,
            max_tokens=self.MAX_TOKENS,
            verify_ssl_certs=False,
        ) as client:
            completion = client.chat(
                Chat(messages=[Messages(role=MessagesRole.USER, content=prompt)])
            )

        text = completion.choices[0].message.content.strip()
        # Убираем markdown-обёртку, если модель всё-таки добавила ```json ... ```
        md_match = _re.search(r'```(?:json)?\s*([\s\S]+?)\s*```', text)
        if md_match:
            text = md_match.group(1)

        parsed = ParsedSearchQuery.model_validate(json.loads(text))

        tokens = getattr(getattr(completion, 'usage', None), 'total_tokens', 0)
        if tokens:
            _track_tokens(tokens)

        logger.info('GigaChat: "%s" → %s (%s tokens)', query, parsed.model_dump(), tokens)
        return parsed


# ── RegexFallbackProvider ─────────────────────────────────────────────────

class RegexFallbackProvider(LLMProvider):
    """
    Pure Python-парсер. Работает без сети.
    Понимает падежи и синонимы городов через _SYNONYM_INDEX.
    """

    _MONTHS: dict[str, int] = {
        'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
        'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
        'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12,
    }

    def parse_query(self, query: str) -> ParsedSearchQuery:
        q = query.lower().strip()
        city = self._extract_city(q)
        category = self._extract_category(q)
        return ParsedSearchQuery(
            city_name=city,
            category_query=category,
            max_price=self._extract_price(q),
            start_date=self._extract_start_date(q),
            end_date=self._extract_end_date(q),
            keywords=query if not category else None,
        )

    def _extract_city(self, q: str) -> Optional[str]:
        # Длинные синонимы проверяем первыми, чтобы «нижний новгород» не матчился как «нижний»
        for syn in sorted(_SYNONYM_INDEX, key=len, reverse=True):
            if syn in q:
                return _SYNONYM_INDEX[syn]
        return None

    def _extract_category(self, q: str) -> Optional[str]:
        for category, keywords in CATEGORY_KEYWORDS:
            for kw in keywords:
                if kw in q:
                    return category
        return None

    def _extract_price(self, q: str) -> Optional[float]:
        m = re.search(
            r'(?:до|не дороже|не дороже|максимум|max)\s*(\d[\d\s]*(?:[.,]\d+)?)\s*(к|тыс)?',
            q,
        )
        if m:
            raw = m.group(1).replace(' ', '').replace(',', '.')
            try:
                val = float(raw)
                if m.group(2):
                    val *= 1000
                return val
            except ValueError:
                pass
        return None

    def _extract_start_date(self, q: str) -> Optional[str]:
        today = date.today()
        if 'завтра' in q:
            return (today + timedelta(days=1)).isoformat()
        if 'сегодня' in q:
            return today.isoformat()
        if 'на выходных' in q or 'в выходные' in q:
            days_ahead = (5 - today.weekday()) % 7 or 7
            return (today + timedelta(days=days_ahead)).isoformat()
        m = re.search(r'(\d{1,2})\s+(' + '|'.join(self._MONTHS) + ')', q)
        if m:
            try:
                day = int(m.group(1))
                month = self._MONTHS[m.group(2)]
                year = today.year if month >= today.month else today.year + 1
                return date(year, month, day).isoformat()
            except ValueError:
                pass
        return None

    def _extract_end_date(self, q: str) -> Optional[str]:
        today = date.today()
        if 'на выходных' in q or 'в выходные' in q:
            days_ahead = (6 - today.weekday()) % 7 or 7
            return (today + timedelta(days=days_ahead)).isoformat()
        return None


# ── Счётчик токенов через Redis (без DB-модели) ───────────────────────────

def _track_tokens(count: int) -> None:
    """Накапливает расход токенов в Redis. Не блокирует при ошибке."""
    try:
        from django.core.cache import cache
        today_key = f'gigachat:tokens:{date.today().isoformat()}'
        # 30 дней хранения дневного счётчика
        cache.get_or_set(today_key, 0, timeout=86400 * 30)
        cache.incr(today_key, count)
        # Вечный суммарный счётчик (сбрасывается при flush redis)
        cache.get_or_set('gigachat:tokens:total', 0, timeout=None)
        cache.incr('gigachat:tokens:total', count)
    except Exception as exc:
        logger.debug('_track_tokens недоступен: %s', exc)


# ── Фабрика ───────────────────────────────────────────────────────────────

def get_llm_provider() -> LLMProvider:
    """
    Возвращает нужный провайдер по settings.py.

    Если DEBUG=True и USE_REGEX_FALLBACK_IN_DEBUG=True — всегда regex
    (защита токенов при разработке).

    Если LLM_PROVIDER='gigachat' и GIGACHAT_CREDENTIALS пустой/короткий —
    поднимает ImproperlyConfigured (конфигурационная ошибка, не fallback).
    Fallback на regex происходит только при runtime-ошибках GigaChat (в parser.py).
    """
    from django.conf import settings
    from django.core.exceptions import ImproperlyConfigured

    if settings.DEBUG and getattr(settings, 'USE_REGEX_FALLBACK_IN_DEBUG', False):
        logger.debug('DEBUG + USE_REGEX_FALLBACK_IN_DEBUG=True → RegexFallbackProvider')
        return RegexFallbackProvider()

    provider_name = getattr(settings, 'LLM_PROVIDER', 'gigachat')

    if provider_name == 'gigachat':
        credentials = (getattr(settings, 'GIGACHAT_CREDENTIALS', '') or '').strip()
        if not credentials or len(credentials) < 50:
            raise ImproperlyConfigured(
                'GIGACHAT_CREDENTIALS не настроен в .env (пустой или короче 50 символов). '
                'Проверьте файл .env в корне проекта и перезапустите docker-compose. '
                'Получить ключ: https://developers.sber.ru/studio'
            )
        return GigaChatProvider(credentials)

    # LLM_PROVIDER='regex' или любое другое значение
    return RegexFallbackProvider()
