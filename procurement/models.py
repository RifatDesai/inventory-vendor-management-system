from django.db import models


class PurchaseRequest(models.Model):
    STATUS_CHOICES = [
        ("DRAFT", "DRAFT"),
        ("SUBMITTED", "SUBMITTED"),
        ("UNDER_REVIEW", "UNDER_REVIEW"),
        ("APPROVED", "APPROVED"),
        ("REJECTED", "REJECTED"),
        ("CONVERTED", "CONVERTED"),
        ("CLOSED", "CLOSED"),
    ]

    request_no = models.CharField(
        max_length=100,
        unique=True,
    )

    requested_by = models.IntegerField()

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="DRAFT",
    )

    required_date = models.DateField(
        blank=True,
        null=True,
    )

    reason = models.TextField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return self.request_no


class PurchaseRequestItem(models.Model):
    purchase_request = models.ForeignKey(
        PurchaseRequest,
        on_delete=models.CASCADE,
        related_name="items",
    )

    product_id = models.IntegerField()

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    remarks = models.TextField(
        blank=True,
        null=True,
    )

    def __str__(self):
        return f"{self.purchase_request.request_no} - Product {self.product_id}"


class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ("DRAFT", "DRAFT"),
        ("PENDING_APPROVAL", "PENDING_APPROVAL"),
        ("APPROVED", "APPROVED"),
        ("PARTIALLY_RECEIVED", "PARTIALLY_RECEIVED"),
        ("FULLY_RECEIVED", "FULLY_RECEIVED"),
        ("CANCELLED", "CANCELLED"),
        ("CLOSED", "CLOSED"),
    ]

    po_no = models.CharField(
        max_length=100,
        unique=True,
    )

    vendor_id = models.IntegerField()

    warehouse_id = models.IntegerField()

    order_date = models.DateField()

    expected_date = models.DateField(
        blank=True,
        null=True,
    )
    terms = models.TextField(
    blank=True,
    null=True,
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="DRAFT",
    )

    subtotal = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )

    discount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )

    tax = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )

    charges = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )

    total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )

    def __str__(self):
        return self.po_no


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name="items",
    )

    product_id = models.IntegerField()

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    tax = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    line_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    def __str__(self):
        return (
            f"{self.purchase_order.po_no} - "
            f"Product {self.product_id}"
        )