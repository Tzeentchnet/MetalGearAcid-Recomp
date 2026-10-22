import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools" / "mga" / "scaling_capture.py"
SPEC = importlib.util.spec_from_file_location(
    "mga_scaling_capture", MODULE_PATH
)
scaling_capture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scaling_capture)


class ScalingCaptureTests(unittest.TestCase):
    def test_reports_offset_bias_and_block_variation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reference = bytes(
                scaling_capture.PSP_WIDTH
                * scaling_capture.PSP_HEIGHT
                * 3
            )
            width = scaling_capture.PSP_WIDTH * 2
            height = scaling_capture.PSP_HEIGHT * 2
            capture = bytearray(width * height * 3)
            capture[(width + 1) * 3] = 20
            reference_path = root / "reference.ppm"
            capture_path = root / "capture.ppm"
            scaling_capture.write_ppm(
                reference_path,
                scaling_capture.PSP_WIDTH,
                scaling_capture.PSP_HEIGHT,
                reference,
            )
            scaling_capture.write_ppm(
                capture_path, width, height, capture
            )
            report = scaling_capture.analyze_capture(
                capture_path, reference_path
            )
            self.assertEqual(report["scale"], 2)
            self.assertEqual(
                report["block_variation"]["varying_logical_pixels"], 1
            )
            self.assertEqual(
                report["block_variation"][
                    "max_intra_pixel_channel_range"
                ],
                20,
            )
            self.assertEqual(
                report["samples"][0]["different_pixels"], 0
            )
            self.assertEqual(
                report["samples"][1]["different_pixels"], 1
            )
            self.assertEqual(
                report["box_average"]["different_pixels"], 1
            )
            self.assertEqual(
                report["box_average"]["max_channel_delta"], 5
            )

    def test_rejects_non_integer_scale(self):
        with self.assertRaisesRegex(
            scaling_capture.CaptureError, "integer-scaled"
        ):
            scaling_capture.capture_scale(481, 272)


if __name__ == "__main__":
    unittest.main()
