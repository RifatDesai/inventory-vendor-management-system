from django.contrib import admin
from django.urls import path, include

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

from procurement.views import (
    purchase_orders_view,
    approve_purchase_order_view,
)


urlpatterns = [
    path('admin/', admin.site.urls),

    # Authentication
    path(
        'api/v1/auth/',
        include('accounts.urls'),
    ),

    # Products
    path(
        'api/v1/products/',
        include('products.urls'),
    ),

    # Inventory
    path(
        'api/v1/inventory/',
        include('inventory.urls'),
    ),

    # Purchase Requests
    path(
        'api/v1/purchase-requests/',
        include('procurement.urls'),
    ),

    # Purchase Orders
    # GET  /api/v1/purchase-orders/
    # POST /api/v1/purchase-orders/
    path(
        'api/v1/purchase-orders/',
        purchase_orders_view,
        name='purchase-orders',
    ),
    path(
    'api/v1/purchase-orders/<int:purchase_order_id>/approve/',
    approve_purchase_order_view,
    name='purchase-order-approve',
    ),

    # Swagger / OpenAPI
    path(
        'api/schema/',
        SpectacularAPIView.as_view(),
        name='schema',
    ),
    path(
        'api/docs/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui',
    ),
]