from django.contrib import admin
from .models import Song, ChatRoom, Message

@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ('track_name', 'artist_name', 'album_name', 'preview_url')
    search_fields = ('track_name', 'artist_name', 'album_name')
    ordering = ('track_name',)

@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at', 'participants_count')
    search_fields = ('name',)
    ordering = ('-created_at',)
    filter_horizontal = ('participants',)  

    def participants_count(self, obj):
        return obj.participants.count()
    participants_count.short_description = "参加者数"

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'room', 'sender', 'short_content', 'created_at')
    search_fields = ('sender__username', 'content', 'room__name')
    list_filter = ('room', 'created_at')
    ordering = ('-created_at',)

    def short_content(self, obj):
        return obj.content[:50] + ('...' if len(obj.content) > 50 else '')
    short_content.short_description = '内容（短縮）'

