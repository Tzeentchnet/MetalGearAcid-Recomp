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
}


class SummaryError(ValueError):
    pass


def count_dispatch_misses(path):
    if path is None or not Path(path).exists():
        return 0
    addresses = set()
    with Path(path).open("r", encoding="ascii") as stream:
        for line_number, raw_line in enumerate(stream, 1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if (
                len(line) != 10
                or not line.startswith("0x")
                or any(
                    character not in "0123456789abcdefABCDEF"
                    for character in line[2:]
                )
            ):
                raise SummaryError(
                    f"{path}:{line_number}: invalid dispatch address"
                )
            address = int(line, 16)
            if address in addresses:
                raise SummaryError(
                    f"{path}:{line_number}: duplicate dispatch address"
                )
            addresses.add(address)
    return len(addresses)


def build_summary(log, misses=None, present_limit=None, padscript=None):
    stage_pattern = re.compile(
        r"module loader: mgp_stage uid=0x([0-9a-fA-F]+) "
        r"base=([0-9a-fA-F]{8}) size=([0-9a-fA-F]+) "
        r"entry=([0-9a-fA-F]{8}) gp=([0-9a-fA-F]{8})"
    )
    limit_pattern = re.compile(
        r"presentation limit reached at present (\d+)"
    )
    stages = []
    reached_present = None
    unimplemented_hle = 0
    host_crashes = 0
    watchdogs = 0
    interpreter_stops = 0
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
            unimplemented_hle += "HLE: unimplemented" in line
            host_crashes += "HOST CRASH" in line
            watchdogs += "WATCHDOG:" in line
            interpreter_stops += "dispatch: interpreter stopped" in line
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
        "dispatch_misses": count_dispatch_misses(misses),
        "failures": {
            "unimplemented_hle": unimplemented_hle,
            "host_crashes": host_crashes,
            "watchdogs": watchdogs,
            "interpreter_stops": interpreter_stops,
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
