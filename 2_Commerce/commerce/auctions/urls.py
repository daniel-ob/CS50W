from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("register", views.register, name="register"),
    path("listings/create", views.create, name="create"),
    path("listings/<int:listing_id>", views.listing_view, name="listing"),
    path("listings/<int:listing_id>/bid", views.bid, name="bid"),
    path("listings/<int:listing_id>/close", views.close, name="close"),
    path("listings/<int:listing_id>/comment", views.comment, name="comment"),
    path("watchlist", views.watchlist, name="watchlist"),
    path("categories", views.categories_index, name="categories_index"),
    path("categories/<int:category_id>", views.category, name="category")
]
