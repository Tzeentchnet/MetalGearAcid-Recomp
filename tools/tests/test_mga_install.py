import argparse
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock


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

        self.assertEqual(runtime.branch, "kzl")
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

    def test_creates_renderer_specific_cmake_commands(self):
        sdl3 = self.root / "SDL3" / "cmake"
        configure, build = install.cmake_commands(
            "d3d12",
            "cmake.exe",
            sdl3,
        )

        self.assertEqual(configure[:3], [
            "cmake.exe",
            "--preset",
            "clang-cl-d3d12",
        ])
        self.assertEqual(configure[3], f"-DSDL3_DIR={sdl3}")
        self.assertEqual(build[2:5], [
            "--preset",
            "clang-cl-d3d12",
            "--target",
        ])

    def test_requires_sdl3_for_hardware_renderer(self):
        with self.assertRaisesRegex(
            install.InstallError,
            "requires an SDL3 development package",
        ):
            install.resolve_sdl3_dir("d3d12", None, {})

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
        executable = self.root / "out" / "build" / "clang-cl" / "mga.exe"
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


if __name__ == "__main__":
    unittest.main()
