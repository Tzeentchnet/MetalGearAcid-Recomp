#!/usr/bin/env python3
"""Verify a supported ISO, generate game code, and build Metal Gear Acid."""

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Callable, Mapping, Sequence
import urllib.request
import zipfile

try:
    import tomllib
except ModuleNotFoundError:
    print("ERROR: Python 3.11 or newer is required.", file=sys.stderr)
    raise SystemExit(1)


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools" / "mga"))
import discimage  # noqa: E402

MINIMUM_CMAKE = (3, 25, 0)
STAMP = Path("build/mga/install_stamp.json")
GENERATED_IMAGE = Path("build/mga/gen/mga_image.bin")
CONVERTED_ISO = Path("build/mga/disc/Metal Gear Acid (USA).iso")
SDL3_VERSION = "3.4.20"
SDL3_URL = (
    "https://github.com/libsdl-org/SDL/releases/download/"
    f"release-{SDL3_VERSION}/SDL3-devel-{SDL3_VERSION}-VC.zip"
)
SDL3_SHA256 = (
    "1ec3009655ee37b1f73e52b3b120acc5afd8abaf9532f3303b1bf1dfe91b5969"
)
VS_BOOTSTRAPPER_URL = "https://aka.ms/vs/17/release/vs_BuildTools.exe"
VS_COMPONENTS = (
    "Microsoft.VisualStudio.Workload.VCTools",
    "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
    "Microsoft.VisualStudio.Component.VC.CMake.Project",
    "Microsoft.VisualStudio.Component.VC.Llvm.Clang",
    "Microsoft.VisualStudio.Component.VC.Llvm.ClangToolset",
    "Microsoft.VisualStudio.Component.Windows11SDK.22621",
)
RENDERERS = {
    "software": {
        "preset": "clang-cl",
        "executable": Path("out/build/clang-cl/mga.exe"),
    },
    "d3d12": {
        "preset": "clang-cl-d3d12",
        "executable": Path("out/build/clang-cl-d3d12/mga.exe"),
    },
    "vulkan": {
        "preset": "clang-cl-vulkan",
        "executable": Path("out/build/clang-cl-vulkan/mga.exe"),
    },
}


class InstallError(RuntimeError):
    """A setup failure with an actionable user-facing message."""


class ToolchainMissing(InstallError):
    """Visual Studio, Clang, CMake, Ninja or the Windows SDK is missing."""


@dataclass(frozen=True)
class RuntimeConfig:
    repository: str
    branch: str
    commit: str


def env_value(
    env: Mapping[str, str],
    name: str,
    default: str | None = None,
) -> str | None:
    """Look a variable up the way Windows does, ignoring case.

    dict(os.environ) has upper-case keys on Windows, so a plain
    env.get("ProgramFiles(x86)") would always miss.
    """
    if name in env:
        return env[name]
    folded = name.upper()
    for key, value in env.items():
        if key.upper() == folded:
            return value
    return default


