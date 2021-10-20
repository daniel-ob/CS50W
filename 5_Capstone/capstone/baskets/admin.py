from django.contrib import admin

from .models import User, Producer, Product, Delivery, UserOrder, UserOrderItem


class ProductInline(admin.TabularInline):
    model = Product


class ProducerAdmin(admin.ModelAdmin):
    inlines = [ProductInline]


class DeliveryAdmin(admin.ModelAdmin):
    list_display = ("date", )


class UserOrderItemInline(admin.TabularInline):
    model = UserOrderItem


class UserOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "delivery", "amount", "creation_date")
    list_filter = ("user", "delivery")
    readonly_fields = ["amount", "creation_date"]
    inlines = [UserOrderItemInline]


admin.site.register(User)
admin.site.register(Producer, ProducerAdmin)
admin.site.register(Delivery, DeliveryAdmin)
admin.site.register(UserOrder, UserOrderAdmin)
