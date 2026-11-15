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
from lsdisk.models import (
    BlockDevice,
    StorageDeviceKind,
    StorageDeviceReference,
    StorageRelationship,
    storage_reference_identity,
)
from lsdisk.ui.styles import PALETTE, usage_style


SUMMARY_CATEGORIES = {"persistent", "network"}
COMPACT_MIN_WIDTH = 100
TABLE_MIN_WIDTH = 100
EXPANDED_MIN_WIDTH = 120
WIDTH_NOTICE = (
    "Warning: Terminal width is limited; optional columns or long values "
    "have been abbreviated."
)
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


def _terminal_width(console: Console, fallback: int = 80) -> int:
    """Return the console width, with a conservative fallback."""
    try:
        width = int(console.width)
    except (AttributeError, TypeError, ValueError):
        return fallback
    return width if width > 0 else fallback


def _abbreviate(value: str, width: int) -> str:
    """Shorten a value only for a constrained terminal presentation."""
    if len(value) <= width:
        return value
    if width <= 3:
        return value[:width]
    return f"{value[:width - 3]}..."


def _render_width(console: Console, *, panel: bool = False) -> int:
    """Return the width available to a renderable."""
    width = _terminal_width(console)
    return max(1, width - 4 if panel else width)


def _cell_length(value: object) -> int:
    """Return the plain-text length of a table cell."""
    return len(str(value))


def _allocate_column_widths(
    headers: list[str],
    rows: list[list[object]],
    available_width: int,
    *,
    optional: set[int] | None = None,
    priority: tuple[int, ...] = (),
) -> tuple[list[int], list[int], bool]:
    """Fit columns to a renderable width without starving key values."""
    optional = optional or set()
    overhead = 3 * len(headers) + 1
    content_width = max(0, available_width - overhead)
    preferred = [
        max([
            len(header),
            *(
                _cell_length(row[index])
                for row in rows
                if index < len(row)
            ),
        ])
        for index, header in enumerate(headers)
    ]
    widths = [len(header) for header in headers]
    kept = list(range(len(headers)))
    reduced = False

    while kept and sum(widths[index] for index in kept) > content_width:
        removable = [
            index for index in reversed(kept) if index in optional
        ]
        if not removable:
            break
        kept.remove(removable[0])
        reduced = True

    content_width = max(0, available_width - (3 * len(kept) + 1))
    while (
        kept
        and sum(preferred[index] for index in kept) > content_width
    ):
        removable = [
            index for index in reversed(kept) if index in optional
        ]
        if not removable:
            break
        kept.remove(removable[0])
        reduced = True
        content_width = max(0, available_width - (3 * len(kept) + 1))

    remaining = content_width - sum(widths[index] for index in kept)
    order = priority + tuple(
        index for index in kept if index not in priority
    )
    while remaining > 0:
        grew = False
        for index in order:
            if index not in kept or widths[index] >= preferred[index]:
                continue
            widths[index] += 1
            remaining -= 1
            grew = True
            if remaining == 0:
                break
        if not grew:
            break

    if any(widths[index] < preferred[index] for index in kept):
        reduced = True
    return widths, kept, reduced


def _add_sized_columns(
    table: Table,
    headers: list[tuple[str, str | None]],
    widths: list[int],
) -> None:
    """Add fixed-width columns so Rich and enclosing panels share a budget."""
    for (header, style), width in zip(headers, widths):
        table.add_column(
            header,
            style=style,
            width=max(1, width),
            justify="right" if header in {
                "Total", "Used", "Available", "Used %", "Size", "Avail",
                "Use%",
            } else "left",
            no_wrap=True,
            overflow="ellipsis",
        )


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


