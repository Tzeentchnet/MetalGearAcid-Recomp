#!/usr/bin/env python3
"""Validate shared PPSSPP/native psp-recomp v3 pad scripts."""

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

HEADER = "# psp-recomp pad script v3"
MAX_EVENTS = 256


class PadScriptError(ValueError):
    pass


@dataclass(frozen=True)
class PadEvent:
    ppsspp_vblank: int
    runtime_present: int
    mask: int
    ppsspp_width: int
    runtime_width: int


def read_padscript(path):
    path = Path(path)
    events = []
    header_seen = False
    previous_ppsspp = -1
    previous_runtime = -1
    with path.open("r", encoding="ascii") as stream:
        for line_number, raw_line in enumerate(stream, 1):
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("#"):
                if line == HEADER:
                    header_seen = True
                continue
            fields = line.split()
            if len(fields) != 5:
                raise PadScriptError(
                    f"{path}:{line_number}: expected five fields"
                )
            try:
                ppsspp_vblank = int(fields[0], 10)
                runtime_present = int(fields[1], 10)
                mask = int(fields[2], 16)
                ppsspp_width = int(fields[3], 10)
                runtime_width = int(fields[4], 10)
            except ValueError as error:
                raise PadScriptError(
                    f"{path}:{line_number}: invalid numeric field"
                ) from error
            if ppsspp_vblank <= previous_ppsspp:
                raise PadScriptError(
                    f"{path}:{line_number}: PPSSPP vblanks must increase"
                )
            if runtime_present <= previous_runtime:
                raise PadScriptError(
                    f"{path}:{line_number}: runtime presents must increase"
                )
            if ppsspp_width <= 0 or runtime_width <= 0:
                raise PadScriptError(
                    f"{path}:{line_number}: widths must be positive"
                )
            if mask < 0 or mask > 0xFFFFFFFF:
                raise PadScriptError(
                    f"{path}:{line_number}: mask is outside uint32"
                )
            events.append(
                PadEvent(
                    ppsspp_vblank,
                    runtime_present,
                    mask,
                    ppsspp_width,
                    runtime_width,
                )
            )
            if len(events) > MAX_EVENTS:
                raise PadScriptError(
                    f"{path}: more than {MAX_EVENTS} events"
                )
            previous_ppsspp = ppsspp_vblank
            previous_runtime = runtime_present
    if not header_seen:
        raise PadScriptError(f"{path}: missing '{HEADER}'")
    return events


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scripts", type=Path, nargs="+")
    return parser.parse_args(argv)


def main(argv):
    args = parse_args(argv[1:])
    for path in args.scripts:
        events = read_padscript(path)
        if events:
            first = events[0]
            last = events[-1]
            print(
                f"{path}: {len(events)} events; "
                f"PPSSPP {first.ppsspp_vblank}-{last.ppsspp_vblank}; "
                f"runtime {first.runtime_present}-{last.runtime_present}"
            )
        else:
            print(f"{path}: neutral (0 events)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
