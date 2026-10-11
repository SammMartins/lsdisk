"""Tests for the lsdisk command-line interface."""

import json
import unittest
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from unittest.mock import patch

from lsdisk.inventory import StorageInventory
from lsdisk.main import build_parser, main


class TestCommandLineParser(unittest.TestCase):
    def test_default_mode_is_simple(self):
        args = build_parser().parse_args([])
        self.assertFalse(args.all)
        self.assertFalse(args.json)

    def test_all_mode(self):
        args = build_parser().parse_args(["--all"])
        self.assertTrue(args.all)

    def test_json_mode(self):
        args = build_parser().parse_args(["--all", "--json"])
        self.assertTrue(args.all)
        self.assertTrue(args.json)

    def test_color_options(self):
        self.assertEqual(
            build_parser().parse_args(["--color", "never"]).color,
            "never",
        )
        self.assertEqual(
            build_parser().parse_args(["--no-color"]).color,
            "never",
        )

    def test_simple_and_all_are_mutually_exclusive(self):
        output = StringIO()

        with redirect_stderr(output):
            with self.assertRaises(SystemExit) as context:
                build_parser().parse_args(["--simple", "--all"])

        self.assertEqual(context.exception.code, 2)


class TestCommandExecution(unittest.TestCase):
    def test_help_exits_without_collecting_inventory(self):
        with patch("lsdisk.main.collect_storage_inventory") as collector:
            with redirect_stdout(StringIO()):
                with self.assertRaises(SystemExit) as context:
                    main(["--help"])

        self.assertEqual(context.exception.code, 0)
        collector.assert_not_called()

    def test_version_exits_without_collecting_inventory(self):
        with patch("lsdisk.main.collect_storage_inventory") as collector:
            with redirect_stdout(StringIO()):
                with self.assertRaises(SystemExit) as context:
                    main(["--version"])

        self.assertEqual(context.exception.code, 0)
        collector.assert_not_called()

    def test_json_output_is_parseable_and_contains_no_terminal_ui(self):
        inventory = StorageInventory(
            devices=[],
            filesystems=[],
            filesystem_groups=[],
        )
        output = StringIO()

        with patch(
            "lsdisk.main.collect_storage_inventory",
            return_value=inventory,
        ):
            with redirect_stdout(output):
                result = main(["--all", "--json"])

        self.assertEqual(result, 0)
        data = json.loads(output.getvalue())
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["mode"], "all")
        self.assertEqual(data["devices"], [])
        self.assertNotIn("Storage Overview", output.getvalue())


if __name__ == "__main__":
    unittest.main()