def _device_table(
    *,
    detailed: bool = False,
    reduced: bool = False,
    width: int | None = None,
) -> Table:
    table = Table(
        title="Block Devices",
        header_style=PALETTE["heading"],
        padding=(0, 1),
        expand=False,
        show_lines=False,
        width=width,
    )
    table.add_column("Device", style=PALETTE["device"], no_wrap=True)
    table.add_column("Type", no_wrap=True)
    table.add_column("Capacity", justify="right", no_wrap=True)
    if reduced:
        table.add_column("Filesystem", overflow="ellipsis", max_width=16)
        table.add_column("Mount", overflow="ellipsis", max_width=20)
    else:
        table.add_column("Filesystem", no_wrap=True)
        table.add_column("Mountpoints", no_wrap=True)

    if detailed and not reduced:
        table.add_column("Model", no_wrap=True)
        table.add_column("Transport", no_wrap=True)
        table.add_column("Media", no_wrap=True)

    return table


def _add_device_rows(
    table: Table,
    devices: list[BlockDevice],
    *,
    detailed: bool = False,
    reduced: bool = False,
    depth: int = 0,
) -> None:
    """Add a recursive device hierarchy to a table."""
    for device in devices:
        name = f"{'  ' * depth}{device.name}"
        mountpoints = ", ".join(device.mountpoints) or "Not mounted"
        if reduced:
            name = f"{'  ' * depth}{_abbreviate(device.name, 20)}"
            mountpoints = _abbreviate(mountpoints, 20)

        row = [
            name,
            _device_type(device),
            format_bytes(device.size_bytes),
            device.filesystem_type or "Unknown",
            mountpoints,
        ]

        if detailed and not reduced:
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
            reduced=reduced,
            depth=depth + 1,
        )


def _relationship_label(
    reference: StorageDeviceReference,
    *,
    width: int | None = None,
) -> Text:
    """Format a topology reference while retaining its canonical identity."""
    identifier = (
        _abbreviate(reference.identifier, width)
        if width is not None
        else reference.identifier
    )
    label = Text(identifier, style="bold cyan")
    label.append(f"  [{reference.kind.value}]", style="dim")
    return label


def _relationship_choice_key(
    relationship: StorageRelationship,
) -> tuple[bool, str, str]:
    """Prefer canonical upper labels when duplicate edges are equivalent."""
    upper = relationship.upper
    return (
        upper.identifier != upper.canonical_path,
        upper.identifier,
        repr(relationship),
    )


def _topology_tree(
    relationships: list[StorageRelationship],
    *,
    narrow: bool = False,
) -> Tree:
    """Build a stable, readable view of verified storage-layer edges."""
    root = Tree(
        Text("Storage Topology", style="bold cyan"),
        guide_style="dim",
    )
    unique: dict[
        tuple[str, str, tuple[str, ...]], StorageRelationship
    ] = {}
    for relationship in relationships:
        lower = tuple(sorted({
            storage_reference_identity(reference)
            for reference in relationship.lower
        }))
        if not lower:
            continue
        key = (
            relationship.relationship_type,
            storage_reference_identity(relationship.upper),
            lower,
        )
        current = unique.get(key)
        if current is None or _relationship_choice_key(relationship) < (
            _relationship_choice_key(current)
        ):
            unique[key] = relationship

    for key in sorted(unique):
        relationship = unique[key]
        upper = root.add(_relationship_label(
            relationship.upper,
            width=28 if narrow else None,
        ))
        lower_by_identity: dict[str, StorageDeviceReference] = {}
        for reference in sorted(
            relationship.lower,
            key=lambda item: (
                storage_reference_identity(item),
                item.identifier != item.canonical_path,
                item.identifier,
                item.kind.value,
                item.filesystem_uuid or "",
            ),
        ):
            lower_by_identity.setdefault(
                storage_reference_identity(reference),
                reference,
            )
        for reference in (
            lower_by_identity[identity]
            for identity in sorted(lower_by_identity)
        ):
            lower = Text(
                f"{relationship.relationship_type} -> ",
                style="yellow",
            )
            lower.append_text(_relationship_label(
                reference,
                width=28 if narrow else None,
            ))
            upper.add(lower)

    return root


