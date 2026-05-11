"""
Декораторы для проверки ролей пользователей.
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def role_required(*roles):
    """
    Декоратор проверки роли пользователя.
    Заменяет @user_passes_test(is_staff) с явным указанием допустимых ролей.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('users:login')
            if request.user.role not in roles:
                messages.error(request, 'Недостаточно прав для выполнения этого действия.')
                return redirect('core:home')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
