from django.contrib import admin

from .models import User, Producer, Product


class ProductInline(admin.TabularInline):
    model = Product


class ProducerAdmin(admin.ModelAdmin):
    inlines = [ProductInline]


admin.site.register(User)
admin.site.register(Producer, ProducerAdmin)
