"""Tests for lsdisk data models."""

import unittest

from lsdisk.models import BlockDevice, FilesystemUsage


class TestBlockDevice(unittest.TestCase):
    def test_identifies_physical_disk(self):
        device = BlockDevice(
            name="sda",
            path="/dev/sda",
            device_type="disk",
            size_bytes=240_000_000_000,
            physical=True,
        )
        self.assertTrue(device.is_physical_disk)

    def test_unclassified_disk_is_not_assumed_physical(self):
        for name in ("loop0", "dm-0", "md0", "zram0"):
            with self.subTest(name=name):
                device = BlockDevice(
                    name=name,
                    path=f"/dev/{name}",
                    device_type="disk",
                    size_bytes=1_000_000,
                )
                self.assertFalse(device.is_physical_disk)

    def test_zram_is_not_a_physical_disk(self):
        device = BlockDevice(
            name="zram0",
            path="/dev/zram0",
            device_type="disk",
            size_bytes=8_000_000_000,
        )
        self.assertFalse(device.is_physical_disk)

    def test_identifies_partition(self):
        device = BlockDevice(
            name="sda1",
            path="/dev/sda1",
            device_type="part",
            size_bytes=100_000_000_000,
            parent_name="sda",
        )
        self.assertTrue(device.is_partition)

    def test_rejects_negative_device_size(self):
        with self.assertRaises(ValueError):
            BlockDevice(
                name="sda",
                path="/dev/sda",
                device_type="disk",
                size_bytes=-1,
            )


class TestFilesystemUsage(unittest.TestCase):
    def test_calculates_used_space(self):
        filesystem = FilesystemUsage(
            mountpoint="/",
            source="/dev/sda6",
            filesystem_type="btrfs",
            total_bytes=1000,
            free_bytes=250,
            available_bytes=200,
        )
        self.assertEqual(filesystem.used_bytes, 750)
        self.assertEqual(filesystem.used_percent, 75.0)

    def test_rejects_available_space_above_free_space(self):
        with self.assertRaises(ValueError):
            FilesystemUsage(
                mountpoint="/",
                source="/dev/sda6",
                filesystem_type="btrfs",
                total_bytes=1000,
                free_bytes=200,
                available_bytes=300,
            )


if __name__ == "__main__":
    unittest.main()
