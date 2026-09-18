from django.urls import path

from .views import (
    create_purchase_request_view,
    approve_purchase_request_view,
)


urlpatterns = [
    path(
        "",
        create_purchase_request_view,
        name="purchase-request-create",
    ),
    path(
        "<int:request_id>/approve/",
        approve_purchase_request_view,
        name="purchase-request-approve",
    ),
]