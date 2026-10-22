import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools" / "mga" / "perf_report.py"
SPEC = importlib.util.spec_from_file_location("mga_perf_report", MODULE_PATH)
perf_report = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(perf_report)


class PerformanceReportTests(unittest.TestCase):
    def write_samples(self, root, name, rows):
        path = Path(root) / name
        path.write_text(
            perf_report.SCHEMA
            + "\n"
            + ",".join(perf_report.COLUMNS)
            + "\n"
            + "\n".join(rows)
            + "\n",
            encoding="ascii",
        )
        return path

    def test_builds_multi_run_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            first = self.write_samples(
                temporary,
                "first.csv",
                [
                    "2,10,7,3,-1,0",
                    "3,20,16,4,2,1",
                    "4,30,25,5,3,1",
                ],
            )
            second = self.write_samples(
                temporary,
                "second.csv",
                [
                    "2,12,9,3,1,0",
                    "3,18,14,4,2,1",
                    "4,24,19,5,3,1",
                ],
            )
            report = perf_report.build_report([first, second])
            self.assertEqual(report["aggregate"]["run_count"], 2)
            self.assertEqual(report["runs"][0]["frame_ms"]["p50"], 20.0)
            self.assertEqual(report["runs"][0]["frame_ms"]["p95"], 30.0)
            self.assertEqual(report["runs"][0]["frame_ms"]["over_budget"], 2)
            self.assertEqual(report["runs"][0]["gpu_ms"]["samples"], 2)

    def test_rejects_non_monotonic_present(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = self.write_samples(
                temporary,
                "bad.csv",
                [
                    "2,10,7,3,1,0",
                    "2,11,8,3,1,0",
                ],
            )
            with self.assertRaisesRegex(
                perf_report.PerformanceError, "out-of-range"
            ):
                perf_report.load_samples(path)


if __name__ == "__main__":
    unittest.main()
