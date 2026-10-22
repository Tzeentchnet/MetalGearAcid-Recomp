#!/usr/bin/env python3
"""Summarize structured psp-recomp presentation performance samples."""

import argparse
import csv
import json
import math
from pathlib import Path
import statistics
import sys


SCHEMA = "# psp-recomp present performance v1"
COLUMNS = (
    "present",
    "frame_ms",
    "frontend_ms",
    "backend_ms",
    "gpu_ms",
    "over_budget",
)


class PerformanceError(ValueError):
    pass


def percentile(values, percent):
    if not values:
        raise PerformanceError("cannot calculate a percentile without samples")
    ordered = sorted(values)
    index = (len(ordered) * percent + 99) // 100 - 1
    return ordered[index]


def load_samples(path):
    path = Path(path)
    with path.open("r", encoding="ascii", newline="") as stream:
        if stream.readline().rstrip("\r\n") != SCHEMA:
            raise PerformanceError(f"{path}: unsupported performance schema")
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise PerformanceError(
                f"{path}: expected columns {','.join(COLUMNS)}"
            )
        samples = []
        previous_present = 0
        for line_number, row in enumerate(reader, 3):
            try:
                present = int(row["present"])
                frame_ms = float(row["frame_ms"])
                frontend_ms = float(row["frontend_ms"])
                backend_ms = float(row["backend_ms"])
                gpu_ms = float(row["gpu_ms"])
                over_budget = int(row["over_budget"])
            except (TypeError, ValueError) as error:
                raise PerformanceError(
                    f"{path}:{line_number}: invalid sample"
                ) from error
            timings = (frame_ms, frontend_ms, backend_ms, gpu_ms)
            if (
                present <= previous_present
                or not all(math.isfinite(value) for value in timings)
                or frame_ms <= 0.0
                or frontend_ms < 0.0
                or backend_ms < 0.0
                or gpu_ms < -1.0
                or over_budget not in (0, 1)
            ):
                raise PerformanceError(
                    f"{path}:{line_number}: out-of-range sample"
                )
            previous_present = present
            samples.append(
                {
                    "present": present,
                    "frame_ms": frame_ms,
                    "frontend_ms": frontend_ms,
                    "backend_ms": backend_ms,
                    "gpu_ms": gpu_ms,
                    "over_budget": over_budget,
                }
            )
    if not samples:
        raise PerformanceError(f"{path}: no performance samples")
    return samples


def summarize_run(path, samples):
    frames = [sample["frame_ms"] for sample in samples]
    frontend = [sample["frontend_ms"] for sample in samples]
    backend = [sample["backend_ms"] for sample in samples]
    gpu = [
        sample["gpu_ms"] for sample in samples
        if sample["gpu_ms"] >= 0.0
    ]
    average = statistics.fmean(frames)
    return {
        "file": str(Path(path)),
        "samples": len(samples),
        "present_first": samples[0]["present"],
        "present_last": samples[-1]["present"],
        "fps": 1000.0 / average,
        "frame_ms": {
            "average": average,
            "p50": percentile(frames, 50),
            "p95": percentile(frames, 95),
            "p99": percentile(frames, 99),
            "maximum": max(frames),
            "over_budget": sum(
                sample["over_budget"] for sample in samples
            ),
        },
        "frontend_ms": {
            "average": statistics.fmean(frontend),
            "maximum": max(frontend),
        },
        "backend_ms": {
            "average": statistics.fmean(backend),
            "maximum": max(backend),
        },
        "gpu_ms": {
            "samples": len(gpu),
            "average": statistics.fmean(gpu) if gpu else None,
            "p95": percentile(gpu, 95) if gpu else None,
            "maximum": max(gpu) if gpu else None,
        },
    }


def build_report(paths):
    runs = [
        summarize_run(path, load_samples(path))
        for path in paths
    ]
    fps = [run["fps"] for run in runs]
    median_fps = statistics.median(fps)
    spread = max(fps) - min(fps)
    return {
        "schema": "mga-performance-report-v1",
        "runs": runs,
        "aggregate": {
            "run_count": len(runs),
            "median_fps": median_fps,
            "minimum_fps": min(fps),
            "maximum_fps": max(fps),
            "fps_spread_percent": (
                spread * 100.0 / median_fps
                if median_fps > 0.0 else None
            ),
            "median_frame_ms": statistics.median(
                run["frame_ms"]["average"] for run in runs
            ),
            "median_p95_ms": statistics.median(
                run["frame_ms"]["p95"] for run in runs
            ),
            "median_p99_ms": statistics.median(
                run["frame_ms"]["p99"] for run in runs
            ),
        },
    }


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("samples", nargs="+", type=Path)
    parser.add_argument("--out", type=Path)
    return parser.parse_args(argv[1:])


def main(argv):
    args = parse_args(argv)
    try:
        report = build_report(args.samples)
    except (OSError, PerformanceError) as error:
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
