"""Tests for associating probed signatures with block devices."""

import unittest
from unittest.mock import patch

from lsdisk.collectors.filesystem_metadata import FilesystemMetadata
from lsdisk.inventory import collect_storage_inventory
from lsdisk.models import (
    BlockDevice,
    StorageDeviceReference,
    StorageRelationship,
    StorageRelationshipType,
)


class TestInventoryMetadata(unittest.TestCase):
    @patch("lsdisk.inventory.collect_lsblk_metadata", return_value={})
    @patch("lsdisk.inventory.collect_filesystems", return_value=[])
    @patch("lsdisk.inventory.probe_filesystem")
    @patch("lsdisk.inventory.collect_block_devices")
    def test_collects_metadata_for_unmounted_partition(
            self,
            collect_devices,
            probe_filesystem,
            _collect_filesystems,
            _collect_lsblk_metadata,
    ):
        partition = BlockDevice(
            name="sda1",
            path="/dev/sda1",
            device_type="part",
            size_bytes=1024,
            parent_name="sda",
        )
        disk = BlockDevice(
            name="sda",
            path="/dev/sda",
            device_type="disk",
            size_bytes=2048,
            physical=True,
            children=[partition],
        )
        collect_devices.return_value = [disk]
        probe_filesystem.side_effect = [
            None,
            FilesystemMetadata(
                filesystem_type="ext4",
                label="DATA",
                uuid="ext4-uuid",
            ),
        ]

        inventory = collect_storage_inventory()

        self.assertEqual(partition.filesystem_type, "ext4")
        self.assertEqual(partition.filesystem_label, "DATA")
        self.assertEqual(partition.filesystem_uuid, "ext4-uuid")
        self.assertEqual(partition.mountpoints, [])

    @patch("lsdisk.inventory.collect_lsblk_metadata")
    @patch("lsdisk.inventory.collect_filesystems", return_value=[])
    @patch("lsdisk.inventory.probe_filesystem")
    @patch("lsdisk.inventory.collect_block_devices")
    def test_fallback_preserves_lsblk_values(
        self,
        collect_devices,
        probe_filesystem,
        _collect_filesystems,
        collect_lsblk_metadata,
    ):
        partition = BlockDevice(
            name="sda1",
            path="/dev/sda1",
            device_type="part",
            size_bytes=1024,
        )
        collect_devices.return_value = [partition]
        collect_lsblk_metadata.return_value = {
            "/dev/sda1": FilesystemMetadata(
                filesystem_type="crypto_LUKS",
                label="encrypted",
                uuid="luks-uuid",
            )
        }
        probe_filesystem.return_value = FilesystemMetadata(
            filesystem_type="ext4",
            label=None,
            uuid=None,
        )

        inventory = collect_storage_inventory()

        self.assertEqual(inventory.devices[0].filesystem_type, "crypto_LUKS")
        self.assertEqual(inventory.devices[0].filesystem_label, "encrypted")
        self.assertEqual(inventory.devices[0].filesystem_uuid, "luks-uuid")

    @patch("lsdisk.inventory.collect_lsblk_metadata")
    @patch("lsdisk.inventory.collect_filesystems", return_value=[])
    @patch("lsdisk.inventory.probe_filesystem")
    @patch("lsdisk.inventory.collect_block_devices")
    def test_skips_probe_when_lsblk_has_complete_metadata(
        self,
        collect_devices,
        probe_filesystem,
        _collect_filesystems,
        collect_lsblk_metadata,
    ):
        partition = BlockDevice(
            name="sda1",
            path="/dev/sda1",
            device_type="part",
            size_bytes=1024,
        )
        collect_devices.return_value = [partition]
        collect_lsblk_metadata.return_value = {
            "/dev/sda1": FilesystemMetadata(
                filesystem_type="ext4",
                label="DATA",
                uuid="ext4-uuid",
            )
        }

        collect_storage_inventory()

        probe_filesystem.assert_not_called()

    @patch("lsdisk.inventory.collect_lvm_relationships")
    @patch("lsdisk.inventory.collect_mdraid_relationships", return_value=[])
    @patch("lsdisk.inventory.collect_storage_relationships", return_value=[])
    @patch("lsdisk.inventory.collect_lsblk_metadata", return_value={})
    @patch("lsdisk.inventory.collect_filesystems", return_value=[])
    @patch("lsdisk.inventory.probe_filesystem", return_value=None)
    @patch("lsdisk.inventory.collect_block_devices")
    def test_integrates_lvm_relationships_without_changing_devices(
        self,
        collect_devices,
        _probe,
        _collect_filesystems,
        _collect_lsblk_metadata,
        _collect_storage_relationships,
        _collect_mdraid_relationships,
        collect_lvm_relationships,
    ):
        device = BlockDevice(
            name="sda1",
            path="/dev/sda1",
            device_type="part",
            size_bytes=1024,
        )
        collect_devices.return_value = [device]
        relationship = StorageRelationship(
            relationship_type=StorageRelationshipType.LVM_LOGICAL_VOLUME,
            upper=StorageDeviceReference("lvm:lv:data/root"),
            lower=(StorageDeviceReference("lvm:vg:data"),),
        )
        collect_lvm_relationships.return_value = [relationship]

        inventory = collect_storage_inventory()

        self.assertEqual(inventory.relationships, [relationship])
        self.assertEqual(inventory.devices, [device])

    @patch("lsdisk.inventory.collect_lvm_relationships", return_value=[])
    @patch("lsdisk.inventory.collect_mdraid_relationships")
    @patch("lsdisk.inventory.collect_storage_relationships", return_value=[])
    @patch("lsdisk.inventory.collect_lsblk_metadata", return_value={})
    @patch("lsdisk.inventory.collect_filesystems", return_value=[])
    @patch("lsdisk.inventory.probe_filesystem", return_value=None)
    @patch("lsdisk.inventory.collect_block_devices")
    def test_integrates_mdraid_relationships_without_changing_devices(
        self,
        collect_devices,
        _probe,
        _collect_filesystems,
        _collect_lsblk_metadata,
        _collect_storage_relationships,
        collect_mdraid_relationships,
        _collect_lvm_relationships,
    ):
        device = BlockDevice(
            name="sda1",
            path="/dev/sda1",
            device_type="part",
            size_bytes=1024,
        )
        collect_devices.return_value = [device]
        relationship = StorageRelationship(
            relationship_type=StorageRelationshipType.RAID_MEMBER,
            upper=StorageDeviceReference("/dev/md0"),
            lower=(StorageDeviceReference("/dev/sda1"),),
        )
        collect_mdraid_relationships.return_value = [relationship]

        inventory = collect_storage_inventory()

        self.assertEqual(inventory.relationships, [relationship])
        self.assertEqual(inventory.devices, [device])


if __name__ == "__main__":
    unittest.main()
