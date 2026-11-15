"""Integration tests for the per-user shell installer."""

import hashlib
import io
import json
import os
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = PROJECT_ROOT / "install.sh"
UNINSTALLER = PROJECT_ROOT / "uninstall.sh"


class TestInstallerReplacement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary_directory = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary_directory.name)
        cls.artifact_directory = cls.root / "artifacts"
        cls.artifact_directory.mkdir()
        subprocess.run(
            [
                str(PROJECT_ROOT / ".venv" / "bin" / "python"),
                "-m",
                "build",
                "--sdist",
                "--no-isolation",
                "--outdir",
                str(cls.artifact_directory),
            ],
            cwd=PROJECT_ROOT,
            check=True,
            stdout=subprocess.DEVNULL,
        )
        cls.archive = next(cls.artifact_directory.glob("lsdisk-*.tar.gz"))
        cls.curl_directory = cls.root / "bin"
        cls.curl_directory.mkdir()
        digest = hashlib.sha256(cls.archive.read_bytes()).hexdigest()
        metadata = {
            "info": {"version": "0.1.3"},
            "urls": [
                {
                    "packagetype": "sdist",
                    "filename": cls.archive.name,
                    "url": f"https://files.pythonhosted.org/packages/{cls.archive.name}",
                    "digests": {"sha256": digest},
                }
            ],
        }
        (cls.root / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
        (cls.curl_directory / "curl").write_text(
            """#!/usr/bin/env bash
set -Eeuo pipefail
output=""
for ((index = 1; index <= $#; index++)); do
    if [[ "${!index}" == "--output" ]]; then
        next=$((index + 1))
        output="${!next}"
    fi
done
if [[ "$output" == *.json ]]; then
    cp "$LSDISK_TEST_METADATA" "$output"
else
    cp "$LSDISK_TEST_ARCHIVE" "$output"
fi
""",
            encoding="utf-8",
        )
        (cls.curl_directory / "curl").chmod(0o755)

    @classmethod
    def tearDownClass(cls):
        cls.temporary_directory.cleanup()

    def setUp(self):
        self.home = self.root / "home"
        self.data_home = self.home / "data"
        self.bin_home = self.home / "bin"
        self.environment = {
            **os.environ,
            "HOME": str(self.home),
            "XDG_DATA_HOME": str(self.data_home),
            "XDG_BIN_HOME": str(self.bin_home),
            "LSDISK_TEST_METADATA": str(self.root / "metadata.json"),
            "LSDISK_TEST_ARCHIVE": str(self.archive),
            "PATH": f"{self.curl_directory}:{os.environ['PATH']}",
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        }

    def run_installer(self, **overrides):
        environment = {**self.environment, **overrides}
        return subprocess.run(
            ["bash", str(INSTALLER)],
            cwd=PROJECT_ROOT,
            env=environment,
            capture_output=True,
            text=True,
        )

    def write_metadata(self, metadata, *, name="metadata-case.json"):
        path = self.root / name
        path.write_text(json.dumps(metadata), encoding="utf-8")
        return path

    def run_metadata_case(self, metadata):
        metadata_path = self.write_metadata(metadata)
        result = self.run_installer(
            LSDISK_TEST_METADATA=str(metadata_path),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "The requested lsdisk version or source artifact is unavailable.",
            result.stderr,
        )
        self.assertNotIn("Traceback", result.stderr)
        self.assertFalse((self.data_home / "lsdisk").exists())
        self.assertFalse((self.bin_home / "lsdisk").exists())

    def make_archive(self, member_type, member_name, *, linkname=None):
        archive_path = self.root / f"{member_type}-{member_name.replace('/', '_')}.tar.gz"
        with tarfile.open(archive_path, "w:gz") as archive:
            member = tarfile.TarInfo(member_name)
            member.type = member_type
            member.mode = 0o644
            if member_type == tarfile.REGTYPE:
                content = b"unsafe"
                member.size = len(content)
                archive.addfile(member, io.BytesIO(content))
            else:
                member.linkname = linkname or ""
                archive.addfile(member)
        return archive_path

    def make_members_archive(self, members, *, name="members.tar.gz"):
        archive_path = self.root / name
        with tarfile.open(archive_path, "w:gz") as archive:
            for member_type, member_name, linkname in members:
                member = tarfile.TarInfo(member_name)
                member.type = member_type
                member.mode = 0o644
                if member_type == tarfile.REGTYPE:
                    content = b"unsafe"
                    member.size = len(content)
                    archive.addfile(member, io.BytesIO(content))
                else:
                    member.linkname = linkname or ""
                    archive.addfile(member)
        return archive_path

    def run_archive_case(self, archive_path):
        digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
        metadata = {
            "info": {"version": "0.1.3"},
            "urls": [
                {
                    "packagetype": "sdist",
                    "filename": "lsdisk-0.1.3.tar.gz",
                    "url": "https://files.pythonhosted.org/packages/test.tar.gz",
                    "digests": {"sha256": digest},
                }
            ],
        }
        metadata_path = self.write_metadata(
            metadata,
            name=f"{archive_path.name}.json",
        )
        result = self.run_installer(
            LSDISK_TEST_METADATA=str(metadata_path),
            LSDISK_TEST_ARCHIVE=str(archive_path),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "The source archive contains unsafe or unsupported members.",
            result.stderr,
        )
        self.assertNotIn("Traceback", result.stderr)
        self.assertFalse((self.data_home / "lsdisk").exists())
        self.assertFalse((self.bin_home / "lsdisk").exists())

    def test_valid_source_archive_extraction_and_rollbacks_restore_previous_files(self):
        first = self.run_installer()
        self.assertEqual(first.returncode, 0, first.stderr)

        install_dir = self.data_home / "lsdisk"
        launcher = self.bin_home / "lsdisk"
        self.assertTrue((install_dir / "venv" / "bin" / "lsdisk").exists())
        self.assertIn("exec", launcher.read_text(encoding="utf-8"))

        old_marker = install_dir / "old-marker"
        old_marker.write_text("old", encoding="utf-8")
        old_launcher = launcher.read_text(encoding="utf-8")

        failed_app = self.run_installer(LSDISK_TEST_FAIL_AFTER_INSTALL_REPLACEMENT="1")
        self.assertNotEqual(failed_app.returncode, 0)
        self.assertEqual(old_marker.read_text(encoding="utf-8"), "old")
        self.assertEqual(launcher.read_text(encoding="utf-8"), old_launcher)

        failed_launcher = self.run_installer(
            LSDISK_TEST_FAIL_DURING_LAUNCHER_REPLACEMENT="1"
        )
        self.assertNotEqual(failed_launcher.returncode, 0)
        self.assertEqual(old_marker.read_text(encoding="utf-8"), "old")
        self.assertEqual(launcher.read_text(encoding="utf-8"), old_launcher)

        upgraded = self.run_installer()
        self.assertEqual(upgraded.returncode, 0, upgraded.stderr)
        self.assertFalse(old_marker.exists())

        uninstalled = subprocess.run(
            ["bash", str(UNINSTALLER)],
            cwd=PROJECT_ROOT,
            env=self.environment,
            capture_output=True,
            text=True,
        )
        self.assertEqual(uninstalled.returncode, 0, uninstalled.stderr)
        self.assertFalse(install_dir.exists())
        self.assertFalse(launcher.exists())

    def test_rejects_malformed_pypi_metadata_without_tracebacks(self):
        cases = [
            None,
            {},
            {"info": None},
            {"info": {"version": "0.1.3"}},
            {"info": {"version": "0.1.3"}, "urls": None},
            {"info": {"version": "0.1.3"}, "urls": [None]},
            {
                "info": {"version": "0.1.3"},
                "urls": [{"packagetype": 1}],
            },
            {
                "info": {"version": "0.1.3"},
                "urls": [{"packagetype": "sdist"}],
            },
            {
                "info": {"version": "0.1.3"},
                "urls": [{
                    "packagetype": "sdist",
                    "filename": "lsdisk-0.1.1.tar.gz",
                }],
            },
            {
                "info": {"version": "0.1.3"},
                "urls": [{
                    "packagetype": "sdist",
                    "filename": "lsdisk-0.1.3.tar.gz",
                    "url": "https://files.pythonhosted.org/packages/test.tar.gz",
                    "digests": {},
                }],
            },
            {
                "info": {"version": "0.1.3"},
                "urls": [{
                    "packagetype": "sdist",
                    "filename": "lsdisk-0.1.3.tar.gz",
                    "url": "https://files.pythonhosted.org/packages/test.tar.gz",
                    "digests": {"sha256": "G" * 64},
                }],
            },
            {
                "info": {"version": "0.1.3"},
                "urls": [{
                    "packagetype": "sdist",
                    "filename": "lsdisk-0.1.3.tar.gz",
                    "url": "http://files.pythonhosted.org/packages/test.tar.gz",
                    "digests": {"sha256": "a" * 64},
                }],
            },
            {
                "info": {"version": "0.1.3"},
                "urls": [{
                    "packagetype": "sdist",
                    "filename": "lsdisk-0.1.3.tar.gz",
                    "url": "https://example.com/lsdisk.tar.gz",
                    "digests": {"sha256": "a" * 64},
                }],
            },
            {
                "info": {"version": "0.1.3"},
                "urls": [
                    {
                        "packagetype": "sdist",
                        "filename": "lsdisk-0.1.3.tar.gz",
                        "url": "https://files.pythonhosted.org/packages/test.tar.gz",
                        "digests": {"sha256": "a" * 64},
                    },
                    {
                        "packagetype": "sdist",
                        "filename": "lsdisk-0.1.3.tar.gz",
                        "url": "https://files.pythonhosted.org/packages/test2.tar.gz",
                        "digests": {"sha256": "b" * 64},
                    },
                ],
            },
        ]
        for case in cases:
            with self.subTest(metadata=case):
                self.run_metadata_case(case)

    def test_rejects_unsafe_archive_members_before_extraction(self):
        cases = [
            (tarfile.REGTYPE, "../escape"),
            (tarfile.REGTYPE, "/absolute"),
            (tarfile.SYMTYPE, "root/link"),
            (tarfile.LNKTYPE, "root/hardlink"),
            (tarfile.FIFOTYPE, "root/fifo"),
        ]
        for member_type, member_name in cases:
            with self.subTest(member_type=member_type, member_name=member_name):
                self.run_archive_case(
                    self.make_archive(member_type, member_name, linkname="root/file")
                )

    def test_rejects_archive_member_collisions_before_extraction(self):
        cases = [
            [
                (tarfile.REGTYPE, "root/file", None),
                (tarfile.REGTYPE, "root/file", None),
            ],
            [
                (tarfile.DIRTYPE, "root/item", None),
                (tarfile.REGTYPE, "root/item", None),
            ],
            [
                (tarfile.REGTYPE, "root", None),
                (tarfile.REGTYPE, "root/file", None),
            ],
            [
                (tarfile.REGTYPE, "root/./file", None),
                (tarfile.REGTYPE, "root/file", None),
            ],
        ]
        for index, members in enumerate(cases):
            with self.subTest(members=members):
                self.run_archive_case(
                    self.make_members_archive(members, name=f"collision-{index}.tar.gz")
                )

    def test_installer_and_uninstaller_have_valid_shell_syntax(self):
        for script in (INSTALLER, UNINSTALLER):
            with self.subTest(script=script.name):
                subprocess.run(["bash", "-n", str(script)], check=True)


if __name__ == "__main__":
    unittest.main()
