"""Tests for the compact terminal interface."""

import unittest
from io import StringIO

from rich.console import Console

from lsdisk.analyzers.filesystems import group_filesystems
from lsdisk.inventory import StorageInventory
from lsdisk.models import BlockDevice, FilesystemUsage
from lsdisk.ui.terminal import render_compact
from lsdisk.ui.terminal import (
    _usage_bar,
    _usage_color,
    render_compact,
)


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
        self.assertIn("Usage:", rendered)
        self.assertIn("60.0%", rendered)
        self.assertIn("█", rendered)
        self.assertIn("░", rendered)
        self.assertIn("Mounts:", rendered)

        # The filesystem source must appear once in the grouped details.
        details = rendered.split("Filesystem Details", 1)[1]
        self.assertEqual(details.count("/dev/sda1"), 1)

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

if __name__ == "__main__":
    unittest.main()
