#!/usr/bin/env python3
"""Verify a supported ISO, generate game code, and build Metal Gear Acid."""

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Callable, Mapping, Sequence

try:
    import tomllib
except ModuleNotFoundError:
    print("ERROR: Python 3.11 or newer is required.", file=sys.stderr)
    raise SystemExit(1)


ROOT = Path(__file__).resolve().parent
MINIMUM_CMAKE = (3, 25, 0)
RENDERERS = {
    "combined": {
        "preset": "clang-cl",
        "executable": Path("out/build/clang-cl/mga.exe"),
    },
    "software": {
        "preset": "clang-cl-software",
        "executable": Path("out/build/clang-cl-software/mga.exe"),
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


@dataclass(frozen=True)
class RuntimeConfig:
    repository: str
    branch: str
    commit: str


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
            "path to a Metal Gear Acid USA ULUS-10006 v1.00 ISO; "
            "omit it to enter the path interactively"
        ),
    )
    renderer_group = parser.add_mutually_exclusive_group()
    renderer_group.add_argument(
        "--renderer",
        choices=tuple(RENDERERS),
        default="combined",
        help=(
            "renderer set to build (default: combined D3D12, Vulkan, and "
            "software)"
        ),
    )
    renderer_group.add_argument(
        "--software-only",
        action="store_true",
        help="build only the dependency-light software reference renderer",
    )
    parser.add_argument(
        "--sdl3-dir",
        type=Path,
        help=(
            "optional directory containing SDL3Config.cmake; otherwise "
            "the pinned SDL3 development package is downloaded"
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
    args = parser.parse_args(argv)
    if args.software_only:
        args.renderer = "software"
    return args


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
) -> str:
    command = shutil.which(name, path=env.get("PATH"))
    if command is None:
        raise InstallError(f"{name} was not found. {install_hint}")
    return command


def ensure_runtime(
    root: Path,
    runtime: RuntimeConfig,
    git: str,
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

    program_files_x86 = env.get("ProgramFiles(x86)")
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
        base = env.get(variable)
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

    raise InstallError(
        "Visual Studio 2022 C++ Build Tools were not found. Install the "
        "'Desktop development with C++' workload and the Clang tools for "
        "Windows, or pass --vcvars C:\\path\\to\\vcvars64.bat."
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
    comspec = base_env.get("COMSPEC")
    if not comspec:
        system_root = base_env.get("SystemRoot", r"C:\Windows")
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
        ),
        "ninja": find_command(
            "ninja",
            build_env,
            "Install Ninja and add it to PATH.",
        ),
        "clang-cl": find_command(
            "clang-cl",
            build_env,
            "Add the Visual Studio C++ Clang tools component.",
        ),
        "llvm-lib": find_command(
            "llvm-lib",
            build_env,
            "Add the Visual Studio C++ Clang tools component.",
        ),
        "rc": find_command(
            "rc",
            build_env,
            "Install a Windows SDK through Visual Studio Installer.",
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
        raise InstallError(
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
        return None
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
    if renderer not in {"combined", "vulkan"}:
        return
    sdk = env.get("VULKAN_SDK")
    if sdk:
        candidates = [Path(sdk)]
    else:
        sdk_root = Path(r"C:\VulkanSDK")
        try:
            candidates = sorted(
                (path for path in sdk_root.iterdir() if path.is_dir()),
                reverse=True,
            )
        except OSError:
            candidates = []
    if any(
        (candidate / "Include" / "vulkan" / "vulkan.h").is_file()
        and (candidate / "Lib" / "vulkan-1.lib").is_file()
        for candidate in candidates
    ):
        return
    if sdk:
        raise InstallError(
            "VULKAN_SDK does not contain the required x64 headers and "
            f"library: {sdk}"
        )
    raise InstallError(
        "The combined renderer build requires a Vulkan SDK. Install it "
        "under C:\\VulkanSDK, set VULKAN_SDK, choose --renderer d3d12, "
        "or use --software-only."
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
    runtime = load_runtime_config(root)
    iso = resolve_iso_path(args.iso, root=root, input_fn=input_fn)
    git = find_command(
        "git",
        base_env,
        "Install Git for Windows and add it to PATH.",
    )

    build_env = None
    tools = None
    sdl3_dir = None
    if not args.no_build:
        build_env, tools = prepare_build_tools(
            base_env,
            runner,
            args.vcvars,
        )
        sdl3_dir = resolve_sdl3_dir(
            args.renderer,
            args.sdl3_dir,
            build_env,
        )
        validate_renderer_environment(args.renderer, build_env)

    print("\nMetal Gear Acid setup")
    print(f"  ISO:      {iso}")
    print(f"  Renderer: {args.renderer}")

    total_steps = 4 if not args.no_build else 3
    print(f"\n[1/{total_steps}] Preparing the runtime fork")
    ensure_runtime(root, runtime, git, runner, base_env)

    print(f"\n[2/{total_steps}] Verifying and extracting the ISO")
    runner.run(
        [sys.executable, root / "tools" / "mga" / "extract.py", iso],
        cwd=root,
        env=base_env,
    )
    iso_config = persist_iso_path(root, iso)
    print(f"Saved the local ISO path in {iso_config}")

    print(f"\n[3/{total_steps}] Generating native sources")
    runner.run(
        [sys.executable, root / "tools" / "mga" / "gen.py"],
        cwd=root,
        env=base_env,
    )

    if args.no_build:
        print("\nExtraction and generation completed.")
        print("Build a CMake preset manually when the toolchain is ready.")
        return 0

    print(f"\n[4/{total_steps}] Configuring and building {args.renderer}")
    assert build_env is not None
    assert tools is not None
    configure, build = cmake_commands(
        args.renderer,
        tools["cmake"],
        sdl3_dir,
    )
    runner.run(configure, cwd=root, env=build_env)
    runner.run(build, cwd=root, env=build_env)

    executable = root / Path(RENDERERS[args.renderer]["executable"])
    if not executable.is_file():
        raise InstallError(
            f"The build completed without creating {executable}"
        )

    print("\nSetup completed successfully.")
    print(f"Built executable: {executable}")
    print(f'Launch with: "{root / "Launch Metal Gear Acid.bat"}"')
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
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
