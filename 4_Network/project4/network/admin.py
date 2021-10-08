from django.contrib import admin

# Register your models here.
from .models import User, Post


class PostAdmin(admin.ModelAdmin):
    list_display = ("id", "author", "text", "likes_count", "creation_date")
    list_filter = ("author", )


class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "username")


admin.site.register(User, UserAdmin)
admin.site.register(Post, PostAdmin)
