
from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("register", views.register, name="register"),
    path("posts", views.create_post, name="create_post"),
    path("users/<int:user_id>", views.profile, name="profile"),
    path("following", views.following, name="following"),

    # API Routes
    path("users/<int:user_id>/follow", views.follow, name="follow"),
    path("posts/<int:post_id>", views.update_post, name="update_post")
]
