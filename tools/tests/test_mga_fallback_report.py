import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools" / "mga" / "fallback_report.py"
SPEC = importlib.util.spec_from_file_location(
    "mga_fallback_report", MODULE_PATH
)
fallback = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fallback)


class FallbackReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write_misses(self):
        path = self.root / "misses.txt"
        path.write_text(
            "# psp-recomp interpreter misses v2\n"
            "mga_stage_init 0x09b43c00\n"
            "mga_stage_title 0x09b43c00\n",
            encoding="ascii",
        )
        return path

    def test_preserves_overlapping_module_targets(self):
        targets = fallback.load_targets(self.write_misses())

        self.assertEqual(
            targets,
            {
                ("mga_stage_init", 0x09B43C00),
                ("mga_stage_title", 0x09B43C00),
            },
        )

    def test_checks_exact_allowlist(self):
        allowlist = self.root / "allowlist.toml"
        allowlist.write_text(
            'schema = "mga-fallback-allowlist-v1"\n'
            "[[module]]\n"
            'prefix = "mga_stage_init"\n'
            "targets = [0x09b43c00]\n"
            "[[module]]\n"
            'prefix = "mga_stage_title"\n'
            "targets = [0x09b43c00]\n",
            encoding="ascii",
        )
        targets = fallback.load_targets(self.write_misses())

        result = fallback.validate_allowlist(targets, allowlist)

        self.assertEqual(result["targets"], 2)

    def test_rejects_unexpected_target(self):
        allowlist = self.root / "allowlist.toml"
        allowlist.write_text(
            'schema = "mga-fallback-allowlist-v1"\n',
            encoding="ascii",
        )

        with self.assertRaisesRegex(
            fallback.FallbackError, "unexpected"
        ):
            fallback.validate_allowlist(
                fallback.load_targets(self.write_misses()), allowlist
            )


if __name__ == "__main__":
    unittest.main()
