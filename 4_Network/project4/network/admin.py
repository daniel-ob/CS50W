from django.contrib import admin

# Register your models here.
from .models import User, Post


class PostAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "text", "creation_date")
    list_filter = ("user", )


class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "username")


admin.site.register(User, UserAdmin)
admin.site.register(Post, PostAdmin)
