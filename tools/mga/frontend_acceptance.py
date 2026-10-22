#!/usr/bin/env python3
"""Validate the deterministic native title-menu route."""

import argparse
import json
from pathlib import Path
import sys

import fallback_report
import native_summary

CAPTURE_PRESENTS = (3000, 3120, 3240, 3360)


class AcceptanceError(ValueError):
    pass


def read_ppm(path):
    path = Path(path)
    with path.open("rb") as stream:
        def token():
            value = bytearray()
            while True:
                byte = stream.read(1)
                if not byte:
                    raise AcceptanceError(f"{path}: truncated PPM header")
                if byte == b"#":
                    stream.readline()
                    continue
                if not byte.isspace():
                    value.extend(byte)
                    break
            while True:
                byte = stream.read(1)
                if not byte or byte.isspace():
                    break
                value.extend(byte)
            return bytes(value)

        magic = token()
        if magic != b"P6":
            raise AcceptanceError(f"{path}: expected binary P6 PPM")
        try:
            width = int(token())
            height = int(token())
            maximum = int(token())
        except ValueError as error:
            raise AcceptanceError(f"{path}: invalid PPM header") from error
        if width != 480 or height != 272 or maximum != 255:
            raise AcceptanceError(
                f"{path}: expected 480x272 max 255, got "
                f"{width}x{height} max {maximum}"
            )
        pixels = stream.read()
    expected = width * height * 3
    if len(pixels) != expected:
        raise AcceptanceError(
            f"{path}: expected {expected} pixel bytes, got {len(pixels)}"
        )
    return width, height, pixels


def bright_pixels(pixels, x0, y0, x1, y1, width=480):
    count = 0
    for y in range(y0, y1):
        for x in range(x0, x1):
            offset = (y * width + x) * 3
            if min(pixels[offset : offset + 3]) >= 180:
                count += 1
    return count


def frame_summary(path):
    width, height, pixels = read_ppm(path)
    colors = set()
    nonblack = 0
    bright = 0
    for offset in range(0, len(pixels), 3):
        color = bytes(pixels[offset : offset + 3])
        colors.add(color)
        if max(color) > 8:
            nonblack += 1
        if min(color) >= 180:
            bright += 1
    return {
        "file": Path(path).name,
        "width": width,
        "height": height,
        "nonblack_pixels": nonblack,
        "bright_pixels": bright,
        "unique_colors": len(colors),
        "selector_new": bright_pixels(pixels, 0, 186, 22, 196),
        "selector_load": bright_pixels(pixels, 0, 196, 22, 206),
    }


def require(condition, message):
    if not condition:
        raise AcceptanceError(message)


def validate(
    log, misses, frames_dir, present_limit, expected_dispatch_misses,
    allowlist=None, config_path=Path("config/mga.toml"),
):
    summary = native_summary.build_summary(
        log,
        misses=misses,
        present_limit=present_limit,
        padscript="mga_menu_probe.pad",
    )
    require(
        all(value == 0 for value in summary["failures"].values()),
        f"{log}: failure markers are {summary['failures']}",
    )
    if expected_dispatch_misses is not None:
        require(
            summary["dispatch_misses"] == expected_dispatch_misses,
            f"{log}: expected {expected_dispatch_misses} dispatch misses, "
            f"got {summary['dispatch_misses']}",
        )
    fallback_check = None
    if allowlist is not None:
        fallback_check = fallback_report.validate_allowlist(
            fallback_report.load_targets(misses), allowlist, exact=True,
            config_path=config_path,
        )
    stage_names = [
        stage["name"] for stage in summary["stage_checkpoints"]
    ]
    require(
        stage_names[:3] == ["init", "title", "new_game_intro"],
        f"{log}: unexpected stage route {stage_names}",
    )
    input_masks = [
        int(event["mask"], 16)
        for event in summary["pad_events"]
        if event["present"] >= 2700 and int(event["mask"], 16) != 0
    ]
    require(
        input_masks == [0x0008, 0x0040, 0x0010, 0x2000],
        f"{log}: unexpected menu input sequence "
        f"{[f'0x{mask:04x}' for mask in input_masks]}",
    )

    audio = summary["audio"]
    require(audio is not None, f"{log}: XAudio2 did not initialize")
    require(audio.get("backend") == "XAudio2", f"{log}: wrong audio backend")
    require(
        audio.get("sample_rate_hz") == 44100 and audio.get("channels") == 2,
        f"{log}: expected 44.1 kHz stereo audio, got {audio}",
    )
    shutdown = audio.get("shutdown")
    require(shutdown is not None, f"{log}: audio did not shut down cleanly")
    require(
        shutdown["played_frames"] >= 44100,
        f"{log}: fewer than one second of audio was played",
    )
    require(
        shutdown["device_buffers_max"] > 0,
        f"{log}: no device buffer was observed",
    )
    require(
        shutdown["dropped"] == 0,
        f"{log}: audio dropped {shutdown['dropped']} blocks",
    )
    require(
        shutdown["underruns"] == 0,
        f"{log}: audio had {shutdown['underruns']} device underruns",
    )

    frames = {
        present: frame_summary(
            Path(frames_dir) / f"capture_present_{present}.ppm"
        )
        for present in CAPTURE_PRESENTS
    }
    for present in (3000, 3120, 3240):
        frame = frames[present]
        require(
            frame["nonblack_pixels"] >= 120000
            and frame["bright_pixels"] >= 20000
            and frame["unique_colors"] >= 500,
            f"presentation {present}: title frame metrics out of range "
            f"{frame}",
        )
    require(
        frames[3000]["selector_new"] >= 40
        and frames[3000]["selector_load"] <= 25,
        f"presentation 3000: NEW GAME is not selected",
    )
    require(
        frames[3120]["selector_new"] <= 25
        and frames[3120]["selector_load"] >= 40,
        f"presentation 3120: LOAD GAME is not selected",
    )
    require(
        frames[3240]["selector_new"] >= 40
        and frames[3240]["selector_load"] <= 25,
        f"presentation 3240: NEW GAME is not reselected",
    )
    transition = frames[3360]
    require(
        transition["nonblack_pixels"] >= 50000
        and transition["bright_pixels"] < 5000
        and transition["unique_colors"] < 100,
        f"presentation 3360: title transition metrics out of range "
        f"{transition}",
    )
    return {
        "schema": "mga-frontend-acceptance-v1",
        "result": "pass",
        "native": summary,
        "fallback_check": fallback_check,
        "frames": {
            str(present): frames[present] for present in CAPTURE_PRESENTS
        },
    }


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--misses", type=Path, required=True)
    parser.add_argument("--frames-dir", type=Path, required=True)
    parser.add_argument("--present-limit", type=int, default=4200)
    parser.add_argument("--expected-dispatch-misses", type=int)
    parser.add_argument("--allowlist", type=Path)
    parser.add_argument(
        "--config", type=Path, default=Path("config/mga.toml")
    )
    parser.add_argument("--out", type=Path)
    return parser.parse_args(argv[1:])


def main(argv):
    args = parse_args(argv)
    try:
        document = validate(
            args.log,
            args.misses,
            args.frames_dir,
            args.present_limit,
            args.expected_dispatch_misses,
            args.allowlist,
            args.config,
        )
    except (
        OSError,
        native_summary.SummaryError,
        fallback_report.FallbackError,
        AcceptanceError,
    ) as error:
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
