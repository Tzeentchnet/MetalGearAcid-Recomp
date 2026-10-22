import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools" / "mga" / "interp_profile.py"
SPEC = importlib.util.spec_from_file_location(
    "mga_interp_profile", MODULE_PATH
)
interp_profile = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(interp_profile)


class InterpreterProfileTests(unittest.TestCase):
    def write_profile(self, root, name, rows):
        path = Path(root) / name
        path.write_text(
            interp_profile.SCHEMA
            + "\n"
            + "\t".join(interp_profile.COLUMNS)
            + "\n"
            + "\n".join(rows)
            + "\n",
            encoding="ascii",
        )
        return path

    def test_aggregates_and_ranks_profiles(self):
        with tempfile.TemporaryDirectory() as temporary:
            first = self.write_profile(
                temporary,
                "first.tsv",
                [
                    "title\t0x09b40000\t2\t200\t1\t3\t0\t2\t0",
                    "title\t0x09b40040\t10\t100\t0\t1\t0\t10\t0",
                ],
            )
            second = self.write_profile(
                temporary,
                "second.tsv",
                ["title\t0x09b40000\t1\t150\t0\t2\t1\t1\t0"],
            )
            report = interp_profile.build_report([first, second], top=1)
            self.assertEqual(report["unique_targets"], 2)
            self.assertEqual(report["totals"]["instructions"], 450)
            self.assertEqual(report["top"][0]["target"], "0x09b40000")
            self.assertEqual(report["top"][0]["calls"], 3)
            self.assertEqual(report["top"][0]["instructions"], 350)

    def test_rejects_duplicate_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = self.write_profile(
                temporary,
                "bad.tsv",
                [
                    "title\t0x09b40000\t1\t10\t0\t0\t0\t1\t0",
                    "title\t0x09b40000\t1\t10\t0\t0\t0\t1\t0",
                ],
            )
            with self.assertRaisesRegex(
                interp_profile.ProfileError, "duplicate"
            ):
                interp_profile.load_profile(path)


if __name__ == "__main__":
    unittest.main()
