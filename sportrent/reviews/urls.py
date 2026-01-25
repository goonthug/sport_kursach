from django.urls import path
from . import views

app_name = 'reviews'

urlpatterns = [
    path('', views.review_list, name='list'),
    path('create/<uuid:rental_id>/', views.review_create, name='create'),
    path('<uuid:pk>/approve/', views.review_approve, name='approve'),
    path('<uuid:pk>/reject/', views.review_reject, name='reject'),
]