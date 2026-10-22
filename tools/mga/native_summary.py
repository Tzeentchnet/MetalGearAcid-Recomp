#!/usr/bin/env python3
"""Reduce a protected native run to non-game front-end checkpoint metadata."""

import argparse
import json
from pathlib import Path
import re
import sys

SCHEMA = "mga-native-reference-v1"
STAGE_NAMES_BY_ALLOCATION = {
    0xF500: "init",
    0x1C100: "title",
    0x1C600: "new_game_intro",
    0x19200: "st00",
}


class SummaryError(ValueError):
    pass


def count_dispatch_misses(path):
    if path is None or not Path(path).exists():
        return 0
    targets = set()
    with Path(path).open("r", encoding="ascii") as stream:
        for line_number, raw_line in enumerate(stream, 1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            fields = line.split()
            if len(fields) == 1:
                module = "unknown"
                address_text = fields[0]
            elif len(fields) == 2:
                module, address_text = fields
            else:
                raise SummaryError(
                    f"{path}:{line_number}: invalid dispatch target"
                )
            if (
                len(address_text) != 10
                or not address_text.startswith("0x")
                or any(
                    character not in "0123456789abcdefABCDEF"
                    for character in address_text[2:]
                )
            ):
                raise SummaryError(
                    f"{path}:{line_number}: invalid dispatch address"
                )
            target = (module, int(address_text, 16))
            if target in targets:
                raise SummaryError(
                    f"{path}:{line_number}: duplicate dispatch target"
                )
            targets.add(target)
    return len(targets)


def build_summary(log, misses=None, present_limit=None, padscript=None):
    stage_pattern = re.compile(
        r"module loader: mgp_stage uid=0x([0-9a-fA-F]+) "
        r"base=([0-9a-fA-F]{8}) size=([0-9a-fA-F]+) "
        r"entry=([0-9a-fA-F]{8}) gp=([0-9a-fA-F]{8})"
    )
    limit_pattern = re.compile(
        r"presentation limit reached at present (\d+)"
    )
    pad_pattern = re.compile(
        r"PADSCRIPT clock=(present|vblank) frame=(\d+) "
        r"present=(\d+) vblank=(\d+) mask=0x([0-9a-fA-F]+)"
    )
    audio_init_pattern = re.compile(
        r"audio: (\S+) ([0-9.]+) kHz (mono|stereo), "
        r"(\d+) x (\d+)-frame buffers \(([0-9.]+) ms\)"
    )
    audio_shutdown_pattern = re.compile(
        r"audio: \S+ shutdown played=(\d+) frames \(([0-9.]+) ms\), "
        r"clock_drift=([-0-9.]+) ms, device_buffers=(\d+)\.\.(\d+), "
        r"max_guest_queue=(\d+), dropped=(\d+), resynced=(\d+), "
        r"silent_blocks=(\d+), underruns=(\d+)"
    )
    stages = []
    pad_events = []
    audio = None
    reached_present = None
    unimplemented_hle = 0
    host_crashes = 0
    watchdogs = 0
    interpreter_stops = 0
    permissive_fallbacks = 0
    with Path(log).open("r", encoding="utf-8", errors="replace") as stream:
        for line in stream:
            match = stage_pattern.search(line)
            if match:
                allocation = int(match.group(3), 16)
                stages.append(
                    {
                        "name": STAGE_NAMES_BY_ALLOCATION.get(
                            allocation, "unknown"
                        ),
                        "uid": f"0x{int(match.group(1), 16):x}",
                        "base": f"0x{int(match.group(2), 16):08x}",
                        "allocation": f"0x{allocation:x}",
                        "entry": f"0x{int(match.group(4), 16):08x}",
                        "gp": f"0x{int(match.group(5), 16):08x}",
                    }
                )
            match = limit_pattern.search(line)
            if match:
                reached_present = int(match.group(1), 10)
            match = pad_pattern.search(line)
            if match:
                pad_events.append(
                    {
                        "clock": match.group(1),
                        "frame": int(match.group(2), 10),
                        "present": int(match.group(3), 10),
                        "vblank": int(match.group(4), 10),
                        "mask": f"0x{int(match.group(5), 16):04x}",
                    }
                )
            match = audio_init_pattern.search(line)
            if match:
                audio = {
                    "backend": match.group(1),
                    "sample_rate_hz": int(float(match.group(2)) * 1000),
                    "channels": 1 if match.group(3) == "mono" else 2,
                    "buffer_count": int(match.group(4), 10),
                    "buffer_frames": int(match.group(5), 10),
                    "latency_ms": float(match.group(6)),
                }
            match = audio_shutdown_pattern.search(line)
            if match:
                if audio is None:
                    audio = {}
                audio["shutdown"] = {
                    "played_frames": int(match.group(1), 10),
                    "played_ms": float(match.group(2)),
                    "clock_drift_ms": float(match.group(3)),
                    "device_buffers_min": int(match.group(4), 10),
                    "device_buffers_max": int(match.group(5), 10),
                    "max_guest_queue": int(match.group(6), 10),
                    "dropped": int(match.group(7), 10),
                    "resynced": int(match.group(8), 10),
                    "silent_blocks": int(match.group(9), 10),
                    "underruns": int(match.group(10), 10),
                }
            unimplemented_hle += "HLE: unimplemented" in line
            host_crashes += "HOST CRASH" in line
            watchdogs += "WATCHDOG:" in line
            interpreter_stops += "dispatch: interpreter stopped" in line
            permissive_fallbacks += (
                "dispatch: permissive no-op return" in line
            )
    if present_limit is not None and reached_present != present_limit:
        raise SummaryError(
            f"{log}: reached present {reached_present}, "
            f"expected {present_limit}"
        )
    return {
        "schema": SCHEMA,
        "source_log": Path(log).name,
        "padscript": None if padscript is None else Path(padscript).name,
        "present_limit": present_limit,
        "reached_present": reached_present,
        "stage_checkpoints": stages,
        "pad_events": pad_events,
        "audio": audio,
        "dispatch_misses": count_dispatch_misses(misses),
        "failures": {
            "unimplemented_hle": unimplemented_hle,
            "host_crashes": host_crashes,
            "watchdogs": watchdogs,
            "interpreter_stops": interpreter_stops,
            "permissive_fallbacks": permissive_fallbacks,
        },
    }


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--misses", type=Path)
    parser.add_argument("--present-limit", type=int)
    parser.add_argument("--padscript", type=Path)
    parser.add_argument("--out", type=Path)
    return parser.parse_args(argv)


def main(argv):
    args = parse_args(argv[1:])
    try:
        document = build_summary(
            args.log, args.misses, args.present_limit, args.padscript
        )
    except (OSError, SummaryError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    text = json.dumps(document, indent=2, sort_keys=True) + "\n"
    if args.out is None:
        sys.stdout.write(text)
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="ascii")
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
