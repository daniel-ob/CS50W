from django.contrib.auth.models import AbstractUser
from django.db import models
from django.forms import ModelForm, Textarea


class User(AbstractUser):
    pass


class Category(models.Model):
    name = models.CharField(max_length=64)

    def __str__(self):
        return f"{self.name}"


class Listing(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="listings")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, related_name="listings", null=True, blank=True)
    title = models.CharField(max_length=64)
    description = models.CharField(max_length=512, null=True, blank=True)
    starting_bid_dollars = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    image_url = models.URLField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.title} ({self.user})"


class Bid(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bids")
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="bids")
    amount_dollars = models.DecimalField(max_digits=8, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} offers {self.amount_dollars} for {self.listing}"


class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="comments")
    text = models.CharField(max_length=128)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} said: \'{self.text}\' on {self.listing}"


class NewListingForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(NewListingForm, self).__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.order_by("name")

    class Meta:
        model = Listing
        fields = ["category", "title", "description", "starting_bid_dollars", "image_url"]
        widgets = {
            "description": Textarea(attrs={"cols": 54, "rows": 4}),
        }


class NewBidForm(ModelForm):
    class Meta:
        model = Bid
        fields = ["amount_dollars"]
