from PIL import Image
from PIL.ExifTags import TAGS
import piexif

def decode_user_comment(value):
    # Ensure we use UTF-8 decoding and strip the "UNICODE" prefix if it exists
    if value.startswith(b'UNICODE'):
        return value[8:].decode('utf-8', errors='ignore').strip()
    else:
        return value.decode('utf-8', errors='ignore').strip()

def extract_exif_data(image_path):
    image = Image.open(image_path)
    
    # Check if EXIF data is present
    exif_data = image._getexif()
    
    if exif_data:
        readable_metadata = {}
        for tag, value in exif_data.items():
            tag_name = TAGS.get(tag, tag)
            if isinstance(value, bytes):
                try:
                    decoded_value = decode_user_comment(value)
                except Exception as e:
                    decoded_value = f"Error decoding: {e}"
                readable_metadata[tag_name] = decoded_value
            else:
                readable_metadata[tag_name] = value
        
        if readable_metadata:
            print("EXIF Data:")
            for key, value in readable_metadata.items():
                print(f"{key}: {value}\n")
        else:
            print("EXIF data found but no readable metadata.")
    else:
        print("No EXIF data found in the image.")

def extract_png_text_chunks(image_path):
    image = Image.open(image_path)
    
    if image.format == 'PNG':
        print("Checking PNG text chunks...")
        try:
            text_data = image.text
            if text_data:
                print("PNG Text Chunks:")
                for key, value in text_data.items():
                    print(f"{key}: {value}\n")
            else:
                print("No PNG text chunks found.")
        except Exception as e:
            print(f"Error reading PNG text chunks: {e}")
    else:
        print("The image is not in PNG format.")

# Path to the uploaded image
image_path = (r"Path to File")

# Extract and display EXIF data
extract_exif_data(image_path)

# If EXIF data is not found, check for PNG text chunks
extract_png_text_chunks(image_path)