class CommandRunner:
    def run(
        self,
        command: Sequence[os.PathLike[str] | str],
        *,
        cwd: Path,
        env: Mapping[str, str] | None = None,
    ) -> None:
        command_text = [os.fspath(part) for part in command]
        print(f"\n> {subprocess.list2cmdline(command_text)}")
        try:
            result = subprocess.run(
                command_text,
                cwd=cwd,
                env=env,
                check=False,
            )
        except OSError as error:
            raise InstallError(
                f"Could not start {command_text[0]}: {error}"
            ) from error
        if result.returncode:
            raise InstallError(
                f"Command exited with code {result.returncode}: "
                f"{subprocess.list2cmdline(command_text)}"
            )

    def capture(
        self,
        command: Sequence[os.PathLike[str] | str] | str,
        *,
        cwd: Path,
        env: Mapping[str, str] | None = None,
    ) -> str:
        if isinstance(command, str):
            process_command: Sequence[str] | str = command
            display_command = command
            command_name = "command"
        else:
            command_text = [os.fspath(part) for part in command]
            process_command = command_text
            display_command = subprocess.list2cmdline(command_text)
            command_name = command_text[0]
        try:
            result = subprocess.run(
                process_command,
                cwd=cwd,
                env=env,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except OSError as error:
            raise InstallError(
                f"Could not start {command_name}: {error}"
            ) from error
        if result.returncode:
            detail = result.stderr.strip() or result.stdout.strip()
            if detail:
                detail = f"\n{detail}"
            raise InstallError(
                f"Command exited with code {result.returncode}: "
                f"{display_command}{detail}"
            )
        return result.stdout.strip()


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "iso",
        nargs="?",
        type=Path,
        help=(
            "path to a Metal Gear Acid USA ULUS-10006 v1.00 disc image "
            "(.iso, .cso or .chd); omit it to enter the path interactively"
        ),
    )
    parser.add_argument(
        "--renderer",
        choices=tuple(RENDERERS),
        help=(
            "renderer to build; setup asks when run interactively, and "
            "otherwise builds software, which needs no SDL3"
        ),
    )
    parser.add_argument(
        "--download-sdl3",
        action="store_true",
        help=(
            f"download SDL3 {SDL3_VERSION} from GitHub for a D3D12 or Vulkan "
            "build when no SDL3 package is given"
        ),
    )
    parser.add_argument(
        "--install-build-tools",
        action="store_true",
        help=(
            "install or complete Visual Studio 2022 Build Tools with the "
            "C++ Clang tools when they are missing (you accept Microsoft's "
            "license terms)"
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="redo every step even when the last setup is still current",
    )
    parser.add_argument(
        "--sdl3-dir",
        type=Path,
        help=(
            "directory containing SDL3Config.cmake for a D3D12 or "
            "Vulkan build"
        ),
    )
    parser.add_argument(
        "--vcvars",
        type=Path,
        help=(
            "path to vcvars64.bat when Visual Studio cannot be detected"
        ),
    )
    parser.add_argument(
        "--no-build",
        action="store_true",
        help="verify, extract, and generate without configuring or building",
    )
    parser.add_argument(
        "--prepare",
        action="store_true",
        help=(
            "run unattended for a launcher: never prompt, and print "
            "'progress <0-1> <text>' lines"
        ),
    )
    return parser.parse_args(argv)


def progress_reporter(enabled: bool) -> Callable[[float, str], None]:
    def report(fraction: float, text: str) -> None:
        if enabled:
            print(f"progress {fraction:g} {text}", flush=True)

    return report


def runtime_needs_git(root: Path) -> bool:
    target = root / "external" / "psp-recomp"
    return (
        (root / ".git").exists()
        or (target / ".git").exists()
        or not (target / "tools" / "codegen.py").is_file()
    )


def load_runtime_config(root: Path) -> RuntimeConfig:
    config_path = root / "config" / "mga.toml"
    try:
        with config_path.open("rb") as stream:
            document = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise InstallError(
            f"Could not read project configuration {config_path}: {error}"
        ) from error

    runtime = document.get("runtime")
    if not isinstance(runtime, dict):
        raise InstallError(
            f"{config_path} does not contain a [runtime] table"
        )
    repository = runtime.get("repository")
    branch = runtime.get("branch")
    commit = runtime.get("commit")
    if not all(isinstance(value, str) and value for value in (
        repository,
        branch,
        commit,
    )):
        raise InstallError(
            f"{config_path} has an incomplete [runtime] table"
        )
    if re.fullmatch(r"[0-9a-fA-F]{40}", commit) is None:
        raise InstallError(
            f"{config_path} contains an invalid runtime commit: {commit}"
        )
    return RuntimeConfig(repository, branch, commit.lower())


def _path_from_input(value: os.PathLike[str] | str) -> Path:
    text = os.fspath(value).strip()
    if (
        len(text) >= 2
        and text[0] == text[-1]
        and text[0] in {'"', "'"}
    ):
        text = text[1:-1]
    if not text:
        raise InstallError("The ISO path cannot be empty")
    return Path(text).expanduser()


def resolve_iso_path(
    value: os.PathLike[str] | str | None,
    *,
    root: Path,
    input_fn: Callable[[str], str] = input,
) -> Path:
    if value is None:
        default_iso = (
            root / "Metal Gear Acid (USA)" / "Metal Gear Acid (USA).iso"
        )
        if default_iso.is_file():
            print(f"Using ISO at {default_iso}")
            value = default_iso
        else:
            try:
                value = input_fn(
                    "ISO path (drag the file here, then press Enter): "
                )
            except EOFError as error:
                raise InstallError(
                    "No ISO path was supplied. Pass it on the command line."
                ) from error

    candidate = _path_from_input(value)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as error:
        raise InstallError(f"ISO was not found: {candidate}") from error
    if not resolved.is_file():
        raise InstallError(f"ISO path is not a file: {resolved}")
    return resolved


def find_command(
    name: str,
    env: Mapping[str, str],
    install_hint: str,
    error_type: type[InstallError] = InstallError,
) -> str:
    command = shutil.which(name, path=env.get("PATH"))
    if command is None:
        raise error_type(f"{name} was not found. {install_hint}")
    return command


def ensure_runtime(
    root: Path,
    runtime: RuntimeConfig,
    git: str | None,
    runner: CommandRunner,
    env: Mapping[str, str],
) -> None:
    target = root / "external" / "psp-recomp"
    codegen = target / "tools" / "codegen.py"
    target_git = target / ".git"

    if (root / ".git").exists():
        runner.run(
            [git, "submodule", "update", "--init", "--recursive"],
            cwd=root,
            env=env,
        )
    elif not codegen.is_file():
        if target.exists() and not target.is_dir():
            raise InstallError(
                f"{target} exists but is not a directory. Move it aside, "
                "then run the installer again."
            )
        if target.exists() and any(target.iterdir()) and not target_git.exists():
            raise InstallError(
                f"{target} is not empty and is not a Git checkout. "
                "Move it aside, then run the installer again."
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target_git.exists():
            runner.run(
                [
                    git,
                    "clone",
                    "--branch",
                    runtime.branch,
                    "--single-branch",
                    "--no-checkout",
                    runtime.repository,
                    target,
                ],
                cwd=root,
                env=env,
            )
        runner.run(
            [git, "-C", target, "checkout", "--detach", runtime.commit],
            cwd=root,
            env=env,
        )
        runner.run(
            [git, "-C", target, "submodule", "update", "--init", "--recursive"],
            cwd=root,
            env=env,
        )
    elif not target_git.exists():
        print("Using the runtime bundled with this source archive.")

    if not codegen.is_file():
        raise InstallError(
            f"Runtime setup completed without creating {codegen}"
        )
    if target_git.exists():
        actual_commit = runner.capture(
            [git, "-C", target, "rev-parse", "HEAD"],
            cwd=root,
            env=env,
        ).lower()
        if actual_commit != runtime.commit:
            raise InstallError(
                "The runtime checkout does not match the configured pin: "
                f"{actual_commit} != {runtime.commit}"
            )


def persist_iso_path(root: Path, iso: Path) -> Path:
    destination = root / "config" / "mga_iso_path.txt"
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(f"{iso}\n", encoding="utf-8")
    except OSError as error:
        raise InstallError(
            f"Could not save the local ISO path in {destination}: {error}"
        ) from error
    return destination


def find_vcvars64(
    env: Mapping[str, str],
    override: Path | None = None,
) -> Path:
    candidates = []
    if override is not None:
        candidates.append(override)
    configured = env.get("MGA_VCVARS64")
    if configured:
        configured_path = Path(configured).expanduser()
        if not configured_path.is_file():
            raise InstallError(
                "MGA_VCVARS64 points to a missing file: "
                f"{configured_path}"
            )
        candidates.append(configured_path)
    install_dir = env.get("VSINSTALLDIR")
    if install_dir:
        candidates.append(
            Path(install_dir) / "VC" / "Auxiliary" / "Build" / "vcvars64.bat"
        )
    for candidate in candidates:
        resolved = candidate.expanduser()
        if resolved.is_file():
            return resolved.resolve()
    if override is not None:
        raise InstallError(f"vcvars64.bat was not found at {override}")

    program_files_x86 = env_value(env, "ProgramFiles(x86)")
    if program_files_x86:
        vswhere = (
            Path(program_files_x86)
            / "Microsoft Visual Studio"
            / "Installer"
            / "vswhere.exe"
        )
        if vswhere.is_file():
            try:
                result = subprocess.run(
                    [
                        str(vswhere),
                        "-latest",
                        "-products",
                        "*",
                        "-requires",
                        "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
                        "-property",
                        "installationPath",
                    ],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
            except OSError as error:
                print(
                    f"Warning: could not start vswhere: {error}",
                    file=sys.stderr,
                )
                result = None
            if result is not None:
                if result.returncode:
                    detail = result.stderr.strip() or "no diagnostic"
                    print(
                        f"Warning: vswhere failed: {detail}",
                        file=sys.stderr,
                    )
                else:
                    installations = [
                        Path(line.strip())
                        for line in result.stdout.splitlines()
                        if line.strip()
                    ]
                    if installations:
                        candidate = (
                            installations[-1]
                            / "VC"
                            / "Auxiliary"
                            / "Build"
                            / "vcvars64.bat"
                        )
                        if candidate.is_file():
                            return candidate.resolve()

    editions = ("BuildTools", "Community", "Professional", "Enterprise")
    for variable in ("ProgramFiles", "ProgramFiles(x86)"):
        base = env_value(env, variable)
        if not base:
            continue
        for edition in editions:
            candidate = (
                Path(base)
                / "Microsoft Visual Studio"
                / "2022"
                / edition
                / "VC"
                / "Auxiliary"
                / "Build"
                / "vcvars64.bat"
            )
            if candidate.is_file():
                return candidate.resolve()

    raise ToolchainMissing(
        "Visual Studio 2022 C++ Build Tools were not found. Install the "
        "'Desktop development with C++' workload and the Clang tools for "
        "Windows, pass --vcvars C:\\path\\to\\vcvars64.bat, or rerun "
        "setup with --install-build-tools."
    )


def _set_environment_value(
    environment: dict[str, str],
    key: str,
    value: str,
) -> None:
    for existing in tuple(environment):
        if existing.upper() == key.upper() and existing != key:
            del environment[existing]
    environment[key] = value


def load_vcvars_environment(
    vcvars: Path,
    base_env: Mapping[str, str],
    runner: CommandRunner,
) -> dict[str, str]:
    comspec = env_value(base_env, "COMSPEC")
    if not comspec:
        system_root = env_value(base_env, "SystemRoot", r"C:\Windows")
        comspec = str(Path(system_root) / "System32" / "cmd.exe")
    command_line = (
        f"{subprocess.list2cmdline([comspec])} /d /c "
        f'call "{vcvars}" >nul && set'
    )
    output = runner.capture(
        command_line,
        cwd=ROOT,
        env=base_env,
    )
    environment = dict(base_env)
    for line in output.splitlines():
        key, separator, value = line.partition("=")
        if not separator or not key or key.startswith("="):
            continue
        canonical = "PATH" if key.upper() == "PATH" else key
        _set_environment_value(environment, canonical, value)
    if not environment.get("VSCMD_VER"):
        raise InstallError(
            f"{vcvars} completed without creating a Visual Studio environment"
        )
    return environment


def parse_cmake_version(output: str) -> tuple[int, int, int]:
    match = re.search(
        r"cmake version (\d+)\.(\d+)\.(\d+)",
        output,
        flags=re.IGNORECASE,
    )
    if match is None:
        raise InstallError(f"Could not parse the CMake version from: {output}")
    return tuple(int(group) for group in match.groups())


def prepare_build_tools(
    env: Mapping[str, str],
    runner: CommandRunner,
    vcvars_override: Path | None,
) -> tuple[dict[str, str], dict[str, str]]:
    if os.name != "nt":
        raise InstallError("Native builds are currently supported on Windows only")

    if env.get("VSCMD_VER"):
        build_env = dict(env)
    else:
        vcvars = find_vcvars64(env, vcvars_override)
        print(f"Using Visual Studio environment: {vcvars}")
        build_env = load_vcvars_environment(vcvars, env, runner)

    tools = {
        "cmake": find_command(
            "cmake",
            build_env,
            "Install CMake 3.25 or newer and add it to PATH.",
            ToolchainMissing,
        ),
        "ninja": find_command(
            "ninja",
            build_env,
            "Install Ninja and add it to PATH.",
            ToolchainMissing,
        ),
        "clang-cl": find_command(
            "clang-cl",
            build_env,
            "Add the Visual Studio C++ Clang tools component.",
            ToolchainMissing,
        ),
        "llvm-lib": find_command(
            "llvm-lib",
            build_env,
            "Add the Visual Studio C++ Clang tools component.",
            ToolchainMissing,
        ),
        "rc": find_command(
            "rc",
            build_env,
            "Install a Windows SDK through Visual Studio Installer.",
            ToolchainMissing,
        ),
    }
    cmake_version = parse_cmake_version(
        runner.capture(
            [tools["cmake"], "--version"],
            cwd=ROOT,
            env=build_env,
        )
    )
    if cmake_version < MINIMUM_CMAKE:
        found = ".".join(str(part) for part in cmake_version)
        required = ".".join(str(part) for part in MINIMUM_CMAKE)
        raise ToolchainMissing(
            f"CMake {found} is too old; CMake {required} or newer is required"
        )
    return build_env, tools


def resolve_sdl3_dir(
    renderer: str,
    supplied: Path | None,
    env: Mapping[str, str],
) -> Path | None:
    if renderer == "software":
        return None
    value = supplied or (
        Path(env["SDL3_DIR"]) if env.get("SDL3_DIR") else None
    )
    if value is None:
        if env.get("CMAKE_PREFIX_PATH"):
            return None
        raise InstallError(
            f"The {renderer} renderer requires an SDL3 development package. "
            "Pass --download-sdl3 to fetch SDL3 from GitHub, pass "
            "--sdl3-dir C:\\path\\to\\SDL3\\cmake, or set SDL3_DIR."
        )
    try:
        resolved = value.expanduser().resolve(strict=True)
    except OSError as error:
        raise InstallError(f"SDL3 directory was not found: {value}") from error
    if not resolved.is_dir():
        raise InstallError(f"SDL3 path is not a directory: {resolved}")
    return resolved


def validate_renderer_environment(
    renderer: str,
    env: Mapping[str, str],
) -> None:
    if renderer != "vulkan":
        return
    sdk = env.get("VULKAN_SDK")
    if not sdk or not Path(sdk).is_dir():
        raise InstallError(
            "The Vulkan renderer requires an installed Vulkan SDK with "
            "VULKAN_SDK set."
        )


def cmake_commands(
    renderer: str,
    cmake: str,
    sdl3_dir: Path | None,
) -> tuple[list[str], list[str]]:
    preset = str(RENDERERS[renderer]["preset"])
    configure = [cmake, "--preset", preset]
    if sdl3_dir is not None:
        configure.append(f"-DSDL3_DIR={sdl3_dir}")
    build = [
        cmake,
        "--build",
        "--preset",
        preset,
        "--target",
        "mga_driver",
        "--parallel",
    ]
    return configure, build


def ask_yes_no(
    question: str,
    input_fn: Callable[[str], str],
    default: bool,
) -> bool:
    suffix = " [Y/n] " if default else " [y/N] "
    try:
        answer = input_fn(question + suffix).strip().lower()
    except EOFError:
        return default
    if not answer:
        return default
    return answer in {"y", "yes"}


# --- "already built" stamp -------------------------------------------------


def _hash_tree(digest, root: Path, base: Path, suffixes: Sequence[str]) -> None:
    if not base.is_dir():
        return
    for path in sorted(base.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in suffixes:
            continue
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")


def generation_fingerprint(root: Path, runtime: RuntimeConfig) -> str:
    """What extraction and code generation read besides the disc."""
    digest = hashlib.sha256(b"mga-generate-1\0")
    digest.update(runtime.commit.encode("ascii"))
    _hash_tree(digest, root, root / "tools" / "mga", (".py", ".c"))
    _hash_tree(digest, root, root / "config", (".toml",))
    _hash_tree(
        digest,
        root,
        root / "external" / "psp-recomp" / "tools",
        (".py",),
    )
    return digest.hexdigest()


def build_fingerprint(
    root: Path,
    generated: str,
    renderer: str,
    sdl3_dir: Path | None,
) -> str:
    """What the CMake build reads besides the generated sources."""
    digest = hashlib.sha256(b"mga-build-1\0")
    digest.update(f"{generated}\0{renderer}\0{sdl3_dir or ''}\0".encode())
    for name in ("CMakeLists.txt", "CMakePresets.json"):
        path = root / name
        if path.is_file():
            digest.update(path.read_bytes())
    runtime = root / "external" / "psp-recomp"
    _hash_tree(
        digest,
        root,
        runtime / "src",
        (".c", ".cpp", ".h", ".hpp", ".hlsl", ".inc", ".glsl", ".spv"),
    )
    return digest.hexdigest()


def source_identity(path: Path) -> dict[str, object]:
    status = path.stat()
    return {
        "path": str(path),
        "size": status.st_size,
        "mtime_ns": status.st_mtime_ns,
    }


def load_stamp(root: Path) -> dict:
    try:
        stamp = json.loads((root / STAMP).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return stamp if isinstance(stamp, dict) and stamp.get("version") == 1 else {}


def save_stamp(root: Path, stamp: dict) -> None:
    path = root / STAMP
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(json.dumps(stamp, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


# --- CSO and CHD -----------------------------------------------------------


def prepare_disc_image(
    root: Path,
    source: Path,
    stamp: dict,
    force: bool,
    report: Callable[[float, str], None],
) -> Path:
    """Return a plain ISO for source, converting a CSO or CHD once."""
    try:
        kind = discimage.image_kind(source)
    except OSError as error:
        raise InstallError(f"Could not read {source}: {error}") from error
    if kind == "iso":
        return source
    destination = root / CONVERTED_ISO
    if (
        not force
        and destination.is_file()
        and stamp.get("converted_from") == source_identity(source)
    ):
        print(f"Using the ISO already converted from {source.name}")
        return destination

    print(f"Converting {source.name} to {destination}")
    last = [-1]

    def progress(done: int, total: int) -> None:
        percent = done * 100 // max(total, 1)
        if percent != last[0] and percent % 5 == 0:
            last[0] = percent
            print(f"  {percent}%", flush=True)
            report(0.1 + 0.08 * done / max(total, 1), "Unpacking your disc image")

    try:
        discimage.convert_to_iso(source, destination, progress)
    except discimage.DiscImageError as error:
        raise InstallError(str(error)) from error
    except OSError as error:
        raise InstallError(f"Could not convert {source}: {error}") from error
    stamp.pop("generated", None)
    stamp["converted_from"] = source_identity(source)
    save_stamp(root, stamp)
    return destination


# --- SDL3 --------------------------------------------------------------------


def download_file(url: str, destination: Path) -> str:
    """Download url to destination and return its SHA-256."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".partial")
    digest = hashlib.sha256()
    try:
        request = urllib.request.Request(
            url, headers={"User-Agent": "MetalGearAcid-Recomp-setup"}
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            with temporary.open("wb") as output:
                while chunk := response.read(1 << 20):
                    output.write(chunk)
                    digest.update(chunk)
        os.replace(temporary, destination)
    except OSError as error:
        temporary.unlink(missing_ok=True)
        raise InstallError(f"Could not download {url}: {error}") from error
    return digest.hexdigest()


def ensure_sdl3(root: Path) -> Path:
    """Download and unpack the pinned SDL3 package; return its cmake dir."""
    deps = root / "build" / "deps"
    package = deps / f"SDL3-{SDL3_VERSION}"
    cmake_dir = package / "cmake"
    if (cmake_dir / "SDL3Config.cmake").is_file():
        print(f"Using SDL3 {SDL3_VERSION} from {package}")
        return cmake_dir
    archive = deps / f"SDL3-devel-{SDL3_VERSION}-VC.zip"
    print(f"Downloading SDL3 {SDL3_VERSION} from {SDL3_URL}")
    actual = download_file(SDL3_URL, archive)
    if actual != SDL3_SHA256:
        archive.unlink(missing_ok=True)
        raise InstallError(
            f"The SDL3 download has SHA-256 {actual}, expected {SDL3_SHA256}"
        )
    prefix = f"SDL3-{SDL3_VERSION}/"
    try:
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.infolist():
                name = member.filename
                if (
                    not name.startswith(prefix)
                    or ".." in Path(name).parts
                    or Path(name).is_absolute()
                ):
                    raise InstallError(f"Unexpected file in SDL3 package: {name}")
            bundle.extractall(deps)
    except zipfile.BadZipFile as error:
        raise InstallError(f"The SDL3 download is damaged: {error}") from error
    archive.unlink(missing_ok=True)
    if not (cmake_dir / "SDL3Config.cmake").is_file():
        raise InstallError(f"The SDL3 package has no {cmake_dir}")
    return cmake_dir


# --- Visual Studio Build Tools ----------------------------------------------


def find_visual_studio_instance(env: Mapping[str, str]) -> Path | None:
    """Any Visual Studio 2022 instance, with or without the C++ tools."""
    program_files_x86 = env_value(env, "ProgramFiles(x86)")
    if not program_files_x86:
        return None
    vswhere = (
        Path(program_files_x86)
        / "Microsoft Visual Studio"
        / "Installer"
        / "vswhere.exe"
    )
    if not vswhere.is_file():
        return None
    result = subprocess.run(
        [
            str(vswhere), "-latest", "-products", "*",
            "-version", "[17.0,18.0)", "-property", "installationPath",
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return Path(lines[-1]) if result.returncode == 0 and lines else None


def verify_microsoft_signature(path: Path) -> None:
    script = (
        "$s = Get-AuthenticodeSignature -LiteralPath $args[0]; "
        "if ($s.Status -ne 'Valid' -or "
        "$s.SignerCertificate.Subject -notmatch 'O=Microsoft Corporation') "
        "{ Write-Output $s.Status; exit 1 }"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script,
         str(path)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if result.returncode:
        raise InstallError(
            f"{path} is not signed by Microsoft ({result.stdout.strip()})"
        )


def install_build_tools(root: Path, env: Mapping[str, str]) -> None:
    """Install, or add the missing components to, Visual Studio 2022."""
    if os.name != "nt":
        raise InstallError("Build Tools can be installed on Windows only")
    adds = [argument for component in VS_COMPONENTS
            for argument in ("--add", component)]
    flags = ["--passive", "--wait", "--norestart", "--includeRecommended"]
    instance = find_visual_studio_instance(env)
    if instance is not None:
        installer = (
            Path(env_value(env, "ProgramFiles(x86)"))
            / "Microsoft Visual Studio"
            / "Installer"
            / "setup.exe"
        )
        command = [str(installer), "modify", "--installPath", str(instance),
                   *adds, *flags]
        print(f"Adding the C++ and Clang tools to {instance}")
    else:
        with tempfile.TemporaryDirectory() as temporary:
            bootstrapper = Path(temporary) / "vs_BuildTools.exe"
            print(f"Downloading Visual Studio Build Tools from "
                  f"{VS_BOOTSTRAPPER_URL}")
            download_file(VS_BOOTSTRAPPER_URL, bootstrapper)
            verify_microsoft_signature(bootstrapper)
            command = [str(bootstrapper), *adds, *flags]
            _run_vs_installer(command)
        return
    _run_vs_installer(command)


def _run_vs_installer(command: list[str]) -> None:
    print("Visual Studio Installer is running. Windows asks for permission, "
          "and the download is several gigabytes; this can take a while.")
    print(f"\n> {subprocess.list2cmdline(command)}", flush=True)
    try:
        result = subprocess.run(command, check=False)
    except OSError as error:
        raise InstallError(f"Could not start {command[0]}: {error}") from error
    if result.returncode == 3010:
        print("Build Tools installed. Windows asks for a restart; setup "
              "continues now.")
    elif result.returncode:
        raise InstallError(
            f"Visual Studio Installer exited with code {result.returncode}"
        )


def ensure_build_tools(
    root: Path,
    env: Mapping[str, str],
    runner: CommandRunner,
    vcvars_override: Path | None,
    *,
    allowed: bool,
    unattended: bool,
    input_fn: Callable[[str], str],
) -> tuple[dict[str, str], dict[str, str]]:
    try:
        return prepare_build_tools(env, runner, vcvars_override)
    except ToolchainMissing as error:
        if not allowed:
            if unattended:
                raise
            print(f"\n{error}")
            allowed = ask_yes_no(
                "Install Visual Studio 2022 Build Tools with the C++ Clang "
                "tools now? You accept Microsoft's license terms "
                "(https://visualstudio.microsoft.com/license-terms/) and "
                "download several gigabytes.",
                input_fn,
                False,
            )
            if not allowed:
                raise
    install_build_tools(root, env)
    return prepare_build_tools(env, runner, vcvars_override)


# --- setup -------------------------------------------------------------------


def choose_renderer(
    args: argparse.Namespace,
    unattended: bool,
    input_fn: Callable[[str], str],
) -> tuple[str, bool]:
    """Return the renderer and whether SDL3 may be downloaded."""
    renderer = getattr(args, "renderer", None)
    download = bool(getattr(args, "download_sdl3", False))
    if renderer is not None or unattended or args.no_build:
        return renderer or "software", download
    if ask_yes_no(
        "Build the recommended D3D12 renderer? Setup downloads SDL3 "
        f"{SDL3_VERSION} (about 17 MB) from GitHub. Answer n for the "
        "software renderer.",
        input_fn,
        True,
    ):
        return "d3d12", True
    return "software", download


def execute_install(
    args: argparse.Namespace,
    *,
    root: Path = ROOT,
    runner: CommandRunner | None = None,
    env: Mapping[str, str] | None = None,
    input_fn: Callable[[str], str] = input,
) -> int:
    if sys.version_info < (3, 11):
        raise InstallError("Python 3.11 or newer is required")

    runner = runner or CommandRunner()
    base_env = dict(os.environ if env is None else env)
    unattended = getattr(args, "prepare", False)
    force = getattr(args, "force", False)
    report = progress_reporter(unattended)
    runtime = load_runtime_config(root)
    if unattended and args.iso is None:
        raise InstallError("--prepare needs the path to your disc image")
    source = resolve_iso_path(args.iso, root=root, input_fn=input_fn)
    renderer, may_download_sdl3 = choose_renderer(args, unattended, input_fn)
    git = None
    if runtime_needs_git(root):
        git = find_command(
            "git",
            base_env,
            "Install Git for Windows and add it to PATH.",
        )

    build_env = None
    tools = None
    sdl3_dir = None
    if not args.no_build:
        report(0, "Checking the build tools")
        build_env, tools = ensure_build_tools(
            root,
            base_env,
            runner,
            args.vcvars,
            allowed=getattr(args, "install_build_tools", False),
            unattended=unattended,
            input_fn=input_fn,
        )
        if (
            renderer != "software"
            and args.sdl3_dir is None
            and not build_env.get("SDL3_DIR")
            and not build_env.get("CMAKE_PREFIX_PATH")
            and may_download_sdl3
        ):
            report(0.02, "Downloading SDL3")
            sdl3_dir = ensure_sdl3(root)
        else:
            sdl3_dir = resolve_sdl3_dir(renderer, args.sdl3_dir, build_env)
        validate_renderer_environment(renderer, build_env)

    print("\nMetal Gear Acid setup")
    print(f"  Disc:     {source}")
    print(f"  Renderer: {renderer}")

    stamp = {} if force else load_stamp(root)
    stamp["version"] = 1
    total_steps = 4 if not args.no_build else 3
    print(f"\n[1/{total_steps}] Preparing the runtime fork")
    report(0.05, "Preparing the runtime")
    ensure_runtime(root, runtime, git, runner, base_env)

    print(f"\n[2/{total_steps}] Verifying and extracting the disc")
    report(0.1, "Verifying your disc image")
    iso = prepare_disc_image(root, source, stamp, force, report)
    generated = generation_fingerprint(root, runtime)
    current = {"source": source_identity(source), "fingerprint": generated}
    up_to_date = (
        stamp.get("generated") == current
        and (root / GENERATED_IMAGE).is_file()
    )
    if up_to_date:
        print("The disc and generated code are unchanged; skipping "
              "extraction. Pass --force to redo it.")
    else:
        runner.run(
            [sys.executable, root / "tools" / "mga" / "extract.py", iso],
            cwd=root,
            env=base_env,
        )
    iso_config = persist_iso_path(root, iso)
    print(f"Saved the local ISO path in {iso_config}")

    print(f"\n[3/{total_steps}] Generating native sources")
    report(0.2, "Generating native code")
    if not up_to_date:
        stamp.pop("generated", None)
        stamp.pop("builds", None)
        runner.run(
            [sys.executable, root / "tools" / "mga" / "gen.py"],
            cwd=root,
            env=base_env,
        )
        stamp["generated"] = current
        save_stamp(root, stamp)

    if args.no_build:
        print("\nExtraction and generation completed.")
        print("Build a CMake preset manually when the toolchain is ready.")
        return 0

    print(f"\n[4/{total_steps}] Configuring and building {renderer}")
    assert build_env is not None
    assert tools is not None
    executable = root / Path(RENDERERS[renderer]["executable"])
    builds = stamp.setdefault("builds", {})
    fingerprint = build_fingerprint(root, generated, renderer, sdl3_dir)
    if builds.get(renderer) == fingerprint and executable.is_file():
        print(f"The {renderer} build is current; skipping it. Pass --force "
              "to rebuild.")
    else:
        builds.pop(renderer, None)
        configure, build = cmake_commands(
            renderer,
            tools["cmake"],
            sdl3_dir,
        )
        report(0.4, "Configuring the build")
        runner.run(configure, cwd=root, env=build_env)
        report(0.45, "Compiling the game (this can take a while)")
        runner.run(build, cwd=root, env=build_env)
        if not executable.is_file():
            raise InstallError(
                f"The build completed without creating {executable}"
            )
        builds[renderer] = fingerprint
    stamp["renderer"] = renderer
    save_stamp(root, stamp)

    report(1, "Ready to play")
    print("\nSetup completed successfully.")
    print(f"Built executable: {executable}")
    print(f'Launch with: "{root / "Launch Metal Gear Acid.bat"}"')
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.prepare:
        # Keep progress lines in order with the child processes' output.
        sys.stdout.reconfigure(line_buffering=True)
    try:
        return execute_install(args)
    except InstallError as error:
        print(f"\nERROR: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nSetup cancelled.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
