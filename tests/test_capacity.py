"""Unit tests for the capacity analyzer."""

import unittest

from lsdisk.analyzers.capacity import Capacity, format_bytes


class TestCapacity(unittest.TestCase):
    def test_calculates_used_space(self):
        capacity = Capacity(total_bytes=1000, available_bytes=250)
        self.assertEqual(capacity.used_bytes, 750)

    def test_calculates_used_percentage(self):
        capacity = Capacity(total_bytes=1000, available_bytes=280)
        self.assertAlmostEqual(capacity.used_percent, 72.0)

    def test_calculates_available_percentage(self):
        capacity = Capacity(total_bytes=1000, available_bytes=280)
        self.assertAlmostEqual(capacity.available_percent, 28.0)

    def test_empty_capacity(self):
        capacity = Capacity(total_bytes=0, available_bytes=0)
        self.assertEqual(capacity.used_percent, 0.0)

    def test_rejects_negative_total_capacity(self):
        with self.assertRaises(ValueError):
            Capacity(total_bytes=-1, available_bytes=0)

    def test_rejects_negative_available_space(self):
        with self.assertRaises(ValueError):
            Capacity(total_bytes=100, available_bytes=-1)

    def test_rejects_available_space_above_total(self):
        with self.assertRaises(ValueError):
            Capacity(total_bytes=100, available_bytes=101)

    def test_formats_gib(self):
        self.assertEqual(format_bytes(1024**3), "1.00 GiB")

    def test_formats_zero(self):
        self.assertEqual(format_bytes(0), "0 B")


if __name__ == "__main__":
    unittest.main()
