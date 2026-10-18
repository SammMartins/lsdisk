"""Tests for the architecture-independent Debian package."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = PROJECT_ROOT / "packaging" / "deb" / "build-deb.sh"


class TestDebPackage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if shutil.which("dpkg-deb") is None:
            raise unittest.SkipTest("dpkg-deb is not installed")
        subprocess.run(["bash", "-n", str(BUILD_SCRIPT)], check=True)

        version_output = subprocess.check_output(
            ["python3", "-c", "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])"],
            cwd=PROJECT_ROOT,
            text=True,
        ).strip()
        cls.version = version_output
        cls.temporary_directory = tempfile.TemporaryDirectory()
        cls.output_dir = Path(cls.temporary_directory.name) / "dist"
        cls.build_dir = Path(cls.temporary_directory.name) / "build"
        cls.package = cls.output_dir / f"lsdisk_{cls.version}_all.deb"
        cls.build_environment = {
            **os.environ,
            "BUILD_ROOT": str(cls.build_dir),
            "OUTPUT_DIR": str(cls.output_dir),
        }
        subprocess.run(
            ["bash", str(BUILD_SCRIPT)],
            cwd=PROJECT_ROOT,
            env=cls.build_environment,
            check=True,
        )

    @classmethod
    def tearDownClass(cls):
        cls.temporary_directory.cleanup()

    def run_build(self, *, release_tag=None):
        environment = dict(self.build_environment)
        if release_tag is None:
            environment.pop("RELEASE_TAG", None)
        else:
            environment["RELEASE_TAG"] = release_tag
        return subprocess.run(
            ["bash", str(BUILD_SCRIPT)],
            cwd=PROJECT_ROOT,
            env=environment,
            capture_output=True,
            text=True,
        )

    def test_local_build_without_release_tag_succeeds(self):
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_matching_release_tags_are_accepted(self):
        for tag in (self.version, f"v{self.version}"):
            with self.subTest(tag=tag):
                result = self.run_build(release_tag=tag)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_mismatched_release_tag_is_rejected(self):
        result = self.run_build(release_tag=f"v{self.version}.1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("release tag and project version do not match", result.stderr)

    def test_metadata_is_consistent(self):
        fields = subprocess.check_output(
            ["dpkg-deb", "--field", str(self.package), "Package", "Version", "Architecture", "Depends"],
            text=True,
        ).splitlines()
        fields = [field.split(": ", 1)[1] for field in fields]
        self.assertEqual(fields[0], "lsdisk")
        self.assertEqual(fields[1], self.version)
        self.assertEqual(fields[2], "all")
        self.assertIn("python3 (>= 3.11)", fields[3])
        self.assertIn("python3-rich (>= 13.0)", fields[3])
        maintainer = subprocess.check_output(
            ["dpkg-deb", "--field", str(self.package), "Maintainer"],
            text=True,
        ).strip()
        self.assertEqual(maintainer, "SammMartins <sammartins@users.noreply.github.com>")

    def test_contents_have_no_bytecode_and_include_executable(self):
        contents = subprocess.check_output(
            ["dpkg-deb", "--contents", str(self.package)],
            text=True,
        )
        self.assertIn("./usr/bin/lsdisk", contents)
        for source_file in (
            "main.py",
            "inventory.py",
            "models.py",
            "serialization.py",
            "collectors/block_devices.py",
            "collectors/filesystems.py",
            "analyzers/capacity.py",
            "analyzers/filesystems.py",
            "ui/terminal.py",
        ):
            self.assertIn(f"./usr/lib/lsdisk/lsdisk/{source_file}", contents)
        self.assertNotIn("__pycache__", contents)
        self.assertNotIn(".pyc", contents)
        self.assertIn("./usr/lib/lsdisk/pyproject.toml", contents)
        self.assertNotIn("_version.py", contents)

    def test_extracted_cli_reports_version_and_help(self):
        system_python = Path("/usr/bin/python3")
        if not system_python.exists():
            self.skipTest("/usr/bin/python3 is not installed")
        rich_check = subprocess.run(
            [str(system_python), "-c", "import rich"],
            capture_output=True,
        )
        if rich_check.returncode != 0:
            self.skipTest("python3-rich is not installed for the packaged interpreter")
        with tempfile.TemporaryDirectory() as temporary_directory:
            extracted = Path(temporary_directory)
            subprocess.run(
                ["dpkg-deb", "--extract", str(self.package), str(extracted)],
                check=True,
            )
            executable = extracted / "usr/bin/lsdisk"
            self.assertTrue(executable.stat().st_mode & 0o111)


            version_result = subprocess.run(
                [str(executable), "--version"],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                version_result.returncode,
                0,
                msg=(
                    f"stdout:\n{version_result.stdout}\n"
                    f"stderr:\n{version_result.stderr}"
                ),
            )
            self.assertEqual(
                version_result.stdout.strip(),
                f"lsdisk {self.version}",
            )


            help_result = subprocess.run(
                [str(executable), "--help"],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn("usage: lsdisk", help_result.stdout)
            self.assertIn("--version", help_result.stdout)


if __name__ == "__main__":
    unittest.main()
