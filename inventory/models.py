from django.db import models


class Inventory(models.Model):
    product_id = models.IntegerField()
    warehouse_id = models.IntegerField()
    quantity = models.PositiveIntegerField(default=0)
    reserved_qty = models.PositiveIntegerField(default=0)
    damaged_qty = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['product_id', 'warehouse_id'],
                name='unique_product_warehouse_inventory'
            )
        ]

    @property
    def total_quantity(self):
        return self.quantity + self.reserved_qty + self.damaged_qty

    def __str__(self):
        return f"Inventory - Product {self.product_id}"


class StockTransaction(models.Model):

    TRANSACTION_TYPES = [
        ('STOCK_IN', 'STOCK_IN'),
        ('STOCK_OUT', 'STOCK_OUT'),
        ('TRANSFER_OUT', 'TRANSFER_OUT'),
        ('TRANSFER_IN', 'TRANSFER_IN'),
        ('ADJUSTMENT_IN', 'ADJUSTMENT_IN'),
        ('ADJUSTMENT_OUT', 'ADJUSTMENT_OUT'),
        ('RETURN', 'RETURN'),
        ('DAMAGE', 'DAMAGE'),
        ('REVERSAL', 'REVERSAL'),
    ]

    product_id = models.IntegerField()
    warehouse_id = models.IntegerField()
    type = models.CharField(
        max_length=30,
        choices=TRANSACTION_TYPES
    )
    quantity = models.PositiveIntegerField()
    reference_type = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    reference_id = models.IntegerField(
        blank=True,
        null=True
    )
    reason = models.TextField(
        blank=True,
        null=True
    )
    created_by = models.IntegerField(
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(
                fields=['product_id', 'warehouse_id', 'created_at']
            )
        ]

    def __str__(self):
        return f"{self.type} - Product {self.product_id}"


class StockTransfer(models.Model):

    STATUS_CHOICES = [
        ('DRAFT', 'DRAFT'),
        ('REQUESTED', 'REQUESTED'),
        ('APPROVED', 'APPROVED'),
        ('IN_TRANSIT', 'IN_TRANSIT'),
        ('RECEIVED', 'RECEIVED'),
        ('CANCELLED', 'CANCELLED'),
    ]

    transfer_no = models.CharField(
        max_length=50,
        unique=True
    )
    from_warehouse_id = models.IntegerField()
    to_warehouse_id = models.IntegerField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT'
    )
    requested_by = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.transfer_no


class StockTransferItem(models.Model):

    transfer = models.ForeignKey(
        StockTransfer,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product_id = models.IntegerField()
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.transfer.transfer_no} - Product {self.product_id}"