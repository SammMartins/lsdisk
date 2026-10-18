"""Tests for read-only Linux MD RAID relationship discovery."""

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lsdisk.collectors.mdraid import collect_mdraid_relationships
from lsdisk.models import BlockDevice, StorageRelationshipType


class TestMdraidCollector(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.sysfs = Path(self.temp_dir.name) / "class" / "block"
        self.sysfs.mkdir(parents=True)
        self.mdstat = Path(self.temp_dir.name) / "mdstat"
        self.mdstat.write_text(
            "Personalities : [raid1]\n"
            "md0 : active raid1 sda1[0] sdb1[1]\n"
            "      100 blocks [2/2] [UU]\n",
            encoding="utf-8",
        )
        self.devices = [
            BlockDevice("sda1", "/dev/sda1", "part", 100),
            BlockDevice("sdb1", "/dev/sdb1", "part", 100),
        ]
        slaves = self.sysfs / "md0" / "slaves"
        slaves.mkdir(parents=True)
        (slaves / "sda1").symlink_to("/dev/null")
        (slaves / "sdb1").symlink_to("/dev/null")

    def test_discovers_array_with_multiple_members(self):
        relationships = collect_mdraid_relationships(
            self.devices, sysfs_path=self.sysfs, mdstat_path=self.mdstat
        )
        self.assertEqual(len(relationships), 1)
        self.assertEqual(
            relationships[0].relationship_type,
            StorageRelationshipType.RAID_MEMBER,
        )
        self.assertEqual(relationships[0].upper.identifier, "/dev/md0")
        self.assertEqual(
            {item.identifier for item in relationships[0].lower},
            {"/dev/sda1", "/dev/sdb1"},
        )

    def test_discovers_multiple_arrays_and_deduplicates_members(self):
        second = self.sysfs / "md1" / "slaves"
        second.mkdir(parents=True)
        (second / "sda1").symlink_to("/dev/null")
        (second / "sda1-copy").symlink_to("/dev/null")
        self.devices.append(BlockDevice("sda1-copy", "/dev/sda1", "part", 100))
        self.mdstat.write_text(
            "md0 : active raid1 sda1[0] sdb1[1]\n"
            "md1 : active raid1 sda1[0]\n",
            encoding="utf-8",
        )
        relationships = collect_mdraid_relationships(
            self.devices, sysfs_path=self.sysfs, mdstat_path=self.mdstat
        )
        self.assertEqual(len(relationships), 2)
        self.assertEqual(len(relationships[0].lower), 2)
        self.assertEqual(len(relationships[1].lower), 1)

    def test_missing_interfaces_return_no_relationships(self):
        self.assertEqual(
            collect_mdraid_relationships(
                self.devices,
                sysfs_path=Path(self.temp_dir.name) / "missing",
                mdstat_path=Path(self.temp_dir.name) / "missing-stat",
            ),
            [],
        )

    def test_empty_mdstat_does_not_hide_sysfs_topology(self):
        self.mdstat.write_text("", encoding="utf-8")
        self.assertEqual(
            len(collect_mdraid_relationships(
                self.devices, sysfs_path=self.sysfs, mdstat_path=self.mdstat
            )),
            1,
        )

    def test_unresolved_member_is_not_invented(self):
        (self.sysfs / "md0" / "slaves" / "sdb1").unlink()
        (self.sysfs / "md0" / "slaves" / "missing").symlink_to("/dev/null")
        relationships = collect_mdraid_relationships(
            self.devices, sysfs_path=self.sysfs, mdstat_path=self.mdstat
        )
        self.assertEqual(len(relationships), 1)
        self.assertEqual(
            [member.identifier for member in relationships[0].lower],
            ["/dev/sda1"],
        )

    @patch("lsdisk.collectors.mdraid.subprocess.run")
    def test_optional_mdadm_fallback_handles_missing_permission_and_timeout(self, run):
        (self.sysfs / "md0" / "slaves" / "sda1").unlink()
        (self.sysfs / "md0" / "slaves" / "sdb1").unlink()
        run.side_effect = FileNotFoundError
        self.assertEqual(
            collect_mdraid_relationships(
                self.devices, sysfs_path=self.sysfs, mdstat_path=self.mdstat
            ),
            [],
        )
        run.side_effect = PermissionError
        self.assertEqual(
            collect_mdraid_relationships(
                self.devices, sysfs_path=self.sysfs, mdstat_path=self.mdstat
            ),
            [],
        )
        run.side_effect = subprocess.TimeoutExpired(cmd="mdadm", timeout=2)
        self.assertEqual(
            collect_mdraid_relationships(
                self.devices, sysfs_path=self.sysfs, mdstat_path=self.mdstat
            ),
            [],
        )

    @patch("lsdisk.collectors.mdraid.subprocess.run")
    def test_mdadm_export_resolves_members_when_sysfs_is_empty(self, run):
        (self.sysfs / "md0" / "slaves" / "sda1").unlink()
        (self.sysfs / "md0" / "slaves" / "sdb1").unlink()
        run.return_value = subprocess.CompletedProcess(
            args=["mdadm"], returncode=0,
            stdout="MD_DEVICE_0_DEV=/dev/sda1\nMD_DEVICE_1_DEV=/dev/sdb1\n",
            stderr="",
        )
        relationships = collect_mdraid_relationships(
            self.devices, sysfs_path=self.sysfs, mdstat_path=self.mdstat
        )
        self.assertEqual(len(relationships), 1)
        self.assertEqual(len(relationships[0].lower), 2)

    def test_malformed_mdstat_and_duplicate_sysfs_entries_are_safe(self):
        self.mdstat.write_text("not mdstat\n", encoding="utf-8")
        (self.sysfs / "md0" / "slaves" / "sda1-copy").symlink_to("/dev/null")
        self.devices.append(BlockDevice("sda1-copy", "/dev/sda1", "part", 100))
        relationships = collect_mdraid_relationships(
            self.devices, sysfs_path=self.sysfs, mdstat_path=self.mdstat
        )
        self.assertEqual(len(relationships), 1)
        self.assertEqual(len(relationships[0].lower), 2)

    def test_skips_md_array_cycles(self):
        md1_slaves = self.sysfs / "md1" / "slaves"
        md1_slaves.mkdir(parents=True)
        (md1_slaves / "md0").symlink_to("/dev/null")
        self.devices.extend([
            BlockDevice("md0", "/dev/md0", "disk", 100, physical=False),
            BlockDevice("md1", "/dev/md1", "disk", 100, physical=False),
        ])
        (self.sysfs / "md0" / "slaves" / "sda1").unlink()
        (self.sysfs / "md0" / "slaves" / "sdb1").unlink()
        (self.sysfs / "md0" / "slaves" / "md1").symlink_to("/dev/null")
        self.mdstat.write_text(
            "md0 : active raid1 md1[0]\n"
            "md1 : active raid1 md0[0]\n",
            encoding="utf-8",
        )
        relationships = collect_mdraid_relationships(
            self.devices, sysfs_path=self.sysfs, mdstat_path=self.mdstat
        )
        self.assertEqual(len(relationships), 1)

    def test_invalid_mdstat_encoding_is_non_fatal(self):
        self.mdstat.write_bytes(b"\xff\xfe")
        relationships = collect_mdraid_relationships(
            self.devices, sysfs_path=self.sysfs, mdstat_path=self.mdstat
        )
        self.assertEqual(len(relationships), 1)


if __name__ == "__main__":
    unittest.main()
