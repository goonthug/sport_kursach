from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('', views.inventory_list, name='list'),
    path('create/', views.inventory_create, name='create'),
    path('my/', views.my_inventory, name='my_inventory'),
    path('<uuid:pk>/', views.inventory_detail, name='detail'),
    path('<uuid:pk>/edit/', views.inventory_update, name='update'),
    path('<uuid:pk>/delete/', views.inventory_delete, name='delete'),
]