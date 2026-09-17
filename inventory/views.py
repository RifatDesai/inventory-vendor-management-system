from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes
)
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    inline_serializer
)

from .models import Inventory, StockTransaction
from .services import (
    post_stock_transaction,
    create_stock_transfer,
    create_stock_adjustment,
)


# ============================================================
# CURRENT INVENTORY
# ============================================================

@extend_schema(
    responses={
        200: inline_serializer(
            name='InventoryListResponse',
            fields={
                'success': serializers.BooleanField(),
                'message': serializers.CharField(),
                'data': serializers.ListField(
                    child=serializers.DictField()
                ),
                'errors': serializers.JSONField(allow_null=True),
                'meta': serializers.DictField(),
            },
        ),
    },
)
@api_view(['GET'])
def list_inventory(request):

    inventory_records = Inventory.objects.all().order_by('-id')

    data = []

    for inventory in inventory_records:
        data.append({
            'id': inventory.id,
            'product_id': inventory.product_id,
            'warehouse_id': inventory.warehouse_id,
            'available_qty': inventory.quantity,
            'reserved_qty': inventory.reserved_qty,
            'damaged_qty': inventory.damaged_qty,
            'total_quantity': inventory.total_quantity,
        })

    return Response({
        'success': True,
        'message': 'Inventory retrieved successfully.',
        'data': data,
        'errors': None,
        'meta': {
            'total': len(data)
        }
    }, status=status.HTTP_200_OK)


# ============================================================
# STOCK TRANSACTIONS - GET + POST
# ============================================================

