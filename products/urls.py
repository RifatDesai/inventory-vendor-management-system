from django.urls import path
from .views import add_product, edit_product, deactivate_product

urlpatterns = [
    path('', add_product, name='add-product'),
    path('<int:product_id>/', edit_product, name='edit-product'),
    path('<int:product_id>/deactivate/', deactivate_product, name='deactivate-product'),
]