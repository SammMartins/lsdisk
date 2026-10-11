"""Discover Linux block devices through sysfs."""

from pathlib import Path

from storix.models import BlockDevice


SYSFS_BLOCK_PATH = Path("/sys/class/block")
SECTOR_SIZE_BYTES = 512


def _read_text(path: Path) -> str | None:
    """Read a sysfs value, returning None when it is unavailable."""
    try:
        return path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return None


def _detect_transport(device_path: Path) -> str | None:
    """Infer the transport from available sysfs information."""
    transport = _read_text(device_path / "device" / "transport")
    if transport:
        return transport

    resolved = str(device_path.resolve()).lower()

    indicators = (
        ("nvme", "nvme"),
        ("ata", "sata"),
        ("usb", "usb"),
        ("virtio", "virtio"),
        ("mmc", "mmc"),
        ("iscsi", "iscsi"),
        ("sas", "sas"),
    )

    for indicator, transport_name in indicators:
        if indicator in resolved:
            return transport_name

    return None


def _build_device(entry: Path) -> BlockDevice | None:
    """Build a device model from a sysfs block-device entry."""
    try:
        resolved = entry.resolve(strict=True)
    except OSError:
        return None

    raw_size = _read_text(entry / "size")
    if raw_size is None:
        return None

    try:
        size_bytes = int(raw_size) * SECTOR_SIZE_BYTES
    except ValueError:
        return None

    is_partition = (entry / "partition").exists()
    device_type = "part" if is_partition else "disk"

    scsi_type = _read_text(entry / "device" / "type")
    if not is_partition and scsi_type == "5":
        device_type = "rom"

    parent_name = resolved.parent.name if is_partition else None

    model = _read_text(entry / "device" / "model")
    rotational_value = _read_text(entry / "queue" / "rotational")

    rotational = None
    if rotational_value in {"0", "1"}:
        rotational = rotational_value == "1"

    is_virtual = "/devices/virtual/" in str(resolved)
    has_device_link = (entry / "device").exists()

    physical = (
        device_type == "disk"
        and not is_virtual
        and has_device_link
    )

    return BlockDevice(
        name=entry.name,
        path=f"/dev/{entry.name}",
        device_type=device_type,
        size_bytes=size_bytes,
        physical=physical,
        parent_name=parent_name,
        model=model,
        transport=_detect_transport(entry),
        rotational=rotational,
    )


def collect_block_devices(
    sysfs_path: Path = SYSFS_BLOCK_PATH,
) -> list[BlockDevice]:
    """Discover block devices and return a hierarchy of devices and partitions."""
    if not sysfs_path.is_dir():
        return []

    discovered: dict[str, BlockDevice] = {}

    for entry in sorted(sysfs_path.iterdir(), key=lambda item: item.name):
        device = _build_device(entry)
        if device is not None:
            discovered[device.name] = device

    roots: list[BlockDevice] = []

    for device in discovered.values():
        parent = discovered.get(device.parent_name or "")

        if parent is None:
            roots.append(device)
        else:
            parent.children.append(device)

    return roots
