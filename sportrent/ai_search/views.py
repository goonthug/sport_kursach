"""
REST API endpoint для AI-геолокационного поиска инвентаря.
Центральная фича диплома: принимает текст → LLM парсинг → DB поиск → JSON.
"""

import logging
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from inventory.serializers import InventoryListSerializer
from .parser import parse_query
from .search import search_inventory

logger = logging.getLogger('ai_search')


class AISearchView(APIView):
    """
    POST /api/v1/ai-search/

    Тело запроса: { "query": "беговые лыжи в Казани до 500р на завтра" }

    Ответ:
    {
        "query": "исходный запрос",
        "parsed": { "category_query": "...", "city_name": "...", ... },
        "results": [ { inventory } ],
        "count": 5
    }
    """

    permission_classes = [AllowAny]

    def post(self, request):
        query = (request.data.get('query') or '').strip()
        if not query:
            return Response(
                {'error': 'Поле query обязательно'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(query) > 500:
            return Response(
                {'error': 'Запрос слишком длинный (максимум 500 символов)'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            parsed = parse_query(query)
            inventory_qs = search_inventory(parsed)
            serializer = InventoryListSerializer(
                inventory_qs,
                many=True,
                context={'request': request},
            )
            return Response({
                'query': query,
                'parsed': parsed.model_dump(),
                'results': serializer.data,
                'count': len(serializer.data),
            })
        except Exception as exc:
            logger.error('Ошибка AI-поиска для запроса "%s": %s', query, exc)
            return Response(
                {'error': 'Внутренняя ошибка при обработке запроса'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
