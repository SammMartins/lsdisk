"""Tests for conservative physical-capacity ownership."""

import unittest

from lsdisk.analyzers.capacity import capacity_owners, owned_capacity_bytes
from lsdisk.models import BlockDevice


class TestCapacityOwnership(unittest.TestCase):
    def test_excludes_partitions_and_logical_devices_from_physical_total(self):
        disk = BlockDevice(
            name="disk-a",
            path="/dev/disk-a",
            device_type="disk",
            size_bytes=10_000,
            physical=True,
        )
        disk.children.append(
            BlockDevice(
                name="partition-a",
                path="/dev/partition-a",
                device_type="part",
                size_bytes=5_000,
                parent_name="disk-a",
            )
        )
        logical = BlockDevice(
            name="array",
            path="/dev/md0",
            device_type="disk",
            size_bytes=5_000,
            physical=False,
        )

        self.assertEqual(capacity_owners([disk, logical]), [disk])
        self.assertEqual(owned_capacity_bytes([disk, logical]), 10_000)

    def test_counts_multiple_physical_members_once(self):
        devices = [
            BlockDevice(
                name="disk-a",
                path="/dev/disk-a",
                device_type="disk",
                size_bytes=10_000,
                physical=True,
            ),
            BlockDevice(
                name="disk-b",
                path="/dev/disk-b",
                device_type="disk",
                size_bytes=20_000,
                physical=True,
            ),
        ]
        self.assertEqual(owned_capacity_bytes(devices), 30_000)

    def test_deduplicates_verified_canonical_aliases(self):
        aliases = [
            BlockDevice(
                name="null-a",
                path="/dev/null",
                device_type="disk",
                size_bytes=10_000,
                physical=True,
            ),
            BlockDevice(
                name="null-b",
                path="/dev/../dev/null",
                device_type="disk",
                size_bytes=10_000,
                physical=True,
            ),
        ]
        self.assertEqual(owned_capacity_bytes(aliases), 10_000)
