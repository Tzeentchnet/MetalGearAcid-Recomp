#!/usr/bin/env python3
"""Verify a Metal Gear Acid ISO and extract local build inputs."""

import argparse
import hashlib
import os
from pathlib import Path
import sys
import tomllib

from iso9660 import Iso, sha1_file

ROOT = Path(__file__).resolve().parents[2]


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iso", type=Path)
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "build" / "mga" / "disc",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "config" / "mga.toml",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="extract an unrecognized disc while reporting hash mismatches",
    )
    return parser.parse_args(argv[1:])


def write_entry(iso, iso_path, output_root):
    data = iso.read(iso_path)
    destination = output_root.joinpath(*iso_path.split("/"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return data, destination


def main(argv):
    args = parse_args(argv)
    with args.config.open("rb") as stream:
        config = tomllib.load(stream)

    expected_size = config["disc"]["iso_size"]
    actual_size = args.iso.stat().st_size
    failures = []
    if actual_size != expected_size:
        failures.append(
            f"ISO size {actual_size} != expected {expected_size}"
        )
    else:
        print(f"hashing {args.iso} ({actual_size:,} bytes)...")
        actual_sha1 = sha1_file(args.iso)
        if actual_sha1 != config["disc"]["iso_sha1"]:
            failures.append(
                f"ISO SHA-1 {actual_sha1} != expected "
                f"{config['disc']['iso_sha1']}"
            )
        else:
            print(f"ISO SHA-1 ok ({actual_sha1})")

    if failures and not args.no_verify:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        print(
            "This project currently supports only ULUS-10006 v1.00. "
            "Use --no-verify only for analysis.",
            file=sys.stderr,
        )
        return 1

    args.out.mkdir(parents=True, exist_ok=True)
    extracted = set()
    with Iso(args.iso) as iso:
        for iso_path, expected_sha1 in config["disc"]["files"].items():
            data, destination = write_entry(iso, iso_path, args.out)
            actual_sha1 = hashlib.sha1(data).hexdigest()
            status = "ok" if actual_sha1 == expected_sha1 else "MISMATCH"
            if actual_sha1 != expected_sha1:
                failures.append(
                    f"{iso_path}: {actual_sha1} != {expected_sha1}"
                )
            extracted.add(iso_path.upper())
            print(
                f"  {iso_path:<52} {len(data):>10,} "
                f"{actual_sha1} {status}"
            )

        roots = tuple(
            root.upper().rstrip("/") + "/"
            for root in config["disc"]["plaintext_module_roots"]
        )
        plaintext_count = 0
        encrypted_count = 0
        for entry in sorted(iso.files(), key=lambda item: item.path):
            iso_path = entry.path.lstrip("/")
            upper_path = iso_path.upper()
            if (
                not upper_path.endswith(".PRX")
                or not upper_path.startswith(roots)
                or upper_path in extracted
            ):
                continue
            if iso.read(entry, 0, 4) != b"\x7fELF":
                encrypted_count += 1
                continue
            data, _ = write_entry(iso, iso_path, args.out)
            plaintext_count += 1
            print(f"  {iso_path:<52} {len(data):>10,} plaintext")

    if failures and not args.no_verify:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        return 1
    print(
        f"wrote {args.out} "
        f"({plaintext_count} additional plaintext PRXs, "
        f"{encrypted_count} encrypted PRXs skipped)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
