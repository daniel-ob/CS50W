from datetime import date

from django.contrib import admin, messages
from django.contrib.auth.models import Group
from django.db.models import Count, Sum
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import User, Producer, Product, Delivery, Order, OrderItem
from . import utils


class ProductInline(admin.TabularInline):
    model = Product


class DeliveryProductInline(admin.TabularInline):
    model = Delivery.products.through
    readonly_fields = ["producer", "product", "total_ordered_quantity", "modify_quantities"]
    extra = 0

    def producer(self, obj):
        return obj.product.producer

    def total_ordered_quantity(self, obj):
        d = obj.delivery
        d_items = obj.product.order_items.filter(order__delivery=d)
        total_quantity = d_items.aggregate(Sum("quantity"))["quantity__sum"]
        return total_quantity if total_quantity else 0

    def modify_quantities(self, obj):
        order_item_admin_url = reverse("admin:baskets_orderitem_changelist")
        d = obj.delivery
        p = obj.product
        return format_html(
            f"<a href='{order_item_admin_url}?order__delivery__id__exact={d.id}&product__id__exact={p.id}'>"
            "Modify ordered quantities</a>"
        )


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    fields = ["product", "unit_price", "quantity", "amount"]
    readonly_fields = ["unit_price", "amount"]
    extra = 0

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
        if obj.is_active:
            utils.email_user_account_activated(obj)


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

    @admin.display(ordering="orders__count")
    def orders_count(self, obj):
        delivery_orders_url = reverse("admin:baskets_order_changelist") + f"?delivery__id__exact={obj.id}"
        return format_html(
            f"<a href='{delivery_orders_url}'>{obj.orders__count}</a>"
        )

    def export(self, obj):
        d = obj
        delivery_export_url = reverse("delivery_export", args=[d.id])
        if date.today() > d.order_deadline and d.orders.count():
            return format_html(
                f"<a href='{delivery_export_url}'>Export order forms</a>"
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
    list_editable = ("quantity", )
    list_filter = ("order__delivery", "product")

    def delivery(self, obj):
        return obj.order.delivery

    @admin.display(ordering="order__user")
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
                mark_safe(
                    f"{user}'s <a href='{order_admin_url}'>order</a> has been updated, remember to prevent user: "
                    f"<a href='mailto:{user.email}'>{user.email}</a>, <a href='tel:{user.phone}'>{user.phone}</a>"
                )
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
        return format_html(
            f"<a href='mailto:?bcc={emails_str}'>send email to {obj.name} group</a>"
        )
