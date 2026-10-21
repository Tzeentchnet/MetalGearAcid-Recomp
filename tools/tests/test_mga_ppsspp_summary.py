import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools" / "mga" / "ppsspp_summary.py"
SPEC = importlib.util.spec_from_file_location(
    "mga_ppsspp_summary", MODULE_PATH
)
summary = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(summary)


class PpssppSummaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write_log(self):
        path = self.root / "ppsspp.log"
        path.write_text(
            "\n".join(
                [
                    "D 24027=sceDisplayGetAccumulatedHcount()",
                    "D 0=sceDisplaySetFrameBuf(0,0,0,0)",
                    "D Block: 09b43c00 - 09b53100 size 0000f500 "
                    "taken=1 tag=ELF/mgp_stage",
                    "I Module mgp_stage: 09b5af20 09b51714 09b5172c",
                    "I sceKernelStartModule(00000174, 00000004, "
                    "09fffdc0, 00000000, 00000000): 'mgp_stage'",
                    "D 2=sceCtrlReadBufferPositive(09fffd90, 8)",
                    "D 47765=sceDisplayGetAccumulatedHcount()",
                    "D 0=sceDisplaySetFrameBuf(0,0,0,0)",
                    "D Block: 09b43c00 - 09b5fd00 size 0001c100 "
                    "taken=1 tag=ELF/mgp_stage",
                    "I Module mgp_stage: 09b67b20 09b5cc94 09b5ccac",
                    "I sceKernelStartModule(0000017c, 00000004, "
                    "09fffdc0, 00000000, 00000000): 'mgp_stage'",
                    "D 256=sceAudioOutputBlocking(7, 0, 0)",
                    "W ERRNO_FILE_NOT_FOUND=sceIoGetstat("
                    "ms0:PSP/SAVEDATA/ULUS10006000, 0): FILE NOT FOUND",
                    "E Missing filesystem for 'lang/.ini'",
                ]
            )
            + "\n",
            encoding="ascii",
        )
        return path

    def test_summarizes_stage_and_hle_checkpoints(self):
        document = summary.build_summary(
            self.write_log(), timeout=20, padscript="mga_boot.pad"
        )

        self.assertEqual(document["timeout_seconds"], 20)
        self.assertEqual(document["padscript"], "mga_boot.pad")
        self.assertEqual(
            [stage["name"] for stage in document["stage_checkpoints"]],
            ["init", "title"],
        )
        self.assertEqual(
            document["stage_checkpoints"][0]["vblank"], 84
        )
        self.assertEqual(
            document["stage_checkpoints"][1]["presents"], 2
        )
        self.assertEqual(document["controller_reads"], 1)
        self.assertEqual(
            document["selected_hle_calls"]["sceAudioOutputBlocking"], 1
        )
        self.assertEqual(
            document["diagnostics"]["expected_missing_savedata_slots"], 1
        )
        self.assertEqual(
            document["diagnostics"]["host_language_asset_errors"], 1
        )
        self.assertEqual(document["diagnostics"]["other_errors"], 0)

    def test_summarizes_call_edges(self):
        calls = self.root / "calls.txt"
        calls.write_text(
            "# psp-recomp call trace v1\n"
            "0x08804000 jal 0x08804100\n"
            "0x08804010 jalr 0x08804200\n",
            encoding="ascii",
        )

        result = summary.summarize_calls(calls)

        self.assertEqual(result["edges"], 2)
        self.assertEqual(result["targets"], 2)
        self.assertEqual(result["kinds"], {"jal": 1, "jalr": 1})

    def test_rejects_stage_without_allocation(self):
        path = self.root / "bad.log"
        path.write_text(
            "I Module mgp_stage: 09b5af20 09b51714 09b5172c\n",
            encoding="ascii",
        )
        with self.assertRaisesRegex(
            summary.SummaryError, "stage has no allocation"
        ):
            summary.summarize_log(path)


if __name__ == "__main__":
    unittest.main()
