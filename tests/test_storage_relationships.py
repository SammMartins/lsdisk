"""Tests for read-only storage relationship discovery."""

import tempfile
import unittest
from pathlib import Path

from lsdisk.collectors.storage_relationships import collect_storage_relationships
from lsdisk.models import (
    BlockDevice,
    StorageDeviceKind,
    StorageRelationshipType,
)


class TestStorageRelationshipCollector(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.sysfs = Path(self.temp_dir.name) / "class" / "block"
        self.sysfs.mkdir(parents=True)

    def test_discovers_partition_parent_relationship(self):
        disk = BlockDevice(
            name="disk-a",
            path="/dev/disk-a",
            device_type="disk",
            size_bytes=1000,
            physical=True,
        )
        partition = BlockDevice(
            name="partition-a",
            path="/dev/partition-a",
            device_type="part",
            size_bytes=500,
            parent_name="disk-a",
        )

        # The normal collector supplies partitions as children.
        disk.children.append(partition)
        relationships = collect_storage_relationships([disk], sysfs_path=self.sysfs)

        self.assertEqual(len(relationships), 1)
        self.assertEqual(relationships[0].upper.kind, StorageDeviceKind.PARTITION)
        self.assertEqual(relationships[0].lower[0].identifier, "/dev/disk-a")

    def test_discovers_luks_mapping_from_sysfs_slave(self):
        encrypted = BlockDevice(
            name="partition-a",
            path="/dev/partition-a",
            device_type="part",
            size_bytes=500,
            filesystem_type="crypto_LUKS",
        )
        mapping = BlockDevice(
            name="dm-0",
            path="/dev/mapper/crypt-data",
            device_type="disk",
            size_bytes=500,
            physical=False,
        )
        slave_dir = self.sysfs / "dm-0" / "slaves"
        slave_dir.mkdir(parents=True)
        (slave_dir / "partition-a").symlink_to("/dev/null")

        relationships = collect_storage_relationships(
            [encrypted, mapping],
            sysfs_path=self.sysfs,
        )

        self.assertEqual(len(relationships), 1)
        self.assertEqual(
            relationships[0].relationship_type,
            StorageRelationshipType.ENCRYPTED_MAPPING,
        )

    def test_ignores_missing_or_inaccessible_topology(self):
        device = BlockDevice(
            name="unknown",
            path="/dev/unknown",
            device_type="disk",
            size_bytes=1,
        )
        self.assertEqual(
            collect_storage_relationships([device], sysfs_path=self.sysfs),
            [],
        )

    def test_skips_self_referential_relationship(self):
        device = BlockDevice(
            name="self",
            path="/dev/self",
            device_type="disk",
            size_bytes=1,
            parent_name="self",
        )
        self.assertEqual(
            collect_storage_relationships([device], sysfs_path=self.sysfs),
            [],
        )

    def test_skips_two_node_cycle(self):
        first = BlockDevice(
            name="first",
            path="/dev/first",
            device_type="disk",
            size_bytes=1,
            parent_name="second",
        )
        second = BlockDevice(
            name="second",
            path="/dev/second",
            device_type="disk",
            size_bytes=1,
            parent_name="first",
        )
        relationships = collect_storage_relationships(
            [first, second],
            sysfs_path=self.sysfs,
        )
        self.assertEqual(len(relationships), 1)

    def test_skips_longer_cycle_but_keeps_valid_edge(self):
        first = BlockDevice(
            name="first",
            path="/dev/first",
            device_type="disk",
            size_bytes=1,
            parent_name="second",
        )
        second = BlockDevice(
            name="second",
            path="/dev/second",
            device_type="disk",
            size_bytes=1,
            parent_name="third",
        )
        third = BlockDevice(
            name="third",
            path="/dev/third",
            device_type="disk",
            size_bytes=1,
            parent_name="first",
        )
        valid = BlockDevice(
            name="valid",
            path="/dev/valid",
            device_type="disk",
            size_bytes=1,
            parent_name="first",
        )
        relationships = collect_storage_relationships(
            [first, second, third, valid],
            sysfs_path=self.sysfs,
        )
        self.assertEqual(len(relationships), 3)
        self.assertEqual(relationships[-1].upper.identifier, "/dev/valid")

    def test_skips_ambiguous_duplicate_names(self):
        duplicate_a = BlockDevice(
            name="duplicate",
            path="/dev/duplicate-a",
            device_type="disk",
            size_bytes=1,
        )
        duplicate_b = BlockDevice(
            name="duplicate",
            path="/dev/duplicate-b",
            device_type="disk",
            size_bytes=1,
        )
        upper = BlockDevice(
            name="upper",
            path="/dev/upper",
            device_type="disk",
            size_bytes=1,
            parent_name="duplicate",
        )
        self.assertEqual(
            collect_storage_relationships(
                [duplicate_a, duplicate_b, upper],
                sysfs_path=self.sysfs,
            ),
            [],
        )

    def test_discovers_multiple_lower_devices(self):
        lower_a = BlockDevice(
            name="lower-a",
            path="/dev/lower-a",
            device_type="disk",
            size_bytes=1,
        )
        lower_b = BlockDevice(
            name="lower-b",
            path="/dev/lower-b",
            device_type="disk",
            size_bytes=1,
        )
        upper = BlockDevice(
            name="upper",
            path="/dev/upper",
            device_type="disk",
            size_bytes=1,
            physical=False,
        )
        slave_dir = self.sysfs / "upper" / "slaves"
        slave_dir.mkdir(parents=True)
        (slave_dir / "lower-a").symlink_to("/dev/null")
        (slave_dir / "lower-b").symlink_to("/dev/null")
        relationships = collect_storage_relationships(
            [lower_a, lower_b, upper],
            sysfs_path=self.sysfs,
        )
        self.assertEqual(len(relationships), 1)
        self.assertEqual(len(relationships[0].lower), 2)

    def test_deduplicates_slave_aliases_by_canonical_identity(self):
        lower_a = BlockDevice(
            name="lower-a",
            path="/dev/null",
            device_type="disk",
            size_bytes=1,
        )
        lower_b = BlockDevice(
            name="lower-b",
            path="/dev/../dev/null",
            device_type="disk",
            size_bytes=1,
        )
        upper = BlockDevice(
            name="upper",
            path="/dev/upper",
            device_type="disk",
            size_bytes=1,
            physical=False,
        )
        slave_dir = self.sysfs / "upper" / "slaves"
        slave_dir.mkdir(parents=True)
        (slave_dir / "lower-a").symlink_to("/dev/null")
        (slave_dir / "lower-b").symlink_to("/dev/null")

        relationships = collect_storage_relationships(
            [lower_a, lower_b, upper],
            sysfs_path=self.sysfs,
        )

        self.assertEqual(len(relationships), 1)
        self.assertEqual(len(relationships[0].lower), 1)


if __name__ == "__main__":
    unittest.main()
