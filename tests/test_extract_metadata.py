from io import BytesIO
import unittest

from PIL import Image, PngImagePlugin

from extract_metadata import extract_metadata, readable, format_text
from utils import load_existing_metadata


class ExtractMetadataTests(unittest.TestCase):
    def test_ui_reads_nested_unicode_exif_comment(self):
        for encoding in ("utf-16-le", "utf-16-be"):
            with self.subTest(encoding=encoding):
                buffer = BytesIO()
                text = "Prompt: café\nNegative prompt: blur\nSteps: 8"
                exif = Image.Exif()
                exif[0x8769] = {0x9286: b"UNICODE\x00" + text.encode(encoding)}
                Image.new("RGB", (4, 4)).save(buffer, format="JPEG", exif=exif)
                buffer.seek(0)
                self.assertEqual(load_existing_metadata(buffer), text)

    def test_ui_reports_absent_generation_metadata(self):
        buffer = BytesIO()
        Image.new("RGB", (4, 4)).save(buffer, format="PNG")
        buffer.seek(0)
        self.assertEqual(load_existing_metadata(buffer), "No readable metadata found.")

    def test_unicode_comments_and_binary_summary(self):
        text = "Prompt: café\nSteps: 8"
        for order, encoding in (("little", "utf-16-le"), ("big", "utf-16-be")):
            self.assertEqual(readable(b"UNICODE\x00" + text.encode(encoding), order), text)
        self.assertEqual(readable(b"UNICODE\x00" + text.encode("utf-16-be"), "little"), text)
        self.assertEqual(readable(b"\xff\x00"), {"byte_count": 2})
        output = format_text({"format": "JPEG", "size": [4, 4],
                              "parameters_found": False, "info": {},
                              "exif": {"UserComment": text}})
        self.assertIn(text, output)
        self.assertNotIn("\\u0000", output)

    def test_png_reports_parameters_and_other_text(self):
        buffer = BytesIO()
        info = PngImagePlugin.PngInfo()
        info.add_text("parameters", "Prompt: café\nSteps: 20")
        info.add_text("workflow", '{"nodes": []}')
        Image.new("RGB", (4, 4)).save(buffer, format="PNG", pnginfo=info)
        buffer.seek(0)
        result = extract_metadata(buffer)
        self.assertTrue(result["parameters_found"])
        self.assertEqual(result["parameters"], "Prompt: café\nSteps: 20")
        self.assertEqual(result["info"]["workflow"], '{"nodes": []}')

    def test_jpeg_reports_exif_without_parameters(self):
        buffer = BytesIO()
        exif = Image.Exif()
        exif[0x010E] = "Example description"
        Image.new("RGB", (4, 4)).save(buffer, format="JPEG", exif=exif)
        buffer.seek(0)
        result = extract_metadata(buffer)
        self.assertFalse(result["parameters_found"])
        self.assertEqual(result["exif"]["ImageDescription"], "Example description")


if __name__ == "__main__":
    unittest.main()
