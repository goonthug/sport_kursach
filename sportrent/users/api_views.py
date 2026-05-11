"""
REST API views для аутентификации и профиля пользователей.
JWT хранится в httpOnly cookie — токены не доступны из JS (защита от XSS).
"""

import logging
from django.contrib.auth import authenticate
from django.db import transaction
from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, Client, Owner, PassportNDA
from .serializers import UserSerializer, LoginSerializer, RegisterSerializer

logger = logging.getLogger('users')


def _set_jwt_cookies(response, refresh):
    """Устанавливает access и refresh JWT в httpOnly cookie."""
    jwt = settings.SIMPLE_JWT
    response.set_cookie(
        key=jwt['AUTH_COOKIE'],
        value=str(refresh.access_token),
        max_age=int(jwt['ACCESS_TOKEN_LIFETIME'].total_seconds()),
        httponly=jwt['AUTH_COOKIE_HTTP_ONLY'],
        samesite=jwt['AUTH_COOKIE_SAMESITE'],
        secure=jwt['AUTH_COOKIE_SECURE'],
    )
    response.set_cookie(
        key=jwt['AUTH_COOKIE_REFRESH'],
        value=str(refresh),
        max_age=int(jwt['REFRESH_TOKEN_LIFETIME'].total_seconds()),
        httponly=jwt['AUTH_COOKIE_HTTP_ONLY'],
        samesite=jwt['AUTH_COOKIE_SAMESITE'],
        secure=jwt['AUTH_COOKIE_SECURE'],
    )


class LoginAPIView(APIView):
    """POST /api/v1/auth/login/ — JWT-аутентификация, токены в httpOnly cookie."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            username=serializer.validated_data['email'],
            password=serializer.validated_data['password'],
        )
        if user is None:
            return Response(
                {'error': 'Неверный email или пароль'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if user.status == 'blocked':
            return Response({'error': 'Аккаунт заблокирован'}, status=status.HTTP_403_FORBIDDEN)

        refresh = RefreshToken.for_user(user)
        response = Response({'user': UserSerializer(user).data})
        _set_jwt_cookies(response, refresh)
        logger.info('API-вход: %s', user.email)
        return response


class LogoutAPIView(APIView):
    """POST /api/v1/auth/logout/ — удаляет JWT cookie."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        jwt = settings.SIMPLE_JWT
        response = Response({'message': 'Выход выполнен'})
        response.delete_cookie(jwt['AUTH_COOKIE'])
        response.delete_cookie(jwt['AUTH_COOKIE_REFRESH'])
        return response


class RegisterAPIView(APIView):
    """POST /api/v1/auth/register/ — регистрация с JWT cookie в ответе."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    email=data['email'],
                    password=data['password'],
                    role=data['role'],
                    phone=data.get('phone') or None,
                )
                if data['role'] == 'client':
                    Client.objects.create(
                        user=user,
                        full_name=data['full_name'],
                        passport_series=data.get('passport_series') or None,
                        passport_number=data.get('passport_number') or None,
                        passport_issue_date=data.get('passport_issue_date'),
                        passport_department_code=data.get('passport_department_code') or None,
                    )
                    xff = request.META.get('HTTP_X_FORWARDED_FOR')
                    ip = xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')
                    PassportNDA.objects.create(user=user, version='v1.0', ip_address=ip)
                elif data['role'] == 'owner':
                    Owner.objects.create(
                        user=user,
                        full_name=data['full_name'],
                        tax_number=data.get('tax_number') or None,
                    )

            refresh = RefreshToken.for_user(user)
            response = Response(
                {'user': UserSerializer(user).data},
                status=status.HTTP_201_CREATED,
            )
            _set_jwt_cookies(response, refresh)
            logger.info('API-регистрация: %s, роль: %s', user.email, user.role)
            return response

        except Exception as e:
            logger.error('Ошибка API-регистрации: %s', e)
            return Response(
                {'error': 'Ошибка при регистрации'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ProfileAPIView(APIView):
    """GET /api/v1/auth/profile/ — профиль текущего пользователя."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'user': UserSerializer(request.user).data})


class TokenRefreshCookieView(APIView):
    """POST /api/v1/auth/token/refresh/ — обновление access_token из refresh cookie."""

    permission_classes = [AllowAny]

    def post(self, request):
        jwt = settings.SIMPLE_JWT
        refresh_cookie = request.COOKIES.get(jwt['AUTH_COOKIE_REFRESH'])
        if not refresh_cookie:
            return Response(
                {'error': 'Refresh token не найден'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            refresh = RefreshToken(refresh_cookie)
            response = Response({'message': 'Токен обновлён'})
            response.set_cookie(
                key=jwt['AUTH_COOKIE'],
                value=str(refresh.access_token),
                max_age=int(jwt['ACCESS_TOKEN_LIFETIME'].total_seconds()),
                httponly=jwt['AUTH_COOKIE_HTTP_ONLY'],
                samesite=jwt['AUTH_COOKIE_SAMESITE'],
                secure=jwt['AUTH_COOKIE_SECURE'],
            )
            return response
        except Exception:
            return Response(
                {'error': 'Недействительный refresh token'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
