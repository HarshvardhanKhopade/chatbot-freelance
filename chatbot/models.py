from django.db import models

class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    category = models.CharField(max_length=100, default="Uncategorized")
    best_seller = models.BooleanField(default=False)  # 🔥 For Best selling filter 

    def __str__(self):
        return f"{self.name} ({self.price})"


class QuotationRequest(models.Model):
    customer_name = models.CharField(max_length=100)
    contact = models.CharField(max_length=50)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)  # ✅ allow null
    quantity = models.PositiveIntegerField()
    message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer_name} - {self.product.name if self.product else 'No product'}"


class Lead(models.Model):  # 🔥 for Interested users
    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Lead: {self.name} ({self.phone})"
