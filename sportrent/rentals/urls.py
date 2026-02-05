from django.urls import path
from . import views

app_name = 'rentals'

urlpatterns = [
    path('', views.rental_list, name='list'),
    path('<uuid:pk>/', views.rental_detail, name='detail'),
    path('create/<uuid:inventory_id>/', views.rental_create, name='create'),
    path('<uuid:pk>/pay/', views.rental_pay, name='pay'),
    path('<uuid:pk>/confirm/', views.rental_confirm, name='confirm'),
    path('<uuid:pk>/reject/', views.rental_reject, name='reject'),
    path('<uuid:pk>/complete/', views.rental_complete, name='complete'),
    path('<uuid:pk>/extend/', views.rental_extend, name='extend'),
    path('<uuid:pk>/cancel/', views.rental_cancel, name='cancel'),
]