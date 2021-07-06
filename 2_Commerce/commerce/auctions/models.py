from django.contrib.auth.models import AbstractUser
from django.db import models
from django.forms import ModelForm, Select, TextInput, Textarea, NumberInput


class User(AbstractUser):
    pass


class Category(models.Model):
    name = models.CharField(max_length=64)

    def __str__(self):
        return f"{self.name}"

    @property
    def active_listings_count(self):
        return self.listings.filter(is_active=True).count()


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


class Watchlist(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name="watchlist")
    listings = models.ManyToManyField(Listing, blank=True, related_name="in_watchlists")

    def __str__(self):
        return f"{self.user}'s"


class NewListingForm(ModelForm):
    # sort categories by name
    def __init__(self, *args, **kwargs):
        super(NewListingForm, self).__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.order_by("name")

    class Meta:
        model = Listing
        fields = ["category", "title", "description", "starting_bid_dollars", "image_url"]
        widgets = {
            "category": Select(attrs={"class": "form-control"}),
            "title": TextInput(attrs={"class": "form-control"}),
            "description": Textarea(attrs={"class": "form-control", "rows": 4}),
            "starting_bid_dollars": NumberInput(attrs={"class": "form-control"}),
            "image_url": TextInput(attrs={"class": "form-control"})
        }


class NewBidForm(ModelForm):
    class Meta:
        model = Bid
        fields = ["amount_dollars"]


class NewCommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ["text"]
        labels = {
            "text": ""
        }
        widgets = {
            "text": TextInput(attrs={"placeholder": "Add a Comment"}),
        }
