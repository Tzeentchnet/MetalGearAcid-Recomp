import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
MODULE_DIR = ROOT / "tools" / "mga"
sys.path.insert(0, str(MODULE_DIR))
MODULE_PATH = MODULE_DIR / "frontend_acceptance.py"
SPEC = importlib.util.spec_from_file_location(
    "mga_frontend_acceptance", MODULE_PATH
)
acceptance = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(acceptance)


class FrontendAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write_ppm(self, name, selector):
        width, height = 480, 272
        pixels = bytearray(width * height * 3)
        for y in range(height):
            for x in range(width):
                offset = (y * width + x) * 3
                pixels[offset : offset + 3] = bytes(
                    (32 + x % 192, 32 + y % 192, 32 + (x + y) % 192)
                )
        y0 = 186 if selector == "new" else 196
        for y in range(y0, y0 + 10):
            for x in range(0, 22):
                offset = (y * width + x) * 3
                pixels[offset : offset + 3] = b"\xff\xff\xff"
        path = self.root / name
        path.write_bytes(
            f"P6\n{width} {height}\n255\n".encode("ascii") + pixels
        )
        return path

    def test_reads_selector_regions(self):
        new_frame = acceptance.frame_summary(
            self.write_ppm("new.ppm", "new")
        )
        load_frame = acceptance.frame_summary(
            self.write_ppm("load.ppm", "load")
        )

        self.assertEqual(new_frame["width"], 480)
        self.assertGreater(new_frame["selector_new"], 40)
        self.assertGreater(load_frame["selector_load"], 40)

    def test_rejects_truncated_pixels(self):
        path = self.root / "bad.ppm"
        path.write_bytes(b"P6\n480 272\n255\n\x00")

        with self.assertRaisesRegex(
            acceptance.AcceptanceError, "pixel bytes"
        ):
            acceptance.read_ppm(path)


if __name__ == "__main__":
    unittest.main()
