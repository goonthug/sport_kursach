from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def rental_list(request):
    """Список аренд пользователя."""
    return render(request, 'rentals/rental_list.html', {})
