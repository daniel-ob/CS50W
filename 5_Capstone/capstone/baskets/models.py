from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator, MinValueValidator
from django.db import models

# FR phone numbers regex
PHONE_REGEX = RegexValidator(regex=r"^"
                                   r"(?:(?:\+|00)33|0)"     # Dialing code
                                   r"\s*[1-9]"              # First number (from 1 to 9)
                                   r"(?:[\s.-]*\d{2}){4}"   # End of the phone number
                                   r"$")


class User(AbstractUser):
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

    def __str__(self):
        return f"{self.name}"


class Delivery(models.Model):
    date = models.DateField(blank=False, unique=True)
    products = models.ManyToManyField(Product, related_name="deliveries")
    message = models.CharField(blank=True, max_length=128)

    def __str__(self):
        return f"{self.date}"


class UserOrder(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="orders")
    delivery = models.ForeignKey(Delivery, on_delete=models.PROTECT, related_name="user_orders")
    creation_date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(default=0.00, max_digits=8, decimal_places=2, editable=False)
    message = models.CharField(blank=True, max_length=128)

    def __str__(self):
        return f"From {self.user} for {self.delivery.date}"


class UserOrderItem(models.Model):
    user_order = models.ForeignKey(UserOrder, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="user_order_items")
    quantity = models.PositiveIntegerField(null=False, validators=[MinValueValidator(1)])

    def __str__(self):
        return f"{self.user_order}: {self.quantity} x {self.product}"
