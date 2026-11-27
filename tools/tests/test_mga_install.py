import argparse
import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import zipfile


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "install.py"
SPEC = importlib.util.spec_from_file_location("mga_install", MODULE_PATH)
install = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(install)


class FakeRunner:
    def __init__(self, runtime_target, commit, build_executable=None):
        self.runtime_target = runtime_target
        self.commit = commit
        self.build_executable = build_executable
        self.commands = []

    def run(self, command, *, cwd, env=None):
        command = [str(part) for part in command]
        self.commands.append(command)
        if "clone" in command:
            (self.runtime_target / ".git").mkdir(parents=True)
        if "checkout" in command or command[1:4] == [
            "submodule",
            "update",
            "--init",
        ]:
            codegen = self.runtime_target / "tools" / "codegen.py"
            codegen.parent.mkdir(parents=True, exist_ok=True)
            codegen.write_text("", encoding="ascii")
            if not (self.runtime_target / ".git").exists():
                (self.runtime_target / ".git").write_text(
                    "gitdir: synthetic\n",
                    encoding="ascii",
                )
        if "--build" in command and self.build_executable is not None:
            self.build_executable.parent.mkdir(parents=True, exist_ok=True)
            self.build_executable.write_bytes(b"synthetic-executable")

    def capture(self, command, *, cwd, env=None):
        if isinstance(command, str):
            self.commands.append(command)
        else:
            self.commands.append([str(part) for part in command])
        return self.commit


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_uses_default_iso_when_present(self):
        iso = (
            self.root
            / "Metal Gear Acid (USA)"
            / "Metal Gear Acid (USA).iso"
        )
        iso.parent.mkdir()
        iso.write_bytes(b"synthetic")

        resolved = install.resolve_iso_path(
            None,
            root=self.root,
            input_fn=lambda prompt: self.fail(prompt),
        )

        self.assertEqual(resolved, iso.resolve())

    def test_prompt_accepts_dragged_quoted_path(self):
        iso = self.root / "disc image.iso"
        iso.write_bytes(b"synthetic")

        resolved = install.resolve_iso_path(
            None,
            root=self.root,
            input_fn=lambda prompt: f'"{iso}"',
        )

        self.assertEqual(resolved, iso.resolve())

    def test_persists_iso_path_for_launcher(self):
        iso = self.root / "disc.iso"
        iso.write_bytes(b"synthetic")

        destination = install.persist_iso_path(self.root, iso.resolve())

        self.assertEqual(
            destination.read_text(encoding="utf-8").strip(),
            str(iso.resolve()),
        )

    def test_project_runtime_pin_is_complete(self):
        runtime = install.load_runtime_config(ROOT)

        self.assertEqual(runtime.branch, "main")
        self.assertRegex(runtime.commit, r"^[0-9a-f]{40}$")
        self.assertTrue(runtime.repository.endswith("/psp-recomp.git"))

    def test_archive_checkout_clones_configured_runtime(self):
        runtime = install.RuntimeConfig(
            "https://example.invalid/runtime.git",
            "tested",
            "1" * 40,
        )
        target = self.root / "external" / "psp-recomp"
        runner = FakeRunner(target, runtime.commit)

        install.ensure_runtime(
            self.root,
            runtime,
            "git",
            runner,
            {"PATH": ""},
        )

        self.assertEqual(runner.commands[0][1:5], [
            "clone",
            "--branch",
            "tested",
            "--single-branch",
        ])
        self.assertIn(runtime.commit, runner.commands[1])
        self.assertTrue((target / "tools" / "codegen.py").is_file())

    def test_finds_vcvars_from_visual_studio_environment(self):
        vcvars = (
            self.root
            / "Visual Studio"
            / "VC"
            / "Auxiliary"
            / "Build"
            / "vcvars64.bat"
        )
        vcvars.parent.mkdir(parents=True)
        vcvars.write_text("", encoding="ascii")

        found = install.find_vcvars64(
            {"VSINSTALLDIR": str(self.root / "Visual Studio")}
        )

        self.assertEqual(found, vcvars.resolve())

    def test_finds_vcvars_with_upper_case_environment(self):
        # dict(os.environ) on Windows holds PROGRAMFILES, not ProgramFiles.
        vcvars = (
            self.root
            / "Microsoft Visual Studio"
            / "2022"
            / "BuildTools"
            / "VC"
            / "Auxiliary"
            / "Build"
            / "vcvars64.bat"
        )
        vcvars.parent.mkdir(parents=True)
        vcvars.write_text("", encoding="ascii")

        found = install.find_vcvars64({"PROGRAMFILES": str(self.root)})

        self.assertEqual(found, vcvars.resolve())

    def test_creates_combined_renderer_cmake_commands(self):
        sdl3 = self.root / "SDL3" / "cmake"
        configure, build = install.cmake_commands(
            "combined",
            "cmake.exe",
            sdl3,
        )

        self.assertEqual(configure[:3], [
            "cmake.exe",
            "--preset",
            "clang-cl",
        ])
        self.assertEqual(configure[3], f"-DSDL3_DIR={sdl3}")
        self.assertEqual(build[2:5], [
            "--preset",
            "clang-cl",
            "--target",
        ])

    def test_uses_pinned_sdl3_when_no_override_is_supplied(self):
        self.assertIsNone(install.resolve_sdl3_dir("combined", None, {}))

    def test_renderer_is_chosen_at_setup_when_not_given(self):
        args = install.parse_args(["disc.iso"])

        self.assertIsNone(args.renderer)
        self.assertEqual(
            install.parse_args(["disc.iso", "--renderer", "combined"]).renderer,
            "combined",
        )

    def test_software_only_alias_selects_software_preset(self):
        args = install.parse_args(["disc.iso", "--software-only"])

        self.assertEqual(args.renderer, "software")

    def test_accepts_vulkan_sdk_with_required_x64_files(self):
        sdk = self.root / "VulkanSDK"
        header = sdk / "Include" / "vulkan" / "vulkan.h"
        library = sdk / "Lib" / "vulkan-1.lib"
        header.parent.mkdir(parents=True)
        library.parent.mkdir(parents=True)
        header.write_text("", encoding="ascii")
        library.write_bytes(b"synthetic")

        install.validate_renderer_environment(
            "combined",
            {"VULKAN_SDK": str(sdk)},
        )

    def test_rejects_unparseable_cmake_version(self):
        with self.assertRaisesRegex(
            install.InstallError,
            "Could not parse",
        ):
            install.parse_cmake_version("not cmake")

    def test_executes_complete_software_install_flow(self):
        config = self.root / "config" / "mga.toml"
        config.parent.mkdir()
        config.write_text(
            "\n".join(
                [
                    "[runtime]",
                    'repository = "https://example.invalid/runtime.git"',
                    'branch = "tested"',
                    f'commit = "{"2" * 40}"',
                    "",
                ]
            ),
            encoding="ascii",
        )
        iso = self.root / "disc.iso"
        iso.write_bytes(b"synthetic")
        executable = (
            self.root
            / "out"
            / "build"
            / "clang-cl-software"
            / "mga.exe"
        )
        runner = FakeRunner(
            self.root / "external" / "psp-recomp",
            "2" * 40,
            executable,
        )
        args = argparse.Namespace(
            iso=iso,
            renderer="software",
            sdl3_dir=None,
            vcvars=None,
            no_build=False,
        )
        tools = {"cmake": "cmake.exe"}

        with (
            mock.patch.object(install, "find_command", return_value="git"),
            mock.patch.object(
                install,
                "prepare_build_tools",
                return_value=({}, tools),
            ),
        ):
            result = install.execute_install(
                args,
                root=self.root,
                runner=runner,
                env={},
            )

        self.assertEqual(result, 0)
        self.assertTrue(executable.is_file())
        self.assertEqual(
            (self.root / "config" / "mga_iso_path.txt")
            .read_text(encoding="utf-8")
            .strip(),
            str(iso.resolve()),
        )
        flattened = [" ".join(command) for command in runner.commands]
        self.assertTrue(any("extract.py" in command for command in flattened))
        self.assertTrue(any("gen.py" in command for command in flattened))
        self.assertTrue(any("--build" in command for command in flattened))

    def test_prepare_requires_iso_without_prompting(self):
        config = self.root / "config" / "mga.toml"
        config.parent.mkdir()
        config.write_text(
            "\n".join(
                [
                    "[runtime]",
                    'repository = "https://example.invalid/runtime.git"',
                    'branch = "tested"',
                    f'commit = "{"2" * 40}"',
                    "",
                ]
            ),
            encoding="ascii",
        )
        args = install.parse_args(["--prepare"])

        with self.assertRaisesRegex(install.InstallError, "--prepare needs"):
            install.execute_install(
                args,
                root=self.root,
                runner=FakeRunner(self.root, "2" * 40),
                env={},
                input_fn=lambda prompt: self.fail(prompt),
            )

    def test_prepare_reports_progress_with_bundled_runtime(self):
        config = self.root / "config" / "mga.toml"
        config.parent.mkdir()
        config.write_text(
            "\n".join(
                [
                    "[runtime]",
                    'repository = "https://example.invalid/runtime.git"',
                    'branch = "tested"',
                    f'commit = "{"2" * 40}"',
                    "",
                ]
            ),
            encoding="ascii",
        )
        codegen = self.root / "external" / "psp-recomp" / "tools" / "codegen.py"
        codegen.parent.mkdir(parents=True)
        codegen.write_text("", encoding="ascii")
        iso = self.root / "disc.iso"
        iso.write_bytes(b"synthetic")
        executable = self.root / "out" / "build" / "clang-cl-software" / "mga.exe"
        runner = FakeRunner(codegen.parents[1], "2" * 40, executable)
        args = install.parse_args(["--prepare", str(iso)])

        self.assertFalse(install.runtime_needs_git(self.root))
        with (
            mock.patch.object(
                install,
                "find_command",
                side_effect=AssertionError("git is not needed"),
            ),
            mock.patch.object(
                install,
                "prepare_build_tools",
                return_value=({}, {"cmake": "cmake.exe"}),
            ),
            mock.patch("builtins.print") as printed,
        ):
            result = install.execute_install(
                args,
                root=self.root,
                runner=runner,
                env={},
            )

        self.assertEqual(result, 0)
        lines = [
            call.args[0] for call in printed.call_args_list if call.args
        ]
        progress = [line for line in lines if line.startswith("progress ")]
        self.assertEqual(progress[0], "progress 0 Checking the build tools")
        self.assertEqual(progress[-1], "progress 1 Ready to play")
        self.assertFalse(any("git" in command[0] for command in runner.commands))

    def _write_config(self):
        config = self.root / "config" / "mga.toml"
        config.parent.mkdir(exist_ok=True)
        config.write_text(
            "\n".join(
                [
                    "[runtime]",
                    'repository = "https://example.invalid/runtime.git"',
                    'branch = "tested"',
                    f'commit = "{"2" * 40}"',
                    "",
                ]
            ),
            encoding="ascii",
        )
        codegen = self.root / "external" / "psp-recomp" / "tools" / "codegen.py"
        codegen.parent.mkdir(parents=True, exist_ok=True)
        codegen.write_text("", encoding="ascii")
        return codegen.parents[1]

    def _run(self, runner, *argv):
        args = install.parse_args(["--prepare", *argv])
        with (
            mock.patch.object(
                install,
                "prepare_build_tools",
                return_value=({}, {"cmake": "cmake.exe"}),
            ),
            mock.patch("builtins.print"),
        ):
            return install.execute_install(
                args, root=self.root, runner=runner, env={}
            )

    def test_second_run_skips_current_steps(self):
        runtime = self._write_config()
        iso = self.root / "disc.iso"
        iso.write_bytes(b"synthetic")
        executable = self.root / "out" / "build" / "clang-cl-software" / "mga.exe"
        image = self.root / install.GENERATED_IMAGE
        image.parent.mkdir(parents=True)
        image.write_bytes(b"image")

        first = FakeRunner(runtime, "2" * 40, executable)
        self.assertEqual(self._run(first, str(iso)), 0)
        self.assertTrue((self.root / install.STAMP).is_file())

        second = FakeRunner(runtime, "2" * 40, executable)
        self.assertEqual(self._run(second, str(iso)), 0)
        flattened = [" ".join(command) for command in second.commands]
        self.assertFalse(any("extract.py" in c for c in flattened))
        self.assertFalse(any("gen.py" in c for c in flattened))
        self.assertFalse(any("--build" in c for c in flattened))

        # A changed generator invalidates generation and the build.
        tool = self.root / "tools" / "mga" / "gen.py"
        tool.parent.mkdir(parents=True)
        tool.write_text("# changed\n", encoding="ascii")
        third = FakeRunner(runtime, "2" * 40, executable)
        self.assertEqual(self._run(third, str(iso)), 0)
        flattened = [" ".join(command) for command in third.commands]
        self.assertTrue(any("gen.py" in c for c in flattened))
        self.assertTrue(any("--build" in c for c in flattened))

        forced = FakeRunner(runtime, "2" * 40, executable)
        self.assertEqual(self._run(forced, str(iso), "--force"), 0)
        flattened = [" ".join(command) for command in forced.commands]
        self.assertTrue(any("extract.py" in c for c in flattened))

    def test_converts_cso_before_extraction(self):
        sys.path.insert(0, str(ROOT / "tools" / "tests"))
        import test_mga_discimage

        runtime = self._write_config()
        data = test_mga_discimage.sample_image(8)
        cso = self.root / "disc.cso"
        test_mga_discimage.write_cso(cso, data)
        executable = self.root / "out" / "build" / "clang-cl-software" / "mga.exe"
        runner = FakeRunner(runtime, "2" * 40, executable)

        self.assertEqual(self._run(runner, str(cso)), 0)

        converted = self.root / install.CONVERTED_ISO
        self.assertEqual(converted.read_bytes(), data)
        extract = next(c for c in runner.commands if "extract.py" in " ".join(c))
        self.assertEqual(extract[-1], str(converted))
        self.assertEqual(
            (self.root / "config" / "mga_iso_path.txt")
            .read_text(encoding="utf-8").strip(),
            str(converted),
        )

    def test_renderer_choice(self):
        args = install.parse_args(["disc.iso"])
        self.assertEqual(
            install.choose_renderer(args, False, lambda prompt: ""),
            ("d3d12", True),
        )
        self.assertEqual(
            install.choose_renderer(args, False, lambda prompt: "n"),
            ("software", False),
        )
        self.assertEqual(
            install.choose_renderer(args, True, lambda prompt: self.fail()),
            ("software", False),
        )
        launcher = install.parse_args(
            ["--prepare", "disc.iso", "--renderer", "d3d12", "--download-sdl3"]
        )
        self.assertEqual(
            install.choose_renderer(launcher, True, lambda prompt: self.fail()),
            ("d3d12", True),
        )

    def test_sdl3_download_checks_hash_and_paths(self):
        prefix = f"SDL3-{install.SDL3_VERSION}/"

        def fake_download(members):
            def download(url, destination):
                destination.parent.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(destination, "w") as bundle:
                    for name in members:
                        bundle.writestr(name, "x")
                return hashlib.sha256(destination.read_bytes()).hexdigest()
            return download

        tampered = fake_download([prefix + "cmake/SDL3Config.cmake"])
        with mock.patch.object(install, "download_file", tampered):
            with self.assertRaisesRegex(install.InstallError, "SHA-256"):
                install.ensure_sdl3(self.root)

        # Pin the hash of whatever the fake serves, to reach the path checks.
        def matching(members):
            inner = fake_download(members)

            def download(url, destination):
                digest = inner(url, destination)
                install.SDL3_SHA256 = digest
                return digest
            return download

        original = install.SDL3_SHA256
        self.addCleanup(setattr, install, "SDL3_SHA256", original)
        with mock.patch.object(
            install, "download_file", matching(["../evil.txt"])
        ):
            with self.assertRaisesRegex(install.InstallError, "Unexpected"):
                install.ensure_sdl3(self.root)
        with mock.patch.object(
            install,
            "download_file",
            matching([prefix + "cmake/SDL3Config.cmake"]),
        ):
            cmake_dir = install.ensure_sdl3(self.root)
        self.assertTrue((cmake_dir / "SDL3Config.cmake").is_file())


if __name__ == "__main__":
    unittest.main()
