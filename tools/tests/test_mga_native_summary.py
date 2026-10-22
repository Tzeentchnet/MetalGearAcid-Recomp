import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools" / "mga" / "native_summary.py"
SPEC = importlib.util.spec_from_file_location(
    "mga_native_summary", MODULE_PATH
)
summary = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(summary)


class NativeSummaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write_log(self, present=600):
        path = self.root / "stderr.log"
        path.write_text(
            "module loader: mgp_stage uid=0x174 base=09b43c00 "
            "size=f500 entry=09b43c34 gp=09b5af20\n"
            "module loader: mgp_stage uid=0x17b base=09b43c00 "
            "size=1c100 entry=09b43c34 gp=09b67b20\n"
            "PADSCRIPT clock=present frame=3003 present=3003 "
            "vblank=1298 mask=0x0040\n"
            "audio: XAudio2 44.1 kHz stereo, 8 x 256-frame buffers "
            "(46.44 ms)\n"
            "audio: XAudio2 shutdown played=44100 frames (1000.00 ms), "
            "clock_drift=-2.50 ms, device_buffers=1..8, "
            "max_guest_queue=512, dropped=0, resynced=10, "
            "silent_blocks=2, underruns=3\n"
            f"presentation limit reached at present {present}\n",
            encoding="ascii",
        )
        return path

    def test_names_first_mission_overlay(self):
        self.assertEqual(
            summary.STAGE_NAMES_BY_ALLOCATION[0x19200],
            "st00",
        )

    def test_summarizes_successful_title_gate(self):
        misses = self.root / "misses.txt"
        misses.write_text(
            "# psp-recomp interpreter misses v1\n"
            "0x09b43c34\n"
            "0x09b45ac8\n",
            encoding="ascii",
        )
        document = summary.build_summary(
            self.write_log(), misses, 600, "mga_boot.pad"
        )

        self.assertEqual(document["reached_present"], 600)
        self.assertEqual(document["dispatch_misses"], 2)
        self.assertEqual(
            [stage["name"] for stage in document["stage_checkpoints"]],
            ["init", "title"],
        )
        self.assertEqual(
            document["failures"],
            {
                "unimplemented_hle": 0,
                "host_crashes": 0,
                "watchdogs": 0,
                "interpreter_stops": 0,
                "permissive_fallbacks": 0,
            },
        )
        self.assertEqual(document["pad_events"][0]["mask"], "0x0040")
        self.assertEqual(document["audio"]["backend"], "XAudio2")
        self.assertEqual(
            document["audio"]["shutdown"]["played_frames"], 44100
        )

    def test_rejects_wrong_present_limit(self):
        with self.assertRaisesRegex(
            summary.SummaryError, "expected 600"
        ):
            summary.build_summary(self.write_log(599), present_limit=600)

    def test_detects_failure_markers(self):
        path = self.root / "failed.log"
        path.write_text(
            "HLE: unimplemented nid\n"
            "HOST CRASH\n"
            "WATCHDOG: no frame\n"
            "dispatch: interpreter stopped\n"
            "dispatch: permissive no-op return after interpreter failure\n"
            "presentation limit reached at present 1\n",
            encoding="ascii",
        )
        document = summary.build_summary(path, present_limit=1)
        self.assertTrue(all(document["failures"].values()))


if __name__ == "__main__":
    unittest.main()
