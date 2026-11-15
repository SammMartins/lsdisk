"""Tests for inventory serialization."""

import copy
import unittest
from types import SimpleNamespace

from lsdisk.analyzers.filesystems import group_filesystems
from lsdisk.inventory import StorageInventory
from lsdisk.models import (
    BlockDevice,
    FstabEntry,
    FilesystemUsage,
    PartitionMetadata,
    StorageDeviceKind,
    StorageDeviceReference,
    StorageRelationship,
    StorageRelationshipType,
    UnallocatedRegion,
)
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
        partition_metadata=PartitionMetadata(
            partition_table="gpt",
            logical_sector_size=512,
            physical_sector_size=4096,
            start_sector=0,
            end_sector=9,
            partition_name="Data",
            partition_type="linux",
            flags=("boot",),
        ),
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

    overlay = FilesystemUsage(
        mountpoint="/var/lib/containers/storage/overlay",
        source="overlay",
        filesystem_type="overlay",
        total_bytes=0,
        free_bytes=0,
        available_bytes=0,
        device_id="0:42",
    )

    image = FilesystemUsage(
        mountpoint="/opt/example",
        source="/opt/example.dwarfs",
        filesystem_type="fuse.dwarfs",
        total_bytes=100,
        free_bytes=0,
        available_bytes=0,
        device_id="0:91",
    )

    filesystems = [btrfs_root, btrfs_subvolume, tmpfs, overlay, image]

    return StorageInventory(
        devices=[disk, virtual_disk],
        filesystems=filesystems,
        filesystem_groups=group_filesystems(filesystems),
        fstab_entries=[
            FstabEntry(
                source="UUID=data",
                mountpoint="/data",
                filesystem_type="btrfs",
                options=("defaults",),
                dump="0",
                pass_number="2",
            )
        ],
        unallocated_regions=[
            UnallocatedRegion(
                disk_path="/dev/sda",
                start_bytes=5120,
                end_bytes=6143,
                size_bytes=1024,
            )
        ],
    )


