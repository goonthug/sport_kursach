from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def review_list(request):
    """Список отзывов."""
    return render(request, 'reviews/review_list.html', {})