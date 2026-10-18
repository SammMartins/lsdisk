"""Tests for read-only block-device signature probing."""

import subprocess
import unittest
from unittest.mock import patch

from lsdisk.collectors.filesystem_metadata import (
    FilesystemMetadata,
    _parse_export_output,
    probe_filesystem,
    probe_filesystem_outcome,
)
from lsdisk.models import ProbeState
from lsdisk.collectors.filesystem_metadata import (
    collect_lsblk_metadata,
)


class TestLsblkMetadata(unittest.TestCase):
    @patch("lsdisk.collectors.filesystem_metadata.subprocess.run")
    def test_collects_metadata_from_nested_devices(self, run):
        run.return_value = subprocess.CompletedProcess(
            args=["lsblk"],
            returncode=0,
            stdout=(
                '{"blockdevices": [{"path": "/dev/sda", "children": ['
                '{"path": "/dev/sda1", "fstype": "btrfs", '
                '"label": "OMARCHY_DATA", "uuid": "test-uuid"}'
                ']}]}'
            ),
            stderr="",
        )

        metadata = collect_lsblk_metadata()

        self.assertEqual(
            metadata["/dev/sda1"],
            FilesystemMetadata(
                filesystem_type="btrfs",
                label="OMARCHY_DATA",
                uuid="test-uuid",
            ),
        )


class TestFilesystemMetadataParser(unittest.TestCase):
    def test_parses_filesystem_type_label_and_uuid(self):
        metadata = _parse_export_output(
            "DEVNAME=/dev/sda1\nTYPE=ext4\nLABEL=System\\x20Disk\nUUID=abc-123\n"
        )
        self.assertEqual(
            metadata,
            FilesystemMetadata(
                filesystem_type="ext4",
                label="System Disk",
                uuid="abc-123",
            ),
        )

    def test_preserves_non_hex_backslashes_when_unescaping(self):
        metadata = _parse_export_output(
            "TYPE=ext4\nLABEL=" + r"path\\name\x3ddata" + "\n"
        )
        self.assertEqual(metadata.label, r"path\\name=data")

    def test_returns_none_when_no_metadata_is_present(self):
        self.assertIsNone(_parse_export_output("DEVNAME=/dev/sda1\n"))


