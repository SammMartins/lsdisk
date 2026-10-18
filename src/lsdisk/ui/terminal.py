"""Rich-based terminal interface for lsdisk."""

from rich.console import Console
from pathlib import Path

from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree
from rich.table import Table

from lsdisk.analyzers.capacity import capacity_owners, format_bytes
from lsdisk.analyzers.filesystems import (
    classify_filesystem,
    filesystem_identity,
)
from lsdisk.inventory import StorageInventory, walk_devices
from lsdisk.models import BlockDevice


SUMMARY_CATEGORIES = {"persistent", "network"}
CATEGORY_LABELS = {
    "persistent": "Persistent Storage",
    "network": "Network",
    "application_image": "Application Image",
    "temporary": "Temporary",
    "virtual": "Virtual",
    "unknown": "Unknown",
}


def _category_label(category: str) -> str:
    """Return the human-readable label for a filesystem category."""
    return CATEGORY_LABELS.get(category, category.replace("_", " ").title())


def create_console(color: str = "auto") -> Console:
    """Create a terminal console with the requested color policy."""
    if color == "always":
        return Console(force_terminal=True)

    if color == "never":
        return Console(force_terminal=False, no_color=True)

    return Console()


def _device_type(device: BlockDevice) -> str:
    """Return a human-readable device classification."""
    if device.device_type == "disk":
        if device.physical is True:
            return "Physical disk"
        if device.physical is False:
            return "Virtual or logical disk"
        return "Unclassified disk"

    if device.device_type == "part":
        return "Partition"

    if device.device_type == "rom":
        return "Optical drive"

    return device.device_type


def _device_table(*, detailed: bool = False) -> Table:
    table = Table(title="Block Devices")
    table.add_column("Device", style="cyan")
    table.add_column("Type")
    table.add_column("Capacity", justify="right")
    table.add_column("Filesystem")
    table.add_column("Mountpoints")

    if detailed:
        table.add_column("Model")
        table.add_column("Transport")
        table.add_column("Media")

    return table


def _add_device_rows(
    table: Table,
    devices: list[BlockDevice],
    *,
    detailed: bool = False,
    depth: int = 0,
) -> None:
    """Add a recursive device hierarchy to a table."""
    for device in devices:
        name = f"{'  ' * depth}{device.name}"
        mountpoints = ", ".join(device.mountpoints) or "Not mounted"

        row = [
            name,
            _device_type(device),
            format_bytes(device.size_bytes),
            device.filesystem_type or "Unknown",
            mountpoints,
        ]

        if detailed:
            if device.rotational is True:
                media = "Rotational"
            elif device.rotational is False:
                media = "Non-rotational"
            else:
                media = "Unknown"

            row.extend([
                device.model or "Unknown",
                device.transport or "Unknown",
                media,
            ])

        table.add_row(*row)

        _add_device_rows(
            table,
            device.children,
            detailed=detailed,
            depth=depth + 1,
        )


def _filesystem_group_table() -> Table:
    table = Table(title="Filesystem Capacity Summary")
    table.add_column("Filesystem", style="cyan")
    table.add_column("Category")
    table.add_column("Source")
    table.add_column("Total", justify="right")
    table.add_column("Used", justify="right")
    table.add_column("Available", justify="right")
    table.add_column("Used %", justify="right")
    table.add_column("Mountpoints")
    return table


def _mount_table() -> Table:
    table = Table(title="Mounted Filesystems")
    table.add_column("Mountpoint", style="cyan")
    table.add_column("Filesystem")
    table.add_column("Category")
    table.add_column("Source")
    table.add_column("Total", justify="right")
    table.add_column("Used", justify="right")
    table.add_column("Available", justify="right")
    table.add_column("Used %", justify="right")
    table.add_column("Device ID")
    table.add_column("Filesystem Root")
    return table


