import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools" / "mga" / "memstick.py"
SPEC = importlib.util.spec_from_file_location("mga_memstick", MODULE_PATH)
memstick = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(memstick)


class MemstickFixtureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_creates_empty_backend_layouts(self):
        for backend, layout in memstick.LAYOUTS.items():
            fixture = self.root / backend
            document = memstick.create_fixture(fixture, backend)

            self.assertEqual(document["profile"], "empty")
            self.assertTrue((fixture / layout).is_dir())
            self.assertEqual(
                memstick.verify_fixture(fixture, backend), document
            )

    def test_clones_existing_save_without_source_path(self):
        template = self.root / "template"
        savedata = memstick.expected_savedata(template, "ppsspp")
        savedata.mkdir(parents=True)
        save = savedata / "ULUS10006TEST" / "DATA.BIN"
        save.parent.mkdir()
        save.write_bytes(b"synthetic-save")

        fixture = self.root / "clone"
        document = memstick.create_fixture(
            fixture, "ppsspp", template=template
        )

        self.assertEqual(document["profile"], "existing-save")
        self.assertEqual((fixture / save.relative_to(template)).read_bytes(), b"synthetic-save")
        manifest_text = (fixture / memstick.MANIFEST).read_text(
            encoding="ascii"
        )
        self.assertNotIn(str(template), manifest_text)
        memstick.verify_fixture(fixture, "ppsspp")

    def test_rejects_existing_output(self):
        output = self.root / "existing"
        output.mkdir()
        with self.assertRaisesRegex(
            memstick.FixtureError, "output already exists"
        ):
            memstick.create_fixture(output, "native")

    def test_rejects_wrong_template_layout(self):
        template = self.root / "template"
        template.mkdir()
        with self.assertRaisesRegex(
            memstick.FixtureError, "missing backend layout"
        ):
            memstick.create_fixture(
                self.root / "clone", "native", template=template
            )

    def test_detects_fixture_mutation(self):
        fixture = self.root / "fixture"
        memstick.create_fixture(fixture, "native")
        changed = fixture / memstick.LAYOUTS["native"] / "changed.bin"
        changed.write_bytes(b"changed")

        with self.assertRaisesRegex(
            memstick.FixtureError, "inventory has changed"
        ):
            memstick.verify_fixture(fixture, "native")


if __name__ == "__main__":
    unittest.main()
