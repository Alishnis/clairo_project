from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Song
import random
import os
import requests
from pydub import AudioSegment
from django.conf import settings
from django.forms.models import model_to_dict
import string

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

def get_lyrics_from_genius(artist, title):
    # First, search for the song
    search_url = f"https://api.genius.com/search"
    headers = {
        "Authorization": f"Bearer {settings.GENIUS_ACCESS_TOKEN}"
    }
    params = {
        "q": f"{title} {artist}"
    }
    
    try:
        search_response = requests.get(search_url, headers=headers, params=params)
        search_data = search_response.json()
        
        if 'response' in search_data and 'hits' in search_data['response']:
            hits = search_data['response']['hits']
            if hits:
                # Get the first result's URL
                song_url = hits[0]['result']['url']
                
                # Now get the lyrics from the song page
                lyrics_response = requests.get(song_url)
                if lyrics_response.status_code == 200:
                    # Extract lyrics from the page (this is a simple example)
                    # You might need to adjust this based on the actual HTML structure
                    lyrics = lyrics_response.text
                    # Add more sophisticated parsing here
                    return lyrics
        
        return None
    except Exception as e:
        print(f"Error getting lyrics from Genius: {str(e)}")
        return None

def clean_text(text):
    # Remove punctuation and convert to lowercase
    return text.translate(str.maketrans('', '', string.punctuation)).lower().strip()

@csrf_exempt
def complete_lyrics_game(request):
    # Initialize session variables if they don't exist
    if 'played_songs' not in request.session:
        request.session['played_songs'] = []
    if 'score' not in request.session:
        request.session['score'] = 0
    if 'total_attempts' not in request.session:
        request.session['total_attempts'] = 0

    songs = Song.objects.all()
    if not songs:
        return render(request, 'main/complete_lyrics.html', {'error': 'No songs found in the database'})

    # Filter out already played songs
    played_songs = request.session['played_songs']
    available_songs = [song for song in songs if song.id not in played_songs]

    # If all songs have been played, show final score and reset
    if not available_songs:
        final_score = request.session['score']
        total_attempts = request.session['total_attempts']
        accuracy = (final_score / total_attempts * 100) if total_attempts > 0 else 0
        
        # Reset session
        request.session['played_songs'] = []
        request.session['score'] = 0
        request.session['total_attempts'] = 0
        
        return render(request, 'main/complete_lyrics.html', {
            'game_completed': True,
            'final_score': final_score,
            'total_attempts': total_attempts,
            'accuracy': round(accuracy, 1)
        })

    song = random.choice(available_songs)
    audio_path = os.path.join(settings.MEDIA_ROOT, str(song.audio_file))
    if not os.path.exists(audio_path):
        return render(request, 'main/complete_lyrics.html', {'error': 'Audio file not found'})

    # Debug information
    print(f"\nDebug Information:")
    print(f"Song from database - Title: '{song.title}', Artist: '{song.artist}'")
    print(f"Audio file path: {audio_path}")
    print(f"Audio file exists: {os.path.exists(audio_path)}")

    # Try to get lyrics from Genius first
    lyrics = get_lyrics_from_genius(song.artist, song.title)
    
    # If Genius fails, try lyrics.ovh as fallback
    if not lyrics:
        try:
            encoded_artist = requests.utils.quote(song.artist)
            encoded_title = requests.utils.quote(song.title)
            api_url = f"https://api.lyrics.ovh/v1/{encoded_artist}/{encoded_title}"
            print(f"\nLyrics.ovh API Request:")
            print(f"Original artist: '{song.artist}'")
            print(f"Original title: '{song.title}'")
            print(f"Encoded artist: '{encoded_artist}'")
            print(f"Encoded title: '{encoded_title}'")
            print(f"Full API URL: {api_url}")
            
            response = requests.get(api_url)
            print(f"Response status code: {response.status_code}")
            print(f"Response content: {response.text[:200]}")
            
            if response.status_code == 200:
                lyrics_data = response.json()
                lyrics = lyrics_data.get('lyrics', '')
                if lyrics:
                    print("Lyrics found successfully!")
                else:
                    print("No lyrics in the response data")
            else:
                print(f"API request failed with status code: {response.status_code}")
        except Exception as e:
            print(f"Error getting lyrics from lyrics.ovh: {str(e)}")
            lyrics = None

    if not lyrics:
        return render(request, 'main/complete_lyrics.html', {
            'error': f'Lyrics are not available for {song.title} by {song.artist}',
            'song_title': song.title,
            'song_artist': song.artist,
            'audio_url': f'{settings.MEDIA_URL}{song.audio_file}',
            'current_score': request.session['score'],
            'songs_remaining': len(available_songs) - 1
        })

    # Process lyrics to create the game
    lines = [line.strip() for line in lyrics.split("\n") if line.strip()]
    if not lines:
        return render(request, 'main/complete_lyrics.html', {
            'error': f'Lyrics are not available for {song.title} by {song.artist}',
            'song_title': song.title,
            'song_artist': song.artist,
            'audio_url': f'{settings.MEDIA_URL}{song.audio_file}',
            'current_score': request.session['score'],
            'songs_remaining': len(available_songs) - 1
        })

    # Select visible lines (up to 5 lines)
    visible_lines = lines[:5]
    
    # Choose a random line to create a blank
    blank_line_index = random.randint(0, len(visible_lines) - 1)
    line_with_blank = visible_lines[blank_line_index]

    # Create the blank in the line
    words = line_with_blank.split()
    if len(words) > 2:
        blank_index = random.randint(0, len(words) - 1)
        removed_word = clean_text(words[blank_index])  # Clean the word
        words[blank_index] = "____"
        blank_line = ' '.join(words)
    else:
        removed_word = clean_text(words[-1]) if words else ''
        blank_line = ' '.join(words[:-1]) + " ____"

    visible_lines[blank_line_index] = blank_line

    # Add song to played songs
    request.session['played_songs'].append(song.id)
    request.session.modified = True

    context = {
        'song_title': song.title,
        'song_artist': song.artist,
        'audio_url': f'{settings.MEDIA_URL}{song.audio_file}',
        'lyrics_snippet': visible_lines,
        'missing_word': removed_word,
        'current_score': request.session['score'],
        'songs_remaining': len(available_songs) - 1
    }

    return render(request, 'main/complete_lyrics.html', context)

@csrf_exempt
def check_answer(request):
    if request.method == 'POST':
        user_answer = clean_text(request.POST.get('answer', ''))
        correct_answer = clean_text(request.POST.get('correct_answer', ''))
        
        request.session['total_attempts'] = request.session.get('total_attempts', 0) + 1
        
        if user_answer == correct_answer:
            request.session['score'] = request.session.get('score', 0) + 1
            request.session.modified = True
            return JsonResponse({'correct': True, 'score': request.session['score']})
        else:
            return JsonResponse({'correct': False, 'score': request.session['score']})
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
def debug_songs(request):
    songs = Song.objects.all()
    debug_info = []
    for song in songs:
        debug_info.append({
            'id': song.id,
            'title': song.title,
            'artist': song.artist,
            'audio_file': str(song.audio_file)
        })
    return JsonResponse({'songs': debug_info})