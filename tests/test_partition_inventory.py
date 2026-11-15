"""Tests for partition geometry, unallocated gaps, and persistent mounts."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lsdisk.analyzers.partitions import find_unallocated_regions
from lsdisk.collectors.fstab import collect_fstab_entries
from lsdisk.collectors.partition_metadata import collect_partition_metadata
from lsdisk.models import BlockDevice, PartitionMetadata


def _build_device(row, metadata):
    return BlockDevice(
        name=row["path"].rsplit("/", 1)[-1],
        path=row["path"],
        device_type=row["type"],
        size_bytes=row["size"],
        physical=row.get("type") == "disk",
        partition_metadata=metadata[row["path"]],
        children=[
            _build_device(child, metadata)
            for child in row.get("children", [])
        ],
    )


def _build_devices(payload, metadata):
    return [
        _build_device(row, metadata)
        for row in payload["blockdevices"]
    ]


def _partition(name, start, end, size_bytes=None, logical=512):
    if size_bytes is None:
        size_bytes = (end - start + 1) * 512
    return BlockDevice(
        name,
        f"/dev/{name}",
        "part",
        size_bytes,
        parent_name="sda",
        partition_metadata=PartitionMetadata(
            start_sector=start,
            end_sector=end,
            logical_sector_size=logical,
        ),
    )


def _disk(name, sectors, partitions, logical=512):
    return BlockDevice(
        name,
        f"/dev/{name}",
        "disk",
        sectors * logical,
        physical=True,
        partition_metadata=PartitionMetadata(
            partition_table="gpt",
            logical_sector_size=logical,
        ),
        children=partitions,
    )


class TestPersistentMounts(unittest.TestCase):
    def test_parses_escaped_and_unresolved_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fstab"
            path.write_text(
                r"UUID=abc /data\040files ext4 defaults,x-systemd.device-timeout=1 0 2"
                "\n/dev/missing /mnt auto noauto 0 0\n# ignored\n",
                encoding="utf-8",
            )
            entries = collect_fstab_entries(path)
        self.assertEqual(entries[0].mountpoint, "/data files")
        self.assertEqual(entries[0].source, "UUID=abc")
        self.assertEqual(entries[0].options[1], "x-systemd.device-timeout=1")
        self.assertEqual(entries[1].source, "/dev/missing")


class TestPartitionMetadata(unittest.TestCase):
    @patch("lsdisk.collectors.partition_metadata.subprocess.run")
    def test_parses_512_byte_sector_geometry_and_flags(self, run):
        payload = {"blockdevices": [{
            "path": "/dev/sda",
            "type": "disk",
            "size": 4194304,
            "start": None,
            "log-sec": 512,
            "phy-sec": 4096,
            "pttype": "gpt",
            "partflags": None,
            "children": [{
                "path": "/dev/sda1",
                "type": "part",
                "size": 524288,
                "start": 2048,
                "log-sec": 512,
                "phy-sec": 4096,
                "partlabel": "Boot",
                "parttype": "c12a7328-f81f-11d2-ba4b-00a0c93ec93b",
                "partflags": "boot,esp",
            }, {
                "path": "/dev/sda2",
                "type": "part",
                "size": 1048576,
                "start": 4096,
                "log-sec": 512,
                "phy-sec": 4096,
                "partlabel": "Data",
                "parttype": "0fc63daf-8483-4772-8e79-3d69d8477de4",
                "partflags": None,
            }],
        }]}
        run.return_value.returncode = 0
        run.return_value.stdout = json.dumps(payload)

        metadata = collect_partition_metadata()
        devices = _build_devices(payload, metadata)

        self.assertIsNone(metadata["/dev/sda"].start_sector)
        self.assertIsNone(metadata["/dev/sda"].end_sector)
        self.assertEqual(metadata["/dev/sda1"].start_sector, 2048)
        self.assertEqual(metadata["/dev/sda1"].end_sector, 3071)
        self.assertEqual(metadata["/dev/sda2"].start_sector, 4096)
        self.assertEqual(metadata["/dev/sda2"].end_sector, 6143)
        self.assertEqual(metadata["/dev/sda1"].flags, ("boot", "esp"))
        self.assertEqual(
            [(region.start_bytes, region.end_bytes)
             for region in find_unallocated_regions(devices)],
            [(0, 1048575), (1572864, 2097151), (3145728, 4194303)],
        )

    @patch("lsdisk.collectors.partition_metadata.subprocess.run")
    def test_uses_512_byte_sectors_for_4096_byte_logical_devices(self, run):
        payload = {"blockdevices": [{
            "path": "/dev/nvme0n1",
            "type": "disk",
            "size": 16777216,
            "start": None,
            "log-sec": 4096,
            "phy-sec": 4096,
            "pttype": "gpt",
            "children": [{
                "path": "/dev/nvme0n1p1",
                "type": "part",
                "size": 4194304,
                "start": 2048,
                "log-sec": 4096,
                "phy-sec": 4096,
            }, {
                "path": "/dev/nvme0n1p2",
                "type": "part",
                "size": 2097152,
                "start": 12288,
                "log-sec": 4096,
                "phy-sec": 4096,
            }],
        }]}
        run.return_value.returncode = 0
        run.return_value.stdout = json.dumps(payload)

        metadata = collect_partition_metadata()
        devices = _build_devices(payload, metadata)

        self.assertEqual(metadata["/dev/nvme0n1p1"].end_sector, 10239)
        self.assertEqual(metadata["/dev/nvme0n1p2"].end_sector, 16383)
        self.assertEqual(
            [(region.start_bytes, region.end_bytes)
             for region in find_unallocated_regions(devices)],
            [(0, 1048575), (5242880, 6291455), (8388608, 16777215)],
        )

    @patch("lsdisk.collectors.partition_metadata.subprocess.run")
    def test_rejects_misaligned_4096_byte_partition_start(self, run):
        payload = {"blockdevices": [{
            "path": "/dev/nvme0n1",
            "type": "disk",
            "size": 32768,
            "start": None,
            "log-sec": 4096,
            "phy-sec": 4096,
            "pttype": "gpt",
            "children": [{
                "path": "/dev/nvme0n1p1",
                "type": "part",
                "size": 4096,
                "start": 9,
                "log-sec": 4096,
                "phy-sec": 4096,
            }],
        }]}
        run.return_value.returncode = 0
        run.return_value.stdout = json.dumps(payload)

        metadata = collect_partition_metadata()
        devices = _build_devices(payload, metadata)

        self.assertIsNone(metadata["/dev/nvme0n1p1"].end_sector)
        self.assertEqual(find_unallocated_regions(devices), [])

    def test_accepts_aligned_4096_byte_starts_and_capacity(self):
        disk = _disk("nvme0n1", 8, [
            _partition("nvme0n1p1", 8, 15, logical=4096),
            _partition("nvme0n1p2", 24, 31, logical=4096),
        ], logical=4096)

        self.assertEqual(
            [(region.start_bytes, region.end_bytes)
             for region in find_unallocated_regions([disk])],
            [(0, 4095), (8192, 12287), (16384, 32767)],
        )

    def test_rejects_misaligned_4096_byte_partition_start_in_analyzer(self):
        disk = _disk("nvme0n1", 8, [
            _partition("nvme0n1p1", 9, 16, logical=4096),
        ], logical=4096)

        self.assertEqual(find_unallocated_regions([disk]), [])

    def test_rejects_misaligned_4096_byte_disk_capacity(self):
        disk = BlockDevice(
            "nvme0n1", "/dev/nvme0n1", "disk", 33280, physical=True,
            partition_metadata=PartitionMetadata(
                partition_table="gpt", logical_sector_size=4096
            ),
            children=[_partition("nvme0n1p1", 8, 15, logical=4096)],
        )

        self.assertEqual(find_unallocated_regions([disk]), [])

    def test_rejects_misaligned_4096_byte_partition_size(self):
        disk = _disk("nvme0n1", 8, [
            _partition("nvme0n1p1", 8, 16, logical=4096),
        ], logical=4096)

        self.assertEqual(find_unallocated_regions([disk]), [])

    def test_physical_sector_size_difference_does_not_reject_geometry(self):
        disk = _disk("sda", 8, [
            _partition("sda1", 2, 3),
        ])
        disk.partition_metadata = PartitionMetadata(
            partition_table="gpt",
            logical_sector_size=512,
            physical_sector_size=4096,
        )
        disk.children[0].partition_metadata = PartitionMetadata(
            start_sector=2,
            end_sector=3,
            logical_sector_size=512,
            physical_sector_size=4096,
        )

        self.assertEqual(
            [(region.start_bytes, region.end_bytes)
             for region in find_unallocated_regions([disk])],
            [(0, 1023), (2048, 4095)],
        )

    @patch("lsdisk.collectors.partition_metadata.subprocess.run")
    def test_rejects_missing_malformed_and_inconsistent_geometry(self, run):
        payload = {"blockdevices": [{
            "path": "/dev/sdb",
            "type": "disk",
            "size": 4194304,
            "start": None,
            "log-sec": 4096,
            "phy-sec": 4096,
            "pttype": "gpt",
            "children": [{
                "path": "/dev/sdb1",
                "type": "part",
                "size": 0,
                "start": 2048,
                "log-sec": 4096,
                "phy-sec": 4096,
            }, {
                "path": "/dev/sdb2",
                "type": "part",
                "size": -512,
                "start": 2048,
                "log-sec": 4096,
                "phy-sec": 4096,
            }, {
                "path": "/dev/sdb3",
                "type": "part",
                "size": 4096,
                "start": -1,
                "log-sec": 4096,
                "phy-sec": 4096,
            }, {
                "path": "/dev/sdb4",
                "type": "part",
                "size": 4608,
                "start": 2048,
                "log-sec": 4096,
                "phy-sec": 4096,
            }, {
                "path": "/dev/sdb5",
                "type": "part",
                "size": 1000,
                "start": 2048,
                "log-sec": 4096,
                "phy-sec": 4096,
            }, {
                "path": "/dev/sdb6",
                "type": "part",
                "size": "not-a-number",
                "start": 2048,
                "log-sec": 4096,
                "phy-sec": 4096,
            }],
        }]}
        run.return_value.returncode = 0
        run.return_value.stdout = json.dumps(payload)

        metadata = collect_partition_metadata()

        for index in range(1, 7):
            self.assertIsNone(
                metadata[f"/dev/sdb{index}"].end_sector,
                f"/dev/sdb{index} must not invent an end boundary",
            )

    def test_unallocated_regions_require_complete_nonoverlapping_geometry(self):
        partition_a = BlockDevice(
            "sda1", "/dev/sda1", "part", 20, parent_name="sda",
            partition_metadata=PartitionMetadata(
                start_sector=2, end_sector=3, logical_sector_size=512
            ),
        )
        partition_b = BlockDevice(
            "sda2", "/dev/sda2", "part", 20, parent_name="sda",
            partition_metadata=PartitionMetadata(
                start_sector=5, end_sector=6, logical_sector_size=512
            ),
        )
        disk = BlockDevice(
            "sda", "/dev/sda", "disk", 8 * 512, physical=True,
            partition_metadata=PartitionMetadata(
                partition_table="gpt", logical_sector_size=512
            ),
            children=[partition_a, partition_b],
        )
        regions = find_unallocated_regions([disk])
        self.assertEqual(
            [(item.start_bytes, item.end_bytes) for item in regions],
            [(0, 1023), (2048, 2559), (3584, 4095)],
        )

    def test_overlap_discards_gap_already_found_for_the_disk(self):
        disk = _disk("sda", 8, [
            _partition("sda1", 2, 3),
            _partition("sda2", 5, 6),
            _partition("sda3", 6, 7),
        ])
        self.assertEqual(find_unallocated_regions([disk]), [])

    def test_out_of_range_partition_discards_gap_already_found_for_the_disk(self):
        disk = _disk("sda", 8, [
            _partition("sda1", 2, 3),
            _partition("sda2", 6, 8),
        ])
        self.assertEqual(find_unallocated_regions([disk]), [])

    def test_rejects_missing_reversed_and_duplicate_boundaries(self):
        second_partitions = {
            "missing": PartitionMetadata(logical_sector_size=512),
            "reversed": PartitionMetadata(
                start_sector=6, end_sector=4, logical_sector_size=512
            ),
            "duplicate": PartitionMetadata(
                start_sector=2, end_sector=3, logical_sector_size=512
            ),
        }
        for label, metadata in second_partitions.items():
            with self.subTest(label=label):
                second = _partition("sda2", 2, 3)
                second.partition_metadata = metadata
                disk = _disk("sda", 8, [
                    _partition("sda1", 2, 3),
                    second,
                ])
                self.assertEqual(find_unallocated_regions([disk]), [])

    def test_invalid_disk_does_not_suppress_valid_disk_regions(self):
        valid = _disk("sda", 8, [
            _partition("sda1", 2, 3),
            _partition("sda2", 5, 6),
        ])
        invalid = _disk("sdb", 8, [
            _partition("sdb1", 2, 3),
            _partition("sdb2", 3, 5),
        ])

        regions = find_unallocated_regions([valid, invalid])

        self.assertEqual(
            [(item.disk_path, item.start_bytes, item.end_bytes)
             for item in regions],
            [
                ("/dev/sda", 0, 1023),
                ("/dev/sda", 2048, 2559),
                ("/dev/sda", 3584, 4095),
            ],
        )


if __name__ == "__main__":
    unittest.main()