def _add_group_rows(
    table: Table,
    inventory: StorageInventory,
    *,
    include_all: bool,
) -> int:
    """Add unique filesystem groups without repeating capacity."""
    count = 0

    for group in inventory.filesystem_groups:
        filesystem = group.representative
        category = classify_filesystem(filesystem)

        if not include_all and category not in SUMMARY_CATEGORIES:
            continue

        total = group.total_bytes
        table.add_row(
            filesystem.filesystem_type,
            _category_label(category),
            filesystem.source,
            format_bytes(total) if total > 0 else "Unavailable",
            format_bytes(group.used_bytes) if total > 0 else "Unavailable",
            (
                format_bytes(group.available_bytes)
                if total > 0
                else "Unavailable"
            ),
            f"{filesystem.used_percent:.1f}%" if total > 0 else "N/A",
            ", ".join(group.mountpoints),
        )
        count += 1

    return count


def render_simple(
    inventory: StorageInventory,
    console: Console | None = None,
) -> None:
    """Render the default storage overview."""
    console = console or Console()

    console.print(
        Panel(
            "[bold cyan]lsdisk[/bold cyan]\n"
            "Cross-distro Linux Storage Explorer",
            title="Storage Overview",
            border_style="cyan",
        )
    )

    physical_disks = [
        device for device in inventory.devices
        if device.is_physical_disk
    ]

    if physical_disks:
        table = _device_table()
        _add_device_rows(table, physical_disks)
        console.print(table)
    else:
        console.print("[yellow]No physical disks detected.[/yellow]")

    filesystems = _filesystem_group_table()
    count = _add_group_rows(
        filesystems,
        inventory,
        include_all=False,
    )

    if count:
        console.print(filesystems)
    else:
        console.print(
            "[yellow]No persistent or network filesystems detected.[/yellow]"
        )


def render_all(
    inventory: StorageInventory,
    console: Console | None = None,
) -> None:
    """Render the complete storage inventory."""
    console = console or Console()

    console.print(
        Panel(
            "[bold cyan]lsdisk[/bold cyan]\n"
            "Complete storage inventory",
            title="Storage Overview",
            border_style="cyan",
        )
    )

    devices = _device_table(detailed=True)
    _add_device_rows(
        devices,
        inventory.devices,
        detailed=True,
    )
    console.print(devices)

    mounts = _mount_table()
    for filesystem in inventory.filesystems:
        total = filesystem.total_bytes
        mounts.add_row(
            filesystem.mountpoint,
            filesystem.filesystem_type,
            _category_label(classify_filesystem(filesystem)),
            filesystem.source,
            format_bytes(total) if total > 0 else "Unavailable",
            format_bytes(filesystem.used_bytes) if total > 0 else "Unavailable",
            (
                format_bytes(filesystem.available_bytes)
                if total > 0
                else "Unavailable"
            ),
            f"{filesystem.used_percent:.1f}%" if total > 0 else "N/A",
            filesystem.device_id or "Unknown",
            filesystem.filesystem_root,
        )
    console.print(mounts)

    groups = _filesystem_group_table()
    _add_group_rows(groups, inventory, include_all=True)
    console.print(groups)

    console.print(
        f"\nDiscovered mountpoints: {len(inventory.filesystems)}"
        f" | Unique filesystem groups: {len(inventory.filesystem_groups)}"
    )


def _source_key(source: str) -> str:
    """Normalize a local device path for matching."""
    if not source.startswith("/dev/"):
        return source

    try:
        return str(Path(source).resolve())
    except (OSError, RuntimeError):
        return source


def _percentage(used: int, total: int) -> str:
    """Format a percentage without hiding small nonzero values."""
    if total <= 0:
        return "N/A"

    percent = used / total * 100

    if 0 < percent < 0.1:
        return "<0.1%"

    return f"{percent:.1f}%"


def _usage_color(percentage: float) -> str:
    """Select a color based on filesystem utilization."""
    if percentage >= 90:
        return "red"
    if percentage >= 70:
        return "yellow"
    return "green"


def _local_filesystem_groups(
    inventory: StorageInventory,
):
    """Return mounted local persistent filesystems."""
    return [
        group
        for group in inventory.filesystem_groups
        if (
            classify_filesystem(group.representative) == "persistent"
            and group.representative.source.startswith("/dev/")
        )
    ]


def _groups_by_source(inventory: StorageInventory):
    """Index local filesystem groups by their source device."""
    result = {}

    for group in _local_filesystem_groups(inventory):
        key = _source_key(group.representative.source)
        result.setdefault(key, []).append(group)

    return result


