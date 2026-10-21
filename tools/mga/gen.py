#!/usr/bin/env python3
"""Generate C and a relocated image for Metal Gear Acid's main PRX."""

import argparse
import glob
from pathlib import Path
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[2]


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "build" / "mga" / "gen",
    )
    parser.add_argument(
        "--single",
        action="store_true",
        help="emit one large C file instead of split translation units",
    )
    return parser.parse_args(argv[1:])


def run(command, **kwargs):
    print(" ".join(str(part) for part in command))
    return subprocess.run(command, check=False, **kwargs)


def main(argv):
    args = parse_args(argv)
    with (ROOT / "config" / "mga.toml").open("rb") as stream:
        config = tomllib.load(stream)

    module = config["module"]
    prx = ROOT / "build" / "mga" / "disc" / Path(module["file"])
    if not prx.exists():
        print(
            f"missing {prx}; run tools\\mga\\extract.py <ISO> first",
            file=sys.stderr,
        )
        return 1

    toolkit = ROOT / "external" / "psp-recomp" / "tools"
    if not toolkit.exists():
        print(
            "missing external\\psp-recomp; initialize the git submodule first",
            file=sys.stderr,
        )
        return 1

    args.out.mkdir(parents=True, exist_ok=True)
    for pattern in (
        "mga_recomp_[0-9][0-9][0-9].c",
        "mga_recomp_hot_[0-9][0-9][0-9].c",
        "mga_recomp_cold_[0-9][0-9][0-9].c",
    ):
        for path in glob.glob(str(args.out / pattern)):
            Path(path).unlink()

    stubs = args.out / "stubs.txt"
    stubs.unlink(missing_ok=True)
    codegen_log = args.out / "codegen.log"
    codegen_command = [
        sys.executable,
        toolkit / "codegen.py",
        prx,
        args.out / "mga_recomp.c",
        f"--base={module['base']:#x}",
    ]
    if not args.single:
        codegen_command.append("--split")
    with codegen_log.open("w", encoding="utf-8") as log:
        result = run(codegen_command, stderr=log)
    if result.returncode:
        print(codegen_log.read_text(encoding="utf-8"), file=sys.stderr)
        return result.returncode
    if stubs.exists():
        print(
            f"ERROR: trapping stubs were emitted; see {stubs}",
            file=sys.stderr,
        )
        return 1

    commands = [
        [
            sys.executable,
            toolkit / "prxload.py",
            prx,
            f"{module['base']:#x}",
            f"--out={args.out / 'mga_image.bin'}",
        ],
        [
            sys.executable,
            toolkit / "imports.py",
            prx,
            f"{module['base']:#x}",
            f"--toml={args.out / 'mga_imports.toml'}",
        ],
        [
            sys.executable,
            toolkit / "analyze.py",
            prx,
            f"--base={module['base']:#x}",
            f"--toml={args.out / 'mga_functions.toml'}",
            "--quiet",
        ],
    ]
    for command in commands:
        result = run(command)
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
