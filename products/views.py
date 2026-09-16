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