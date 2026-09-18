from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    inline_serializer,
)

from .services import (
    create_purchase_request,
    approve_purchase_request,
    create_purchase_order,
    approve_purchase_order,
)

from .models import PurchaseOrder


# ============================================================
# CREATE PURCHASE REQUEST
# ============================================================

@extend_schema(
    request=inline_serializer(
        name="CreatePurchaseRequest",
        fields={
            "required_date": serializers.DateField(
                required=False,
                allow_null=True,
            ),
            "reason": serializers.CharField(
                required=False,
                allow_blank=True,
                allow_null=True,
            ),
            "items": serializers.ListField(
                child=serializers.DictField(),
            ),
        },
    ),
    responses={
        201: inline_serializer(
            name="CreatePurchaseRequestResponse",
            fields={
                "success": serializers.BooleanField(),
                "message": serializers.CharField(),
                "data": serializers.DictField(),
                "errors": serializers.JSONField(allow_null=True),
                "meta": serializers.DictField(),
            },
        ),
        400: OpenApiResponse(
            description="Validation failed"
        ),
        401: OpenApiResponse(
            description="Authentication required"
        ),
    },
)
@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def create_purchase_request_view(request):

    required_date = request.data.get("required_date")
    reason = request.data.get("reason")
    items = request.data.get("items")

    errors = {}

    if items is None:
        errors["items"] = [
            "This field is required."
        ]

    elif not isinstance(items, list) or not items:
        errors["items"] = [
            "At least one purchase request item is required."
        ]

    if errors:
        return Response(
            {
                "success": False,
                "message": "Validation failed.",
                "data": None,
                "errors": errors,
                "meta": {},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        purchase_request = create_purchase_request(
            user_id=request.user.id,
            required_date=required_date,
            reason=reason,
            items=items,
        )

        request_items = []

        for item in purchase_request.items.all():
            request_items.append(
                {
                    "product_id": item.product_id,
                    "quantity": str(item.quantity),
                    "remarks": item.remarks,
                }
            )

        return Response(
            {
                "success": True,
                "message": "Purchase request created successfully.",
                "data": {
                    "id": purchase_request.id,
                    "request_no": purchase_request.request_no,
                    "requested_by": purchase_request.requested_by,
                    "status": purchase_request.status,
                    "required_date": purchase_request.required_date,
                    "reason": purchase_request.reason,
                    "created_at": purchase_request.created_at,
                    "items": request_items,
                },
                "errors": None,
                "meta": {},
            },
            status=status.HTTP_201_CREATED,
        )

    except ValueError as error:
        return Response(
            {
                "success": False,
                "message": "Unable to create purchase request.",
                "data": None,
                "errors": {
                    "detail": str(error)
                },
                "meta": {},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


# ============================================================
# APPROVE PURCHASE REQUEST
# ============================================================

@extend_schema(
    responses={
        200: inline_serializer(
            name="ApprovePurchaseRequestResponse",
            fields={
                "success": serializers.BooleanField(),
                "message": serializers.CharField(),
                "data": serializers.DictField(),
                "errors": serializers.JSONField(allow_null=True),
                "meta": serializers.DictField(),
            },
        ),
        400: OpenApiResponse(
            description="Validation failed"
        ),
        401: OpenApiResponse(
            description="Authentication required"
        ),
        403: OpenApiResponse(
            description="Approval permission denied"
        ),
        404: OpenApiResponse(
            description="Purchase request not found"
        ),
    },
)
@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def approve_purchase_request_view(request, request_id):

    allowed_roles = [
        "Super Admin",
        "Purchase Manager",
    ]

    user_role = request.user.role.name if request.user.role else None

    if user_role not in allowed_roles:
        return Response(
            {
                "success": False,
                "message": "Approval permission denied.",
                "data": None,
                "errors": {
                    "permission": (
                        "You are not authorized to approve "
                        "purchase requests."
                    )
                },
                "meta": {},
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        purchase_request = approve_purchase_request(
            request_id=request_id,
            user_id=request.user.id,
        )

        items = []

        for item in purchase_request.items.all():
            items.append(
                {
                    "product_id": item.product_id,
                    "quantity": str(item.quantity),
                    "remarks": item.remarks,
                }
            )

        return Response(
            {
                "success": True,
                "message": "Purchase request approved successfully.",
                "data": {
                    "id": purchase_request.id,
                    "request_no": purchase_request.request_no,
                    "requested_by": purchase_request.requested_by,
                    "status": purchase_request.status,
                    "required_date": purchase_request.required_date,
                    "reason": purchase_request.reason,
                    "created_at": purchase_request.created_at,
                    "items": items,
                    "approved_by": request.user.id,
                },
                "errors": None,
                "meta": {},
            },
            status=status.HTTP_200_OK,
        )

    except ValueError as error:
        return Response(
            {
                "success": False,
                "message": str(error),
                "data": None,
                "errors": {
                    "approval": str(error)
                },
                "meta": {},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


# ============================================================
# PURCHASE ORDERS - GET + POST
# ============================================================

@extend_schema(
    methods=["GET"],
    responses={
        200: inline_serializer(
            name="PurchaseOrderListResponse",
            fields={
                "success": serializers.BooleanField(),
                "message": serializers.CharField(),
                "data": serializers.ListField(
                    child=serializers.DictField()
                ),
                "errors": serializers.JSONField(allow_null=True),
                "meta": serializers.DictField(),
            },
        ),
        401: OpenApiResponse(
            description="Authentication required"
        ),
    },
)
@extend_schema(
    methods=["POST"],
    request=inline_serializer(
        name="CreatePurchaseOrderRequest",
        fields={
            "vendor_id": serializers.IntegerField(),
            "warehouse_id": serializers.IntegerField(),
            "order_date": serializers.DateField(),
            "expected_date": serializers.DateField(
                required=False,
                allow_null=True,
            ),
            "terms": serializers.CharField(
                required=False,
                allow_blank=True,
                allow_null=True,
            ),
            "header_discount": serializers.DecimalField(
                max_digits=14,
                decimal_places=2,
                required=False,
                default=0,
            ),
            "header_tax": serializers.DecimalField(
                max_digits=14,
                decimal_places=2,
                required=False,
                default=0,
            ),
            "charges": serializers.DecimalField(
                max_digits=14,
                decimal_places=2,
                required=False,
                default=0,
            ),
            "items": serializers.ListField(
                child=serializers.DictField(),
            ),
        },
    ),
    responses={
        201: inline_serializer(
            name="CreatePurchaseOrderResponse",
            fields={
                "success": serializers.BooleanField(),
                "message": serializers.CharField(),
                "data": serializers.DictField(),
                "errors": serializers.JSONField(allow_null=True),
                "meta": serializers.DictField(),
            },
        ),
        400: OpenApiResponse(
            description="Validation failed"
        ),
        401: OpenApiResponse(
            description="Authentication required"
        ),
    },
)
@api_view(["GET", "POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def purchase_orders_view(request):

    # ========================================================
    # GET - LIST PURCHASE ORDERS
    # ========================================================

    if request.method == "GET":

        purchase_orders = PurchaseOrder.objects.all().order_by("-id")

        data = []

        for purchase_order in purchase_orders:
            data.append(
                {
                    "id": purchase_order.id,
                    "po_no": purchase_order.po_no,
                    "vendor_id": purchase_order.vendor_id,
                    "warehouse_id": purchase_order.warehouse_id,
                    "order_date": purchase_order.order_date,
                    "expected_date": purchase_order.expected_date,
                    "terms": purchase_order.terms,
                    "status": purchase_order.status,
                    "subtotal": str(purchase_order.subtotal),
                    "discount": str(purchase_order.discount),
                    "tax": str(purchase_order.tax),
                    "charges": str(purchase_order.charges),
                    "total": str(purchase_order.total),
                }
            )

        return Response(
            {
                "success": True,
                "message": "Purchase orders retrieved successfully.",
                "data": data,
                "errors": None,
                "meta": {
                    "total": len(data)
                },
            },
            status=status.HTTP_200_OK,
        )

    # ========================================================
    # POST - CREATE PURCHASE ORDER
    # ========================================================

    vendor_id = request.data.get("vendor_id")
    warehouse_id = request.data.get("warehouse_id")
    order_date = request.data.get("order_date")
    expected_date = request.data.get("expected_date")
    terms = request.data.get("terms")

    header_discount = request.data.get("header_discount", 0)
    header_tax = request.data.get("header_tax", 0)
    charges = request.data.get("charges", 0)

    items = request.data.get("items")

    errors = {}

    if vendor_id is None:
        errors["vendor_id"] = [
            "This field is required."
        ]

    if warehouse_id is None:
        errors["warehouse_id"] = [
            "This field is required."
        ]

    if order_date is None:
        errors["order_date"] = [
            "This field is required."
        ]

    if items is None:
        errors["items"] = [
            "This field is required."
        ]

    elif not isinstance(items, list) or not items:
        errors["items"] = [
            "At least one purchase order item is required."
        ]

    if errors:
        return Response(
            {
                "success": False,
                "message": "Validation failed.",
                "data": None,
                "errors": errors,
                "meta": {},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        purchase_order = create_purchase_order(
            user_id=request.user.id,
            vendor_id=vendor_id,
            warehouse_id=warehouse_id,
            order_date=order_date,
            expected_date=expected_date,
            terms=terms,
            items=items,
            header_discount=header_discount,
            header_tax=header_tax,
            charges=charges,
        )

        order_items = []

        for item in purchase_order.items.all():
            order_items.append(
                {
                    "product_id": item.product_id,
                    "quantity": str(item.quantity),
                    "unit_price": str(item.unit_price),
                    "discount": str(item.discount),
                    "tax": str(item.tax),
                    "line_total": str(item.line_total),
                }
            )

        return Response(
            {
                "success": True,
                "message": "Purchase order created successfully.",
                "data": {
                    "id": purchase_order.id,
                    "po_no": purchase_order.po_no,
                    "vendor_id": purchase_order.vendor_id,
                    "warehouse_id": purchase_order.warehouse_id,
                    "order_date": purchase_order.order_date,
                    "expected_date": purchase_order.expected_date,
                    "terms": purchase_order.terms,
                    "status": purchase_order.status,
                    "subtotal": str(purchase_order.subtotal),
                    "discount": str(purchase_order.discount),
                    "tax": str(purchase_order.tax),
                    "charges": str(purchase_order.charges),
                    "total": str(purchase_order.total),
                    "items": order_items,
                    "created_by": request.user.id,
                },
                "errors": None,
                "meta": {},
            },
            status=status.HTTP_201_CREATED,
        )

    except ValueError as error:
        return Response(
            {
                "success": False,
                "message": "Unable to create purchase order.",
                "data": None,
                "errors": {
                    "detail": str(error)
                },
                "meta": {},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
# ============================================================
# APPROVE PURCHASE ORDER
# ============================================================

@extend_schema(
    responses={
        200: inline_serializer(
            name="ApprovePurchaseOrderResponse",
            fields={
                "success": serializers.BooleanField(),
                "message": serializers.CharField(),
                "data": serializers.DictField(),
                "errors": serializers.JSONField(allow_null=True),
                "meta": serializers.DictField(),
            },
        ),
        400: OpenApiResponse(
            description="Validation failed"
        ),
        401: OpenApiResponse(
            description="Authentication required"
        ),
        403: OpenApiResponse(
            description="Approval permission denied"
        ),
        404: OpenApiResponse(
            description="Purchase order not found"
        ),
    },
)
@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def approve_purchase_order_view(request, purchase_order_id):

    allowed_roles = [
        "Super Admin",
        "Purchase Manager",
    ]

    user_role = request.user.role.name if request.user.role else None

    if user_role not in allowed_roles:
        return Response(
            {
                "success": False,
                "message": "Approval permission denied.",
                "data": None,
                "errors": {
                    "permission": (
                        "You are not authorized to approve "
                        "purchase orders."
                    )
                },
                "meta": {},
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        purchase_order = approve_purchase_order(
            purchase_order_id=purchase_order_id,
            user_id=request.user.id,
        )

        order_items = []

        for item in purchase_order.items.all():
            order_items.append(
                {
                    "product_id": item.product_id,
                    "quantity": str(item.quantity),
                    "unit_price": str(item.unit_price),
                    "discount": str(item.discount),
                    "tax": str(item.tax),
                    "line_total": str(item.line_total),
                }
            )

        return Response(
            {
                "success": True,
                "message": "Purchase order approved successfully.",
                "data": {
                    "id": purchase_order.id,
                    "po_no": purchase_order.po_no,
                    "vendor_id": purchase_order.vendor_id,
                    "warehouse_id": purchase_order.warehouse_id,
                    "order_date": purchase_order.order_date,
                    "expected_date": purchase_order.expected_date,
                    "terms": purchase_order.terms,
                    "status": purchase_order.status,
                    "subtotal": str(purchase_order.subtotal),
                    "discount": str(purchase_order.discount),
                    "tax": str(purchase_order.tax),
                    "charges": str(purchase_order.charges),
                    "total": str(purchase_order.total),
                    "items": order_items,
                    "approved_by": request.user.id,
                },
                "errors": None,
                "meta": {},
            },
            status=status.HTTP_200_OK,
        )

    except ValueError as error:
        return Response(
            {
                "success": False,
                "message": str(error),
                "data": None,
                "errors": {
                    "approval": str(error)
                },
                "meta": {},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )