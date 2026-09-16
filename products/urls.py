from django.urls import path
from .views import add_product

urlpatterns = [
    path('', add_product, name='add-product'),
]