from django.urls import path
from .api_views import (
    LoginAPIView, LogoutAPIView, RegisterAPIView,
    ProfileAPIView, TokenRefreshCookieView, ChangePasswordAPIView,
)

urlpatterns = [
    path('login/', LoginAPIView.as_view(), name='api-login'),
    path('logout/', LogoutAPIView.as_view(), name='api-logout'),
    path('register/', RegisterAPIView.as_view(), name='api-register'),
    path('profile/', ProfileAPIView.as_view(), name='api-profile'),
    path('token/refresh/', TokenRefreshCookieView.as_view(), name='api-token-refresh'),
    path('change-password/', ChangePasswordAPIView.as_view(), name='api-change-password'),
]
