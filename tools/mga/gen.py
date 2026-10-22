#!/usr/bin/env python3
"""Generate C and a relocated image for Metal Gear Acid's main PRX."""

import argparse
import glob
import hashlib
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
    codegen_command.extend(
        f"--function-entry={address:#x}"
        for address in module.get("function_entries", [])
    )
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

    modules_root = args.out.parent / "modules"
    for native in config.get("native_module", []):
        module_id = native["id"]
        prefix = native["prefix"]
        native_prx = ROOT / "build" / "mga" / "disc" / native["file"]
        if not native_prx.exists():
            print(
                f"missing {native_prx}; run extraction first",
                file=sys.stderr,
            )
            return 1
        native_sha1 = hashlib.sha1(native_prx.read_bytes()).hexdigest()
        if native_sha1 != native["sha1"]:
            print(
                f"{native_prx}: SHA-1 {native_sha1} != "
                f"{native['sha1']}",
                file=sys.stderr,
            )
            return 1
        native_out = modules_root / module_id
        native_out.mkdir(parents=True, exist_ok=True)
        for pattern in (
            f"{prefix}_[0-9][0-9][0-9].c",
            f"{prefix}_hot_[0-9][0-9][0-9].c",
            f"{prefix}_cold_[0-9][0-9][0-9].c",
        ):
            for path in glob.glob(str(native_out / pattern)):
                Path(path).unlink()
        native_stubs = native_out / "stubs.txt"
        native_stubs.unlink(missing_ok=True)
        native_log = native_out / "codegen.log"
        native_command = [
            sys.executable,
            toolkit / "codegen.py",
            native_prx,
            native_out / f"{prefix}.c",
            f"--base={native['base']:#x}",
            f"--symbol-prefix={prefix}",
        ]
        if not args.single:
            native_command.append("--split")
        if native.get("runtime_jal", False):
            native_command.append("--runtime-jal")
        if native.get("verify_runtime_code", False):
            native_command.append("--verify-runtime-code")
        with native_log.open("w", encoding="utf-8") as log:
            result = run(native_command, stderr=log)
        if result.returncode:
            print(native_log.read_text(encoding="utf-8"), file=sys.stderr)
            return result.returncode
        if native_stubs.exists():
            print(
                f"ERROR: {module_id} emitted trapping stubs; "
                f"see {native_stubs}",
                file=sys.stderr,
            )
            return 1
        for command in (
            [
                sys.executable,
                toolkit / "imports.py",
                native_prx,
                f"{native['base']:#x}",
                f"--toml={native_out / f'{prefix}_imports.toml'}",
            ],
            [
                sys.executable,
                toolkit / "analyze.py",
                native_prx,
                f"--base={native['base']:#x}",
                f"--toml={native_out / f'{prefix}_functions.toml'}",
                "--quiet",
            ],
        ):
            result = run(command)
            if result.returncode:
                return result.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
