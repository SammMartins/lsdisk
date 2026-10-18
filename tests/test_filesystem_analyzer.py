"""Tests for filesystem classification and grouping."""

import unittest

from lsdisk.analyzers.filesystems import (
    classify_filesystem,
    group_filesystems,
)
from lsdisk.models import FilesystemUsage


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

    def test_classifies_tmpfs_as_temporary(self):
        filesystem = make_filesystem(
            "/run",
            filesystem_type="tmpfs",
            source="tmpfs",
            device_id="0:26",
        )
        self.assertEqual(classify_filesystem(filesystem), "temporary")

    def test_classifies_ramfs_as_temporary(self):
        filesystem = make_filesystem(
            "/run/ramfs",
            filesystem_type="ramfs",
            source="ramfs",
            device_id="0:27",
        )
        self.assertEqual(classify_filesystem(filesystem), "temporary")

    def test_classifies_dwarfs_as_application_image(self):
        filesystem = make_filesystem(
            "/opt/example",
            filesystem_type="fuse.dwarfs",
            source="/opt/example.dwarfs",
            device_id="0:91",
            total_bytes=100,
            free_bytes=0,
            available_bytes=0,
        )
        self.assertEqual(
            classify_filesystem(filesystem),
            "application_image",
        )

    def test_classifies_kernel_filesystems_as_virtual(self):
        for filesystem_type in (
            "proc",
            "sysfs",
            "cgroup2",
            "debugfs",
            "tracefs",
            "binfmt_misc",
        ):
            filesystem = make_filesystem(
                f"/{filesystem_type}",
                filesystem_type=filesystem_type,
                source=filesystem_type,
                device_id="0:1",
            )
            with self.subTest(filesystem_type=filesystem_type):
                self.assertEqual(
                    classify_filesystem(filesystem),
                    "virtual",
                )

    def test_classifies_container_overlay_as_virtual(self):
        filesystem = make_filesystem(
            "/var/lib/containers/storage/overlay",
            filesystem_type="overlay",
            source="overlay",
            device_id="0:42",
        )
        self.assertEqual(classify_filesystem(filesystem), "virtual")

    def test_keeps_desktop_fuse_filesystems_conservatively_unknown(self):
        for filesystem_type in ("fuse.gvfsd-fuse", "fuse.portal"):
            filesystem = make_filesystem(
                "/run/user/1000/mount",
                filesystem_type=filesystem_type,
                source=filesystem_type,
                device_id="0:43",
            )
            with self.subTest(filesystem_type=filesystem_type):
                self.assertEqual(
                    classify_filesystem(filesystem),
                    "unknown",
                )

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

    def test_groups_verified_device_aliases_without_duplicate_capacity(self):
        filesystems = [
            make_filesystem(
                "/data",
                source="/dev/sda1",
                device_id="8:1",
            ),
            make_filesystem(
                "/data-alias",
                source="/dev/disk/by-id/test",
                device_id="8:1",
                filesystem_root="/@alias",
            ),
        ]
        groups = group_filesystems(filesystems)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].mountpoints, ["/data", "/data-alias"])

    def test_keeps_same_device_id_different_filesystem_types_separate(self):
        filesystems = [
            make_filesystem("/one", filesystem_type="ext4", device_id="8:1"),
            make_filesystem("/two", filesystem_type="xfs", device_id="8:1"),
        ]
        self.assertEqual(len(group_filesystems(filesystems)), 2)


if __name__ == "__main__":
    unittest.main()
