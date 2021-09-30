import json

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import render
from django.urls import reverse

from .models import User, Post, NewPostForm


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
    """Follow/Unfollow user"""

    if request.method != "PUT":
        return JsonResponse({"error": "PUT request required."}, status=400)

    try:
        user_to_follow = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return JsonResponse({"error": f"User with id {user_id} not found."}, status=404)

    # User can only follow other users
    if user_to_follow == request.user:
        return JsonResponse({"error": "You can only follow other users"}, status=400)

    # Request must have a body
    try:
        data = json.loads(request.body)
        # print(data)
    except json.JSONDecodeError:
        return JsonResponse({"error": "'follow' variable (bool) must be specified in request body (JSON)"}, status=400)

    # Ensure that Follow parameter exists and is a boolean
    if "follow" not in data or not isinstance(data["follow"], bool):
        return JsonResponse({"error": "'follow' variable (bool) must be specified in request body (JSON)"}, status=400)
    else:
        follow_ = data["follow"]

    # Update logged user's following list
    if follow_:
        request.user.following.add(user_to_follow)
    else:
        request.user.following.remove(user_to_follow)

    # Send new follower count value in response to update front-end
    return JsonResponse({
        "message": "Follow status set successfully",
        "followerCount": user_to_follow.followers.count()
    }, status=200)
