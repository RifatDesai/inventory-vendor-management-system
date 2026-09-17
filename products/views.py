from django.db import transaction

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status, serializers

from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer

from .models import Product
from inventory.models import Inventory


# ============================================================
# LIST PRODUCTS + ADD PRODUCT
# ============================================================

@extend_schema(
    methods=['GET'],
    responses={
        200: inline_serializer(
            name='ProductListResponse',
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
        name='AddProductRequest',
        fields={
            'name': serializers.CharField(),
            'category_id': serializers.IntegerField(),
            'warehouse_id': serializers.IntegerField(),
            'reorder_level': serializers.IntegerField(default=0),
            'available_qty': serializers.IntegerField(default=0),
            'reserved_qty': serializers.IntegerField(default=0),
            'damaged_qty': serializers.IntegerField(default=0),
        },
    ),
    responses={
        201: inline_serializer(
            name='AddProductResponse',
            fields={
                'success': serializers.BooleanField(),
                'message': serializers.CharField(),
                'data': serializers.DictField(),
            },
        ),
        400: OpenApiResponse(description='Validation failed'),
    },
)
@api_view(['GET', 'POST'])
def products_list_create(request):

    # ========================================================
    # GET - List Products
    # ========================================================

    if request.method == 'GET':

        products = Product.objects.all().order_by('-id')

        data = []

        for product in products:
            data.append({
                'id': product.id,
                'name': product.name,
                'sku': product.sku,
                'category_id': product.category_id,
                'reorder_level': product.reorder_level,
                'status': product.status,
                'created_at': product.created_at,
                'updated_at': product.updated_at,
            })

        return Response({
            'success': True,
            'message': 'Products retrieved successfully.',
            'data': data,
            'errors': None,
            'meta': {
                'total': len(data)
            }
        }, status=status.HTTP_200_OK)

    # ========================================================
    # POST - Add Product
    # ========================================================

    name = request.data.get('name')
    category_id = request.data.get('category_id')
    warehouse_id = request.data.get('warehouse_id')
    reorder_level = request.data.get('reorder_level', 0)
    available_qty = request.data.get('available_qty', 0)
    reserved_qty = request.data.get('reserved_qty', 0)
    damaged_qty = request.data.get('damaged_qty', 0)

    if not name or category_id is None or warehouse_id is None:
        return Response({
            'success': False,
            'message': 'Validation failed.',
            'data': {},
            'errors': {
                'required_fields': [
                    'name, category_id and warehouse_id are required.'
                ]
            },
            'meta': {}
        }, status=status.HTTP_400_BAD_REQUEST)

    numeric_fields = {
        'reorder_level': reorder_level,
        'available_qty': available_qty,
        'reserved_qty': reserved_qty,
        'damaged_qty': damaged_qty
    }

    errors = {}

    for field, value in numeric_fields.items():
        try:
            if int(value) < 0:
                errors[field] = [
                    'Must be greater than or equal to 0.'
                ]
        except (TypeError, ValueError):
            errors[field] = [
                'Must be a valid number.'
            ]

    if errors:
        return Response({
            'success': False,
            'message': 'Validation failed.',
            'data': {},
            'errors': errors,
            'meta': {}
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        with transaction.atomic():

            product = Product.objects.create(
                name=name,
                category_id=category_id,
                reorder_level=reorder_level
            )

            inventory = Inventory.objects.create(
                product_id=product.id,
                warehouse_id=warehouse_id,
                quantity=available_qty,
                reserved_qty=reserved_qty,
                damaged_qty=damaged_qty
            )

        return Response({
            'success': True,
            'message': 'Product created successfully.',
            'data': {
                'id': product.id,
                'sku': product.sku,
                'name': product.name,
                'category_id': product.category_id,
                'warehouse_id': inventory.warehouse_id,
                'reorder_level': product.reorder_level,
                'available_qty': inventory.quantity,
                'reserved_qty': inventory.reserved_qty,
                'damaged_qty': inventory.damaged_qty,
                'total_quantity': inventory.total_quantity
            },
            'errors': None,
            'meta': {}
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({
            'success': False,
            'message': 'Failed to create product.',
            'data': {},
            'errors': {
                'detail': str(e)
            },
            'meta': {}
        }, status=status.HTTP_400_BAD_REQUEST)


# ============================================================
# EDIT PRODUCT
# ============================================================

# ============================================================
# PRODUCT DETAILS + EDIT PRODUCT
# ============================================================

@extend_schema(
    methods=['GET'],
    responses={
        200: inline_serializer(
            name='ProductDetailResponse',
            fields={
                'success': serializers.BooleanField(),
                'message': serializers.CharField(),
                'data': serializers.DictField(),
                'errors': serializers.JSONField(allow_null=True),
                'meta': serializers.DictField(),
            },
        ),
        404: OpenApiResponse(description='Product not found'),
    },
)
@extend_schema(
    methods=['PATCH'],
    request=inline_serializer(
        name='EditProductRequest',
        fields={
            'name': serializers.CharField(required=False),
            'category_id': serializers.IntegerField(required=False),
            'reorder_level': serializers.IntegerField(required=False),
            'status': serializers.BooleanField(required=False),
        },
    ),
    responses={
        200: inline_serializer(
            name='EditProductResponse',
            fields={
                'success': serializers.BooleanField(),
                'message': serializers.CharField(),
                'data': serializers.DictField(),
                'errors': serializers.JSONField(allow_null=True),
                'meta': serializers.DictField(),
            },
        ),
        400: OpenApiResponse(description='Validation failed'),
        404: OpenApiResponse(description='Product not found'),
    },
)
@api_view(['GET', 'PATCH'])
def product_detail(request, product_id):

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Product not found.',
            'data': {},
            'errors': {
                'product': 'Product not found.'
            },
            'meta': {}
        }, status=status.HTTP_404_NOT_FOUND)

    # ========================================================
    # GET - Product Details
    # ========================================================

    if request.method == 'GET':

        return Response({
            'success': True,
            'message': 'Product details retrieved successfully.',
            'data': {
                'id': product.id,
                'name': product.name,
                'sku': product.sku,
                'category_id': product.category_id,
                'reorder_level': product.reorder_level,
                'status': product.status,
                'created_at': product.created_at,
                'updated_at': product.updated_at
            },
            'errors': None,
            'meta': {}
        }, status=status.HTTP_200_OK)

    # ========================================================
    # PATCH - Edit Product
    # ========================================================

    name = request.data.get('name')
    category_id = request.data.get('category_id')
    reorder_level = request.data.get('reorder_level')
    product_status = request.data.get('status')

    errors = {}

    if name is not None and not str(name).strip():
        errors['name'] = ['This field cannot be empty.']

    if category_id is not None:
        try:
            if int(category_id) <= 0:
                errors['category_id'] = [
                    'Must be greater than 0.'
                ]
        except (TypeError, ValueError):
            errors['category_id'] = [
                'Must be a valid number.'
            ]

    if reorder_level is not None:
        try:
            if int(reorder_level) < 0:
                errors['reorder_level'] = [
                    'Must be greater than or equal to 0.'
                ]
        except (TypeError, ValueError):
            errors['reorder_level'] = [
                'Must be a valid number.'
            ]

    if errors:
        return Response({
            'success': False,
            'message': 'Validation failed.',
            'data': {},
            'errors': errors,
            'meta': {}
        }, status=status.HTTP_400_BAD_REQUEST)

    if name is not None:
        product.name = name

    if category_id is not None:
        product.category_id = category_id

    if reorder_level is not None:
        product.reorder_level = reorder_level

    if product_status is not None:
        product.status = product_status

    product.save()

    return Response({
        'success': True,
        'message': 'Product updated successfully.',
        'data': {
            'id': product.id,
            'sku': product.sku,
            'name': product.name,
            'category_id': product.category_id,
            'reorder_level': product.reorder_level,
            'status': product.status,
            'updated_at': product.updated_at
        },
        'errors': None,
        'meta': {}
    }, status=status.HTTP_200_OK)


# ============================================================
# DEACTIVATE PRODUCT
# ============================================================

@extend_schema(
    responses={
        200: inline_serializer(
            name='DeactivateProductResponse',
            fields={
                'success': serializers.BooleanField(),
                'message': serializers.CharField(),
                'data': serializers.DictField(),
            },
        ),
        404: OpenApiResponse(description='Product not found'),
    },
)
@api_view(['PATCH'])
def deactivate_product(request, product_id):

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Product not found.',
            'data': {},
            'errors': {
                'product': 'Product not found.'
            },
            'meta': {}
        }, status=status.HTTP_404_NOT_FOUND)

    product.status = False
    product.save()

    return Response({
        'success': True,
        'message': 'Product deactivated successfully.',
        'data': {
            'id': product.id,
            'sku': product.sku,
            'name': product.name,
            'status': product.status,
            'updated_at': product.updated_at
        },
        'errors': None,
        'meta': {}
    }, status=status.HTTP_200_OK)