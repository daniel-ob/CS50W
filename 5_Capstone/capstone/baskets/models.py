from datetime import date, timedelta

from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator, MinValueValidator
from django.db import models
from django.db.models import Sum, UniqueConstraint
from django.utils.translation import gettext_lazy as _

# FR phone numbers regex
PHONE_REGEX = RegexValidator(regex=r"^"
                                   r"(?:(?:\+|00)33|0)"     # Dialing code
                                   r"\s*[1-9]"              # First number (from 1 to 9)
                                   r"(?:[\s.-]*\d{2}){4}"   # End of the phone number
                                   r"$")


class User(AbstractUser):
    # make last_name and email mandatory
    last_name = models.CharField(_("last name"), max_length=150, blank=False)
    email = models.EmailField(_("email address"), blank=False)

    # add new fields
    phone = models.CharField(_("phone"), blank=True, validators=[PHONE_REGEX], max_length=18)
    address = models.CharField(_("address"), blank=True, max_length=128)

    def __str__(self):
        return f"{self.username}"


class Producer(models.Model):
    name = models.CharField(_("name"), blank=False, max_length=64)
    phone = models.CharField(_("phone"), blank=True, validators=[PHONE_REGEX], max_length=18)
    email = models.EmailField(_("email address"), blank=True)

    class Meta:
        verbose_name = _("producer")
        verbose_name_plural = _("producers")

    def __str__(self):
        return f"{self.name}"


class Product(models.Model):
    producer = models.ForeignKey(Producer, verbose_name=_("producer"), on_delete=models.CASCADE, related_name="products")
    name = models.CharField(_("name"), blank=False, max_length=64)
    unit_price = models.DecimalField(_("unit price"), blank=False, max_digits=8, decimal_places=2)

    class Meta:
        verbose_name = _("product")
        verbose_name_plural = _("products")

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
    ORDER_DEADLINE_HELP_TEXT = _("Last day to order. If left blank, it will be automatically set to "
                                 "{} days before Delivery date").format(ORDER_DEADLINE_DAYS_BEFORE)

    date = models.DateField(blank=False)
    order_deadline = models.DateField(_("order deadline"), blank=True, unique=True, help_text=ORDER_DEADLINE_HELP_TEXT)
    products = models.ManyToManyField(Product, verbose_name=_("products"), related_name="deliveries")
    message = models.CharField(blank=True, max_length=128)

    class Meta:
        verbose_name = _("delivery")
        verbose_name_plural = _("deliveries")

    def serialize(self):
        return {
            "date": self.date,
            "order_deadline": self.order_deadline,
            "products": [product.serialize() for product in self.products.all()],
            "message": self.message,
            "is_open": self.is_open
        }

    def save(self, *args, **kwargs):
        if not self.order_deadline:
            self.order_deadline = self.date - timedelta(days=self.ORDER_DEADLINE_DAYS_BEFORE)
        super().save(*args, **kwargs)

    @property
    def is_open(self):
        """Delivery is open (accepts orders) until its order_deadline"""
        return date.today() <= self.order_deadline

    def __str__(self):
        return f"{self.date}"


class Order(models.Model):
    user = models.ForeignKey(User, verbose_name=_("user"), on_delete=models.PROTECT, related_name="orders")
    delivery = models.ForeignKey(Delivery, verbose_name=_("delivery"), on_delete=models.PROTECT, related_name="orders")
    creation_date = models.DateTimeField(_("creation date"), auto_now_add=True)
    amount = models.DecimalField(_("amount"), default=0.00, max_digits=8, decimal_places=2, editable=False)
    message = models.CharField(_("message"), blank=True, max_length=128)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["delivery", "user"], name="user can only place one order per delivery")
        ]
        verbose_name = _("order")
        verbose_name_plural = _("orders")

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
        return _("From {} for {}").format(self.user, self.delivery.date)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, verbose_name=_("order"), on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, verbose_name=_("product"), on_delete=models.PROTECT, related_name="order_items")
    quantity = models.PositiveIntegerField(_("quantity"), null=False, default=1, validators=[MinValueValidator(1)])
    amount = models.DecimalField(_("amount"), default=0.00, max_digits=8, decimal_places=2, editable=False)

    class Meta:
        verbose_name = _("order item")
        verbose_name_plural = _("order items")

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

    def delete(self, *args, **kwargs):
        # Delete item
        super().delete(*args, **kwargs)
        # Recalculate related order.amount
        self.order.save()

    def is_valid(self):
        """Order item is valid if product is available in related delivery and quantity is greater than 0"""
        return self.product in self.order.delivery.products.all() and self.quantity > 0

    def __str__(self):
        return f"{self.order}: {self.quantity} x {self.product}"
