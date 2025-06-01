import os
import django
import sys

# Set up Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from django.core.files import File
from main.models import Song

def import_songs():
    songs_dir = os.path.join(settings.MEDIA_ROOT, 'songs')
    if not os.path.exists(songs_dir):
        print(f'Error: Directory does not exist: {songs_dir}')
        return

    print(f'Scanning directory: {songs_dir}')

    for filename in os.listdir(songs_dir):
        if filename.endswith(('.mp3', '.wav', '.ogg')):
            print(f'Processing file: {filename}')
            file_path = os.path.join(songs_dir, filename)
            
            # Try to parse title and artist from filename (assuming 'Artist - Title.mp3')
            name_parts = os.path.splitext(filename)[0].split(' - ')
            if len(name_parts) == 2:
                artist = name_parts[0].strip()
                title = name_parts[1].strip()
            else:
                # Fallback to filename if parsing fails
                artist = 'Unknown Artist'
                title = os.path.splitext(filename)[0].strip()

            print(f'  Extracted - Title: {title}, Artist: {artist}')

            # Check if a song with this title and artist already exists
            if Song.objects.filter(title=title, artist=artist).exists():
                print(f'  Warning: Song already exists: {title} - {artist}. Skipping.')
                continue

            try:
                with open(file_path, 'rb') as f:
                    song = Song(title=title, artist=artist)
                    song.audio_file.save(os.path.join('songs', filename), File(f), save=True)
                print(f'  Successfully imported song: {title} - {artist}')
            except Exception as e:
                print(f'  Error importing {filename}: {e}')

    print('Song import process finished.')

if __name__ == '__main__':
    import_songs() 