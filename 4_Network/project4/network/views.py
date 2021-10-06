import json

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import render
from django.urls import reverse

from .models import User, Post, NewPostForm

POSTS_PER_PAGE = 10  # Maximum number of posts per page


def index(request):
    """Render 'All posts' page (all posts from all users), with pagination"""

    all_posts = Post.objects.all().order_by("-creation_date")
    paginator = Paginator(all_posts, POSTS_PER_PAGE)
    page_number = request.GET.get("page")
    posts_page = paginator.get_page(page_number)

    return render(request, "network/index.html", {
        "title": "All Posts",
        "post_form": NewPostForm(),
        "posts_page": posts_page
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
def create_post(request):
    """Create a new post"""
    user = request.user
    if request.method == "POST":
        # Create a form instance from POST data
        f = NewPostForm(request.POST)
        if f.is_valid():
            # Save a new Post object from the form's data
            new_post = f.save(commit=False)
            new_post.author = user
            new_post.save()
            return HttpResponseRedirect(reverse("index"))
        else:
            # Render same page with existing form data, so users can see the error
            return render(request, "network/index.html", {
                "title": "All Posts",
                "post_form": f,
                "posts": Post.objects.all().order_by("-creation_date")
            })
    else:
        return HttpResponseNotAllowed(["POST"])


def profile(request, user_id):
    """Load user's profile if user exists"""

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return HttpResponse("User does not exist.", status=404)

    # Pagination for user posts
    user_posts = user.posts.all().order_by("-creation_date")
    paginator = Paginator(user_posts, POSTS_PER_PAGE)
    page_number = request.GET.get("page")
    posts_page = paginator.get_page(page_number)

    return render(request, "network/profile.html", {
        "user_": user,
        "posts_page": posts_page
    })


@login_required
def follow(request, user_id):
    """Follow/Unfollow user API"""

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


@login_required
def following(request):
    """Render Following page. This page contains all posts made by users that the current user follows"""

    user = request.user
    following_posts = Post.objects.filter(author__in=user.following.all()).order_by("-creation_date")

    # Pagination
    paginator = Paginator(following_posts, POSTS_PER_PAGE)
    page_number = request.GET.get("page")
    posts_page = paginator.get_page(page_number)

    return render(request, "network/index.html", {
        "title": "Following",
        "post_form": None,
        "posts_page": posts_page
    })


@login_required
def update_post(request, post_id):
    """API for updating post content"""

    if request.method != "PUT":
        return JsonResponse({"error": "PUT request required."}, status=400)

    # Try to get post
    try:
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:
        return JsonResponse({"error": f"Post with id {post_id} not found."}, status=404)

    # User can only modify its own posts
    user = request.user
    if post.author != user:
        return JsonResponse({"error": "This post belongs to another user. You can't modify it."}, status=403)

    # Request must have a body
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "You must specify post 'content' (str) in request body (JSON)"}, status=400)

    # text variable must be set on request body with a non-empty value
    if "content" not in data or not data["content"]:
        return JsonResponse({
            "error": "You must specify a non-empty post 'content' (str) in request body (JSON)"
        }, status=400)

    # Update post content
    post.text = data["content"]
    post.save()
    return JsonResponse({"message": "Post content was updated successfully."}, status=200)
