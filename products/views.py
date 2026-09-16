from django.db import transaction
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer
from rest_framework import serializers

from .models import Product
from inventory.models import Inventory


@extend_schema(
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
@api_view(['POST'])
def add_product(request):

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
            'errors': {
                'required_fields': [
                    'name, category_id and warehouse_id are required.'
                ]
            }
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
            'errors': errors
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
            }
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({
            'success': False,
            'message': 'Failed to create product.',
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
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
            },
        ),
        400: OpenApiResponse(description='Validation failed'),
        404: OpenApiResponse(description='Product not found'),
    },
)
@api_view(['PATCH'])
def edit_product(request, product_id):

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Product not found.'
        }, status=status.HTTP_404_NOT_FOUND)

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
            'errors': errors
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
        }
    }, status=status.HTTP_200_OK)

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
        }
    }, status=status.HTTP_200_OK)


# ↓↓↓ PASTE THE NEW CODE BELOW THIS LINE ↓↓↓

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
            'message': 'Product not found.'
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
        }
    }, status=status.HTTP_200_OK)