def _render_topology(
    inventory: StorageInventory,
    console: Console,
) -> bool:
    """Display only relationships verified by the collectors."""
    relationships = [
        relationship
        for relationship in inventory.relationships
        if not (
            relationship.upper.kind is StorageDeviceKind.PARTITION
            and relationship.lower
            and all(
                reference.kind is StorageDeviceKind.PHYSICAL
                for reference in relationship.lower
            )
        )
    ]
    if not relationships:
        return False
    console.print(Panel(
        _topology_tree(
            relationships,
            narrow=_terminal_width(console) < EXPANDED_MIN_WIDTH,
        ),
        title="Storage Topology",
        subtitle="Upper layers point to verified lower layers",
        border_style="blue",
    ))
    return True


def _render_partition_inventory(
    inventory: StorageInventory,
    console: Console,
    *,
    reduced: bool = False,
) -> None:
    """Show geometry and persistent configuration in expanded output."""
    rows = Table(
        title="Partition Geometry",
        header_style=PALETTE["heading"],
        padding=(0, 1),
        expand=False,
    )
    rows.add_column(
        "Device", style=PALETTE["device"], no_wrap=True,
        overflow="ellipsis", max_width=16 if reduced else None,
    )
    rows.add_column("Table" if not reduced else "Tbl", no_wrap=True)
    rows.add_column("Logical" if not reduced else "Log", justify="right", no_wrap=True)
    rows.add_column("Physical" if not reduced else "Phy", justify="right", no_wrap=True)
    rows.add_column("Start sector" if not reduced else "Start", justify="right", no_wrap=True)
    rows.add_column("End sector" if not reduced else "End", justify="right", no_wrap=True)
    rows.add_column("Name", overflow="ellipsis", max_width=12 if reduced else 18)
    rows.add_column("Type", overflow="ellipsis", max_width=12 if reduced else 18)
    for device in walk_devices(inventory.devices):
        metadata = device.partition_metadata
        if metadata is None:
            continue
        rows.add_row(
            _abbreviate(device.path, 16) if reduced else device.path,
            metadata.partition_table or "Unknown",
            str(metadata.logical_sector_size or "N/A"),
            str(metadata.physical_sector_size or "N/A"),
            str(
                metadata.start_sector
                if metadata.start_sector is not None
                else "N/A"
            ),
            str(
                metadata.end_sector
                if metadata.end_sector is not None
                else "N/A"
            ),
            _abbreviate(metadata.partition_name or "N/A", 12)
            if reduced else metadata.partition_name or "N/A",
            _abbreviate(metadata.partition_type or "N/A", 12)
            if reduced else metadata.partition_type or "N/A",
        )
    if rows.row_count:
        console.print(rows)

    regions = Table(
        title="Unallocated Disk Regions (bytes)",
        header_style=PALETTE["heading"],
        padding=(0, 1),
        expand=False,
    )
    regions.add_column(
        "Disk", style=PALETTE["device"], overflow="ellipsis",
        max_width=16 if reduced else None,
    )
    regions.add_column("Start", justify="right")
    regions.add_column("End", justify="right")
    regions.add_column("Size", justify="right")
    for region in inventory.unallocated_regions:
        regions.add_row(
            _abbreviate(region.disk_path, 16) if reduced else region.disk_path,
            str(region.start_bytes),
            str(region.end_bytes),
            str(region.size_bytes),
        )
    if regions.row_count:
        console.print(regions)
    if inventory.fstab_entries:
        fstab = Table(
            title="Persistent Mount Configuration (/etc/fstab)",
            caption="Configured entries are not proof of currently active mounts.",
            header_style=PALETTE["heading"],
            padding=(0, 1),
            expand=False,
        )
        fstab.add_column(
            "Source",
            overflow="ellipsis",
            max_width=24 if reduced else None,
        )
        fstab.add_column(
            "Mountpoint",
            overflow="ellipsis",
            max_width=24 if reduced else None,
        )
        fstab.add_column("Type", no_wrap=True)
        fstab.add_column(
            "Options",
            overflow="ellipsis",
            max_width=28 if reduced else None,
        )
        fstab.add_column("Dump", no_wrap=True)
        fstab.add_column("Pass", no_wrap=True)
        for entry in sorted(
            inventory.fstab_entries,
            key=lambda item: (item.mountpoint, item.source),
        ):
            fstab.add_row(
                entry.source,
                entry.mountpoint,
                entry.filesystem_type,
                ",".join(entry.options) or "defaults",
                entry.dump or "N/A",
                entry.pass_number or "N/A",
            )
        console.print(fstab)
        console.print(
            Text(
                f"Persistent mount configuration entries: "
                f"{len(inventory.fstab_entries)} (not proof of active mounts)",
                style=PALETTE["muted"],
            )
        )


