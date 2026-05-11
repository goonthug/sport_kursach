"""
Парсинг естественно-языковых запросов через Groq LLM (langchain-groq).
При отсутствии GROQ_API_KEY или ошибке API — возвращает исходный запрос как keywords (fallback).
"""

import logging
from typing import Optional
from datetime import date

from django.conf import settings
from pydantic import BaseModel, Field

logger = logging.getLogger('ai_search')


class ParsedSearchQuery(BaseModel):
    """Структурированный результат разбора поискового запроса."""

    category_query: Optional[str] = Field(None, description='Тип инвентаря (беговые лыжи, велосипед)')
    city_name: Optional[str] = Field(None, description='Название города в России')
    start_date: Optional[str] = Field(None, description='Дата начала аренды YYYY-MM-DD')
    end_date: Optional[str] = Field(None, description='Дата окончания аренды YYYY-MM-DD')
    max_price: Optional[float] = Field(None, description='Максимальная цена в руб/день')
    keywords: Optional[str] = Field(None, description='Дополнительные ключевые слова')


def parse_query(query: str) -> ParsedSearchQuery:
    """
    Разбирает текстовый запрос пользователя через Groq LLM.
    Возвращает ParsedSearchQuery. При любой ошибке — fallback с keywords=query.
    """
    api_key = getattr(settings, 'GROQ_API_KEY', '')

    if not api_key:
        logger.debug('GROQ_API_KEY не задан, используется fallback-парсинг')
        return ParsedSearchQuery(keywords=query)

    try:
        from langchain_groq import ChatGroq

        llm = ChatGroq(
            model='llama-3.3-70b-versatile',
            api_key=api_key,
            temperature=0,
            max_retries=2,
        )
        structured_llm = llm.with_structured_output(ParsedSearchQuery)

        prompt = (
            f'Сегодня {date.today().isoformat()}. '
            'Разбери поисковый запрос по аренде спортивного инвентаря на русском языке.\n'
            f'Запрос: "{query}"\n\n'
            'Извлеки поля:\n'
            '- category_query: тип инвентаря (например "беговые лыжи", "велосипед", "ролики")\n'
            '- city_name: название города в России\n'
            '- start_date: дата начала аренды YYYY-MM-DD (учитывай "завтра", "на выходных" и т.д.)\n'
            '- end_date: дата окончания аренды YYYY-MM-DD\n'
            '- max_price: максимальная цена в рублях в день\n'
            '- keywords: прочие ключевые слова\n\n'
            'Если поле не упомянуто — верни null.'
        )

        result = structured_llm.invoke(prompt)
        logger.info('AI-парсинг: "%s" → %s', query, result.model_dump())
        return result

    except Exception as exc:
        logger.warning('Ошибка AI-парсинга, fallback: %s', exc)
        return ParsedSearchQuery(keywords=query)
