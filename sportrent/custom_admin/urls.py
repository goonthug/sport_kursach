from django.urls import path
from . import views

app_name = 'custom_admin'

urlpatterns = [
    path('', views.admin_dashboard, name='dashboard'),
    path('users/', views.admin_users, name='users'),
    path('users/<uuid:user_id>/block/', views.admin_user_block, name='user_block'),
    path('users/<uuid:user_id>/unblock/', views.admin_user_unblock, name='user_unblock'),
    path('inventory/', views.admin_inventory, name='inventory'),
    path('inventory/<uuid:pk>/approve/', views.admin_inventory_approve, name='inventory_approve'),
    path('inventory/<uuid:pk>/reject/', views.admin_inventory_reject, name='inventory_reject'),

    # Экспорт
    path('export/inventory/xlsx/', views.export_inventory_xlsx, name='export_inventory_xlsx'),
    path('export/inventory/pdf/', views.export_inventory_pdf, name='export_inventory_pdf'),
    path('export/rentals/xlsx/', views.export_rentals_xlsx, name='export_rentals_xlsx'),
    path('export/stats/pdf/', views.export_stats_pdf, name='export_stats_pdf'),
]