def _filesystem_group_table(
    *,
    width: int | None = None,
    include_category: bool = True,
    widths: list[int] | None = None,
) -> Table:
    headers = [
        ("Filesystem", PALETTE["filesystem"]),
    ]
    if include_category:
        headers.append(("Category", None))
    headers.extend([
        ("Source", None),
        ("Total", None),
        ("Used", None),
        ("Available", None),
        ("Used %", None),
        ("Mountpoints", None),
    ])
    table = Table(
        title="Filesystem Capacity Summary",
        header_style=PALETTE["heading"],
        padding=(0, 1),
        expand=False,
        show_lines=False,
        width=width,
    )
    if width is None:
        for header, style in headers:
            table.add_column(header, style=style, no_wrap=True)
    else:
        _add_sized_columns(
            table,
            headers,
            widths or [len(header) for header, _ in headers],
        )
    return table


def _mount_table(
    *,
    width: int | None = None,
    include_category: bool = True,
    include_details: bool = True,
    widths: list[int] | None = None,
) -> Table:
    headers = [
        ("Mountpoint", PALETTE["filesystem"]),
        ("Filesystem", None),
    ]
    if include_category:
        headers.append(("Category", None))
    headers.extend([
        ("Source", None),
        ("Total", None),
        ("Used", None),
        ("Available", None),
        ("Used %", None),
    ])
    if include_details:
        headers.extend([
            ("Device ID", None),
            ("Filesystem Root", None),
        ])
    table = Table(
        title="Mounted Filesystems",
        header_style=PALETTE["heading"],
        padding=(0, 1),
        expand=False,
        show_lines=False,
        width=width,
    )
    if width is None:
        for header, style in headers:
            table.add_column(header, style=style)
    else:
        _add_sized_columns(
            table,
            headers,
            widths or [len(header) for header, _ in headers],
        )
    return table


def _group_rows(
    inventory: StorageInventory,
    *,
    include_all: bool,
    include_category: bool = True,
) -> list[list[str]]:
    """Build unique filesystem group rows without repeating capacity."""
    rows = []
    for group in inventory.filesystem_groups:
        filesystem = group.representative
        category = classify_filesystem(filesystem)

        if not include_all and category not in SUMMARY_CATEGORIES:
            continue

        total = group.total_bytes
        row = [
            filesystem.filesystem_type,
        ]
        if include_category:
            row.append(_category_label(category))
        row.extend([
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
        ])
        rows.append(row)
    return rows


def _add_group_rows(
    table: Table,
    inventory: StorageInventory,
    *,
    include_all: bool,
    include_category: bool = True,
) -> int:
    """Add unique filesystem groups without repeating capacity."""
    rows = _group_rows(
        inventory,
        include_all=include_all,
        include_category=include_category,
    )
    for row in rows:
        table.add_row(*row)

    return len(rows)


