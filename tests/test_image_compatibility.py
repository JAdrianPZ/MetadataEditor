import tempfile
import unittest
from pathlib import Path

from PIL import Image, PngImagePlugin

from utils import load_existing_metadata, save_sd_metadata_to_png


class ImageCompatibilityTests(unittest.TestCase):
    def test_export_preserves_existing_text_and_exif(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.png"
            output = Path(directory) / "output.png"
            info = PngImagePlugin.PngInfo()
            info.add_text("workflow", '{"original":true}')
            exif = Image.Exif()
            exif[0x010E] = "Original description"
            Image.new("RGB", (4, 4)).save(source, pnginfo=info, exif=exif)
            save_sd_metadata_to_png(source, output, "new parameters", False)
            with Image.open(output) as image:
                self.assertEqual(image.info["workflow"], '{"original":true}')
                self.assertEqual(image.getexif()[0x010E], "Original description")
                self.assertEqual(image.info["parameters"], "new parameters")

    def test_export_failure_is_propagated(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.png"
            Image.new("RGB", (4, 4)).save(source)
            with self.assertRaises(OSError):
                save_sd_metadata_to_png(source, Path(directory) / "missing" / "out.png", "test", False)

    def test_png_metadata_round_trip_preserves_pixels(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.png"
            output = Path(directory) / "output.png"
            info = PngImagePlugin.PngInfo()
            info.add_text("parameters", "original prompt")
            Image.new("RGBA", (16, 12), (10, 20, 30, 128)).save(source, pnginfo=info)
            self.assertEqual(load_existing_metadata(source), "original prompt")
            metadata = "Nuevo prompt: café\nNegative prompt: blur\nSteps: 20"
            save_sd_metadata_to_png(source, output, metadata, False)
            self.assertEqual(load_existing_metadata(output), metadata)
            with Image.open(source) as before, Image.open(output) as after:
                self.assertEqual(after.size, before.size)
                self.assertEqual(after.mode, before.mode)
                self.assertEqual(after.tobytes(), before.tobytes())

    def test_jpeg_conversion_and_png_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.jpg"
            output = Path(directory) / "output.png"
            Image.new("RGB", (32, 24), "red").save(source)
            with Image.open(source) as image:
                image.thumbnail((20, 20))
                self.assertEqual(image.size, (20, 15))
            save_sd_metadata_to_png(source, output, "first", False)
            save_sd_metadata_to_png(output, output, "updated", True)
            self.assertEqual(load_existing_metadata(output), "updated")
            with Image.open(output) as image:
                self.assertEqual(image.format, "PNG")
                self.assertEqual(image.size, (32, 24))


if __name__ == "__main__":
    unittest.main()
