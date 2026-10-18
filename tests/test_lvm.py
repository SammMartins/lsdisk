"""Tests for read-only LVM relationship discovery."""

import json
import subprocess
import unittest
from unittest.mock import patch

from lsdisk.collectors.lvm import collect_lvm_relationships
from lsdisk.models import BlockDevice, StorageRelationshipType


def report(rows: list[dict[str, str]], section: str) -> str:
    return json.dumps({"report": [{section: {"rows": rows}}]})


class TestLvmCollector(unittest.TestCase):
    def setUp(self):
        self.devices = [
            BlockDevice(
                name="sda1",
                path="/dev/sda1",
                device_type="part",
                size_bytes=100,
            ),
            BlockDevice(
                name="sdb1",
                path="/dev/sdb1",
                device_type="part",
                size_bytes=200,
            ),
        ]

    @patch("lsdisk.collectors.lvm.subprocess.run")
    def test_discovers_one_pv_vg_and_lv(self, run):
        run.side_effect = [
            subprocess.CompletedProcess(
                args=["pvs"], returncode=0,
                stdout=report(
                    [{"pv_name": "/dev/sda1", "vg_name": "data", "pv_uuid": "pv-1"}],
                    "pv",
                ), stderr="",
            ),
            subprocess.CompletedProcess(
                args=["vgs"], returncode=0,
                stdout=report([{"vg_name": "data", "vg_uuid": "vg-1"}], "vg"),
                stderr="",
            ),
            subprocess.CompletedProcess(
                args=["lvs"], returncode=0,
                stdout=report(
                    [{"lv_path": "/dev/data/root", "lv_name": "root",
                      "vg_name": "data", "lv_uuid": "lv-1"}],
                    "lv",
                ), stderr="",
            ),
        ]

        relationships = collect_lvm_relationships(self.devices)

        self.assertEqual(len(relationships), 3)
        self.assertEqual(
            {item.relationship_type for item in relationships},
            {
                StorageRelationshipType.LVM_PHYSICAL_VOLUME,
                StorageRelationshipType.LVM_LOGICAL_VOLUME,
            },
        )
        self.assertEqual(run.call_count, 3)
        self.assertTrue(all("--reportformat" in call.args[0] for call in run.call_args_list))

    @patch("lsdisk.collectors.lvm.subprocess.run")
    def test_supports_multiple_pvs_and_lvs(self, run):
        run.side_effect = [
            subprocess.CompletedProcess(
                args=["pvs"], returncode=0,
                stdout=report(
                    [
                        {"pv_name": "/dev/sda1", "vg_name": "data", "pv_uuid": "1"},
                        {"pv_name": "/dev/sdb1", "vg_name": "data", "pv_uuid": "2"},
                    ], "pv",
                ), stderr="",
            ),
            subprocess.CompletedProcess(
                args=["vgs"], returncode=0,
                stdout=report([{"vg_name": "data", "vg_uuid": "vg"}], "vg"),
                stderr="",
            ),
            subprocess.CompletedProcess(
                args=["lvs"], returncode=0,
                stdout=report(
                    [
                        {"lv_name": "one", "vg_name": "data", "lv_uuid": "1"},
                        {"lv_name": "two", "vg_name": "data", "lv_uuid": "2"},
                    ], "lv",
                ), stderr="",
            ),
        ]
        relationships = collect_lvm_relationships(self.devices)
        vg_edges = [
            item for item in relationships
            if item.relationship_type == StorageRelationshipType.LVM_PHYSICAL_VOLUME
            and item.upper.identifier == "lvm:vg:data"
        ]
        lv_edges = [
            item for item in relationships
            if item.relationship_type == StorageRelationshipType.LVM_LOGICAL_VOLUME
        ]
        self.assertEqual(len(vg_edges[0].lower), 2)
        self.assertEqual(len(lv_edges), 2)

    @patch("lsdisk.collectors.lvm.subprocess.run")
    def test_missing_tool_or_malformed_output_returns_no_relationships(self, run):
        run.side_effect = FileNotFoundError
        self.assertEqual(collect_lvm_relationships(self.devices), [])

    @patch("lsdisk.collectors.lvm.subprocess.run")
    def test_permission_error_and_timeout_return_no_relationships(self, run):
        run.side_effect = PermissionError
        self.assertEqual(collect_lvm_relationships(self.devices), [])

        run.side_effect = subprocess.TimeoutExpired(cmd="pvs", timeout=2)
        self.assertEqual(collect_lvm_relationships(self.devices), [])

        run.side_effect = [
            subprocess.CompletedProcess(args=["pvs"], returncode=0, stdout="{", stderr=""),
            subprocess.CompletedProcess(args=["vgs"], returncode=0, stdout="{}", stderr=""),
            subprocess.CompletedProcess(args=["lvs"], returncode=0, stdout="{}", stderr=""),
        ]
        self.assertEqual(collect_lvm_relationships(self.devices), [])

        run.side_effect = [
            subprocess.CompletedProcess(args=["pvs"], returncode=0, stdout="[]", stderr=""),
            subprocess.CompletedProcess(args=["vgs"], returncode=0, stdout="[]", stderr=""),
            subprocess.CompletedProcess(args=["lvs"], returncode=0, stdout="[]", stderr=""),
        ]
        self.assertEqual(collect_lvm_relationships(self.devices), [])

    @patch("lsdisk.collectors.lvm.subprocess.run")
    def test_skips_incomplete_and_duplicate_metadata(self, run):
        run.side_effect = [
            subprocess.CompletedProcess(
                args=["pvs"], returncode=0,
                stdout=report(
                    [
                        {"pv_name": "/dev/sda1", "vg_name": "data", "pv_uuid": "1"},
                        {"pv_name": "/dev/sda1", "vg_name": "data", "pv_uuid": "1"},
                        {"pv_name": "/dev/sdb1", "vg_name": "", "pv_uuid": "2"},
                    ], "pv",
                ), stderr="",
            ),
            subprocess.CompletedProcess(
                args=["vgs"], returncode=0,
                stdout=report([{"vg_name": "data", "vg_uuid": "vg"}], "vg"),
                stderr="",
            ),
            subprocess.CompletedProcess(
                args=["lvs"], returncode=0,
                stdout=report([{"vg_name": "missing", "lv_name": "x"}], "lv"),
                stderr="",
            ),
        ]
        relationships = collect_lvm_relationships(self.devices)
        vg_relationships = [
            item for item in relationships
            if item.upper.identifier == "lvm:vg:data"
        ]
        self.assertEqual(len(vg_relationships), 1)
        self.assertEqual(len(vg_relationships[0].lower), 1)


if __name__ == "__main__":
    unittest.main()
