from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test

def is_staff(user):
    return user.is_authenticated and user.role in ['manager', 'administrator']

@login_required
@user_passes_test(is_staff)
def admin_dashboard(request):
    """Панель администратора."""
    return render(request, 'custom_admin/dashboard.html', {})