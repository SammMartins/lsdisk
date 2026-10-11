"""Tests for the Linux block-device collector."""

import tempfile
import unittest
from pathlib import Path

from lsdisk.collectors.block_devices import collect_block_devices


class TestBlockDeviceCollector(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.root = Path(self.temp_dir.name)
        self.sysfs = self.root / "class" / "block"
        self.devices = self.root / "devices"
        self.sysfs.mkdir(parents=True)

    def create_device(
        self,
        name,
        size_sectors,
        *,
        parent=None,
        virtual=False,
        rotational="0",
        model="Test Device",
    ):
        if virtual:
            device_dir = self.devices / "virtual" / "block" / name
        elif parent:
            device_dir = (
                self.devices / "block" / parent / name
            )
        else:
            device_dir = self.devices / "block" / name

        device_dir.mkdir(parents=True)

        (device_dir / "size").write_text(str(size_sectors))

        if parent:
            (device_dir / "partition").write_text("1")
        else:
            queue = device_dir / "queue"
            queue.mkdir()
            (queue / "rotational").write_text(rotational)

            if not virtual:
                device = device_dir / "device"
                device.mkdir()
                (device / "model").write_text(model)

        link = self.sysfs / name
        link.symlink_to(device_dir)

        return device_dir

    def test_discovers_disk_and_calculates_size(self):
        self.create_device("sda", 1000)

        devices = collect_block_devices(self.sysfs)

        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0].name, "sda")
        self.assertEqual(devices[0].size_bytes, 512_000)
        self.assertTrue(devices[0].is_physical_disk)

    def test_attaches_partition_to_parent_disk(self):
        self.create_device("sda", 1000)
        self.create_device("sda1", 500, parent="sda")

        devices = collect_block_devices(self.sysfs)

        self.assertEqual(len(devices), 1)
        self.assertEqual(len(devices[0].children), 1)
        self.assertEqual(devices[0].children[0].name, "sda1")
        self.assertTrue(devices[0].children[0].is_partition)

    def test_does_not_classify_virtual_device_as_physical(self):
        self.create_device("zram0", 1000, virtual=True)

        devices = collect_block_devices(self.sysfs)

        self.assertEqual(len(devices), 1)
        self.assertFalse(devices[0].is_physical_disk)

    def test_returns_empty_list_when_sysfs_path_is_missing(self):
        missing_path = self.root / "missing"

        self.assertEqual(collect_block_devices(missing_path), [])

    def test_reads_model_and_rotational_status(self):
        self.create_device(
            "sda",
            1000,
            rotational="1",
            model="Example HDD",
        )

        device = collect_block_devices(self.sysfs)[0]

        self.assertEqual(device.model, "Example HDD")
        self.assertTrue(device.rotational)


if __name__ == "__main__":
    unittest.main()
