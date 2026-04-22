import os
import urllib.request
import urllib.parse
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dbproject.settings')
django.setup()

from workouts.models import ExerciseImage

def run():
    img_dir = os.path.join('static', 'images', 'exercises')
    os.makedirs(img_dir, exist_ok=True)
    
    images = ExerciseImage.objects.all()
    print(f"Downloading {images.count()} images...")
    
    for img in images:
        filename = os.path.basename(img.image_path)
        filepath = os.path.join(img_dir, filename)
        
        if not os.path.exists(filepath):
            # Parse exercise name from caption
            ex_name = img.caption.split('—')[0].strip()
            
            # Add line breaks for long names
            words = ex_name.split(' ')
            if len(words) > 2:
                ex_name = ' '.join(words[:2]) + '\\n' + ' '.join(words[2:])
                
            # URL encode text
            encoded_text = urllib.parse.quote(ex_name)
            
            # placehold.co URL. Dark-mid is 2a2a2a, accent is e8ff00
            url = f"https://placehold.co/600x400/2a2a2a/e8ff00/png?text={encoded_text}"
            
            try:
                urllib.request.urlretrieve(url, filepath)
                print(f"Downloaded: {filename}")
            except Exception as e:
                print(f"Failed to download {filename}: {e}")
        else:
            print(f"Already exists: {filename}")

if __name__ == '__main__':
    run()
