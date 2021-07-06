from django.contrib import admin

from .models import User, Category, Listing, Bid, Comment, Watchlist


class ListingAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "is_active", "creation_date")


class BidAdmin(admin.ModelAdmin):
    list_display = ("listing", "user", "amount_dollars", "date")
    list_filter = ("listing", "user")


class CommentAdmin(admin.ModelAdmin):
    list_display = ("user", "listing", "text", "date")


admin.site.register(User)
admin.site.register(Category)
admin.site.register(Listing, ListingAdmin)
admin.site.register(Bid, BidAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(Watchlist)
