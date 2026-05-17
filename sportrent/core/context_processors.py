"""
Контекстный процессор геолокации — передаёт данные о местоположении
пользователя (из Django-сессии) во все шаблоны.
"""


def geo_context(request):
    """Добавляет geo-переменные в контекст каждого шаблона."""
    return {
        'user_city': request.session.get('user_city', ''),
        'user_address': request.session.get('user_address', ''),
        'geo_source': request.session.get('geo_source', ''),
    }
