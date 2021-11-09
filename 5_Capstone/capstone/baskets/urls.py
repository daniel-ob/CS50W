from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("register", views.register, name="register"),

    # API Routes
    path("orders", views.create_order, name="create_order"),
    path("orders/<int:order_id>", views.order, name="order"),
    path("deliveries/<int:delivery_id>", views.delivery, name="delivery"),

    path("deliveries/<int:delivery_id>/export", views.delivery_export, name="delivery_export")
]
