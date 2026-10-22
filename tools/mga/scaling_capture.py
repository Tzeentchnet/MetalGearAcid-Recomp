#!/usr/bin/env python3
"""Analyze a full-resolution D3D12 capture by logical PSP pixel."""

import argparse
import json
from pathlib import Path
import sys


PSP_WIDTH = 480
PSP_HEIGHT = 272


class CaptureError(ValueError):
    pass


def _token(data, offset):
    while offset < len(data) and data[offset] in b" \t\r\n":
        offset += 1
    start = offset
    while offset < len(data) and data[offset] not in b" \t\r\n":
        offset += 1
    if start == offset:
        raise CaptureError("missing PPM header token")
    return data[start:offset], offset


def read_ppm(path):
    path = Path(path)
    data = path.read_bytes()
    try:
        magic, offset = _token(data, 0)
        width_text, offset = _token(data, offset)
        height_text, offset = _token(data, offset)
        maximum_text, offset = _token(data, offset)
        width = int(width_text)
        height = int(height_text)
        maximum = int(maximum_text)
    except (CaptureError, ValueError) as error:
        raise CaptureError(f"{path}: invalid PPM header") from error
    if magic != b"P6" or maximum != 255 or width <= 0 or height <= 0:
        raise CaptureError(f"{path}: unsupported PPM format")
    if offset >= len(data) or data[offset] not in b" \t\r\n":
        raise CaptureError(f"{path}: missing PPM raster separator")
    offset += 2 if data[offset : offset + 2] == b"\r\n" else 1
    pixels = data[offset:]
    if len(pixels) != width * height * 3:
        raise CaptureError(f"{path}: truncated PPM raster")
    return width, height, pixels


def write_ppm(path, width, height, pixels):
    Path(path).write_bytes(
        f"P6\n{width} {height}\n255\n".encode("ascii") + pixels
    )


def capture_scale(width, height):
    if (
        width % PSP_WIDTH
        or height % PSP_HEIGHT
        or width // PSP_WIDTH != height // PSP_HEIGHT
        or width < PSP_WIDTH
    ):
        raise CaptureError(
            f"expected an integer-scaled 480x272 capture, got "
            f"{width}x{height}"
        )
    return width // PSP_WIDTH


def downsample(width, height, pixels, offset):
    scale = capture_scale(width, height)
    if offset < 0 or offset >= scale:
        raise CaptureError(
            f"sample offset {offset} is outside scale {scale}"
        )
    output = bytearray(PSP_WIDTH * PSP_HEIGHT * 3)
    for y in range(PSP_HEIGHT):
        source_y = y * scale + offset
        for x in range(PSP_WIDTH):
            source = (source_y * width + x * scale + offset) * 3
            destination = (y * PSP_WIDTH + x) * 3
            output[destination : destination + 3] = pixels[
                source : source + 3
            ]
    return bytes(output)


def downsample_average(width, height, pixels):
    scale = capture_scale(width, height)
    samples = scale * scale
    output = bytearray(PSP_WIDTH * PSP_HEIGHT * 3)
    for y in range(PSP_HEIGHT):
        for x in range(PSP_WIDTH):
            total = [0, 0, 0]
            for sy in range(scale):
                row = ((y * scale + sy) * width + x * scale) * 3
                for sx in range(scale):
                    source = row + sx * 3
                    for channel in range(3):
                        total[channel] += pixels[source + channel]
            destination = (y * PSP_WIDTH + x) * 3
            for channel in range(3):
                output[destination + channel] = (
                    total[channel] + samples // 2
                ) // samples
    return bytes(output)


def compare(reference, actual, threshold):
    if len(reference) != len(actual):
        raise CaptureError("logical capture sizes differ")
    different = 0
    above_threshold = 0
    maximum_delta = 0
    for offset in range(0, len(reference), 3):
        delta = max(
            abs(reference[offset] - actual[offset]),
            abs(reference[offset + 1] - actual[offset + 1]),
            abs(reference[offset + 2] - actual[offset + 2]),
        )
        if delta:
            different += 1
            if delta > threshold:
                above_threshold += 1
            maximum_delta = max(maximum_delta, delta)
    pixels = len(reference) // 3
    return {
        "different_pixels": different,
        "different_percent": different * 100.0 / pixels,
        "above_threshold_pixels": above_threshold,
        "above_threshold_percent": above_threshold * 100.0 / pixels,
        "max_channel_delta": maximum_delta,
    }


def block_variation(width, height, pixels):
    scale = capture_scale(width, height)
    varying = 0
    maximum_range = 0
    for y in range(PSP_HEIGHT):
        for x in range(PSP_WIDTH):
            minimum = [255, 255, 255]
            maximum = [0, 0, 0]
            for sy in range(scale):
                row = ((y * scale + sy) * width + x * scale) * 3
                for sx in range(scale):
                    source = row + sx * 3
                    for channel in range(3):
                        value = pixels[source + channel]
                        minimum[channel] = min(minimum[channel], value)
                        maximum[channel] = max(maximum[channel], value)
            channel_range = max(
                maximum[channel] - minimum[channel]
                for channel in range(3)
            )
            if channel_range:
                varying += 1
                maximum_range = max(maximum_range, channel_range)
    logical_pixels = PSP_WIDTH * PSP_HEIGHT
    return {
        "varying_logical_pixels": varying,
        "varying_percent": varying * 100.0 / logical_pixels,
        "max_intra_pixel_channel_range": maximum_range,
    }


def analyze_capture(capture_path, reference_path=None, threshold=8):
    width, height, pixels = read_ppm(capture_path)
    scale = capture_scale(width, height)
    reference = None
    if reference_path is not None:
        reference_width, reference_height, reference = read_ppm(
            reference_path
        )
        if (reference_width, reference_height) != (
            PSP_WIDTH,
            PSP_HEIGHT,
        ):
            raise CaptureError(
                f"{reference_path}: expected a 480x272 reference"
            )
    samples = []
    for offset in range(scale):
        entry = {"offset": offset}
        if reference is not None:
            entry.update(
                compare(
                    reference,
                    downsample(width, height, pixels, offset),
                    threshold,
                )
            )
        samples.append(entry)
    box_average = None
    if reference is not None:
        box_average = compare(
            reference,
            downsample_average(width, height, pixels),
            threshold,
        )
    return {
        "schema": "mga-scaling-capture-v1",
        "file": str(Path(capture_path)),
        "width": width,
        "height": height,
        "scale": scale,
        "threshold": threshold,
        "block_variation": block_variation(width, height, pixels),
        "samples": samples,
        "box_average": box_average,
    }


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--threshold", type=int, default=8)
    parser.add_argument("--write-downsample", type=Path)
    parser.add_argument("--offset", type=int)
    parser.add_argument("--out", type=Path)
    return parser.parse_args(argv[1:])


def main(argv):
    args = parse_args(argv)
    try:
        report = analyze_capture(
            args.capture, args.reference, args.threshold
        )
        if args.write_downsample is not None:
            width, height, pixels = read_ppm(args.capture)
            offset = (
                args.offset
                if args.offset is not None
                else (report["scale"] - 1) // 2
            )
            write_ppm(
                args.write_downsample,
                PSP_WIDTH,
                PSP_HEIGHT,
                downsample(width, height, pixels, offset),
            )
    except (OSError, CaptureError) as error:
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
