"""Tests for lsdisk data models."""

import unittest

from lsdisk.models import (
    BlockDevice,
    FilesystemProbe,
    FilesystemUsage,
    ProbeState,
    StorageDeviceKind,
    StorageDeviceReference,
    StorageRelationship,
)


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

    def test_storage_kind_does_not_use_device_name_prefixes(self):
        device = BlockDevice(
            name="dm-0",
            path="/dev/mapper/data",
            device_type="disk",
            size_bytes=1,
            physical=False,
        )
        self.assertEqual(device.storage_kind, StorageDeviceKind.LOGICAL)

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


class TestFilesystemProbe(unittest.TestCase):
    def test_inconclusive_states_do_not_carry_metadata(self):
        for state in (
            ProbeState.NO_SIGNATURE,
            ProbeState.UNAVAILABLE,
            ProbeState.ERROR,
        ):
            with self.subTest(state=state):
                self.assertIsNone(FilesystemProbe(state).metadata)

    def test_recognized_state_requires_metadata(self):
        with self.assertRaises(ValueError):
            FilesystemProbe(ProbeState.RECOGNIZED)


class TestStorageRelationship(unittest.TestCase):
    def test_supports_multiple_lower_level_devices_and_missing_identifiers(self):
        upper = StorageDeviceReference(
            identifier="dm-0",
            kind=StorageDeviceKind.LOGICAL,
        )
        relationship = StorageRelationship(
            relationship_type="future_layer",
            upper=upper,
            lower=(
                StorageDeviceReference(
                    identifier="lower-1",
                    kind=StorageDeviceKind.PHYSICAL,
                    canonical_path="/dev/sda",
                ),
                StorageDeviceReference(
                    identifier="lower-2",
                    kind=StorageDeviceKind.PARTITION,
                ),
            ),
        )
        self.assertEqual(len(relationship.lower), 2)
        self.assertIsNone(relationship.lower[1].canonical_path)

    def test_rejects_self_reference(self):
        device = StorageDeviceReference(identifier="same")
        with self.assertRaises(ValueError):
            StorageRelationship(
                relationship_type="backed_by",
                upper=device,
                lower=(device,),
            )

    def test_rejects_empty_identifier(self):
        with self.assertRaises(ValueError):
            StorageDeviceReference(identifier=" ")

    def test_allows_duplicate_identifiers_without_inventing_identity(self):
        relationship = StorageRelationship(
            relationship_type="backed_by",
            upper=StorageDeviceReference(identifier="logical"),
            lower=(
                StorageDeviceReference(identifier="lower"),
                StorageDeviceReference(identifier="lower"),
            ),
        )
        self.assertEqual(len(relationship.lower), 2)


if __name__ == "__main__":
    unittest.main()
