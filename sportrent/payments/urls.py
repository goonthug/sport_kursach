from django.urls import path

from . import views

app_name = 'payments'

urlpatterns = [
    path(
        'rental/<uuid:rental_id>/',
        views.create_payment,
        {'purpose': 'rental_main'},
        name='create_rental_payment',
    ),
    path(
        'extension/<uuid:rental_id>/',
        views.create_payment,
        {'purpose': 'extension'},
        name='create_extension_payment',
    ),
    path(
        'overdue/<uuid:rental_id>/',
        views.create_payment,
        {'purpose': 'overdue'},
        name='create_overdue_payment',
    ),
]
