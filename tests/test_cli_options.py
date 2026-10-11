"""Tests for terminal output mode options."""

import unittest
from contextlib import redirect_stderr
from io import StringIO

from lsdisk.main import build_parser


class TestTableModeOptions(unittest.TestCase):
    def test_accepts_short_and_long_table_mode_options(self):
        self.assertTrue(
            build_parser().parse_args(["-T"]).table_mode
        )
        self.assertTrue(
            build_parser().parse_args(["--table-mode"]).table_mode
        )

    def test_json_and_table_mode_are_mutually_exclusive(self):
        with redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit) as context:
                build_parser().parse_args(["--json", "--table-mode"])

        self.assertEqual(context.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
