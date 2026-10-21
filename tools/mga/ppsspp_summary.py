#!/usr/bin/env python3
"""Reduce a protected PPSSPP log/call trace to non-game checkpoint metadata."""

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

SCHEMA = "mga-ppsspp-reference-v1"
HCOUNT_PER_VBLANK = 286
STAGE_NAMES_BY_ALLOCATION = {
    0xF500: "init",
    0x1C100: "title",
}
SELECTED_HLE = (
    "sceMpegRingbufferPut",
    "sceMpegGetAvcAu",
    "sceMpegAvcDecode",
    "sceMpegAtracDecode",
    "sceAudioOutputBlocking",
    "sceAudioOutputPannedBlocking",
)


class SummaryError(ValueError):
    pass


def summarize_calls(path):
    kinds = Counter()
    targets = set()
    edges = 0
    with Path(path).open("r", encoding="ascii") as stream:
        for line_number, raw_line in enumerate(stream, 1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            fields = line.split()
            if (
                len(fields) != 3
                or fields[1] not in ("jal", "jalr")
                or not fields[0].startswith("0x")
                or not fields[2].startswith("0x")
            ):
                raise SummaryError(
                    f"{path}:{line_number}: malformed call edge"
                )
            try:
                int(fields[0], 16)
                int(fields[2], 16)
            except ValueError as error:
                raise SummaryError(
                    f"{path}:{line_number}: malformed call address"
                ) from error
            edges += 1
            kinds[fields[1]] += 1
            targets.add(fields[2].lower())
    return {
        "edges": edges,
        "targets": len(targets),
        "kinds": dict(sorted(kinds.items())),
    }


def summarize_log(path):
    hcount = None
    presents = 0
    controller_reads = 0
    hle_counts = Counter()
    warning_count = 0
    error_count = 0
    missing_savedata_slots = 0
    io_assign_warnings = 0
    missing_host_language = 0
    last_stage_block = None
    pending_stage = None
    stages = []

    block_pattern = re.compile(
        r"Block: ([0-9a-fA-F]{8}) - ([0-9a-fA-F]{8})"
        r".*tag=ELF/mgp_stage"
    )
    module_pattern = re.compile(
        r"I Module mgp_stage: ([0-9a-fA-F]{8})"
    )
    start_pattern = re.compile(
        r"I sceKernelStartModule\(([0-9a-fA-F]{8}), .*"
        r"\): 'mgp_stage'"
    )
    hle_pattern = re.compile(
        r"^[DIW] (?:[0-9a-fA-F]+|[-0-9]+)="
        r"([A-Za-z_][A-Za-z0-9_]+)\("
    )

    with Path(path).open("r", encoding="utf-8", errors="replace") as stream:
        for line_number, line in enumerate(stream, 1):
            if line.startswith("W "):
                warning_count += 1
                if (
                    "ERRNO_FILE_NOT_FOUND=sceIoGetstat("
                    "ms0:PSP/SAVEDATA/ULUS10006" in line
                ):
                    missing_savedata_slots += 1
                elif "sceIoAssign(disc0:, umd0:, isofs:" in line:
                    io_assign_warnings += 1
            elif line.startswith("E "):
                error_count += 1
                if "Missing filesystem for 'lang/.ini'" in line:
                    missing_host_language += 1

            match = re.match(
                r"^[DI] (\d+)=sceDisplayGetAccumulatedHcount", line
            )
            if match:
                hcount = int(match.group(1), 10)

            call = hle_pattern.match(line)
            if call:
                name = call.group(1)
                hle_counts[name] += 1
                if name == "sceDisplaySetFrameBuf":
                    presents += 1
                elif name == "sceCtrlReadBufferPositive":
                    controller_reads += 1

            match = block_pattern.search(line)
            if match:
                start = int(match.group(1), 16)
                end = int(match.group(2), 16)
                last_stage_block = (start, end)

            match = module_pattern.search(line)
            if match:
                if last_stage_block is None:
                    raise SummaryError(
                        f"{path}:{line_number}: stage has no allocation"
                    )
                start, end = last_stage_block
                allocation = end - start
                pending_stage = {
                    "name": STAGE_NAMES_BY_ALLOCATION.get(
                        allocation, "unknown"
                    ),
                    "base": f"0x{start:08x}",
                    "allocation": f"0x{allocation:x}",
                    "gp": f"0x{int(match.group(1), 16):08x}",
                    "hcount": hcount,
                    "vblank": (
                        None
                        if hcount is None
                        else hcount // HCOUNT_PER_VBLANK
                    ),
                    "presents": presents,
                }

            match = start_pattern.search(line)
            if match and pending_stage is not None:
                pending_stage["uid"] = (
                    f"0x{int(match.group(1), 16):x}"
                )
                stages.append(pending_stage)
                pending_stage = None

    if pending_stage is not None:
        raise SummaryError(f"{path}: stage module never started")
    return {
        "stage_checkpoints": stages,
        "controller_reads": controller_reads,
        "hle_calls": sum(hle_counts.values()),
        "unique_hle_calls": len(hle_counts),
        "selected_hle_calls": {
            name: hle_counts[name] for name in SELECTED_HLE
        },
        "top_hle_calls": [
            {"name": name, "count": count}
            for name, count in sorted(
                hle_counts.items(), key=lambda item: (-item[1], item[0])
            )[:20]
        ],
        "warnings": warning_count,
        "errors": error_count,
        "diagnostics": {
            "expected_missing_savedata_slots": missing_savedata_slots,
            "expected_io_assign_warnings": io_assign_warnings,
            "host_language_asset_errors": missing_host_language,
            "other_warnings": (
                warning_count
                - missing_savedata_slots
                - io_assign_warnings
            ),
            "other_errors": error_count - missing_host_language,
        },
    }


def build_summary(log, calls=None, timeout=None, padscript=None):
    document = {
        "schema": SCHEMA,
        "source_log": Path(log).name,
        "timeout_seconds": timeout,
        "padscript": None if padscript is None else Path(padscript).name,
    }
    document.update(summarize_log(log))
    if calls is not None:
        document["call_trace"] = summarize_calls(calls)
    return document


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--calls", type=Path)
    parser.add_argument("--timeout", type=int)
    parser.add_argument("--padscript", type=Path)
    parser.add_argument("--out", type=Path)
    return parser.parse_args(argv)


def main(argv):
    args = parse_args(argv[1:])
    try:
        document = build_summary(
            args.log, args.calls, args.timeout, args.padscript
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
