from django.urls import path

from . import views

app_name = 'payments'

urlpatterns = [
    # Webhook от ЮКассы — URL совпадает с прописанным в ЛК ЮКассы
    path('webhook/', views.payment_webhook, name='webhook'),
    # Страница возврата после оплаты на ЮКассе
    path('return/', views.payment_return, name='return'),

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
