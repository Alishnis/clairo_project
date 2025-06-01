from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.home, name='home'),
    path('get-song/', views.get_song, name='get_song'),
    path('lyrics/', views.complete_lyrics_game, name='complete_lyrics'),
    path('check-answer/', views.check_answer, name='check_answer'),
    path('debug/songs/', views.debug_songs, name='debug_songs'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 