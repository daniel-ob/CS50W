from django.contrib import admin

from .models import User, Producer, Product, Delivery, Order, OrderItem


class ProductInline(admin.TabularInline):
    model = Product


class ProducerAdmin(admin.ModelAdmin):
    inlines = [ProductInline]


class DeliveryAdmin(admin.ModelAdmin):
    list_display = ("date", )


class OrderItemInline(admin.TabularInline):
    model = OrderItem


class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "delivery", "amount", "creation_date")
    list_filter = ("user", "delivery")
    readonly_fields = ["amount", "creation_date"]
    inlines = [OrderItemInline]


admin.site.register(User)
admin.site.register(Producer, ProducerAdmin)
admin.site.register(Delivery, DeliveryAdmin)
admin.site.register(Order, OrderAdmin)