def render_simple(
    inventory: StorageInventory,
    console: Console | None = None,
) -> None:
    """Render the default storage overview."""
    console = console or Console()
    reduced = _terminal_width(console) < TABLE_MIN_WIDTH

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
        table = _device_table(
            reduced=reduced,
            width=_render_width(console),
        )
        _add_device_rows(table, physical_disks, reduced=reduced)
        console.print(table)
    else:
        console.print("[yellow]No physical disks detected.[/yellow]")

    group_rows = _group_rows(
        inventory,
        include_all=False,
        include_category=True,
    )
    headers = [
        ("Filesystem", PALETTE["filesystem"]),
        ("Category", None),
        ("Source", None),
        ("Total", None),
        ("Used", None),
        ("Available", None),
        ("Used %", None),
        ("Mountpoints", None),
    ]
    raw_headers = [header for header, _ in headers]
    widths, kept, table_reduced = _allocate_column_widths(
        raw_headers,
        group_rows,
        _render_width(console),
        optional={1},
        priority=(3, 4, 5, 6, 0, 2, 7),
    )
    headers = [headers[index] for index in kept]
    group_rows = [
        [row[index] for index in kept]
        for row in group_rows
    ]
    filesystems = Table(
        title="Filesystem Capacity Summary",
        header_style=PALETTE["heading"],
        padding=(0, 1),
        expand=False,
        show_lines=False,
        width=_render_width(console),
    )
    _add_sized_columns(
        filesystems,
        headers,
        [widths[index] for index in kept],
    )
    for row in group_rows:
        filesystems.add_row(*row)
    count = len(group_rows)

    if count:
        console.print(filesystems)
    else:
        console.print(
            "[yellow]No persistent or network filesystems detected.[/yellow]"
        )
    if reduced or table_reduced:
        console.print(Text(WIDTH_NOTICE, style=PALETTE["warning"]))


def render_all(
    inventory: StorageInventory,
    console: Console | None = None,
) -> None:
    """Render the complete storage inventory."""
    console = console or Console()
    reduced = _terminal_width(console) < EXPANDED_MIN_WIDTH

    console.print(
        Panel(
            "[bold cyan]lsdisk[/bold cyan]\n"
            "Complete storage inventory",
            title="Storage Overview",
            border_style="cyan",
        )
    )

    devices = _device_table(
        detailed=_terminal_width(console) >= 200,
        width=_render_width(console),
    )
    _add_device_rows(
        devices,
        inventory.devices,
        detailed=_terminal_width(console) >= 200,
    )
    console.print(devices)

    mount_rows = []
    for filesystem in inventory.filesystems:
        total = filesystem.total_bytes
        row = [
            filesystem.mountpoint,
            filesystem.filesystem_type,
            _category_label(classify_filesystem(filesystem)),
        ]
        row.extend([
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
        ])
        mount_rows.append(row)
    mount_headers = [
        ("Mountpoint", PALETTE["filesystem"]),
        ("Filesystem", None),
        ("Category", None),
        ("Source", None),
        ("Total", None),
        ("Used", None),
        ("Available", None),
        ("Used %", None),
        ("Device ID", None),
        ("Filesystem Root", None),
    ]
    mount_widths, mount_kept, mount_reduced = _allocate_column_widths(
        [header for header, _ in mount_headers],
        mount_rows,
        _render_width(console),
        optional={2, 8, 9},
        priority=(4, 5, 6, 7, 0, 1, 3),
    )
    mounts = Table(
        title="Mounted Filesystems",
        header_style=PALETTE["heading"],
        padding=(0, 1),
        expand=False,
        show_lines=False,
        width=_render_width(console),
    )
    _add_sized_columns(
        mounts,
        [mount_headers[index] for index in mount_kept],
        [mount_widths[index] for index in mount_kept],
    )
    for row in mount_rows:
        mounts.add_row(*(row[index] for index in mount_kept))
    console.print(mounts)

    group_rows = _group_rows(
        inventory,
        include_all=True,
        include_category=True,
    )
    group_headers = [
        ("Filesystem", PALETTE["filesystem"]),
        ("Category", None),
        ("Source", None),
        ("Total", None),
        ("Used", None),
        ("Available", None),
        ("Used %", None),
        ("Mountpoints", None),
    ]
    group_widths, group_kept, group_reduced = _allocate_column_widths(
        [header for header, _ in group_headers],
        group_rows,
        _render_width(console),
        optional={1},
        priority=(3, 4, 5, 6, 0, 2, 7),
    )
    groups = Table(
        title="Filesystem Capacity Summary",
        header_style=PALETTE["heading"],
        padding=(0, 1),
        expand=False,
        show_lines=False,
        width=_render_width(console),
    )
    _add_sized_columns(
        groups,
        [group_headers[index] for index in group_kept],
        [group_widths[index] for index in group_kept],
    )
    for row in group_rows:
        groups.add_row(*(row[index] for index in group_kept))
    console.print(groups)
    _render_topology(inventory, console)
    _render_partition_inventory(
        inventory,
        console,
        reduced=reduced,
    )

    console.print(
        f"\nDiscovered mountpoints: {len(inventory.filesystems)}"
        f" | Unique filesystem groups: {len(inventory.filesystem_groups)}"
    )
    if reduced or mount_reduced or group_reduced:
        console.print(Text(WIDTH_NOTICE, style=PALETTE["warning"]))


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
    return usage_style(percentage)


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
    reduced: bool = False,
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
            model = _abbreviate(device.model, 20) if reduced else device.model
            label.append(f"  {model}", style="dim")

        if device.transport and not reduced:
            label.append(f"  [{device.transport}]", style="dim")
        elif device.transport and detailed:
            label.append(f"  [{_abbreviate(device.transport, 10)}]", style="dim")

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
            reduced=reduced,
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
    reduced = _terminal_width(console) < COMPACT_MIN_WIDTH

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
            reduced=reduced,
        )

    if visible_devices:
        console.print(Panel(root, border_style="blue"))
    else:
        console.print("[yellow]No matching block devices detected.[/yellow]")

    if include_all:
        _render_compact_mounts(inventory, console)
        _render_topology(inventory, console)
        _render_partition_inventory(
            inventory,
            console,
            reduced=reduced,
        )
    if reduced:
        note = WIDTH_NOTICE
        if include_all:
            note += " Run 'lsdisk' for the compact view."
        console.print(Text(note, style=PALETTE["warning"]))


