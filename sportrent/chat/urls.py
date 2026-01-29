from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.chat_list, name='list'),
    path('inventory/<uuid:inventory_id>/', views.start_chat_by_inventory, name='start_by_inventory'),
    path('<uuid:rental_id>/', views.chat_detail, name='detail'),
    path('<uuid:rental_id>/start/', views.start_chat, name='start'),
]