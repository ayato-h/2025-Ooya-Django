from django.contrib import admin
from .models import CustomUser, FriendRequest, Friendship

admin.site.register(CustomUser)

@admin.register(FriendRequest)
class FriendRequestAdmin(admin.ModelAdmin):
    list_display = ('from_user', 'to_user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('from_user__username', 'to_user__username')

@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ('user', 'friend')
    search_fields = ('user__username', 'friend__username')