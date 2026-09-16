from django.db import models


class Inventory(models.Model):
    product_id = models.IntegerField()
    warehouse_id = models.IntegerField()
    quantity = models.PositiveIntegerField(default=0)
    reserved_qty = models.PositiveIntegerField(default=0)
    damaged_qty = models.PositiveIntegerField(default=0)

    @property
    def total_quantity(self):
        return self.quantity + self.reserved_qty + self.damaged_qty

    def __str__(self):
        return f"Inventory - Product {self.product_id}"
