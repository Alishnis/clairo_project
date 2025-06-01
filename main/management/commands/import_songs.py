import os
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files import File
from main.models import Song

class Command(BaseCommand):
    help = 'Imports songs from the media/songs directory into the database.'

    def handle(self, *args, **options):
        songs_dir = os.path.join(settings.MEDIA_ROOT, 'songs')
        if not os.path.exists(songs_dir):
            self.stdout.write(self.style.ERROR(f'Directory does not exist: {songs_dir}'))
            return

        self.stdout.write(self.style.SUCCESS(f'Scanning directory: {songs_dir}'))

        for filename in os.listdir(songs_dir):
            if filename.endswith(('.mp3', '.wav', '.ogg')):
                self.stdout.write(f'Processing file: {filename}')
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

                self.stdout.write(f'  Extracted - Title: {title}, Artist: {artist}')

                # Check if a song with this title and artist already exists
                if Song.objects.filter(title=title, artist=artist).exists():
                    self.stdout.write(self.style.WARNING(f'  Song already exists: {title} - {artist}. Skipping.'))
                    continue

                try:
                    with open(file_path, 'rb') as f:
                        song = Song(title=title, artist=artist)
                        song.audio_file.save(os.path.join('songs', filename), File(f), save=True)
                    self.stdout.write(self.style.SUCCESS(f'  Successfully imported song: {title} - {artist}'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  Error importing {filename}: {e}'))

        self.stdout.write(self.style.SUCCESS('Song import process finished.')) 