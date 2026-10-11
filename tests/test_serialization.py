"""Tests for inventory serialization."""

import unittest

from lsdisk.analyzers.filesystems import group_filesystems
from lsdisk.inventory import StorageInventory
from lsdisk.models import BlockDevice, FilesystemUsage
from lsdisk.serialization import inventory_to_dict


def make_inventory():
    disk = BlockDevice(
        name="sda",
        path="/dev/sda",
        device_type="disk",
        size_bytes=10_000,
        physical=True,
        model="Test SSD",
    )

    partition = BlockDevice(
        name="sda1",
        path="/dev/sda1",
        device_type="part",
        size_bytes=5_000,
        parent_name="sda",
        filesystem_type="btrfs",
        mountpoints=["/data"],
    )
    disk.children.append(partition)

    virtual_disk = BlockDevice(
        name="zram0",
        path="/dev/zram0",
        device_type="disk",
        size_bytes=2_000,
        physical=False,
    )

    btrfs_root = FilesystemUsage(
        mountpoint="/data",
        source="/dev/sda1",
        filesystem_type="btrfs",
        total_bytes=5_000,
        free_bytes=2_000,
        available_bytes=1_800,
        device_id="8:1",
        filesystem_root="/",
    )

    btrfs_subvolume = FilesystemUsage(
        mountpoint="/home",
        source="/dev/sda1",
        filesystem_type="btrfs",
        total_bytes=5_000,
        free_bytes=2_000,
        available_bytes=1_800,
        device_id="8:1",
        filesystem_root="/@home",
    )

    tmpfs = FilesystemUsage(
        mountpoint="/run",
        source="tmpfs",
        filesystem_type="tmpfs",
        total_bytes=2_000,
        free_bytes=1_000,
        available_bytes=900,
        device_id="0:26",
    )

    filesystems = [btrfs_root, btrfs_subvolume, tmpfs]

    return StorageInventory(
        devices=[disk, virtual_disk],
        filesystems=filesystems,
        filesystem_groups=group_filesystems(filesystems),
    )


class TestInventorySerialization(unittest.TestCase):
    def test_simple_mode_excludes_virtual_devices(self):
        data = inventory_to_dict(make_inventory())

        self.assertEqual(data["mode"], "simple")
        self.assertEqual(
            [device["name"] for device in data["devices"]],
            ["sda"],
        )

    def test_all_mode_includes_virtual_devices_and_mounts(self):
        data = inventory_to_dict(make_inventory(), include_all=True)

        self.assertEqual(data["mode"], "all")
        self.assertEqual(
            [device["name"] for device in data["devices"]],
            ["sda", "zram0"],
        )
        self.assertEqual(len(data["mounts"]), 3)

    def test_groups_btrfs_subvolumes_without_duplicate_capacity(self):
        data = inventory_to_dict(make_inventory(), include_all=True)

        btrfs_groups = [
            item
            for item in data["filesystems"]
            if item["filesystem_type"] == "btrfs"
        ]

        self.assertEqual(len(btrfs_groups), 1)
        self.assertEqual(
            btrfs_groups[0]["mountpoints"],
            ["/data", "/home"],
        )
        self.assertEqual(btrfs_groups[0]["used_bytes"], 3_000)

    def test_json_values_include_numeric_capacity(self):
        data = inventory_to_dict(make_inventory())

        filesystem = data["filesystems"][0]

        self.assertIsInstance(filesystem["total_bytes"], int)
        self.assertIsInstance(filesystem["used_percent"], float)
        self.assertEqual(data["schema_version"], 1)


if __name__ == "__main__":
    unittest.main()
