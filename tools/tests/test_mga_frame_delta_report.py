import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools" / "mga" / "frame_delta_report.py"
SPEC = importlib.util.spec_from_file_location(
    "mga_frame_delta_report", MODULE_PATH
)
frame_delta_report = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(frame_delta_report)


def write_ppm(path, width, height, pixels):
    Path(path).write_bytes(
        f"P6\n{width} {height}\n255\n".encode("ascii") + bytes(pixels)
    )


class FrameDeltaReportTests(unittest.TestCase):
    def test_classifies_edge_and_neighbor_match(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reference = bytearray(3 * 3 * 3)
            actual = bytearray(reference)
            center = (1 * 3 + 1) * 3
            right = (1 * 3 + 2) * 3
            reference[right : right + 3] = bytes((64, 64, 64))
            actual[center : center + 3] = bytes((64, 64, 64))
            reference_path = root / "reference.ppm"
            actual_path = root / "actual.ppm"
            write_ppm(reference_path, 3, 3, reference)
            write_ppm(actual_path, 3, 3, actual)

            report = frame_delta_report.classify_frame(
                reference_path, actual_path, threshold=8
            )
            self.assertEqual(report["above_threshold_pixels"], 2)
            self.assertEqual(report["edge_adjacent_pixels"], 2)
            self.assertEqual(report["interior_pixels"], 0)
            self.assertEqual(report["neighbor_resolved_pixels"], 2)
            self.assertEqual(report["max_channel_delta"], 64)

    def test_classifies_interior_difference(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reference = bytes(3 * 3 * 3)
            actual = bytearray(reference)
            center = (1 * 3 + 1) * 3
            actual[center : center + 3] = bytes((32, 16, 0))
            reference_path = root / "reference.ppm"
            actual_path = root / "actual.ppm"
            write_ppm(reference_path, 3, 3, reference)
            write_ppm(actual_path, 3, 3, actual)

            report = frame_delta_report.classify_frame(
                reference_path, actual_path, threshold=8
            )
            self.assertEqual(report["edge_adjacent_pixels"], 0)
            self.assertEqual(report["interior_pixels"], 1)
            self.assertEqual(report["neighbor_resolved_pixels"], 0)


if __name__ == "__main__":
    unittest.main()
