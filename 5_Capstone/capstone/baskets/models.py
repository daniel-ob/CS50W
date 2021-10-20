from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
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

