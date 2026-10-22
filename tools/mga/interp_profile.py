#!/usr/bin/env python3
"""Aggregate and rank psp-recomp interpreter profile logs."""

import argparse
import json
from pathlib import Path
import sys


SCHEMA = "# psp-recomp interpreter profile v1"
COLUMNS = (
    "module",
    "target",
    "calls",
    "instructions",
    "syscalls",
    "native_handoffs",
    "step_limits",
    "returns",
    "failures",
)
COUNTERS = COLUMNS[2:]


class ProfileError(ValueError):
    pass


def load_profile(path):
    path = Path(path)
    with path.open("r", encoding="ascii") as stream:
        if stream.readline().rstrip("\r\n") != SCHEMA:
            raise ProfileError(f"{path}: unsupported interpreter profile")
        if tuple(stream.readline().rstrip("\r\n").split("\t")) != COLUMNS:
            raise ProfileError(f"{path}: invalid interpreter profile columns")
        entries = {}
        for line_number, raw_line in enumerate(stream, 3):
            fields = raw_line.rstrip("\r\n").split("\t")
            if len(fields) != len(COLUMNS):
                raise ProfileError(
                    f"{path}:{line_number}: malformed profile row"
                )
            module, target_text = fields[:2]
            try:
                target = int(target_text, 16)
                values = [int(value) for value in fields[2:]]
            except ValueError as error:
                raise ProfileError(
                    f"{path}:{line_number}: invalid profile value"
                ) from error
            key = (module, target)
            if (
                not module
                or not target_text.startswith("0x")
                or target < 0
                or target > 0xFFFFFFFF
                or any(value < 0 for value in values)
                or key in entries
            ):
                raise ProfileError(
                    f"{path}:{line_number}: invalid or duplicate target"
                )
            entries[key] = dict(zip(COUNTERS, values))
    return entries


def build_report(paths, top=25):
    aggregate = {}
    for path in paths:
        for key, counters in load_profile(path).items():
            target = aggregate.setdefault(
                key, {counter: 0 for counter in COUNTERS}
            )
            for counter, value in counters.items():
                target[counter] += value
    totals = {
        counter: sum(entry[counter] for entry in aggregate.values())
        for counter in COUNTERS
    }
    ranked = sorted(
        aggregate.items(),
        key=lambda item: (
            -item[1]["instructions"],
            -item[1]["calls"],
            item[0][0],
            item[0][1],
        ),
    )
    entries = []
    for (module, address), counters in ranked[:top]:
        entry = {
            "module": module,
            "target": f"0x{address:08x}",
            **counters,
            "instruction_percent": (
                counters["instructions"] * 100.0 /
                totals["instructions"]
                if totals["instructions"] else 0.0
            ),
            "call_percent": (
                counters["calls"] * 100.0 / totals["calls"]
                if totals["calls"] else 0.0
            ),
        }
        entries.append(entry)
    return {
        "schema": "mga-interpreter-profile-report-v1",
        "files": [str(Path(path)) for path in paths],
        "unique_targets": len(aggregate),
        "totals": totals,
        "top": entries,
    }


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profiles", nargs="+", type=Path)
    parser.add_argument("--top", type=int, default=25)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv[1:])
    if args.top <= 0:
        parser.error("--top must be positive")
    return args


def main(argv):
    args = parse_args(argv)
    try:
        report = build_report(args.profiles, args.top)
    except (OSError, ProfileError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out is None:
        sys.stdout.write(text)
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="ascii")
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
