from datetime import date

from django.contrib import admin, messages
from django.contrib.auth.models import Group
from django.db.models import Count, Sum
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from .models import User, Producer, Product, Delivery, Order, OrderItem
from . import utils


class ProductInline(admin.TabularInline):
    model = Product


class DeliveryProductInline(admin.TabularInline):
    model = Delivery.products.through
    readonly_fields = ["producer", "product", "total_ordered_quantity"]
    extra = 0

    @admin.display(description=_("producer"))
    def producer(self, obj):
        return obj.product.producer

    @admin.display(description=_("total ordered quantity"))
    def total_ordered_quantity(self, obj):
        d = obj.delivery
        p = obj.product
        order_items = p.order_items.filter(order__delivery=d)
        total_quantity = order_items.aggregate(Sum("quantity"))["quantity__sum"]

        order_item_admin_url = reverse("admin:baskets_orderitem_changelist")
        modify_quantity_url = order_item_admin_url + f"?order__delivery__id__exact={d.id}&product__id__exact={p.id}"

        if total_quantity:
            link_text = _("Modify")
            return format_html(
                f"{total_quantity} <a href='{modify_quantity_url}'>({link_text})</a>"
            )
        else:
            return 0


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    fields = ["product", "unit_price", "quantity", "amount"]
    readonly_fields = ["unit_price", "amount"]
    extra = 0

    @admin.display(description=_("unit price"))
    def unit_price(self, obj):
        p = obj.product
        return p.unit_price


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "is_active")
    exclude = ("user_permissions",)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        # notify user when its account is activated
        user = obj
        if "is_active" in form.changed_data and user.is_active:
            utils.email_user_account_activated(user)
            messages.add_message(
                request,
                messages.INFO,
                _("An email has been sent to '{}' to notify him of the activation of his account").format(user)
            )


@admin.register(Producer)
class ProducerAdmin(admin.ModelAdmin):
    inlines = [ProductInline]


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ("date", "orders_count", "export")
    ordering = ["date"]
    inlines = [DeliveryProductInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(Count("orders"))
        return qs

    @admin.display(description=_("orders count"), ordering="orders__count")
    def orders_count(self, obj):
        delivery_orders_url = reverse("admin:baskets_order_changelist") + f"?delivery__id__exact={obj.id}"
        return format_html(
            f"<a href='{delivery_orders_url}'>{obj.orders__count}</a>"
        )

    @admin.display(description=_("export"))
    def export(self, obj):
        d = obj
        delivery_export_url = reverse("delivery_export", args=[d.id])
        if date.today() > d.order_deadline and d.orders.count():
            link_text = _("Export order forms")
            return format_html(
                f"<a href='{delivery_export_url}'>{link_text}</a>"
            )
        else:
            return "-"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "delivery", "amount", "creation_date")
    list_filter = ("user", "delivery")
    readonly_fields = ["amount", "creation_date"]
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "delivery", "product", "user", "quantity")
    list_editable = ("quantity",)
    list_filter = ("order__delivery", "product")

    @admin.display(description=_("delivery"))
    def delivery(self, obj):
        return obj.order.delivery

    @admin.display(description=_("user"), ordering="order__user")
    def user(self, obj):
        user = obj.order.user
        user_admin_url = reverse("admin:baskets_user_change", args=[user.id])
        return format_html(
            f"<a href='{user_admin_url}'>{user.username}</a>"
        )

    def save_model(self, request, obj, form, change):
        if "quantity" in form.changed_data:
            order = obj.order
            user = obj.order.user
            order_admin_url = reverse("admin:baskets_order_change", args=[order.id])
            messages.add_message(
                request,
                messages.WARNING,
                mark_safe(_("{user}'s <a href='{url}'>order</a> has been updated, remember to prevent user: "
                            "<a href='mailto:{email}'>{email}</a>, <a href='tel:{phone}'>{phone}</a>")
                          .format(user=user, url=order_admin_url, email=user.email, phone=user.phone))
            )
        super().save_model(request, obj, form, change)


# Custom Group admin
admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("name", "email")
    exclude = ("permissions",)

    def email(self, obj):
        group_users = obj.user_set.all()
        emails = [user.email for user in group_users]
        emails_str = ", ".join(emails)
        link_text = _("send email to group")
        return format_html(
            f"<a href='mailto:?bcc={emails_str}'>{link_text}</a>"
        )
