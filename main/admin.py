from django.contrib import admin
from .models import Song

@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ('title', 'artist', 'created_at')
    search_fields = ('title', 'artist')
    list_filter = ('created_at',)
