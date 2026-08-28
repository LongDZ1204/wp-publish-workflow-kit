import importlib.util
import tempfile
import unittest
from pathlib import Path

from PIL import Image


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "image_prepare.py"
spec = importlib.util.spec_from_file_location("image_prepare", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class ImagePrepareTests(unittest.TestCase):
    def make_image(self, path, size=(100, 80), fmt="JPEG"):
        Image.new("RGB", size, (20, 80, 140)).save(path, format=fmt)

    def test_prepare_new_keeps_source(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "source.jpg"
            self.make_image(src)
            original = src.read_bytes()
            result = mod.prepare({
                "profile": {"format_policy": "preserve", "max_kb": 150, "max_width": 1200},
                "images": [{"asset_id": "hero", "source": str(src), "filename": "semantic-hero-image.jpg", "alt": "Semantic hero image for workflow", "decorative": False}],
            }, "prepare-new", root / "out")
            self.assertEqual(src.read_bytes(), original)
            self.assertTrue(Path(result["images"][0]["output"]).exists())
            self.assertEqual(result["images"][0]["action"], "prepare-upload")

    def test_audit_preserves_existing_url(self):
        result = mod.prepare({
            "profile": {"format_policy": "preserve"},
            "images": [{"asset_id": "live", "existing_url": "https://example.com/a.jpg", "alt": "Existing informative workflow image", "decorative": False}],
        }, "audit-existing", Path("unused"))
        self.assertEqual(result["images"][0]["action"], "preserve-existing")

    def test_duplicate_alt_stops(self):
        with self.assertRaises(ValueError):
            mod.prepare({"images": [
                {"asset_id": "a", "existing_url": "https://e/a.jpg", "alt": "same alt", "decorative": False},
                {"asset_id": "b", "existing_url": "https://e/b.jpg", "alt": "same alt", "decorative": False},
            ]}, "audit-existing", Path("unused"))

    def test_existing_output_collision_stops(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "source.jpg"
            self.make_image(src)
            out = root / "out"
            out.mkdir()
            (out / "semantic-image-name.jpg").write_bytes(b"occupied")
            with self.assertRaises(ValueError):
                mod.prepare({"images": [{
                    "asset_id": "x", "source": str(src), "filename": "semantic-image-name.jpg",
                    "alt": "Semantic image name for test", "decorative": False,
                }]}, "prepare-new", out)


if __name__ == "__main__":
    unittest.main()
