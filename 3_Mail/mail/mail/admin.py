from django.contrib import admin

from .models import User, Email


# Register your models here.
class EmailAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "sender", "subject", "timestamp")
    list_filter = ("user", "sender")


admin.site.register(User)
admin.site.register(Email, EmailAdmin)
