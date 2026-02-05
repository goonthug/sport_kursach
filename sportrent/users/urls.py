"""
URL конфигурация для users приложения.
"""

from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Будем добавлять постепенно
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('bank-account/add/', views.bank_account_add, name='bank_account_add'),
    path('bank-account/<uuid:pk>/delete/', views.bank_account_delete, name='bank_account_delete'),
]