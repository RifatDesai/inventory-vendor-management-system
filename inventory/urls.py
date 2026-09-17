from django.urls import path

from .views import (
    list_inventory,
    transactions,
    create_transfer,
    create_adjustment,
)


urlpatterns = [
    path('', list_inventory, name='inventory-list'),

    path(
        'transactions/',
        transactions,
        name='inventory-transactions'
    ),

    path(
        'transfers/',
        create_transfer,
        name='inventory-transfer'
    ),
    path('adjustments/', create_adjustment, name='inventory-adjustment'),
]