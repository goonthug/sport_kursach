"""
Кастомная JWT-аутентификация через httpOnly cookie.
Позволяет React-фронту не хранить токены в localStorage (защита от XSS).
"""

from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


class CookieJWTAuthentication(JWTAuthentication):
    """Читает access_token из httpOnly cookie; fallback на заголовок Authorization."""

    def authenticate(self, request):
        cookie_name = settings.SIMPLE_JWT.get('AUTH_COOKIE', 'access_token')
        raw_token = request.COOKIES.get(cookie_name)

        if raw_token is None:
            # Разрешаем обычный заголовок для отладки через DRF Browsable API / Postman
            return super().authenticate(request)

        try:
            validated_token = self.get_validated_token(raw_token)
        except (InvalidToken, TokenError):
            return None

        return self.get_user(validated_token), validated_token
