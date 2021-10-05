
from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("register", views.register, name="register"),
    path("post", views.post, name="post"),
    path("users/<int:user_id>", views.profile, name="profile"),
    path("following", views.following, name="following"),

    # API Routes
    path("users/<int:user_id>/follow", views.follow, name="follow"),
    path("edit/<int:post_id>", views.edit, name="edit")
]
