from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Song
import random
import os
from pydub import AudioSegment
from django.conf import settings
from django.forms.models import model_to_dict

# Create your views here.

def home(request):
    songs = Song.objects.all().values('title', 'artist') # Get only necessary fields
    songs_list = list(songs)
    return render(request, 'main/home.html', {'all_songs': songs_list})

@csrf_exempt
def get_song(request):
    songs = Song.objects.all()
    if not songs:
        return JsonResponse({'error': 'No songs available'}, status=404)
    
    song = random.choice(songs)
    
    # Create a short clip of the song
    audio_path = os.path.join(settings.MEDIA_ROOT, str(song.audio_file))
    
    # Check if the audio file exists
    if not os.path.exists(audio_path):
        return JsonResponse({'error': f'Audio file not found: {song.audio_file}'}, status=404)

    try:
        audio = AudioSegment.from_file(audio_path)
    except Exception as e:
        return JsonResponse({'error': f'Error processing audio file {song.audio_file}: {e}'}, status=500)

    # Ensure audio is at least 3 seconds long
    if len(audio) < 3000:
         # Use the whole song if it's shorter than 3 seconds
        clip = audio
    else:
        # Get a random 3-second clip
        start_time = random.randint(0, len(audio) - 3000)
        clip = audio[start_time:start_time + 3000]
    
    # Save the clip
    clip_filename = f'clip_{song.id}.mp3'
    clip_path = os.path.join(settings.MEDIA_ROOT, 'clips', clip_filename)
    os.makedirs(os.path.dirname(clip_path), exist_ok=True)
    
    try:
        clip.export(clip_path, format='mp3')
    except Exception as e:
        return JsonResponse({'error': f'Error exporting audio clip: {e}'}, status=500)

    return JsonResponse({
        'title': song.title,
        'artist': song.artist,
        'audio_url': f'{settings.MEDIA_URL}clips/{clip_filename}'
    })
