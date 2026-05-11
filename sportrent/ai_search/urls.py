from django.urls import path
from .views import AISearchView

urlpatterns = [
    path('', AISearchView.as_view(), name='ai-search'),
]
