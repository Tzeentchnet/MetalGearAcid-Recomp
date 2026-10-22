import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools" / "mga" / "padscript.py"
SPEC = importlib.util.spec_from_file_location("mga_padscript", MODULE_PATH)
padscript = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(padscript)


class PadScriptTests(unittest.TestCase):
    def write_script(self, lines):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "test.pad"
        path.write_text("\n".join(lines) + "\n", encoding="ascii")
        return path

    def test_shipped_profiles_are_valid(self):
        neutral = padscript.read_padscript(
            ROOT / "config" / "mga_neutral.pad"
        )
        boot = padscript.read_padscript(ROOT / "config" / "mga_boot.pad")
        menu = padscript.read_padscript(
            ROOT / "config" / "mga_menu_probe.pad"
        )

        self.assertEqual(neutral, [])
        self.assertEqual(len(boot), 10)
        self.assertEqual(boot[0].mask, 0x0008)
        self.assertEqual(boot[0].ppsspp_vblank, 120)
        self.assertEqual(boot[0].runtime_present, 360)
        self.assertEqual(boot[-1].runtime_present, 2520)
        self.assertEqual(len(menu), 14)
        self.assertEqual(
            [event.mask for event in menu[-4:]],
            [0x0008, 0x0040, 0x0010, 0x2000],
        )

    def test_rejects_missing_header(self):
        path = self.write_script(["10 20 0008 2 3"])
        with self.assertRaisesRegex(
            padscript.PadScriptError, "missing.*pad script v3"
        ):
            padscript.read_padscript(path)

    def test_rejects_nonincreasing_backend_timing(self):
        path = self.write_script(
            [
                padscript.HEADER,
                "10 20 0008 2 3",
                "30 20 4000 4 5",
            ]
        )
        with self.assertRaisesRegex(
            padscript.PadScriptError, "runtime presents must increase"
        ):
            padscript.read_padscript(path)

    def test_rejects_zero_width(self):
        path = self.write_script(
            [padscript.HEADER, "10 20 0008 0 3"]
        )
        with self.assertRaisesRegex(
            padscript.PadScriptError, "widths must be positive"
        ):
            padscript.read_padscript(path)

    def test_rejects_oversized_mask(self):
        path = self.write_script(
            [padscript.HEADER, "10 20 100000000 2 3"]
        )
        with self.assertRaisesRegex(
            padscript.PadScriptError, "mask is outside uint32"
        ):
            padscript.read_padscript(path)


if __name__ == "__main__":
    unittest.main()
