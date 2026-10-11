"""Tests for the mounted-filesystem collector."""

import tempfile
import unittest
from pathlib import Path

from lsdisk.collectors.filesystems import (
    _parse_mountinfo_line,
    _unescape_mountinfo,
    collect_filesystems,
)


class TestMountInfoParsing(unittest.TestCase):
    def test_unescapes_spaces_and_backslashes(self):
        self.assertEqual(
            _unescape_mountinfo(r"/mnt/my\040disk"),
            "/mnt/my disk",
        )
        self.assertEqual(
            _unescape_mountinfo(r"/path\134name"),
            "/path\\name",
        )

    def test_parses_mountinfo_fields(self):
        line = (
            r"32 2 8:6 /@ /mnt/my\040disk "
            r"rw,relatime - btrfs /dev/sda6 rw,subvol=/@"
        )

        result = _parse_mountinfo_line(line)

        self.assertIsNotNone(result)
        self.assertEqual(result["device_id"], "8:6")
        self.assertEqual(result["filesystem_root"], "/@")
        self.assertEqual(result["mountpoint"], "/mnt/my disk")
        self.assertEqual(result["filesystem_type"], "btrfs")
        self.assertEqual(result["source"], "/dev/sda6")

    def test_rejects_malformed_line(self):
        self.assertIsNone(_parse_mountinfo_line("invalid mount record"))


class TestFilesystemCollector(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)

    def test_collects_capacity_for_mounted_path(self):
        mountpoint = self.root / "mounted"
        mountpoint.mkdir()

        mountinfo = self.root / "mountinfo"
        mountinfo.write_text(
            f"42 1 8:1 / {mountpoint} rw,relatime "
            "- ext4 /dev/test rw\n",
            encoding="utf-8",
        )

        result = collect_filesystems(mountinfo)

        self.assertEqual(len(result), 1)
        usage = result[0]
        self.assertEqual(usage.mountpoint, str(mountpoint))
        self.assertEqual(usage.source, "/dev/test")
        self.assertEqual(usage.filesystem_type, "ext4")
        self.assertEqual(usage.device_id, "8:1")
        self.assertGreater(usage.total_bytes, 0)
        self.assertGreaterEqual(usage.free_bytes, usage.available_bytes)
        self.assertGreaterEqual(usage.used_bytes, 0)

    def test_skips_mountpoint_that_is_no_longer_accessible(self):
        mountinfo = self.root / "mountinfo"
        missing_mountpoint = self.root / "missing"

        mountinfo.write_text(
            f"42 1 8:1 / {missing_mountpoint} rw,relatime "
            "- ext4 /dev/test rw\n",
            encoding="utf-8",
        )

        self.assertEqual(collect_filesystems(mountinfo), [])

    def test_returns_empty_list_when_mountinfo_is_missing(self):
        self.assertEqual(
            collect_filesystems(self.root / "missing-mountinfo"),
            [],
        )


if __name__ == "__main__":
    unittest.main()