@extend_schema(
    methods=['GET'],
    responses={
        200: inline_serializer(
            name='StockTransactionListResponse',
            fields={
                'success': serializers.BooleanField(),
                'message': serializers.CharField(),
                'data': serializers.ListField(
                    child=serializers.DictField()
                ),
                'errors': serializers.JSONField(allow_null=True),
                'meta': serializers.DictField(),
            },
        ),
    },
)
@extend_schema(
    methods=['POST'],
    request=inline_serializer(
        name='PostStockTransactionRequest',
        fields={
            'product_id': serializers.IntegerField(),
            'warehouse_id': serializers.IntegerField(),
            'type': serializers.ChoiceField(
                choices=[
                    'STOCK_IN',
                    'STOCK_OUT'
                ]
            ),
            'quantity': serializers.IntegerField(),
            'reference_type': serializers.CharField(
                required=False,
                allow_blank=True,
                allow_null=True
            ),
            'reference_id': serializers.IntegerField(
                required=False,
                allow_null=True
            ),
            'reason': serializers.CharField(
                required=False,
                allow_blank=True,
                allow_null=True
            ),
        },
    ),
    responses={
        201: inline_serializer(
            name='PostStockTransactionResponse',
            fields={
                'success': serializers.BooleanField(),
                'message': serializers.CharField(),
                'data': serializers.DictField(),
                'errors': serializers.JSONField(allow_null=True),
                'meta': serializers.DictField(),
            },
        ),
        400: OpenApiResponse(
            description='Validation failed'
        ),
        401: OpenApiResponse(
            description='Authentication required'
        ),
    },
)
@api_view(['GET', 'POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def transactions(request):

    # ========================================================
    # GET - Transaction History
    # ========================================================

    if request.method == 'GET':

        transaction_records = StockTransaction.objects.all().order_by(
            '-created_at',
            '-id'
        )

        data = []

        for transaction in transaction_records:
            data.append({
                'id': transaction.id,
                'product_id': transaction.product_id,
                'warehouse_id': transaction.warehouse_id,
                'type': transaction.type,
                'quantity': transaction.quantity,
                'reference_type': transaction.reference_type,
                'reference_id': transaction.reference_id,
                'reason': transaction.reason,
                'created_by': transaction.created_by,
                'created_at': transaction.created_at,
            })

        return Response({
            'success': True,
            'message': 'Stock transactions retrieved successfully.',
            'data': data,
            'errors': None,
            'meta': {
                'total': len(data)
            }
        }, status=status.HTTP_200_OK)

    # ========================================================
    # POST - Stock Transaction
    # ========================================================

    product_id = request.data.get('product_id')
    warehouse_id = request.data.get('warehouse_id')
    transaction_type = request.data.get('type')
    quantity = request.data.get('quantity')

    reference_type = request.data.get('reference_type')
    reference_id = request.data.get('reference_id')
    reason = request.data.get('reason')

    errors = {}

    if product_id is None:
        errors['product_id'] = ['This field is required.']

    if warehouse_id is None:
        errors['warehouse_id'] = ['This field is required.']

    if not transaction_type:
        errors['type'] = ['This field is required.']

    if quantity is None:
        errors['quantity'] = ['This field is required.']

    if errors:
        return Response({
            'success': False,
            'message': 'Validation failed.',
            'data': None,
            'errors': errors,
            'meta': {}
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        product_id = int(product_id)
        warehouse_id = int(warehouse_id)
        quantity = int(quantity)
    except (TypeError, ValueError):
        return Response({
            'success': False,
            'message': 'Validation failed.',
            'data': None,
            'errors': {
                'detail': (
                    'product_id, warehouse_id and quantity '
                    'must be valid integers.'
                )
            },
            'meta': {}
        }, status=status.HTTP_400_BAD_REQUEST)

    if product_id <= 0:
        errors['product_id'] = ['Must be greater than 0.']

    if warehouse_id <= 0:
        errors['warehouse_id'] = ['Must be greater than 0.']

    if quantity <= 0:
        errors['quantity'] = [
            'Quantity must be greater than zero.'
        ]

    if transaction_type not in ['STOCK_IN', 'STOCK_OUT']:
        errors['type'] = [
            'Only STOCK_IN and STOCK_OUT are supported.'
        ]

    if errors:
        return Response({
            'success': False,
            'message': 'Validation failed.',
            'data': None,
            'errors': errors,
            'meta': {}
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        inventory, transaction_record = post_stock_transaction(
            product_id=product_id,
            warehouse_id=warehouse_id,
            transaction_type=transaction_type,
            quantity=quantity,
            reference_type=reference_type,
            reference_id=reference_id,
            reason=reason,
            user_id=request.user.id
        )

        return Response({
            'success': True,
            'message': 'Stock transaction posted successfully.',
            'data': {
                'transaction': {
                    'id': transaction_record.id,
                    'product_id': transaction_record.product_id,
                    'warehouse_id': transaction_record.warehouse_id,
                    'type': transaction_record.type,
                    'quantity': transaction_record.quantity,
                    'reference_type': transaction_record.reference_type,
                    'reference_id': transaction_record.reference_id,
                    'reason': transaction_record.reason,
                    'created_by': transaction_record.created_by,
                    'created_at': transaction_record.created_at,
                },
                'inventory': {
                    'id': inventory.id,
                    'product_id': inventory.product_id,
                    'warehouse_id': inventory.warehouse_id,
                    'available_qty': inventory.quantity,
                    'reserved_qty': inventory.reserved_qty,
                    'damaged_qty': inventory.damaged_qty,
                    'total_quantity': inventory.total_quantity,
                }
            },
            'errors': None,
            'meta': {}
        }, status=status.HTTP_201_CREATED)

    except ValueError as e:
        return Response({
            'success': False,
            'message': 'Unable to complete the stock transaction.',
            'data': None,
            'errors': {
                'detail': str(e)
            },
            'meta': {}
        }, status=status.HTTP_400_BAD_REQUEST)
    # ============================================================
# STOCK TRANSFER
# ============================================================

@extend_schema(
    request=inline_serializer(
        name='CreateStockTransferRequest',
        fields={
            'from_warehouse_id': serializers.IntegerField(),
            'to_warehouse_id': serializers.IntegerField(),
            'items': serializers.ListField(
                child=serializers.DictField()
            ),
            'reason': serializers.CharField(
                required=False,
                allow_blank=True,
                allow_null=True
            ),
        },
    ),
    responses={
        201: inline_serializer(
            name='CreateStockTransferResponse',
            fields={
                'success': serializers.BooleanField(),
                'message': serializers.CharField(),
                'data': serializers.DictField(),
                'errors': serializers.JSONField(allow_null=True),
                'meta': serializers.DictField(),
            },
        ),
        400: OpenApiResponse(
            description='Validation failed'
        ),
        401: OpenApiResponse(
            description='Authentication required'
        ),
        403: OpenApiResponse(
            description='Transfer permission denied'
        ),
    },
)
@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def create_transfer(request):

    from_warehouse_id = request.data.get('from_warehouse_id')
    to_warehouse_id = request.data.get('to_warehouse_id')
    items = request.data.get('items')
    reason = request.data.get('reason')

    errors = {}

    if from_warehouse_id is None:
        errors['from_warehouse_id'] = [
            'This field is required.'
        ]

    if to_warehouse_id is None:
        errors['to_warehouse_id'] = [
            'This field is required.'
        ]

    if items is None:
        errors['items'] = [
            'This field is required.'
        ]

    if errors:
        return Response({
            'success': False,
            'message': 'Validation failed.',
            'data': None,
            'errors': errors,
            'meta': {}
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        from_warehouse_id = int(from_warehouse_id)
        to_warehouse_id = int(to_warehouse_id)
    except (TypeError, ValueError):
        return Response({
            'success': False,
            'message': 'Validation failed.',
            'data': None,
            'errors': {
                'detail': (
                    'Warehouse IDs must be valid integers.'
                )
            },
            'meta': {}
        }, status=status.HTTP_400_BAD_REQUEST)

    if not isinstance(items, list) or not items:
        return Response({
            'success': False,
            'message': 'Validation failed.',
            'data': None,
            'errors': {
                'items': [
                    'At least one transfer item is required.'
                ]
            },
            'meta': {}
        }, status=status.HTTP_400_BAD_REQUEST)

    if request.user.role and request.user.role.name not in [
        'Super Admin',
        'Inventory Manager',
        'Warehouse/Store Staff'
    ]:
        return Response({
            'success': False,
            'message': 'Transfer permission denied.',
            'data': None,
            'errors': {
                'permission': [
                    'You are not authorized to create stock transfers.'
                ]
            },
            'meta': {}
        }, status=status.HTTP_403_FORBIDDEN)

    try:
        transfer = create_stock_transfer(
            from_warehouse_id=from_warehouse_id,
            to_warehouse_id=to_warehouse_id,
            items=items,
            reason=reason,
            user_id=request.user.id
        )

        transfer_items = []

        for item in transfer.items.all():
            transfer_items.append({
                'product_id': item.product_id,
                'quantity': item.quantity
            })

        return Response({
            'success': True,
            'message': 'Stock transfer created successfully.',
            'data': {
                'id': transfer.id,
                'transfer_no': transfer.transfer_no,
                'from_warehouse_id': transfer.from_warehouse_id,
                'to_warehouse_id': transfer.to_warehouse_id,
                'status': transfer.status,
                'requested_by': transfer.requested_by,
                'created_at': transfer.created_at,
                'items': transfer_items
            },
            'errors': None,
            'meta': {}
        }, status=status.HTTP_201_CREATED)

    except ValueError as e:
        return Response({
            'success': False,
            'message': 'Unable to create stock transfer.',
            'data': None,
            'errors': {
                'detail': str(e)
            },
            'meta': {}
        }, status=status.HTTP_400_BAD_REQUEST)
@extend_schema(
    request=inline_serializer(
        name="StockAdjustmentRequest",
        fields={
            "product_id": serializers.IntegerField(),
            "warehouse_id": serializers.IntegerField(),
            "new_quantity": serializers.IntegerField(min_value=0),
            "reason": serializers.CharField(),
        },
    ),
    responses={
        200: inline_serializer(
            name="StockAdjustmentResponse",
            fields={
                "success": serializers.BooleanField(),
                "message": serializers.CharField(),
                "data": serializers.DictField(),
                "errors": serializers.JSONField(allow_null=True),
                "meta": serializers.DictField(),
            },
        ),
        400: OpenApiResponse(description="Invalid adjustment request"),
        403: OpenApiResponse(description="User is not authorized"),
    },
)
@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def create_adjustment(request):
    allowed_roles = ["Super Admin", "Inventory Manager"]

    user_role = request.user.role.name if request.user.role else None

    if user_role not in allowed_roles:
        return Response(
            {
                "success": False,
                "message": "You are not authorized to perform stock adjustments.",
                "data": {},
                "errors": {
                    "permission": "Adjustment permission is required."
                },
                "meta": {},
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    product_id = request.data.get("product_id")
    warehouse_id = request.data.get("warehouse_id")
    new_quantity = request.data.get("new_quantity")
    reason = request.data.get("reason")

    if product_id is None:
        return Response(
            {
                "success": False,
                "message": "Product ID is required.",
                "data": {},
                "errors": {"product_id": "This field is required."},
                "meta": {},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if warehouse_id is None:
        return Response(
            {
                "success": False,
                "message": "Warehouse ID is required.",
                "data": {},
                "errors": {"warehouse_id": "This field is required."},
                "meta": {},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if new_quantity is None:
        return Response(
            {
                "success": False,
                "message": "New quantity is required.",
                "data": {},
                "errors": {"new_quantity": "This field is required."},
                "meta": {},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if reason is None or not str(reason).strip():
        return Response(
            {
                "success": False,
                "message": "Reason is required.",
                "data": {},
                "errors": {"reason": "This field is required."},
                "meta": {},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        product_id = int(product_id)
        warehouse_id = int(warehouse_id)
        new_quantity = int(new_quantity)
    except (TypeError, ValueError):
        return Response(
            {
                "success": False,
                "message": "Product ID, warehouse ID and new quantity must be valid numbers.",
                "data": {},
                "errors": {
                    "validation": "Invalid numeric value."
                },
                "meta": {},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        result = create_stock_adjustment(
            product_id=product_id,
            warehouse_id=warehouse_id,
            new_quantity=new_quantity,
            reason=reason,
            user_id=request.user.id,
        )

        return Response(
            {
                "success": True,
                "message": "Stock adjustment created successfully.",
                "data": {
                    "product_id": product_id,
                    "warehouse_id": warehouse_id,
                    "before_quantity": result["before_quantity"],
                    "after_quantity": result["after_quantity"],
                    "variance": result["variance"],
                    "transaction_id": result["transaction"].id,
                    "transaction_type": result["transaction"].type,
                    "reason": reason,
                    "created_by": request.user.id,
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
                "data": {},
                "errors": {
                    "adjustment": str(error)
                },
                "meta": {},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
