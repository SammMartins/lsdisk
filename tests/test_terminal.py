"""Tests for the compact terminal interface."""

import unittest
from io import StringIO

from rich.console import Console

from lsdisk.analyzers.filesystems import group_filesystems
from lsdisk.inventory import StorageInventory
from lsdisk.serialization import inventory_to_dict
from lsdisk.models import (
    BlockDevice,
    FstabEntry,
    FilesystemUsage,
    PartitionMetadata,
    StorageDeviceKind,
    StorageDeviceReference,
    StorageRelationship,
    StorageRelationshipType,
)
from lsdisk.ui.terminal import (
    render_all,
    render_classic,
    render_compact,
    render_simple,
)
from lsdisk.ui.terminal import (
    _usage_bar,
    _usage_color,
    render_compact,
)


class TestCompactFilesystemDetails(unittest.TestCase):
    def test_all_mode_shows_partition_metadata_and_fstab_entries(self):
        partition = BlockDevice(
            name="sda1",
            path="/dev/sda1",
            device_type="part",
            size_bytes=1_000,
            partition_metadata=PartitionMetadata(
                partition_table="gpt",
                logical_sector_size=512,
                physical_sector_size=4096,
                start_sector=0,
                end_sector=1,
                partition_name="Data",
                partition_type="linux",
            ),
        )
        inventory = StorageInventory(
            devices=[partition],
            filesystems=[],
            filesystem_groups=[],
            fstab_entries=[
                FstabEntry(
                    source="UUID=data",
                    mountpoint="/data",
                    filesystem_type="ext4",
                    options=("defaults", "nofail"),
                    dump="0",
                    pass_number="2",
                )
            ],
        )
        output = StringIO()

        render_compact(
            inventory,
            Console(file=output, width=120, force_terminal=False),
            include_all=True,
        )

        rendered = output.getvalue()
        self.assertIn("Partition Geometry", rendered)
        self.assertIn("Start sector", rendered)
        self.assertIn("Persistent Mount Configuration", rendered)
        self.assertIn("UUID=data", rendered)
        self.assertIn("not proof of currently active mounts", rendered)

    def test_all_mode_handles_missing_partition_metadata_and_empty_fstab(self):
        inventory = StorageInventory(
            devices=[
                BlockDevice(
                    name="sda1",
                    path="/dev/sda1",
                    device_type="part",
                    size_bytes=1_000,
                )
            ],
            filesystems=[],
            filesystem_groups=[],
        )
        output = StringIO()

        render_compact(
            inventory,
            Console(file=output, width=70, force_terminal=False),
            include_all=True,
        )

        rendered = output.getvalue()
        self.assertNotIn("Partition Geometry", rendered)
        self.assertNotIn("Persistent Mount Configuration", rendered)
        self.assertIn("Warning: Terminal width is limited", rendered)

    def test_all_mode_keeps_fstab_section_at_narrow_width(self):
        inventory = StorageInventory(
            devices=[],
            filesystems=[],
            filesystem_groups=[],
            fstab_entries=[
                FstabEntry(
                    source="UUID=very-long-storage-identifier",
                    mountpoint="/a/very/long/mountpoint",
                    filesystem_type="ext4",
                    options=("defaults", "nofail"),
                )
            ],
        )
        output = StringIO()

        render_compact(
            inventory,
            Console(file=output, width=70, force_terminal=False),
            include_all=True,
        )

        rendered = output.getvalue()
        self.assertIn("Persistent Mount Configuration", rendered)
        self.assertIn("Warning: Terminal width is limited", rendered)

    def test_summary_deduplicates_verified_physical_aliases(self):
        devices = [
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
        inventory = StorageInventory(
            devices=devices,
            filesystems=[],
            filesystem_groups=[],
        )
        output = StringIO()
        console = Console(file=output, width=100, force_terminal=False)

        render_compact(inventory, console)

        rendered = output.getvalue()
        self.assertIn("Physical disks: 1", rendered)
        self.assertIn("Physical capacity: 9.77 KiB", rendered)

    def test_groups_mountpoints_and_shows_btrfs_subvolumes(self):
        disk = BlockDevice(
            name="sda",
            path="/dev/sda",
            device_type="disk",
            size_bytes=20_000,
            physical=True,
        )

        partition = BlockDevice(
            name="sda1",
            path="/dev/sda1",
            device_type="part",
            size_bytes=10_000,
            parent_name="sda",
            filesystem_type="btrfs",
            mountpoints=["/", "/home"],
        )
        disk.children.append(partition)

        filesystems = [
            FilesystemUsage(
                mountpoint="/",
                source="/dev/sda1",
                filesystem_type="btrfs",
                total_bytes=10_000,
                free_bytes=4_000,
                available_bytes=3_500,
                device_id="8:1",
                filesystem_root="/@",
            ),
            FilesystemUsage(
                mountpoint="/home",
                source="/dev/sda1",
                filesystem_type="btrfs",
                total_bytes=10_000,
                free_bytes=4_000,
                available_bytes=3_500,
                device_id="8:1",
                filesystem_root="/@home",
            ),
        ]

        inventory = StorageInventory(
            devices=[disk],
            filesystems=filesystems,
            filesystem_groups=group_filesystems(filesystems),
        )

        output = StringIO()
        console = Console(
            file=output,
            width=100,
            force_terminal=False,
        )

        render_compact(inventory, console, include_all=True)
        rendered = output.getvalue()

        self.assertIn("Filesystem Details", rendered)
        self.assertIn("/", rendered)
        self.assertIn("/home", rendered)
        self.assertIn("subvolume root: /@", rendered)
        self.assertIn("subvolume root: /@home", rendered)
        self.assertIn("Usage:", rendered)
        self.assertIn("60.0%", rendered)
        self.assertIn("█", rendered)
        self.assertIn("░", rendered)
        self.assertIn("Mounts:", rendered)

        # The filesystem source must appear once in the grouped details.
        details = rendered.split("Filesystem Details", 1)[1]
        self.assertEqual(details.count("/dev/sda1"), 1)

    def test_all_mode_shows_nonpersistent_mounts_and_image_warning(self):
        image = FilesystemUsage(
            mountpoint="/opt/example",
            source="/opt/example.dwarfs",
            filesystem_type="fuse.dwarfs",
            total_bytes=100,
            free_bytes=0,
            available_bytes=0,
            device_id="0:91",
        )
        temporary = FilesystemUsage(
            mountpoint="/run",
            source="tmpfs",
            filesystem_type="tmpfs",
            total_bytes=100,
            free_bytes=50,
            available_bytes=40,
            device_id="0:26",
        )
        inventory = StorageInventory(
            devices=[],
            filesystems=[image, temporary],
            filesystem_groups=group_filesystems([image, temporary]),
        )

        output = StringIO()
        console = Console(file=output, width=120, force_terminal=False)

        render_compact(inventory, console, include_all=True)
        rendered = output.getvalue()

        self.assertIn("Application Image", rendered)
        self.assertIn("/opt/example", rendered)
        self.assertIn("Temporary", rendered)
        self.assertIn("100.0%", rendered)
        self.assertIn("does not indicate a full physical disk", rendered)


    def test_detailed_mount_view_does_not_present_zero_capacity_as_measurement(self):
        filesystem = FilesystemUsage(
            mountpoint="/unavailable",
            source="unknown",
            filesystem_type="unknownfs",
            total_bytes=0,
            free_bytes=0,
            available_bytes=0,
        )
        inventory = StorageInventory(
            devices=[],
            filesystems=[filesystem],
            filesystem_groups=group_filesystems([filesystem]),
        )
        output = StringIO()
        console = Console(file=output, width=120, force_terminal=False)

        render_all(inventory, console)

        rendered = output.getvalue()
        self.assertIn("Unavailable", rendered)
        self.assertIn("N/A", rendered)
        self.assertNotIn("0 B", rendered)


class TestUsageBar(unittest.TestCase):
    def test_usage_color_thresholds(self):
        self.assertEqual(_usage_color(0), "green")
        self.assertEqual(_usage_color(69.9), "green")
        self.assertEqual(_usage_color(70), "yellow")
        self.assertEqual(_usage_color(89.9), "yellow")
        self.assertEqual(_usage_color(90), "red")
        self.assertEqual(_usage_color(100), "red")

    def test_usage_bar_displays_percentage(self):
        bar = _usage_bar(75, 100, width=24)

        self.assertIn("75.0%", str(bar))
        self.assertIn("█", str(bar))
        self.assertIn("░", str(bar))

    def test_usage_bar_handles_missing_capacity(self):
        bar = _usage_bar(0, 0)

        self.assertEqual(str(bar), "Usage data unavailable")

    def test_usage_bar_clamps_percentage(self):
        full_bar = _usage_bar(150, 100, width=24)
        empty_bar = _usage_bar(-10, 100, width=24)

        self.assertIn("100.0%", str(full_bar))
        self.assertIn("0.0%", str(empty_bar))


class TestStorageTopology(unittest.TestCase):
    def test_partition_geometry_displays_zero_start_sector(self):
        partition = BlockDevice(
            name="sda1",
            path="/dev/sda1",
            device_type="part",
            size_bytes=512,
            partition_metadata=PartitionMetadata(
                start_sector=0,
                end_sector=0,
            ),
        )
        inventory = StorageInventory(
            devices=[partition],
            filesystems=[],
            filesystem_groups=[],
        )
        output = StringIO()

        render_all(
            inventory,
            Console(file=output, width=160, force_terminal=False),
        )

        rendered = output.getvalue()
        self.assertIn("Start sector", rendered)
        self.assertIn("End sector", rendered)
        geometry_row = next(
            line for line in rendered.splitlines() if "/dev/sda1" in line
        )
        self.assertGreaterEqual(geometry_row.count("0"), 2)

    def test_partition_parent_relationship_is_not_repeated_in_topology(self):
        inventory = StorageInventory(
            devices=[],
            filesystems=[],
            filesystem_groups=[],
            relationships=[
                StorageRelationship(
                    relationship_type=StorageRelationshipType.BACKED_BY,
                    upper=StorageDeviceReference(
                        "/dev/sda1", kind=StorageDeviceKind.PARTITION
                    ),
                    lower=(
                        StorageDeviceReference(
                            "/dev/sda", kind=StorageDeviceKind.PHYSICAL
                        ),
                    ),
                )
            ],
        )
        output = StringIO()
        render_all(
            inventory,
            Console(file=output, width=200, force_terminal=False),
        )
        self.assertNotIn("Storage Topology", output.getvalue())

    def test_all_mode_shows_verified_relationships(self):
        relationship = StorageRelationship(
            relationship_type=StorageRelationshipType.ENCRYPTED_MAPPING,
            upper=StorageDeviceReference(
                "/dev/mapper/crypt-data",
                kind=StorageDeviceKind.LOGICAL,
            ),
            lower=(
                StorageDeviceReference(
                    "/dev/sda2",
                    kind=StorageDeviceKind.PARTITION,
                ),
            ),
        )
        inventory = StorageInventory(
            devices=[],
            filesystems=[],
            filesystem_groups=[],
            relationships=[relationship],
        )
        output = StringIO()
        console = Console(file=output, width=100, force_terminal=False)

        render_compact(inventory, console, include_all=True)

        rendered = output.getvalue()
        self.assertIn("Storage Topology", rendered)
        self.assertIn("/dev/mapper/crypt-data", rendered)
        self.assertIn("encrypted_mapping", rendered)
        self.assertIn("/dev/sda2", rendered)

    def test_compact_mode_does_not_render_topology(self):
        inventory = StorageInventory(
            devices=[],
            filesystems=[],
            filesystem_groups=[],
            relationships=[
                StorageRelationship(
                    relationship_type=StorageRelationshipType.BACKED_BY,
                    upper=StorageDeviceReference("/dev/upper"),
                    lower=(StorageDeviceReference("/dev/lower"),),
                )
            ],
        )
        output = StringIO()
        console = Console(file=output, width=100, force_terminal=False)

        render_compact(inventory, console)

        rendered = output.getvalue()
        self.assertNotIn("Storage Topology", rendered)
        self.assertNotIn("Partition Geometry", rendered)
        self.assertNotIn("Persistent Mount Configuration", rendered)

    def test_all_mode_deduplicates_topology_aliases_by_canonical_path(self):
        relationship = StorageRelationship(
            relationship_type=StorageRelationshipType.BACKED_BY,
            upper=StorageDeviceReference(
                "/dev/mapper/data",
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
        )
        inventory = StorageInventory(
            devices=[],
            filesystems=[],
            filesystem_groups=[],
            relationships=[relationship],
        )
        output = StringIO()
        console = Console(file=output, width=100, force_terminal=False)

        render_all(inventory, console)

        rendered = output.getvalue()
        topology = rendered.split("Storage Topology", 1)[1]
        self.assertEqual(topology.count("/dev/sda1"), 1)
        self.assertNotIn("/dev/disk/by-uuid/data", topology)


class TestAdaptiveTerminalLayout(unittest.TestCase):
    def _inventory(self):
        disk = BlockDevice(
            name="disk-with-a-very-long-name",
            path="/dev/disk-with-a-very-long-name",
            device_type="disk",
            size_bytes=10_000_000,
            physical=True,
            model="A very long storage model name that must remain visible",
            transport="usb",
            rotational=False,
        )
        partition = BlockDevice(
            name="partition-with-a-long-name",
            path="/dev/partition-with-a-long-name",
            device_type="part",
            size_bytes=5_000_000,
            parent_name=disk.name,
            filesystem_type="ext4",
            mountpoints=["/a/mountpoint/with/a/long/path"],
        )
        disk.children.append(partition)
        filesystem = FilesystemUsage(
            mountpoint=partition.mountpoints[0],
            source=partition.path,
            filesystem_type="ext4",
            total_bytes=5_000_000,
            free_bytes=2_000_000,
            available_bytes=1_500_000,
        )
        return StorageInventory(
            devices=[disk],
            filesystems=[filesystem],
            filesystem_groups=group_filesystems([filesystem]),
        )

    def test_wide_compact_view_keeps_full_device_details_without_notice(self):
        output = StringIO()
        render_compact(
            self._inventory(),
            Console(file=output, width=240, force_terminal=False),
            include_all=True,
        )
        rendered = output.getvalue()
        self.assertIn("A very long storage model name that must remain visible", rendered)
        self.assertIn("[usb]", rendered)
        self.assertNotIn("Warning: Terminal width is limited", rendered)

    def test_narrow_compact_view_reduces_secondary_details_with_notice(self):
        output = StringIO()
        render_compact(
            self._inventory(),
            Console(file=output, width=60, force_terminal=False),
            include_all=True,
        )
        rendered = output.getvalue()
        self.assertIn("disk-with-a-very", rendered)
        self.assertIn("ext4", rendered)
        self.assertIn("Warning: Terminal width is limited", rendered)
        self.assertNotIn(
            "A very long storage model name that must remain visible",
            rendered,
        )

    def test_wide_table_keeps_optional_columns_and_narrow_table_warns(self):
        inventory = self._inventory()
        wide = StringIO()
        render_all(
            inventory,
            Console(file=wide, width=260, force_terminal=False),
        )
        wide_text = wide.getvalue()
        self.assertIn("Model", wide_text)
        self.assertIn("Transport", wide_text)
        self.assertIn("Filesystem Root", wide_text)
        self.assertNotIn("Warning: Terminal width is limited", wide_text)

        narrow = StringIO()
        render_all(
            inventory,
            Console(file=narrow, width=70, force_terminal=False),
        )
        narrow_text = narrow.getvalue()
        self.assertIn("Warning: Terminal width is limited", narrow_text)
        self.assertIn("disk-with-a-very", narrow_text)
        self.assertIn("/a/mou", narrow_text)

    def test_simple_table_narrow_warning_only_when_reduced(self):
        inventory = self._inventory()
        output = StringIO()
        render_simple(
            inventory,
            Console(file=output, width=70, force_terminal=False),
        )
        self.assertIn("Warning: Terminal width is limited", output.getvalue())

    def test_intermediate_width_uses_deterministic_reduction_boundary(self):
        inventory = self._inventory()
        full = StringIO()
        render_simple(
            inventory,
            Console(file=full, width=100, force_terminal=False),
        )
        reduced = StringIO()
        render_simple(
            inventory,
            Console(file=reduced, width=99, force_terminal=False),
        )
        self.assertIn("Warning: Terminal width is limited", full.getvalue())
        self.assertIn("Warning: Terminal width is limited", reduced.getvalue())

    def test_width_never_changes_inventory_or_json_data(self):
        inventory = self._inventory()
        before = inventory_to_dict(inventory, include_all=True)
        for width in (60, 240):
            render_compact(
                inventory,
                Console(file=StringIO(), width=width, force_terminal=False),
                include_all=True,
            )
        self.assertEqual(inventory_to_dict(inventory, include_all=True), before)

    def test_classic_wide_layout_has_stable_headers_and_all_cells(self):
        output = StringIO()
        render_classic(
            self._inventory(),
            Console(file=output, width=240, force_terminal=False),
        )
        rendered = output.getvalue()
        for header in (
            "Filesystem", "Type", "Size", "Used", "Avail", "Use%", "Mounted on"
        ):
            self.assertIn(header, rendered)
        self.assertIn("/dev/partition-with-a-long-name", rendered)
        self.assertNotIn("Warning: Terminal width is limited", rendered)

    def test_classic_narrow_layout_keeps_schema_and_warns(self):
        output = StringIO()
        render_classic(
            self._inventory(),
            Console(file=output, width=70, force_terminal=False),
        )
        rendered = output.getvalue()
        for header in (
            "Filesystem", "Type", "Size", "Used", "Avail", "Use%", "Mounted on"
        ):
            self.assertIn(header, rendered)
        self.assertIn("/dev/part", rendered)
        self.assertIn("/a/mountp", rendered)
        self.assertIn("Warning: Terminal width is limited", rendered)

    def test_classic_long_mountpoint_alone_does_not_warn(self):
        filesystem = FilesystemUsage(
            mountpoint="/a/mountpoint/" + "nested/" * 20,
            source="/dev/sda1",
            filesystem_type="ext4",
            total_bytes=5_000_000,
            free_bytes=2_000_000,
            available_bytes=1_500_000,
        )
        inventory = StorageInventory(
            devices=[],
            filesystems=[filesystem],
            filesystem_groups=group_filesystems([filesystem]),
        )
        output = StringIO()
        render_classic(
            inventory,
            Console(file=output, width=100, force_terminal=False),
        )
        rendered = output.getvalue()
        self.assertIn("Mounted on", rendered)
        self.assertIn("/a/mountpoint/", rendered)
        self.assertNotIn("Warning: Terminal width is limited", rendered)

    def test_classic_warning_tracks_actual_layout_degradation_by_width(self):
        inventory = self._inventory()
        expected_warning = {
            80: True,
            100: True,
            120: False,
            160: False,
        }
        for width, warning_expected in expected_warning.items():
            output = StringIO()
            render_classic(
                inventory,
                Console(file=output, width=width, force_terminal=False),
            )
            rendered = output.getvalue()
            self.assertEqual(
                "Warning: Terminal width is limited" in rendered,
                warning_expected,
                width,
            )
            for header in (
                "Filesystem", "Type", "Size", "Used", "Avail", "Use%",
                "Mounted on",
            ):
                self.assertIn(header, rendered)

    def test_table_and_classic_layouts_fit_all_requested_widths(self):
        inventory = self._inventory()
        for width in (80, 100, 120, 160):
            for renderer in (render_simple, render_all, render_classic):
                output = StringIO()
                renderer(
                    inventory,
                    Console(file=output, width=width, force_terminal=False),
                )
                rendered = output.getvalue()
                self.assertLessEqual(
                    max(map(len, rendered.splitlines())),
                    width,
                    (renderer.__name__, width),
                )
                self.assertIn("/dev/pa", rendered)
                if width >= 120:
                    self.assertIn("4.77 MiB", rendered)

            classic = StringIO()
            render_classic(
                inventory,
                Console(file=classic, width=width, force_terminal=False),
            )
            classic_text = classic.getvalue()
            for header in (
                "Filesystem", "Type", "Size", "Used", "Avail", "Use%",
                "Mounted on",
            ):
                self.assertIn(header, classic_text)

    def test_classic_preserves_na_rows_and_repeated_layout(self):
        filesystem = FilesystemUsage(
            mountpoint="/unavailable",
            source="/dev/long-source-name",
            filesystem_type="unknownfs",
            total_bytes=0,
            free_bytes=0,
            available_bytes=0,
        )
        inventory = StorageInventory(
            devices=[],
            filesystems=[filesystem],
            filesystem_groups=group_filesystems([filesystem]),
        )
        first = StringIO()
        second = StringIO()
        render_classic(
            inventory,
            Console(file=first, width=120, force_terminal=False),
        )
        render_classic(
            inventory,
            Console(file=second, width=120, force_terminal=False),
        )
        self.assertEqual(first.getvalue(), second.getvalue())
        self.assertIn("N/A", first.getvalue())
        self.assertIn("/dev/long-source-name", first.getvalue())

    def test_classic_repeated_render_is_deterministic(self):
        first = StringIO()
        second = StringIO()
        inventory = self._inventory()
        render_classic(
            inventory,
            Console(file=first, width=90, force_terminal=False),
        )
        render_classic(
            inventory,
            Console(file=second, width=90, force_terminal=False),
        )
        self.assertEqual(first.getvalue(), second.getvalue())


if __name__ == "__main__":
    unittest.main()
