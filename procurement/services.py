import uuid
from decimal import Decimal, InvalidOperation

from django.db import transaction

from products.models import Product
from audit.services import create_audit_log
from .models import (
    PurchaseRequest,
    PurchaseRequestItem,
    PurchaseOrder,
    PurchaseOrderItem,
)



@transaction.atomic
def create_purchase_request(
    *,
    user_id,
    required_date=None,
    reason=None,
    items=None,
):
    if not items:
        raise ValueError("At least one purchase request item is required.")

    request_no = f"PR-{uuid.uuid4().hex[:8].upper()}"

    purchase_request = PurchaseRequest.objects.create(
        request_no=request_no,
        requested_by=user_id,
        status="DRAFT",
        required_date=required_date,
        reason=reason,
    )

    for item in items:
        product_id = item.get("product_id")
        quantity = item.get("quantity")
        remarks = item.get("remarks")

        if product_id is None:
            raise ValueError("Each item must contain product_id.")

        if quantity is None:
            raise ValueError("Each item must contain quantity.")

        try:
            product_id = int(product_id)
            quantity = Decimal(str(quantity))
        except (TypeError, ValueError, InvalidOperation):
            raise ValueError(
                "product_id and quantity must be valid values."
            )

        if product_id <= 0:
            raise ValueError("Product ID must be greater than zero.")

        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            raise ValueError(f"Product {product_id} not found.")

        if not product.status:
            raise ValueError(f"Product {product_id} is inactive.")

        PurchaseRequestItem.objects.create(
            purchase_request=purchase_request,
            product_id=product_id,
            quantity=quantity,
            remarks=remarks,
        )

@transaction.atomic
def approve_purchase_request(
    *,
    request_id,
    user_id,
):
    try:
        purchase_request = PurchaseRequest.objects.get(id=request_id)
    except PurchaseRequest.DoesNotExist:
        raise ValueError("Purchase request not found.")

    if purchase_request.status != "DRAFT":
        raise ValueError(
            f"Purchase request cannot be approved from status "
            f"{purchase_request.status}."
        )

    if not purchase_request.items.exists():
        raise ValueError(
            "Purchase request must contain at least one item."
        )

    old_status = purchase_request.status

    purchase_request.status = "APPROVED"
    purchase_request.save()

    create_audit_log(
        user_id=user_id,
        action="PURCHASE_REQUEST_APPROVED",
        entity_type="PurchaseRequest",
        entity_id=purchase_request.id,
        old_data={
            "status": old_status,
        },
        new_data={
            "status": purchase_request.status,
            "request_no": purchase_request.request_no,
        },
    )

    return purchase_request
