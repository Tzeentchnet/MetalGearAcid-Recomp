#!/usr/bin/env python3
"""Classify GPU frame deltas as edge-adjacent or interior differences."""

import argparse
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
PPMDIFF_PATH = ROOT / "external" / "psp-recomp" / "tools" / "ppmdiff.py"
SPEC = importlib.util.spec_from_file_location("psp_recomp_ppmdiff", PPMDIFF_PATH)
ppmdiff = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ppmdiff)


class DeltaError(ValueError):
    pass


def pixel_delta(left, left_offset, right, right_offset):
    return max(
        abs(left[left_offset + channel] - right[right_offset + channel])
        for channel in range(3)
    )


def classify_frame(reference_path, actual_path, threshold=8, radius=1):
    reference, width, height = ppmdiff.read_ppm(reference_path)
    actual, actual_width, actual_height = ppmdiff.read_ppm(actual_path)
    if (width, height) != (actual_width, actual_height):
        raise DeltaError(
            f"dimension mismatch {width}x{height} vs "
            f"{actual_width}x{actual_height}"
        )
    if radius < 1:
        raise DeltaError("edge radius must be positive")

    above_threshold = 0
    edge_adjacent = 0
    neighbor_resolved = 0
    maximum_delta = 0
    signed_delta = [0, 0, 0]

    for y in range(height):
        for x in range(width):
            offset = (y * width + x) * 3
            delta = pixel_delta(reference, offset, actual, offset)
            maximum_delta = max(maximum_delta, delta)
            if delta <= threshold:
                continue
            above_threshold += 1
            for channel in range(3):
                signed_delta[channel] += (
                    actual[offset + channel] - reference[offset + channel]
                )

            near_edge = False
            best_neighbor = 255
            for neighbor_y in range(
                max(0, y - radius), min(height, y + radius + 1)
            ):
                for neighbor_x in range(
                    max(0, x - radius), min(width, x + radius + 1)
                ):
                    neighbor = (neighbor_y * width + neighbor_x) * 3
                    best_neighbor = min(
                        best_neighbor,
                        pixel_delta(reference, neighbor, actual, offset),
                    )
                    if (
                        neighbor_x != x or neighbor_y != y
                    ) and pixel_delta(
                        reference, offset, reference, neighbor
                    ) > threshold:
                        near_edge = True
            if near_edge:
                edge_adjacent += 1
            if best_neighbor <= threshold:
                neighbor_resolved += 1

    pixels = width * height
    mean_signed = [
        value / above_threshold if above_threshold else 0.0
        for value in signed_delta
    ]
    return {
        "width": width,
        "height": height,
        "pixels": pixels,
        "threshold": threshold,
        "edge_radius": radius,
        "above_threshold_pixels": above_threshold,
        "above_threshold_percent": above_threshold * 100.0 / pixels,
        "edge_adjacent_pixels": edge_adjacent,
        "edge_adjacent_percent_of_above": (
            edge_adjacent * 100.0 / above_threshold
            if above_threshold else 0.0
        ),
        "interior_pixels": above_threshold - edge_adjacent,
        "neighbor_resolved_pixels": neighbor_resolved,
        "neighbor_resolved_percent_of_above": (
            neighbor_resolved * 100.0 / above_threshold
            if above_threshold else 0.0
        ),
        "mean_signed_rgb": mean_signed,
        "max_channel_delta": maximum_delta,
    }


def build_report(reference_dir, actual_dir, threshold=8, radius=1):
    reference_dir = Path(reference_dir)
    actual_dir = Path(actual_dir)
    reference_names = {
        path.name for path in reference_dir.glob("*.ppm") if path.is_file()
    }
    actual_names = {
        path.name for path in actual_dir.glob("*.ppm") if path.is_file()
    }
    if not reference_names or reference_names != actual_names:
        raise DeltaError(
            "reference and actual directories must contain the same PPM files"
        )
    frames = []
    for name in sorted(reference_names):
        frame = classify_frame(
            reference_dir / name,
            actual_dir / name,
            threshold,
            radius,
        )
        frame["name"] = name
        frames.append(frame)
    return {
        "schema": "mga-frame-delta-report-v1",
        "reference_dir": str(reference_dir.resolve()),
        "actual_dir": str(actual_dir.resolve()),
        "frames": frames,
    }


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference_dir", type=Path)
    parser.add_argument("actual_dir", type=Path)
    parser.add_argument("--threshold", type=int, default=8)
    parser.add_argument("--edge-radius", type=int, default=1)
    parser.add_argument("--out", type=Path)
    return parser.parse_args(argv[1:])


def main(argv):
    args = parse_args(argv)
    try:
        report = build_report(
            args.reference_dir,
            args.actual_dir,
            args.threshold,
            args.edge_radius,
        )
    except (OSError, ppmdiff.PpmError, DeltaError) as error:
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
