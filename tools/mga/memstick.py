#!/usr/bin/env python3
"""Create or verify isolated Metal Gear Acid memstick fixtures."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

MANIFEST = ".mga-fixture.json"
SCHEMA = "mga-memstick-fixture-v1"
LAYOUTS = {
    "ppsspp": Path("PSP") / "SAVEDATA",
    "native": Path("ms0") / "PSP" / "SAVEDATA",
}


class FixtureError(ValueError):
    pass


def sha256_file(path, chunk_size=1 << 20):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                return digest.hexdigest()
            digest.update(chunk)


def expected_savedata(root, backend):
    try:
        relative = LAYOUTS[backend]
    except KeyError as error:
        raise FixtureError(f"unknown backend {backend!r}") from error
    return Path(root) / relative


def file_inventory(root):
    root = Path(root)
    entries = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        if relative == MANIFEST:
            continue
        entries.append(
            {
                "path": relative,
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return entries


def write_manifest(root, backend, profile):
    root = Path(root)
    document = {
        "schema": SCHEMA,
        "backend": backend,
        "profile": profile,
        "files": file_inventory(root),
    }
    (root / MANIFEST).write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="ascii",
    )
    return document


def verify_fixture(root, backend, require_manifest=True):
    root = Path(root)
    if not root.is_dir():
        raise FixtureError(f"{root}: fixture root does not exist")
    savedata = expected_savedata(root, backend)
    if not savedata.is_dir():
        raise FixtureError(
            f"{root}: missing backend layout {savedata.relative_to(root)}"
        )
    manifest_path = root / MANIFEST
    if not manifest_path.exists():
        if require_manifest:
            raise FixtureError(f"{root}: missing {MANIFEST}")
        return None
    try:
        document = json.loads(manifest_path.read_text(encoding="ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FixtureError(f"{manifest_path}: invalid JSON") from error
    if document.get("schema") != SCHEMA:
        raise FixtureError(f"{manifest_path}: unsupported schema")
    if document.get("backend") != backend:
        raise FixtureError(
            f"{manifest_path}: backend is {document.get('backend')!r}, "
            f"expected {backend!r}"
        )
    actual = file_inventory(root)
    if document.get("files") != actual:
        raise FixtureError(f"{manifest_path}: file inventory has changed")
    return document


def create_fixture(output, backend, template=None):
    output = Path(output)
    if output.exists():
        raise FixtureError(
            f"{output}: output already exists; use a new isolated path"
        )
    if template is None:
        expected_savedata(output, backend).mkdir(parents=True)
        profile = "empty"
    else:
        template = Path(template)
        verify_fixture(template, backend, require_manifest=False)
        template_resolved = template.resolve()
        output_resolved = output.resolve()
        if output_resolved == template_resolved or template_resolved in output_resolved.parents:
            raise FixtureError("output cannot be inside the template")
        shutil.copytree(template, output)
        profile = "existing-save"
    return write_manifest(output, backend, profile)


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create")
    create.add_argument("output", type=Path)
    create.add_argument(
        "--backend", choices=sorted(LAYOUTS), required=True
    )
    create.add_argument("--template", type=Path)

    verify = subparsers.add_parser("verify")
    verify.add_argument("root", type=Path)
    verify.add_argument(
        "--backend", choices=sorted(LAYOUTS), required=True
    )
    return parser.parse_args(argv)


def main(argv):
    args = parse_args(argv[1:])
    try:
        if args.command == "create":
            document = create_fixture(
                args.output, args.backend, args.template
            )
            print(
                f"{args.output}: created {document['profile']} "
                f"{args.backend} fixture with {len(document['files'])} files"
            )
        else:
            document = verify_fixture(args.root, args.backend)
            print(
                f"{args.root}: valid {document['profile']} "
                f"{args.backend} fixture with {len(document['files'])} files"
            )
    except FixtureError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
