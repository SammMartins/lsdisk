"""Command-line entry point for lsdisk."""

import argparse
import json
import sys
from collections.abc import Sequence
from importlib.metadata import PackageNotFoundError, version

from lsdisk.inventory import collect_storage_inventory
from lsdisk.serialization import inventory_to_dict
from lsdisk.ui.terminal import (
    create_console,
    render_all,
    render_compact,
    render_simple,
)


def _get_version() -> str:
    """Return the installed package version when available."""
    try:
        return version("lsdisk")
    except PackageNotFoundError:
        try:
            from lsdisk._version import __version__
        except ModuleNotFoundError:
            return "unknown"
        return __version__


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="lsdisk",
        description="Explore Linux storage devices, partitions, and filesystems.",
        epilog=(
            "Examples:\n"
            "  lsdisk\n"
            "  lsdisk --all\n"
            "  lsdisk -T\n"
            "  lsdisk --all --json\n"
            "  lsdisk --color never"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    modes = parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--simple",
        action="store_true",
        help="Show the simplified overview (default).",
    )
    modes.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Show all devices, mounts, and filesystem statistics.",
    )

    output_modes = parser.add_mutually_exclusive_group()
    output_modes.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON instead of terminal views.",
    )
    output_modes.add_argument(
        "-T",
        "--table-mode",
        action="store_true",
        help="Use tabular terminal output instead of the compact layout.",
    )

    parser.add_argument(
        "--color",
        choices=("auto", "always", "never"),
        default="auto",
        help="Control terminal colors (default: auto).",
    )
    parser.add_argument(
        "--no-color",
        dest="color",
        action="store_const",
        const="never",
        default=argparse.SUPPRESS,
        help="Disable terminal colors.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {_get_version()}",
        help="Show the installed version and exit.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run lsdisk."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        inventory = collect_storage_inventory()
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"lsdisk: error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        data = inventory_to_dict(inventory, include_all=args.all)
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0

    console = create_console(args.color)

    if args.table_mode:
        if args.all:
            render_all(inventory, console)
        else:
            render_simple(inventory, console)
    else:
        render_compact(
            inventory,
            console,
            include_all=args.all,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
