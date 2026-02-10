from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('', views.inventory_list, name='list'),
    path('create/', views.inventory_create, name='create'),
    path('my/', views.my_inventory, name='my_inventory'),
    path('earnings/', views.owner_earnings_analytics, name='owner_earnings'),
    path('favorites/', views.favorites_list, name='favorites'),
    path('<uuid:pk>/', views.inventory_detail, name='detail'),
    path('<uuid:pk>/favorite/', views.favorite_toggle, name='favorite_toggle'),
    path('<uuid:pk>/edit/', views.inventory_update, name='update'),
    path('<uuid:pk>/delete/', views.inventory_delete, name='delete'),
]