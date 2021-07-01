from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotAllowed
from django.shortcuts import render
from django.urls import reverse

from .models import *


def index(request):
    return render(request, "auctions/index.html", {
        "listings": Listing.objects.filter(is_active=True)
    })


def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "auctions/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "auctions/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "auctions/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "auctions/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "auctions/register.html")


@login_required
def create(request):
    if request.method == "POST":
        form = NewListingForm(request.POST)
        if form.is_valid():
            new_listing = form.save(commit=False)
            new_listing.user = request.user
            new_listing.save()
        else:
            # render the same page adding existing form data, so users can see the errors they made
            return render(request, "auctions/create.html", {
                "form": form
            })

    # Empty form
    return render(request, "auctions/create.html", {
        "form": NewListingForm()
    })


def listing_view(request, listing_id):
    return render(request, "auctions/listing.html", {
        "listing": Listing.objects.get(pk=listing_id),
        "bid_form": NewBidForm(),
        "comment_form": NewCommentForm()
    })


@login_required
def bid(request, listing_id):
    if request.method == "POST":
        listing = Listing.objects.get(pk=listing_id)

        bid_form = NewBidForm(request.POST)
        if bid_form.is_valid():
            bid_amount = bid_form.cleaned_data["amount_dollars"]
            current_price = listing.bids.last().amount_dollars if listing.bids.count() else listing.starting_bid_dollars
            if bid_amount > current_price:
                # bid is ok. Set user and listing, then save it
                new_bid = bid_form.save(commit=False)
                new_bid.user = request.user
                new_bid.listing = listing
                new_bid.save()
                return HttpResponseRedirect(reverse("listing", args=(listing.id,)))
            else:
                # bad bid
                return render(request, "auctions/listing.html", {
                    "listing": listing,
                    "bid_form": bid_form,
                    "message": "Bid must be greater than current price",
                    "comment_form": NewCommentForm()
                })
        else:
            # send bid_form back to the user, it will display the error
            return render(request, "auctions/listing.html", {
                "listing": listing,
                "bid_form": bid_form,
                "comment_form": NewCommentForm()
            })
    else:
        return HttpResponseNotAllowed(["POST"])


@login_required
def close(request, listing_id):
    if request.method == "POST":
        listing = Listing.objects.get(pk=listing_id)
        if request.user == listing.user:
            listing.is_active = False
            listing.save()
            return HttpResponseRedirect(reverse("listing", args=(listing.id, )))
    else:
        return HttpResponseNotAllowed(["POST"])


@login_required
def comment(request, listing_id):
    if request.method == "POST":
        listing = Listing.objects.get(pk=listing_id)
        comment_form = NewCommentForm(request.POST)
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.user = request.user
            new_comment.listing = listing
            new_comment.save()
            return HttpResponseRedirect(reverse("listing", args=(listing.id, )))
        else:
            return render(request, "auctions/listing.html", {
                "listing": listing,
                "bid_form": NewBidForm(),
                "comment_form": comment_form,
            })
    else:
        return HttpResponseNotAllowed(["POST"])
