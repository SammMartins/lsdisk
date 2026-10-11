"""Tests for filesystem classification and grouping."""

import unittest

from storix.analyzers.filesystems import (
    classify_filesystem,
    group_filesystems,
)
from storix.models import FilesystemUsage


def make_filesystem(
    mountpoint,
    *,
    filesystem_type="btrfs",
    source="/dev/sda6",
    device_id="0:29",
    filesystem_root="/",
    total_bytes=1000,
    free_bytes=400,
    available_bytes=350,
):
    return FilesystemUsage(
        mountpoint=mountpoint,
        source=source,
        filesystem_type=filesystem_type,
        total_bytes=total_bytes,
        free_bytes=free_bytes,
        available_bytes=available_bytes,
        device_id=device_id,
        filesystem_root=filesystem_root,
    )


class TestFilesystemClassification(unittest.TestCase):
    def test_classifies_btrfs_as_persistent(self):
        self.assertEqual(
            classify_filesystem(make_filesystem("/")),
            "persistent",
        )

    def test_classifies_tmpfs_as_virtual(self):
        filesystem = make_filesystem(
            "/run",
            filesystem_type="tmpfs",
            source="tmpfs",
            device_id="0:26",
        )
        self.assertEqual(classify_filesystem(filesystem), "virtual")

    def test_classifies_network_filesystem(self):
        filesystem = make_filesystem(
            "/mnt/share",
            filesystem_type="nfs4",
            source="server:/share",
            device_id="0:90",
        )
        self.assertEqual(classify_filesystem(filesystem), "network")

    def test_preserves_unknown_filesystem_types(self):
        filesystem = make_filesystem(
            "/mnt/custom",
            filesystem_type="customfs",
        )
        self.assertEqual(classify_filesystem(filesystem), "unknown")


class TestFilesystemGrouping(unittest.TestCase):
    def test_groups_btrfs_subvolumes_without_double_counting(self):
        filesystems = [
            make_filesystem("/", filesystem_root="/@"),
            make_filesystem("/home", filesystem_root="/@home"),
            make_filesystem("/var/log", filesystem_root="/@log"),
        ]

        groups = group_filesystems(filesystems)

        self.assertEqual(len(groups), 1)
        self.assertEqual(
            groups[0].mountpoints,
            ["/", "/home", "/var/log"],
        )
        self.assertEqual(groups[0].total_bytes, 1000)
        self.assertEqual(groups[0].used_bytes, 600)

    def test_keeps_different_devices_separate(self):
        filesystems = [
            make_filesystem("/data", source="/dev/sda1", device_id="8:1"),
            make_filesystem(
                "/data-hdd",
                source="/dev/sdb1",
                device_id="8:17",
                total_bytes=2000,
                free_bytes=1500,
                available_bytes=1400,
            ),
        ]

        groups = group_filesystems(filesystems)

        self.assertEqual(len(groups), 2)


if __name__ == "__main__":
    unittest.main()
