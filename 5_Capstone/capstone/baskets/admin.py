from django.contrib import admin
from django.db.models import Count, Sum
from django.urls import reverse
from django.utils.html import format_html

from .models import User, Producer, Product, Delivery, Order, OrderItem


class ProductInline(admin.TabularInline):
    model = Product


class OrderItemInline(admin.TabularInline):
    model = OrderItem


class DeliveryProductInline(admin.TabularInline):
    model = Delivery.products.through
    readonly_fields = ["product", "total_ordered_quantity", "modify_quantities"]
    ordering = ["product"]
    extra = 0

    def total_ordered_quantity(self, obj):
        d = obj.delivery
        d_items = obj.product.order_items.filter(order__delivery=d)
        total_quantity = d_items.aggregate(Sum("quantity"))["quantity__sum"]
        return total_quantity if total_quantity else 0

    def modify_quantities(self, obj):
        order_item_admin_url = reverse("admin:baskets_orderitem_changelist")
        d_id = obj.delivery.id
        p_id = obj.product.id
        return format_html(
            f"<a href='{order_item_admin_url}?order__delivery__id__exact={d_id}&product__id__exact={p_id}'>"
            "Modify ordered quantities</a>"
        )


class ProducerAdmin(admin.ModelAdmin):
    inlines = [ProductInline]


class DeliveryAdmin(admin.ModelAdmin):
    list_display = ("date", "orders_count")
    ordering = ["date"]
    inlines = [DeliveryProductInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(Count("orders"))
        return qs

    @admin.display(ordering="orders__count")
    def orders_count(self, obj):
        return obj.orders__count


class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "delivery", "amount", "creation_date")
    list_filter = ("user", "delivery")
    readonly_fields = ["amount", "creation_date"]
    inlines = [OrderItemInline]


class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("delivery", "product", "user", "quantity")
    list_editable = ("quantity", )
    list_filter = ("order__delivery", "product")

    def delivery(self, obj):
        return obj.order.delivery

    @admin.display(ordering="order__user")
    def user(self, obj):
        return obj.order.user


admin.site.register(User)
admin.site.register(Producer, ProducerAdmin)
admin.site.register(Delivery, DeliveryAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem, OrderItemAdmin)
