"""Tests for the compact terminal interface."""

import unittest
from io import StringIO

from rich.console import Console

from storix.analyzers.filesystems import group_filesystems
from storix.inventory import StorageInventory
from storix.models import BlockDevice, FilesystemUsage
from storix.ui.terminal import render_compact


class TestCompactFilesystemDetails(unittest.TestCase):
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

        # The filesystem source must appear once in the grouped details.
        details = rendered.split("Filesystem Details", 1)[1]
        self.assertEqual(details.count("/dev/sda1"), 1)


if __name__ == "__main__":
    unittest.main()
