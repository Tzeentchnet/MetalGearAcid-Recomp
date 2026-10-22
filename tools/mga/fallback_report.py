#!/usr/bin/env python3
"""Classify and validate module-qualified interpreter fallback targets."""

import argparse
import json
from pathlib import Path
import sys
import tomllib


SCHEMA = "mga-fallback-allowlist-v1"


class FallbackError(ValueError):
    pass


def load_targets(path):
    targets = set()
    with Path(path).open("r", encoding="ascii") as stream:
        header = stream.readline().strip()
        if header != "# psp-recomp interpreter misses v2":
            raise FallbackError(f"{path}: expected v2 miss log")
        for line_number, raw_line in enumerate(stream, 2):
            fields = raw_line.split()
            if not fields:
                continue
            if (
                len(fields) != 2
                or len(fields[1]) != 10
                or not fields[1].startswith("0x")
            ):
                raise FallbackError(
                    f"{path}:{line_number}: malformed fallback target"
                )
            try:
                address = int(fields[1], 16)
            except ValueError as error:
                raise FallbackError(
                    f"{path}:{line_number}: malformed fallback address"
                ) from error
            target = (fields[0], address)
            if target in targets:
                raise FallbackError(
                    f"{path}:{line_number}: duplicate fallback target"
                )
            targets.add(target)
    return targets


def module_metadata(config_path):
    with Path(config_path).open("rb") as stream:
        config = tomllib.load(stream)
    return {
        module["prefix"]: {
            "id": module["id"],
            "file": module["file"],
            "runtime_path": module.get("runtime_path"),
            "sha1": module["sha1"],
        }
        for module in config.get("native_module", [])
    }


def build_report(targets, config_path):
    metadata = module_metadata(config_path)
    grouped = {}
    for prefix, address in sorted(targets):
        grouped.setdefault(prefix, []).append(address)
    modules = []
    for prefix, addresses in grouped.items():
        module = {"prefix": prefix, "count": len(addresses)}
        module.update(metadata.get(prefix, {}))
        module["targets"] = [f"0x{address:08x}" for address in addresses]
        modules.append(module)
    return {
        "schema": "mga-fallback-report-v1",
        "total": len(targets),
        "modules": modules,
    }


def load_allowlist(path):
    with Path(path).open("rb") as stream:
        document = tomllib.load(stream)
    if document.get("schema") != SCHEMA:
        raise FallbackError(f"{path}: unsupported allowlist schema")
    targets = set()
    for module in document.get("module", []):
        prefix = module.get("prefix")
        if not prefix:
            raise FallbackError(f"{path}: module has no prefix")
        for address in module.get("targets", []):
            target = (prefix, address)
            if target in targets:
                raise FallbackError(
                    f"{path}: duplicate target {prefix}/0x{address:08x}"
                )
            targets.add(target)
    return targets


def validate_allowlist(actual, path, exact=True, config_path=None):
    allowed = load_allowlist(path)
    if config_path is not None:
        metadata = module_metadata(config_path)
        with Path(path).open("rb") as stream:
            document = tomllib.load(stream)
        for module in document.get("module", []):
            prefix = module["prefix"]
            expected = metadata.get(prefix)
            if expected is None:
                raise FallbackError(
                    f"{path}: unknown module prefix {prefix}"
                )
            if (
                module.get("file") != expected["file"]
                or module.get("sha1") != expected["sha1"]
            ):
                raise FallbackError(
                    f"{path}: identity mismatch for {prefix}"
                )
    unexpected = sorted(actual - allowed)
    missing = sorted(allowed - actual) if exact else []
    if unexpected or missing:
        details = []
        if unexpected:
            details.append(
                "unexpected "
                + ", ".join(
                    f"{prefix}/0x{address:08x}"
                    for prefix, address in unexpected
                )
            )
        if missing:
            details.append(
                "missing "
                + ", ".join(
                    f"{prefix}/0x{address:08x}"
                    for prefix, address in missing
                )
            )
        raise FallbackError(f"{path}: " + "; ".join(details))
    return {
        "allowlist": Path(path).name,
        "mode": "exact" if exact else "subset",
        "targets": len(actual),
    }


def write_allowlist(path, targets, config_path):
    metadata = module_metadata(config_path)
    grouped = {}
    for prefix, address in sorted(targets):
        grouped.setdefault(prefix, []).append(address)
    lines = [
        f'schema = "{SCHEMA}"',
        "",
    ]
    for prefix, addresses in grouped.items():
        module = metadata.get(prefix, {})
        lines.extend(
            [
                "[[module]]",
                f'prefix = "{prefix}"',
                f'id = "{module.get("id", "unknown")}"',
                f'file = "{module.get("file", "")}"',
                f'sha1 = "{module.get("sha1", "")}"',
                "targets = [",
            ]
        )
        lines.extend(f"  0x{address:08x}," for address in addresses)
        lines.extend(["]", ""])
    Path(path).write_text("\n".join(lines), encoding="ascii")


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("misses", type=Path)
    parser.add_argument(
        "--config", type=Path, default=Path("config/mga.toml")
    )
    parser.add_argument("--allowlist", type=Path)
    parser.add_argument("--allow-new", action="store_true")
    parser.add_argument("--write-allowlist", type=Path)
    parser.add_argument("--out", type=Path)
    return parser.parse_args(argv[1:])


def main(argv):
    args = parse_args(argv)
    try:
        targets = load_targets(args.misses)
        if args.allowlist is not None:
            validate_allowlist(
                targets, args.allowlist, exact=not args.allow_new,
                config_path=args.config,
            )
        if args.write_allowlist is not None:
            write_allowlist(args.write_allowlist, targets, args.config)
        document = build_report(targets, args.config)
    except (OSError, tomllib.TOMLDecodeError, FallbackError) as error:
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