def render_classic(
    inventory: StorageInventory,
    console: Console | None = None,
) -> None:
    """Render a concise df-like filesystem overview using shared inventory."""
    console = console or Console()
    panel_width = _terminal_width(console)
    table_width = _render_width(console, panel=True)
    rows = []
    for filesystem in sorted(
        inventory.filesystems,
        key=lambda item: item.mountpoint,
    ):
        rows.append([
            filesystem.source,
            filesystem.filesystem_type,
            format_bytes(filesystem.total_bytes)
            if filesystem.total_bytes else "N/A",
            format_bytes(filesystem.used_bytes)
            if filesystem.total_bytes else "N/A",
            format_bytes(filesystem.available_bytes)
            if filesystem.total_bytes else "N/A",
            _percentage(filesystem.used_bytes, filesystem.total_bytes),
            filesystem.mountpoint,
        ])

    headers = [
        ("Filesystem", PALETTE["filesystem"]),
        ("Type", None),
        ("Size", None),
        ("Used", None),
        ("Avail", None),
        ("Use%", None),
        ("Mounted on", None),
    ]
    widths, kept, reduced = _allocate_column_widths(
        [header for header, _ in headers],
        rows,
        table_width,
        priority=(2, 3, 4, 5, 0, 1, 6),
    )
    classic_layout_degraded = reduced and (
        len(kept) < len(headers)
        or any(
            index != 6 and widths[index] < max(
                len(headers[index][0]),
                *(
                    _cell_length(row[index])
                    for row in rows
                    if index < len(row)
                ),
            )
            for index in kept
        )
    )
    table = Table(
        title="Filesystem Overview",
        header_style=PALETTE["heading"],
        padding=(0, 1),
        expand=False,
        show_lines=False,
        width=table_width,
    )
    _add_sized_columns(
        table,
        [headers[index] for index in kept],
        [widths[index] for index in kept],
    )
    for filesystem, row in zip(
        sorted(inventory.filesystems, key=lambda item: item.mountpoint),
        rows,
    ):
        row[5] = Text(row[5], style=usage_style(filesystem.used_percent))
        table.add_row(*(row[index] for index in kept))
    console.print(
        Panel(
            table,
            title="lsdisk  Linux Storage Explorer",
            border_style=PALETTE["heading"],
            width=panel_width,
        )
    )
    if classic_layout_degraded:
        console.print(Text(WIDTH_NOTICE, style=PALETTE["warning"]))
