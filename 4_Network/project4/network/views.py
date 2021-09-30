from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotAllowed
from django.shortcuts import render
from django.urls import reverse

from .models import User, Post, FollowingList, NewPostForm


def index(request):
    """Render All posts page (all posts from all users)"""

    return render(request, "network/index.html", {
        "post_form": NewPostForm(),
        "posts": Post.objects.all().order_by("creation_date").reverse()
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
            return render(request, "network/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "network/login.html")


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
            return render(request, "network/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "network/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "network/register.html")


@login_required
def post(request):
    """Create a new post"""
    user = request.user
    if request.method == "POST":
        # Create a form instance from POST data
        f = NewPostForm(request.POST)
        if f.is_valid():
            # Save a new Post object from the form's data
            new_post = f.save(commit=False)
            new_post.user = user
            new_post.save()
            return HttpResponseRedirect(reverse("index"))
    else:
        return HttpResponseNotAllowed(["POST"])


def profile(request, user_id):
    """Load user's profile if user exists"""
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return HttpResponse("User does not exist.", status=404)

    return render(request, "network/profile.html", {
        "user_": user,
        "posts": user.posts.all().order_by("creation_date").reverse()
    })


@login_required
def follow(request, user_id):
    """Add/Remove user from following list"""

    current_user = request.user
    if not hasattr(current_user, "following_list"):
        new_following_list = FollowingList(owner=current_user)
        new_following_list.save()

    if request.method == "POST":
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return HttpResponse("User does not exist.", status=404)

        follow_status = request.POST["follow"]

        if follow_status == "True":
            # Add user to following list
            current_user.following_list.members.add(user)
        else:
            # Remove user to following list
            current_user.following_list.members.remove(user)

        return HttpResponseRedirect(reverse("profile", args=(user.id,)))
    else:
        return HttpResponseNotAllowed(["POST"])