def _usage_bar(used: int, total: int, width: int = 24) -> Text:
    """Create a compact text-based utilization bar."""
    bar = Text()

    if total <= 0:
        bar.append("Usage data unavailable", style="dim")
        return bar

    percentage = min(100.0, max(0.0, used / total * 100))
    filled = round(width * percentage / 100)

    bar.append("█" * filled, style=_usage_color(percentage))
    bar.append("░" * (width - filled), style="dim")
    bar.append(
        f"  {percentage:.1f}%",
        style=_usage_color(percentage),
    )
    return bar


def _add_compact_device(
    parent: Tree,
    device: BlockDevice,
    groups_by_source: dict,
    *,
    detailed: bool,
) -> None:
    """Add a device and its filesystem information to a compact tree."""
    label = Text()
    label.append(device.name, style="bold cyan")
    label.append(f"  {format_bytes(device.size_bytes)}")

    if device.device_type == "disk":
        if device.physical:
            label.append("  Physical disk", style="green")
        elif device.physical is False:
            label.append("  Virtual/logical disk", style="dim")
        else:
            label.append("  Disk type unverified", style="yellow")

        if device.rotational is True:
            label.append("  HDD", style="yellow")
        elif device.rotational is False and device.physical:
            label.append("  SSD/Flash", style="green")

        if device.model:
            label.append(f"  {device.model}", style="dim")

        if detailed and device.transport:
            label.append(f"  [{device.transport}]", style="dim")

    elif device.device_type == "part":
        label.append(
            f"  {device.filesystem_type or 'Unknown filesystem'}",
            style="cyan",
        )

    elif device.device_type == "rom":
        label.append("  Optical drive", style="dim")

    node = parent.add(label)

    if device.is_partition:
        groups = groups_by_source.get(_source_key(device.path), [])

        if groups:
            for group in groups:
                filesystem = group.representative
                percentage = (
                    group.used_bytes / group.total_bytes * 100
                    if group.total_bytes
                    else 0.0
                )

                usage = Text("Usage: ")
                usage.append(
                    f"{format_bytes(group.used_bytes)} used",
                    style=_usage_color(percentage),
                )
                #usage.append(
                #    f" ({_percentage(group.used_bytes, group.total_bytes)})"
                #)
                usage.append(
                    f"  |  {format_bytes(group.available_bytes)} available"
                )
                node.add(usage)
                node.add(
                    _usage_bar(
                        group.used_bytes,
                        group.total_bytes,
                        width=24,
                    )
                )

                mounts = ", ".join(group.mountpoints) or "Not mounted"
                mount_text = Text("Mounts: ", style="dim")
                mount_text.append(mounts)
                node.add(mount_text)

        else:
            status = Text("Usage unavailable", style="dim")
            mounts = ", ".join(device.mountpoints) or "Not mounted"
            status.append(f"  |  {mounts}")
            node.add(status)

    for child in device.children:
        _add_compact_device(
            node,
            child,
            groups_by_source,
            detailed=detailed,
        )


def _render_compact_summary(
    inventory: StorageInventory,
    console: Console,
) -> None:
    """Display hardware counts and unique local filesystem capacity."""
    devices = list(walk_devices(inventory.devices))
    physical_disks = capacity_owners(inventory.devices)
    partitions = [device for device in devices if device.is_partition]

    physical_capacity = sum(device.size_bytes for device in physical_disks)

    groups = _local_filesystem_groups(inventory)
    total = sum(group.total_bytes for group in groups)
    used = sum(group.used_bytes for group in groups)
    available = sum(group.available_bytes for group in groups)

    summary = Text()
    summary.append(f"Physical disks: {len(physical_disks)}")
    summary.append(f"   Partitions: {len(partitions)}")
    summary.append(
        f"   Physical capacity: {format_bytes(physical_capacity)}\n"
    )

    if total > 0:
        summary.append(
            f"Mounted local filesystems: {format_bytes(total)} total\n"
        )
        summary.append("Used: ", style="dim")
        summary.append(
            f"{format_bytes(used)}", # ({_percentage(used, total)})",
            style=_usage_color(used / total * 100),
        )
        summary.append(
            f"   Available to users: {format_bytes(available)}\n"
        )
        summary.append_text(_usage_bar(used, total))
    else:
        summary.append(
            "Mounted local filesystem usage is unavailable.",
            style="dim",
        )

    console.print(
        Panel(
            summary,
            title="Storage Summary",
            border_style="cyan",
        )
    )


