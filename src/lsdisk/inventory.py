"""Build a unified inventory of Linux storage."""

from dataclasses import dataclass
from pathlib import Path
from collections.abc import Iterator

from lsdisk.analyzers.filesystems import (
    FilesystemGroup,
    group_filesystems,
)
from lsdisk.collectors.block_devices import collect_block_devices
from lsdisk.collectors.filesystems import collect_filesystems
from lsdisk.models import BlockDevice, FilesystemUsage


@dataclass
class StorageInventory:
    """Store discovered devices and filesystem information."""

    devices: list[BlockDevice]
    filesystems: list[FilesystemUsage]
    filesystem_groups: list[FilesystemGroup]


def walk_devices(
    devices: list[BlockDevice],
) -> Iterator[BlockDevice]:
    """Yield devices recursively, including partitions."""
    for device in devices:
        yield device
        yield from walk_devices(device.children)


def _canonical_device_path(path: str) -> str | None:
    """Resolve a device path, including available symlink aliases."""
    if not path.startswith("/dev/"):
        return None

    try:
        return str(Path(path).resolve(strict=False))
    except (OSError, RuntimeError):
        return None


def collect_storage_inventory() -> StorageInventory:
    """Collect devices and filesystems and associate their mountpoints."""
    devices = collect_block_devices()
    filesystems = collect_filesystems()

    devices_by_path: dict[str, BlockDevice] = {}

    for device in walk_devices(devices):
        devices_by_path[device.path] = device
        canonical_path = _canonical_device_path(device.path)

        if canonical_path:
            devices_by_path[canonical_path] = device

    for filesystem in filesystems:
        device = devices_by_path.get(filesystem.source)

        if device is None:
            canonical_source = _canonical_device_path(filesystem.source)
            if canonical_source:
                device = devices_by_path.get(canonical_source)

        if device is None:
            continue

        device.filesystem_type = filesystem.filesystem_type

        if filesystem.mountpoint not in device.mountpoints:
            device.mountpoints.append(filesystem.mountpoint)

    return StorageInventory(
        devices=devices,
        filesystems=filesystems,
        filesystem_groups=group_filesystems(filesystems),
    )