@transaction.atomic
def create_purchase_order(
    *,
    user_id,
    vendor_id,
    warehouse_id,
    order_date,
    expected_date=None,
    terms=None,
    items=None,
    header_discount=Decimal("0.00"),
    header_tax=Decimal("0.00"),
    charges=Decimal("0.00"),
):
    if not items:
        raise ValueError("At least one purchase order item is required.")

    try:
        vendor_id = int(vendor_id)
        warehouse_id = int(warehouse_id)
    except (TypeError, ValueError):
        raise ValueError("vendor_id and warehouse_id must be valid integers.")

    if vendor_id <= 0:
        raise ValueError("Vendor ID must be greater than zero.")

    if warehouse_id <= 0:
        raise ValueError("Warehouse ID must be greater than zero.")

    try:
        header_discount = Decimal(str(header_discount))
        header_tax = Decimal(str(header_tax))
        charges = Decimal(str(charges))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(
            "Header discount, tax and charges must be valid numbers."
        )

    if header_discount < 0:
        raise ValueError("Header discount cannot be negative.")

    if header_tax < 0:
        raise ValueError("Header tax cannot be negative.")

    if charges < 0:
        raise ValueError("Charges cannot be negative.")

    po_no = f"PO-{uuid.uuid4().hex[:8].upper()}"

    purchase_order = PurchaseOrder.objects.create(
        po_no=po_no,
        vendor_id=vendor_id,
        warehouse_id=warehouse_id,
        order_date=order_date,
        expected_date=expected_date,
        terms=terms,
        status="DRAFT",
        subtotal=Decimal("0.00"),
        discount=header_discount,
        tax=header_tax,
        charges=charges,
        total=Decimal("0.00"),
    )

    subtotal = Decimal("0.00")

    for item in items:
        product_id = item.get("product_id")
        quantity = item.get("quantity")
        unit_price = item.get("unit_price")
        item_discount = item.get("discount", 0)
        item_tax = item.get("tax", 0)

        if product_id is None:
            raise ValueError("Each purchase order item must contain product_id.")

        if quantity is None:
            raise ValueError("Each purchase order item must contain quantity.")

        if unit_price is None:
            raise ValueError("Each purchase order item must contain unit_price.")

        try:
            product_id = int(product_id)
            quantity = Decimal(str(quantity))
            unit_price = Decimal(str(unit_price))
            item_discount = Decimal(str(item_discount))
            item_tax = Decimal(str(item_tax))
        except (TypeError, ValueError, InvalidOperation):
            raise ValueError("Invalid purchase order item value.")

        if product_id <= 0:
            raise ValueError("Product ID must be greater than zero.")

        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")

        if unit_price < 0:
            raise ValueError("Unit price cannot be negative.")

        if item_discount < 0:
            raise ValueError("Item discount cannot be negative.")

        if item_tax < 0:
            raise ValueError("Item tax cannot be negative.")

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            raise ValueError(f"Product {product_id} not found.")

        if not product.status:
            raise ValueError(f"Product {product_id} is inactive.")

        gross_line_total = quantity * unit_price
        line_total = gross_line_total - item_discount + item_tax

        if line_total < 0:
            raise ValueError(
                f"Line total for product {product_id} cannot be negative."
            )

        PurchaseOrderItem.objects.create(
            purchase_order=purchase_order,
            product_id=product_id,
            quantity=quantity,
            unit_price=unit_price,
            discount=item_discount,
            tax=item_tax,
            line_total=line_total,
        )

        subtotal += line_total

    total = subtotal - header_discount + header_tax + charges

    if total < 0:
        raise ValueError("Purchase order total cannot be negative.")

    purchase_order.subtotal = subtotal
    purchase_order.total = total
    purchase_order.save()

    return purchase_order
# ============================================================
# APPROVE PURCHASE ORDER
# ============================================================

@transaction.atomic
def approve_purchase_order(*, purchase_order_id, user_id):

    purchase_order = (
        PurchaseOrder.objects
        .select_for_update()
        .filter(id=purchase_order_id)
        .first()
    )

    if not purchase_order:
        raise ValueError("Purchase order not found.")

    # The PDF workflow includes DRAFT -> PENDING APPROVAL -> APPROVED.
    # There is no separate submit-PO API in the specified endpoint list,
    # so this approval API accepts both DRAFT and PENDING_APPROVAL.
    if purchase_order.status not in ["DRAFT", "PENDING_APPROVAL"]:
        raise ValueError(
            f"Purchase order cannot be approved from status "
            f"{purchase_order.status}."
        )

    if not purchase_order.items.exists():
        raise ValueError(
            "Purchase order must contain at least one item."
        )

    old_status = purchase_order.status

    purchase_order.status = "APPROVED"
    purchase_order.save(update_fields=["status"])

    create_audit_log(
        user_id=user_id,
        action="PURCHASE_ORDER_APPROVED",
        entity_type="PurchaseOrder",
        entity_id=purchase_order.id,
        old_data={
            "status": old_status,
            "po_no": purchase_order.po_no,
        },
        new_data={
            "status": purchase_order.status,
            "po_no": purchase_order.po_no,
            "approved_by": user_id,
        },
    )

    return purchase_order

    