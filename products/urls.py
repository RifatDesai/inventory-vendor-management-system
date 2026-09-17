from django.urls import path

from django.urls import path

from .views import (
    products_list_create,
    product_detail,
    deactivate_product
)

urlpatterns = [
    path('', products_list_create, name='products-list-create'),
    path('<int:product_id>/', product_detail, name='product-detail'),
    path('<int:product_id>/deactivate/', deactivate_product, name='deactivate-product'),
]