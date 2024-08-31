from PIL import Image, PngImagePlugin
import hashlib
import os

def load_existing_metadata(image_path):
    try:
        image = Image.open(image_path)
        existing_metadata = image.info.get("parameters", None)
        if existing_metadata:
            return existing_metadata
        else:
            return "No readable metadata found."
    except Exception as e:
        return f"Error loading metadata: {str(e)}"

def save_sd_metadata_to_png(image_path, output_path, metadata, overwrite):
    try:
        image = Image.open(image_path)
        pnginfo = PngImagePlugin.PngInfo()
        pnginfo.add_text("parameters", metadata)
        image.save(output_path, "PNG", pnginfo=pnginfo)
        print(f"Image saved at {output_path}")
    except Exception as e:
        print(f"Error saving image: {e}")

def select_model(file_path=None):
    if file_path:
        model_hash, model_name = get_model_hash_and_name(file_path)
        return model_hash, model_name
    return "Unknown", "Unknown"

def get_model_hash_and_name(file_path):
    try:
        with open(file_path, "rb") as f:
            model_data = f.read()
            # Generate a 10-character hash (to match the working example)
            model_hash = hashlib.sha256(model_data).hexdigest()[:10]
            model_name = os.path.basename(file_path).rsplit('.', 1)[0]
        return model_hash, model_name
    except Exception as e:
        return "Error", "Unknown"
