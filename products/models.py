from django.db import models


class Product(models.Model):
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, unique=True, blank=True)
    category_id = models.IntegerField()
    reorder_level = models.PositiveIntegerField(default=0)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.sku:
            prefix = ''.join(
                word[0] for word in self.name.split()[:2]
            ).upper()

            if len(prefix) < 2:
                prefix = self.name[:2].upper()

            last_product = Product.objects.filter(
                sku__startswith=f"{prefix}-"
            ).order_by('-id').first()

            if last_product:
                last_number = int(last_product.sku.split('-')[-1])
                number = last_number + 1
            else:
                number = 1

            self.sku = f"{prefix}-{number:03d}"

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name