class TestFilesystemMetadataProbe(unittest.TestCase):
    @patch("lsdisk.collectors.filesystem_metadata.subprocess.run")
    def test_probes_device_without_mounting(self, run):
        run.return_value = subprocess.CompletedProcess(
            args=["blkid"],
            returncode=0,
            stdout="TYPE=crypto_LUKS\nUUID=luks-123\n",
            stderr="",
        )

        metadata = probe_filesystem("/dev/sda2")

        self.assertEqual(metadata.filesystem_type, "crypto_LUKS")
        self.assertEqual(metadata.uuid, "luks-123")
        args, kwargs = run.call_args
        self.assertEqual(args[0], ["blkid", "--probe", "--output", "export", "/dev/sda2"])
        self.assertEqual(kwargs["timeout"], 2)

    @patch("lsdisk.collectors.filesystem_metadata.subprocess.run")
    def test_returns_none_for_unrecognized_device(self, run):
        run.return_value = subprocess.CompletedProcess(
            args=["blkid"], returncode=2, stdout="", stderr=""
        )
        self.assertIsNone(probe_filesystem("/dev/sda3"))

    @patch("lsdisk.collectors.filesystem_metadata.subprocess.run")
    def test_handles_missing_blkid(self, run):
        run.side_effect = FileNotFoundError
        self.assertIsNone(probe_filesystem("/dev/sda1"))

    @patch("lsdisk.collectors.filesystem_metadata.subprocess.run")
    def test_handles_probe_timeout(self, run):
        run.side_effect = subprocess.TimeoutExpired(cmd="blkid", timeout=2)
        self.assertIsNone(probe_filesystem("/dev/sda1"))

    @patch("lsdisk.collectors.filesystem_metadata.subprocess.run")
    def test_reports_recognized_signature(self, run):
        run.return_value = subprocess.CompletedProcess(
            args=["blkid"], returncode=0,
            stdout="TYPE=crypto_LUKS\nUUID=luks-123\n", stderr="",
        )
        outcome = probe_filesystem_outcome("/dev/sda1")
        self.assertEqual(outcome.state, ProbeState.RECOGNIZED)
        self.assertEqual(outcome.metadata.filesystem_type, "crypto_LUKS")

    @patch("lsdisk.collectors.filesystem_metadata.subprocess.run")
    def test_reports_successful_probe_without_signature(self, run):
        run.return_value = subprocess.CompletedProcess(
            args=["blkid"], returncode=0, stdout="", stderr=""
        )
        self.assertEqual(
            probe_filesystem_outcome("/dev/sda1").state,
            ProbeState.NO_SIGNATURE,
        )

    @patch("lsdisk.collectors.filesystem_metadata.subprocess.run")
    def test_preserves_partial_metadata(self, run):
        run.return_value = subprocess.CompletedProcess(
            args=["blkid"], returncode=0, stdout="UUID=partial-uuid\n", stderr=""
        )
        outcome = probe_filesystem_outcome("/dev/sda1")
        self.assertEqual(outcome.state, ProbeState.RECOGNIZED)
        self.assertEqual(outcome.metadata.uuid, "partial-uuid")

    @patch("lsdisk.collectors.filesystem_metadata.subprocess.run")
    def test_reports_missing_tool_as_unavailable(self, run):
        run.side_effect = FileNotFoundError
        self.assertEqual(
            probe_filesystem_outcome("/dev/sda1").state,
            ProbeState.UNAVAILABLE,
        )

    @patch("lsdisk.collectors.filesystem_metadata.subprocess.run")
    def test_reports_timeout_as_unavailable(self, run):
        run.side_effect = subprocess.TimeoutExpired(cmd="blkid", timeout=2)
        self.assertEqual(
            probe_filesystem_outcome("/dev/sda1").state,
            ProbeState.UNAVAILABLE,
        )

    @patch("lsdisk.collectors.filesystem_metadata.subprocess.run")
    def test_reports_permission_error_as_unavailable(self, run):
        run.return_value = subprocess.CompletedProcess(
            args=["blkid"], returncode=2, stdout="",
            stderr="blkid: permission denied",
        )
        self.assertEqual(
            probe_filesystem_outcome("/dev/sda1").state,
            ProbeState.UNAVAILABLE,
        )

    @patch("lsdisk.collectors.filesystem_metadata.subprocess.run")
    def test_reports_malformed_output_as_error(self, run):
        run.return_value = subprocess.CompletedProcess(
            args=["blkid"], returncode=0, stdout="not export output\n", stderr=""
        )
        self.assertEqual(
            probe_filesystem_outcome("/dev/sda1").state,
            ProbeState.ERROR,
        )

    @patch("lsdisk.collectors.filesystem_metadata.subprocess.run")
    def test_rejects_non_device_paths(self, run):
        self.assertIsNone(probe_filesystem("relative/path"))
        run.assert_not_called()


class TestLsblkMetadataFailures(unittest.TestCase):
    @patch("lsdisk.collectors.filesystem_metadata.subprocess.run")
    def test_handles_malformed_json(self, run):
        run.return_value = subprocess.CompletedProcess(
            args=["lsblk"], returncode=0, stdout="{", stderr=""
        )
        self.assertEqual(collect_lsblk_metadata(), {})

    @patch("lsdisk.collectors.filesystem_metadata.subprocess.run")
    def test_handles_timeout(self, run):
        run.side_effect = subprocess.TimeoutExpired(cmd="lsblk", timeout=2)
        self.assertEqual(collect_lsblk_metadata(), {})


if __name__ == "__main__":
    unittest.main()
