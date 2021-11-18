from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    # Accounts
    path("", views.index, name="index"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register, name="register"),
    path("password_reset/", auth_views.PasswordResetView.as_view(), name="password_reset"),
    path("password_reset/done/", auth_views.PasswordResetDoneView.as_view(), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),

    # API Routes
    path("orders", views.create_order, name="create_order"),
    path("orders/<int:order_id>", views.order, name="order"),
    path("deliveries/<int:delivery_id>", views.delivery, name="delivery"),

    path("deliveries/<int:delivery_id>/export", views.delivery_export, name="delivery_export")
]
