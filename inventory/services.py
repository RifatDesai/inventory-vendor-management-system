import uuid

from django.db import transaction

from .models import (
    Inventory,
    StockTransaction,
    StockTransfer,
    StockTransferItem,
)
from products.models import Product
from audit.services import create_audit_log


@transaction.atomic
def post_stock_transaction(
    *,
    product_id,
    warehouse_id,
    transaction_type,
    quantity,
    reference_type=None,
    reference_id=None,
    reason=None,
    user_id=None,
):
    # Validate product
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        raise ValueError("Product not found.")

    # Product must be active
    if not product.status:
        raise ValueError("Product is inactive.")

    # Quantity must be greater than zero
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")

    # Only STOCK_IN and STOCK_OUT are handled by this endpoint
    if transaction_type not in ["STOCK_IN", "STOCK_OUT"]:
        raise ValueError(
            "Only STOCK_IN and STOCK_OUT are supported by this endpoint."
        )

    # Find inventory for this product + warehouse
    inventory = Inventory.objects.filter(
        product_id=product_id,
        warehouse_id=warehouse_id,
    ).first()

    # STOCK_IN
    if transaction_type == "STOCK_IN":

        if inventory is None:
            inventory = Inventory.objects.create(
                product_id=product_id,
                warehouse_id=warehouse_id,
                quantity=0,
                reserved_qty=0,
                damaged_qty=0,
            )

        inventory.quantity += quantity
        inventory.save()

    # STOCK_OUT
    elif transaction_type == "STOCK_OUT":

        if inventory is None:
            raise ValueError("Inventory record not found.")

        if inventory.quantity < quantity:
            raise ValueError("Insufficient available stock.")

        inventory.quantity -= quantity
        inventory.save()

    # Create transaction history
    transaction_record = StockTransaction.objects.create(
        product_id=product_id,
        warehouse_id=warehouse_id,
        type=transaction_type,
        quantity=quantity,
        reference_type=reference_type,
        reference_id=reference_id,
        reason=reason,
        created_by=user_id,
    )

    return inventory, transaction_record


@transaction.atomic
def create_stock_transfer(
    *,
    from_warehouse_id,
    to_warehouse_id,
    items,
    reason=None,
    user_id=None,
):
    if from_warehouse_id == to_warehouse_id:
        raise ValueError(
            "Source and destination warehouses must be different."
        )

    if from_warehouse_id <= 0 or to_warehouse_id <= 0:
        raise ValueError(
            "Warehouse IDs must be greater than 0."
        )

    if not items:
        raise ValueError(
            "At least one transfer item is required."
        )

    transfer_no = f"TR-{uuid.uuid4().hex[:8].upper()}"

    transfer = StockTransfer.objects.create(
        transfer_no=transfer_no,
        from_warehouse_id=from_warehouse_id,
        to_warehouse_id=to_warehouse_id,
        status="RECEIVED",
        requested_by=user_id,
    )

    for item in items:

        product_id = item.get("product_id")
        quantity = item.get("quantity")

        if product_id is None or quantity is None:
            raise ValueError(
                "Each item must contain product_id and quantity."
            )

        try:
            product_id = int(product_id)
            quantity = int(quantity)
        except (TypeError, ValueError):
            raise ValueError(
                "product_id and quantity must be valid integers."
            )

        if product_id <= 0:
            raise ValueError(
                "Product ID must be greater than 0."
            )

        if quantity <= 0:
            raise ValueError(
                "Transfer quantity must be greater than zero."
            )

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            raise ValueError(
                f"Product {product_id} not found."
            )

        if not product.status:
            raise ValueError(
                f"Product {product_id} is inactive."
            )

        source_inventory = Inventory.objects.select_for_update().filter(
            product_id=product_id,
            warehouse_id=from_warehouse_id,
        ).first()

        if source_inventory is None:
            raise ValueError(
                f"No inventory found for product {product_id} "
                f"in source warehouse."
            )

        if source_inventory.quantity < quantity:
            raise ValueError(
                f"Insufficient stock for product {product_id}."
            )

        destination_inventory = Inventory.objects.select_for_update().filter(
            product_id=product_id,
            warehouse_id=to_warehouse_id,
        ).first()

        if destination_inventory is None:
            destination_inventory = Inventory.objects.create(
                product_id=product_id,
                warehouse_id=to_warehouse_id,
                quantity=0,
                reserved_qty=0,
                damaged_qty=0,
            )

        source_inventory.quantity -= quantity
        source_inventory.save()

        destination_inventory.quantity += quantity
        destination_inventory.save()

        StockTransferItem.objects.create(
            transfer=transfer,
            product_id=product_id,
            quantity=quantity,
        )

        StockTransaction.objects.create(
            product_id=product_id,
            warehouse_id=from_warehouse_id,
            type="TRANSFER_OUT",
            quantity=quantity,
            reference_type="TRANSFER",
            reference_id=transfer.id,
            reason=reason,
            created_by=user_id,
        )

        StockTransaction.objects.create(
            product_id=product_id,
            warehouse_id=to_warehouse_id,
            type="TRANSFER_IN",
            quantity=quantity,
            reference_type="TRANSFER",
            reference_id=transfer.id,
            reason=reason,
            created_by=user_id,
        )

    return transfer


@transaction.atomic
def create_stock_adjustment(
    *,
    product_id,
    warehouse_id,
    new_quantity,
    reason,
    user_id=None,
):
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        raise ValueError("Product not found.")

    if not product.status:
        raise ValueError("Product is inactive.")

    if new_quantity < 0:
        raise ValueError("New quantity cannot be negative.")

    if not reason or not reason.strip():
        raise ValueError("Reason is required.")

    inventory = Inventory.objects.select_for_update().filter(
        product_id=product_id,
        warehouse_id=warehouse_id,
    ).first()

    if inventory is None:
        raise ValueError("Inventory record not found.")

    before_quantity = inventory.quantity
    variance = new_quantity - before_quantity

    if variance == 0:
        raise ValueError(
            "Adjustment quantity is the same as current quantity."
        )

    if variance > 0:
        transaction_type = "ADJUSTMENT_IN"
        transaction_quantity = variance
    else:
        transaction_type = "ADJUSTMENT_OUT"
        transaction_quantity = abs(variance)

    inventory.quantity = new_quantity
    inventory.save()

    transaction_record = StockTransaction.objects.create(
        product_id=product_id,
        warehouse_id=warehouse_id,
        type=transaction_type,
        quantity=transaction_quantity,
        reference_type="ADJUSTMENT",
        reference_id=None,
        reason=reason,
        created_by=user_id,
    )

    # Create audit record for the adjustment
    create_audit_log(
        user_id=user_id,
        action="STOCK_ADJUSTED",
        entity_type="Inventory",
        entity_id=inventory.id,
        old_data={
            "quantity": before_quantity,
        },
        new_data={
            "quantity": new_quantity,
            "variance": variance,
            "reason": reason,
        },
    )

    return {
        "inventory": inventory,
        "transaction": transaction_record,
        "before_quantity": before_quantity,
        "after_quantity": new_quantity,
        "variance": variance,
    }