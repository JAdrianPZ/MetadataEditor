"""Read image metadata without modifying the source image."""

import argparse
import json
import sys

from PIL import ExifTags, Image


def readable(value, byteorder="big"):
    if isinstance(value, bytes):
        # EXIF UserComment can include an eight-byte encoding prefix.
        if value.startswith(b"ASCII\x00\x00\x00"):
            return value[8:].decode("ascii", errors="replace").rstrip("\x00")
        if value.startswith(b"UNICODE\x00"):
            payload = value[8:]
            # Some writers use a different byte order for the comment than TIFF.
            # For predominantly Latin text, the zero-byte positions disambiguate it.
            even_zeros = payload[0::2].count(0)
            odd_zeros = payload[1::2].count(0)
            if max(even_zeros, odd_zeros) > len(payload) // 8:
                byteorder = "big" if even_zeros > odd_zeros else "little"
            encoding = "utf-16" if payload.startswith((b"\xff\xfe", b"\xfe\xff")) else (
                "utf-16-le" if byteorder == "little" else "utf-16-be")
            return payload.decode(encoding, errors="replace").rstrip("\x00")
        if b"\x00" in value:
            return {"byte_count": len(value)}
        try:
            return value.decode("utf-8").rstrip("\x00")
        except UnicodeDecodeError:
            return {"byte_count": len(value)}
    if isinstance(value, dict):
        return {str(key): readable(item, byteorder) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [readable(item, byteorder) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def extract_metadata(source):
    with Image.open(source) as image:
        # PNG text chunks can occur after the pixel data.
        image.load()
        exif = image.getexif()
        raw_exif = image.info.get("exif", b"")
        byteorder = "little" if raw_exif.startswith(b"Exif\x00\x00II") else "big"
        exif_data = {ExifTags.TAGS.get(tag, str(tag)): readable(value, byteorder)
                     for tag, value in exif.items()}
        for tag, name in ((0x8769, "ExifIFD"), (0x8825, "GPSIFD")):
            if tag in exif:
                names = ExifTags.GPSTAGS if name == "GPSIFD" else ExifTags.TAGS
                exif_data[name] = {
                    names.get(key, str(key)): readable(value, byteorder)
                    for key, value in exif.get_ifd(tag).items()
                }
        parameters = image.info.get("parameters")
        return {
            "format": image.format,
            "size": list(image.size),
            "mode": image.mode,
            "parameters_found": bool(parameters),
            "parameters": readable(parameters),
            "info": {key: ({"byte_count": len(value)} if key in ("exif", "icc_profile")
                           and isinstance(value, bytes) else readable(value, byteorder))
                     for key, value in image.info.items()},
            "exif": exif_data,
        }


def format_text(result):
    lines = [f"Format: {result['format']} | Size: {result['size'][0]} x {result['size'][1]}",
             f"parameters field: {'present' if result['parameters_found'] else 'absent'}"]

    def append_fields(fields, prefix=""):
        for key, value in fields.items():
            label = f"{prefix}{key}"
            if isinstance(value, dict) and set(value) == {"byte_count"}:
                lines.append(f"{label}: [binary data: {value['byte_count']} bytes]")
            elif isinstance(value, dict):
                append_fields(value, label + " / ")
            elif isinstance(value, str) and "\n" in value:
                lines.append(f"\n{label}:\n{value}\n")
            else:
                lines.append(f"{label}: {value}")

    append_fields(result["info"], "Info / ")
    append_fields(result["exif"], "EXIF / ")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Read image metadata without modifying the image.")
    parser.add_argument("image", help="Path to a PNG, JPEG or other Pillow-supported image")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of readable text")
    args = parser.parse_args()
    try:
        result = extract_metadata(args.image)
    except Exception as error:
        print(f"Error reading image: {error}", file=sys.stderr)
        return 1
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else format_text(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