def _render_compact_mounts(
    inventory: StorageInventory,
    console: Console,
) -> None:
    """Display filesystem groups with their mountpoints underneath."""
    root = Tree(
        Text("Filesystems and Mountpoints", style="bold cyan"),
        guide_style="dim",
    )

    category_order = {
        "persistent": 0,
        "network": 1,
        "application_image": 2,
        "temporary": 3,
        "virtual": 4,
        "unknown": 5,
    }

    groups = sorted(
        inventory.filesystem_groups,
        key=lambda group: (
            category_order.get(
                classify_filesystem(group.representative), 4
            ),
            group.representative.filesystem_type,
            group.representative.source,
        ),
    )

    for group in groups:
        filesystem = group.representative
        category = classify_filesystem(filesystem)

        label = Text()
        label.append(filesystem.filesystem_type, style="bold cyan")
        label.append("  ")
        label.append(filesystem.source, style="bold")
        label.append(f"  [{_category_label(category)}] ", style="dim")
        label.append(f"  {format_bytes(group.total_bytes)}")

        node = root.add(label)

        if group.total_bytes > 0:
            percentage = group.used_bytes / group.total_bytes * 100

            usage = Text()
            usage.append("Used: ", style="dim")
            usage.append(
                format_bytes(group.used_bytes),
                style=_usage_color(percentage),
            )
            usage.append(f" ({_percentage(group.used_bytes, group.total_bytes)})")
            usage.append("  |  Available: ")
            usage.append(
                format_bytes(group.available_bytes),
                style="green",
            )
            node.add(usage)
            node.add(_usage_bar(group.used_bytes, group.total_bytes, width=24))
        else:
            node.add(
                Text(
                    "Capacity statistics unavailable or not applicable",
                    style="dim",
                )
            )

        if category == "application_image":
            node.add(
                Text(
                    "Application image usage; 100% does not indicate a full physical disk",
                    style="dim",
                )
            )

        identity = filesystem_identity(filesystem)

        mounts = [
            item
            for item in inventory.filesystems
            if filesystem_identity(item) == identity
        ]

        for item in sorted(mounts, key=lambda mount: mount.mountpoint):
            mount_label = Text()
            mount_label.append(item.mountpoint, style="cyan")

            if item.filesystem_root != "/":
                mount_label.append(
                    f"  (subvolume root: {item.filesystem_root})",
                    style="dim",
                )

            node.add(mount_label)

    console.print(
        Panel(
            root,
            title="Filesystem Details",
            subtitle="Capacity is shown once per filesystem group",
            border_style="blue",
        )
    )

def render_compact(
    inventory: StorageInventory,
    console: Console | None = None,
    *,
    include_all: bool = False,
) -> None:
    """Render the default compact view or the complete compact inventory."""
    console = console or Console()

    console.print(
        Panel(
            Text.assemble(
                ("lsdisk", "bold cyan"),
                ("  Linux Storage Explorer", "white"),
            ),
            border_style="cyan",
        )
    )

    _render_compact_summary(inventory, console)

    groups_by_source = _groups_by_source(inventory)

    if include_all:
        visible_devices = inventory.devices
        title = "All Block Devices"
    else:
        visible_devices = [
            device
            for device in inventory.devices
            if device.is_physical_disk
        ]
        title = "Physical Storage"

    root = Tree(Text(title, style="bold cyan"), guide_style="dim")

    for device in visible_devices:
        _add_compact_device(
            root,
            device,
            groups_by_source,
            detailed=include_all,
        )

    if visible_devices:
        console.print(Panel(root, border_style="blue"))
    else:
        console.print("[yellow]No matching block devices detected.[/yellow]")

    if include_all:
        _render_compact_mounts(inventory, console)
