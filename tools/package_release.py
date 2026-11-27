#!/usr/bin/env python3
"""Package the tracked sources and pinned runtime as a Windows release zip.

The zip holds no game data or generated code: players build the game from
their own disc with "Install Metal Gear Acid.bat". recomplauncher.json sits at
the top of the zip, next to the batch files RecompLauncher starts.
"""

import argparse
from pathlib import Path
import re
import subprocess
import sys
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = Path("external/psp-recomp")
REQUIRED = (
    "recomplauncher.json",
    "Install Metal Gear Acid.bat",
    "Launch Metal Gear Acid.bat",
    "install.py",
    "external/psp-recomp/tools/codegen.py",
)
GAME_MEDIA = {".iso", ".cso", ".chd", ".pbp", ".prx", ".bin"}


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version",
        required=True,
        help="release tag, such as v0.1.0",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "dist",
        help="output directory (default: dist)",
    )
    return parser.parse_args(argv)


def git(*args):
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout


def tracked_files():
    output = git("ls-files", "-z", "--recurse-submodules")
    return sorted(path for path in output.split("\0") if path)


def check_runtime_pin():
    with (ROOT / "config" / "mga.toml").open("rb") as stream:
        pinned = tomllib.load(stream)["runtime"]["commit"].lower()
    actual = git("-C", str(RUNTIME), "rev-parse", "HEAD").strip().lower()
    if actual != pinned:
        raise SystemExit(
            f"ERROR: {RUNTIME} is at {actual}, but config/mga.toml pins "
            f"{pinned}. Run: git submodule update --init --recursive"
        )


def main(argv):
    args = parse_args(argv)
    if re.fullmatch(r"v?\d+(\.\d+)*([-.][0-9A-Za-z.]+)?", args.version) is None:
        raise SystemExit(f"ERROR: not a version tag: {args.version}")
    check_runtime_pin()

    files = tracked_files()
    missing = [path for path in REQUIRED if path not in files]
    if missing:
        raise SystemExit(f"ERROR: not tracked: {', '.join(missing)}")
    media = [path for path in files if Path(path).suffix.lower() in GAME_MEDIA]
    if media:
        raise SystemExit(f"ERROR: refusing to package: {', '.join(media)}")

    args.out.mkdir(parents=True, exist_ok=True)
    archive = args.out / (
        f"MetalGearAcid-Recomp-{args.version}-Windows-x64.zip"
    )
    with zipfile.ZipFile(
        archive, "w", compression=zipfile.ZIP_DEFLATED
    ) as bundle:
        for path in files:
            source = ROOT / path
            if source.is_file():
                bundle.write(source, path)
    print(f"wrote {archive} ({len(files)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