class TestInventorySerialization(unittest.TestCase):
    def test_device_attributes_break_sort_key_ties(self):
        first = make_inventory()
        second = copy.deepcopy(first)
        first.devices[0].model = "Model A"
        second.devices[0].model = "Model B"

        first_data = inventory_to_dict(first, include_all=True)
        second_data = inventory_to_dict(second, include_all=True)

        self.assertNotEqual(first_data, second_data)
        self.assertEqual(
            inventory_to_dict(first, include_all=True),
            inventory_to_dict(copy.deepcopy(first), include_all=True),
        )

    def test_mount_attributes_break_sort_key_ties(self):
        first = make_inventory()
        second = copy.deepcopy(first)
        first.filesystems[0] = FilesystemUsage(
            mountpoint="/data",
            source="/dev/sda1",
            filesystem_type="btrfs",
            total_bytes=5_000,
            free_bytes=2_000,
            available_bytes=1_800,
            device_id="8:1",
            filesystem_root="/",
        )
        second.filesystems[0] = FilesystemUsage(
            mountpoint="/data",
            source="/dev/sda1",
            filesystem_type="btrfs",
            total_bytes=5_000,
            free_bytes=2_000,
            available_bytes=1_800,
            device_id="8:1",
            filesystem_root="/@different",
        )

        self.assertNotEqual(
            inventory_to_dict(first, include_all=True)["mounts"],
            inventory_to_dict(second, include_all=True)["mounts"],
        )

    def test_group_attributes_break_sort_key_ties(self):
        def group(used_percent):
            filesystem = SimpleNamespace(
                device_id="8:1",
                source="/dev/sda1",
                filesystem_type="ext4",
                total_bytes=100,
                used_bytes=50,
                available_bytes=50,
                filesystem_root="/",
                used_percent=used_percent,
            )
            return SimpleNamespace(
                representative=filesystem,
                total_bytes=100,
                used_bytes=50,
                available_bytes=50,
                mountpoints=["/data"],
            )

        first = StorageInventory(
            devices=[],
            filesystems=[],
            filesystem_groups=[group(10.0), group(20.0)],
        )
        second = StorageInventory(
            devices=[],
            filesystems=[],
            filesystem_groups=[group(20.0), group(10.0)],
        )

        self.assertEqual(
            inventory_to_dict(first),
            inventory_to_dict(second),
        )

    def test_serialization_orders_equivalent_inventories_without_mutation(self):
        first = make_inventory()
        second = copy.deepcopy(first)

        original_device_order = [device.name for device in second.devices]
        original_child_orders = [
            [child.name for child in device.children]
            for device in second.devices
        ]
        original_group_order = [
            group.representative.source
            for group in second.filesystem_groups
        ]
        original_group_mountpoints = {
            group.representative.source: list(group.mountpoints)
            for group in second.filesystem_groups
        }
        original_mount_order = [
            filesystem.mountpoint
            for filesystem in second.filesystems
        ]

        second.devices.reverse()
        for device in second.devices:
            device.children.reverse()
        second.filesystem_groups.reverse()
        for group in second.filesystem_groups:
            group.mountpoints.reverse()
        second.filesystems.reverse()

        self.assertEqual(
            inventory_to_dict(first, include_all=True),
            inventory_to_dict(second, include_all=True),
        )
        self.assertEqual(
            [device.name for device in second.devices],
            list(reversed(original_device_order)),
        )
        self.assertEqual(
            [
                [child.name for child in device.children]
                for device in second.devices
            ],
            list(reversed(original_child_orders)),
        )
        self.assertEqual(
            [group.representative.source for group in second.filesystem_groups],
            list(reversed(original_group_order)),
        )
        self.assertEqual(
            {
                group.representative.source: list(group.mountpoints)
                for group in second.filesystem_groups
            },
            {
                source: list(reversed(mountpoints))
                for source, mountpoints in original_group_mountpoints.items()
            },
        )
        self.assertEqual(
            [filesystem.mountpoint for filesystem in second.filesystems],
            list(reversed(original_mount_order)),
        )

    def test_simple_mode_excludes_virtual_devices(self):
        data = inventory_to_dict(make_inventory())

        self.assertEqual(data["mode"], "simple")
        self.assertEqual(
            [device["name"] for device in data["devices"]],
            ["sda"],
        )
        self.assertIn("relationships", data)
        self.assertNotIn("fstab", data)
        self.assertNotIn("unallocated_regions", data)
        self.assertNotIn("partition_metadata", data["devices"][0]["children"][0])

    def test_all_mode_includes_virtual_devices_and_mounts(self):
        data = inventory_to_dict(make_inventory(), include_all=True)

        self.assertEqual(data["mode"], "all")
        self.assertEqual(
            [device["name"] for device in data["devices"]],
            ["sda", "zram0"],
        )
        self.assertEqual(len(data["mounts"]), 5)
        self.assertIn("relationships", data)
        self.assertIn("fstab", data)
        self.assertIn("unallocated_regions", data)
        metadata = data["devices"][0]["children"][0]["partition_metadata"]
        self.assertEqual(metadata["start_sector"], 0)
        self.assertEqual(metadata["end_sector"], 9)
        self.assertIsInstance(metadata["flags"], list)
        self.assertEqual(data["fstab"][0]["options"], ["defaults"])
        self.assertEqual(data["unallocated_regions"][0]["size_bytes"], 1024)

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

    def test_all_mode_exposes_stable_filesystem_categories(self):
        data = inventory_to_dict(make_inventory(), include_all=True)

        categories = {
            item["filesystem_type"]: item["category"]
            for item in data["mounts"]
        }

        self.assertEqual(categories["btrfs"], "persistent")
        self.assertEqual(categories["tmpfs"], "temporary")
        self.assertEqual(categories["overlay"], "virtual")
        self.assertEqual(categories["fuse.dwarfs"], "application_image")

    def test_relationships_are_empty_when_no_metadata_is_verified(self):
        data = inventory_to_dict(make_inventory(), include_all=True)
        self.assertEqual(data["relationships"], [])
        self.assertEqual(
            inventory_to_dict(make_inventory())["relationships"],
            [],
        )

    def test_serializes_deduplicated_relationships_deterministically(self):
        inventory = make_inventory()
        inventory.relationships = [
            StorageRelationship(
                relationship_type=StorageRelationshipType.RAID_MEMBER,
                upper=StorageDeviceReference(
                    "/dev/md0",
                    kind=StorageDeviceKind.LOGICAL,
                    canonical_path="/dev/md0",
                ),
                lower=(
                    StorageDeviceReference(
                        "/dev/sdb1",
                        kind=StorageDeviceKind.PARTITION,
                    ),
                    StorageDeviceReference(
                        "/dev/sda1",
                        kind=StorageDeviceKind.PARTITION,
                    ),
                    StorageDeviceReference(
                        "/dev/sda1",
                        kind=StorageDeviceKind.PARTITION,
                    ),
                ),
            )
        ]

        data = inventory_to_dict(inventory, include_all=True)

        self.assertEqual(
            data["relationships"][0]["relationship_type"],
            "raid_member",
        )
        self.assertEqual(
            [item["identifier"] for item in data["relationships"][0]["lower"]],
            ["/dev/sda1", "/dev/sdb1"],
        )

    def test_deduplicates_relationship_aliases_by_canonical_path(self):
        inventory = make_inventory()
        inventory.relationships = [
            StorageRelationship(
                relationship_type=StorageRelationshipType.BACKED_BY,
                upper=StorageDeviceReference(
                    "mapper/data",
                    kind=StorageDeviceKind.LOGICAL,
                    canonical_path="/dev/mapper/data",
                ),
                lower=(
                    StorageDeviceReference(
                        "/dev/disk/by-uuid/data",
                        kind=StorageDeviceKind.PARTITION,
                        canonical_path="/dev/sda1",
                    ),
                    StorageDeviceReference(
                        "/dev/sda1",
                        kind=StorageDeviceKind.PARTITION,
                        canonical_path="/dev/sda1",
                    ),
                ),
            ),
            StorageRelationship(
                relationship_type=StorageRelationshipType.BACKED_BY,
                upper=StorageDeviceReference(
                    "/dev/mapper/data",
                    kind=StorageDeviceKind.LOGICAL,
                    canonical_path="/dev/mapper/data",
                ),
                lower=(
                    StorageDeviceReference(
                        "/dev/sda1",
                        kind=StorageDeviceKind.PARTITION,
                        canonical_path="/dev/sda1",
                    ),
                ),
            ),
        ]

        relationships = inventory_to_dict(
            inventory,
            include_all=True,
        )["relationships"]

        self.assertEqual(len(relationships), 1)
        self.assertEqual(
            [item["identifier"] for item in relationships[0]["lower"]],
            ["/dev/sda1"],
        )
        reversed_inventory = make_inventory()
        reversed_inventory.relationships = list(reversed(inventory.relationships))
        self.assertEqual(
            inventory_to_dict(reversed_inventory, include_all=True)["relationships"],
            relationships,
        )


if __name__ == "__main__":
    unittest.main()
