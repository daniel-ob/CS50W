import datetime

from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator, MinValueValidator
from django.db import models
from django.db.models import Sum, UniqueConstraint

# FR phone numbers regex
PHONE_REGEX = RegexValidator(regex=r"^"
                                   r"(?:(?:\+|00)33|0)"     # Dialing code
                                   r"\s*[1-9]"              # First number (from 1 to 9)
                                   r"(?:[\s.-]*\d{2}){4}"   # End of the phone number
                                   r"$")


class User(AbstractUser):
    last_name = models.CharField(max_length=150, blank=False)
    email = models.EmailField(blank=False)
    phone = models.CharField(blank=True, validators=[PHONE_REGEX], max_length=18)

    def __str__(self):
        return f"{self.username}"


class Producer(models.Model):
    name = models.CharField(blank=False, max_length=64)
    phone = models.CharField(blank=True, validators=[PHONE_REGEX], max_length=18)
    email = models.EmailField(blank=True)

    def __str__(self):
        return f"{self.name}"


class Product(models.Model):
    producer = models.ForeignKey(Producer, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(blank=False, max_length=64)
    unit_price = models.DecimalField(blank=False, max_digits=8, decimal_places=2)

    def serialize(self):
        return {
            "id": self.id,
            "name": self.name,
            "unit_price": self.unit_price
        }

    def __str__(self):
        return f"{self.name}"


class Delivery(models.Model):
    ORDER_DEADLINE_DAYS_BEFORE = 4
    ORDER_DEADLINE_HELP_TEXT = f"Last day to order. If left blank, it will be automatically set to " \
                               f"{ORDER_DEADLINE_DAYS_BEFORE} days before Delivery date"

    date = models.DateField(blank=False)
    order_deadline = models.DateField(blank=True, unique=True, help_text=ORDER_DEADLINE_HELP_TEXT)
    products = models.ManyToManyField(Product, related_name="deliveries")
    message = models.CharField(blank=True, max_length=128)

    def serialize(self):
        return {
            "date": self.date,
            "order_deadline": self.order_deadline,
            "products": [product.serialize() for product in self.products.all()],
            "message": self.message
        }

    def save(self, *args, **kwargs):
        if not self.order_deadline:
            self.order_deadline = self.date - datetime.timedelta(days=self.ORDER_DEADLINE_DAYS_BEFORE)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.date}"


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="orders")
    delivery = models.ForeignKey(Delivery, on_delete=models.PROTECT, related_name="orders")
    creation_date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(default=0.00, max_digits=8, decimal_places=2, editable=False)
    message = models.CharField(blank=True, max_length=128)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["delivery", "user"], name="user can only place one order per delivery")
        ]

    def serialize(self):
        return {
            "delivery_id": self.delivery.id,
            "items": [item.serialize() for item in self.items.all()],
            "amount": self.amount,
            "message": self.message
        }

    def save(self, *args, **kwargs):
        # Order amount is the sum of its items amounts
        order_items = self.items.all()
        self.amount = order_items.aggregate(Sum("amount"))["amount__sum"] if order_items else 0.00
        # Save order
        super().save(*args, **kwargs)

    def __str__(self):
        return f"From {self.user} for {self.delivery.date}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items")
    quantity = models.PositiveIntegerField(null=False, default=1, validators=[MinValueValidator(1)])
    amount = models.DecimalField(default=0.00, max_digits=8, decimal_places=2, editable=False)

    def serialize(self):
        return {
            "product": self.product.serialize(),
            "quantity": self.quantity,
            "amount": self.amount
        }

    def save(self, *args, **kwargs):
        # Calculate item amount
        self.amount = self.quantity * self.product.unit_price
        # Save item
        super().save(*args, **kwargs)
        # Recalculate order.amount with this item
        self.order.save()

    def is_valid(self):
        """Order item is valid if product is available in related delivery and quantity is greater than 0"""
        return self.product in self.order.delivery.products.all() and self.quantity > 0

    def __str__(self):
        return f"{self.order}: {self.quantity} x {self.product}"
