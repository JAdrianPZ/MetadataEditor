from PIL import Image, PngImagePlugin
import hashlib
import os
import tempfile
from pathlib import Path
from extract_metadata import readable
from metadata import normalize_metadata, parse_parameters


def read_image_generation(image_path):
    """Read editable generation fields without importing a node workflow."""
    original = load_existing_metadata(image_path)
    if original.startswith('Error loading metadata:'):
        raise ValueError(original)
    if original == 'No readable metadata found.':
        return {'prompt': '', 'negative': '', 'fields': {}, 'original': original,
                'source': 'Manual entry',
                'warnings': ['No readable generation text found. Enter the prompt, settings, and model/LoRA references manually.']}
    result = normalize_metadata(parse_parameters(original))
    result.update(original=original, source='Parameters / EXIF', warnings=[])
    return result


def load_existing_metadata(image_path):
    try:
        with Image.open(image_path) as image:
            image.load()
            existing_metadata = image.info.get("parameters", None)
            if not existing_metadata:
                exif = image.getexif()
                comment = exif.get(0x9286)
                if 0x8769 in exif:
                    comment = exif.get_ifd(0x8769).get(0x9286) or comment
                raw_exif = image.info.get("exif", b"")
                byteorder = "little" if raw_exif.startswith(b"Exif\x00\x00II") else "big"
                decoded = readable(comment, byteorder)
                if isinstance(decoded, str) and decoded.strip():
                    existing_metadata = decoded
        if existing_metadata:
            return existing_metadata
        else:
            return "No readable metadata found."
    except Exception as e:
        return f"Error loading metadata: {str(e)}"

def save_sd_metadata_to_png(image_path, output_path, metadata, overwrite):
    # Load pixels before opening the destination, including when overwriting.
    with Image.open(image_path) as source:
        source.load()
        info = dict(source.info)
        image = source.copy()
    pnginfo = PngImagePlugin.PngInfo()
    for key, value in info.items():
        if isinstance(value, str) and key != "parameters":
            pnginfo.add_text(key, value)
    pnginfo.add_text("parameters", metadata)
    options = {key: info[key] for key in ("icc_profile", "exif", "dpi") if info.get(key)}
    destination = Path(output_path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, suffix=".png", delete=False) as handle:
            temporary = handle.name
        image.save(temporary, "PNG", pnginfo=pnginfo, **options)
        os.replace(temporary, destination)
    finally:
        image.close()
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)

def select_model(file_path=None):
    if file_path:
        model_hash, model_name = get_model_hash_and_name(file_path)
        return model_hash, model_name
    return "Unknown", "Unknown"

def get_model_hash_and_name(file_path):
    try:
        with open(file_path, "rb") as f:
            digest = hashlib.sha256()
            for block in iter(lambda: f.read(1024 * 1024), b""):
                digest.update(block)
            model_hash = digest.hexdigest()[:10]
            model_name = os.path.basename(file_path).rsplit('.', 1)[0]
        return model_hash, model_name
    except Exception as e:
        return "Error", "Unknown"
