"""Tests for best-effort device identity resolution."""

import unittest

from lsdisk.device_paths import canonical_device_path


class TestCanonicalDevicePath(unittest.TestCase):
    def test_resolves_existing_device(self):
        self.assertEqual(canonical_device_path("/dev/null"), "/dev/null")

    def test_does_not_invent_identity_for_unresolved_path(self):
        self.assertIsNone(canonical_device_path("/dev/does-not-exist-lsdisk"))

    def test_rejects_non_device_paths(self):
        self.assertIsNone(canonical_device_path("/tmp/device"))
