from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('', views.inventory_list, name='list'),
    path('create/', views.inventory_create, name='create'),
    path('/', views.inventory_detail, name='detail'),
    path('/edit/', views.inventory_update, name='update'),
    path('/delete/', views.inventory_delete, name='delete'),
]