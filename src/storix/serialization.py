"""Serialize storage inventory for machine-readable output."""

from typing import Any

from storix.analyzers.capacity import format_bytes
from storix.analyzers.filesystems import classify_filesystem
from storix.inventory import StorageInventory
from storix.models import BlockDevice, FilesystemUsage


SUMMARY_CATEGORIES = {"persistent", "network"}


def _device_to_dict(device: BlockDevice) -> dict[str, Any]:
    """Convert a device and its children to JSON-compatible data."""
    return {
        "name": device.name,
        "path": device.path,
        "type": device.device_type,
        "size_bytes": device.size_bytes,
        "size_human": format_bytes(device.size_bytes),
        "physical": device.physical,
        "parent_name": device.parent_name,
        "model": device.model,
        "transport": device.transport,
        "rotational": device.rotational,
        "filesystem_type": device.filesystem_type,
        "filesystem_label": device.filesystem_label,
        "filesystem_uuid": device.filesystem_uuid,
        "mountpoints": device.mountpoints,
        "children": [_device_to_dict(child) for child in device.children],
    }


def _mount_to_dict(filesystem: FilesystemUsage) -> dict[str, Any]:
    """Convert one mountpoint and its capacity statistics."""
    return {
        "mountpoint": filesystem.mountpoint,
        "source": filesystem.source,
        "filesystem_type": filesystem.filesystem_type,
        "category": classify_filesystem(filesystem),
        "device_id": filesystem.device_id,
        "filesystem_root": filesystem.filesystem_root,
        "total_bytes": filesystem.total_bytes,
        "free_bytes": filesystem.free_bytes,
        "available_bytes": filesystem.available_bytes,
        "used_bytes": filesystem.used_bytes,
        "used_percent": round(filesystem.used_percent, 2),
    }


def inventory_to_dict(
    inventory: StorageInventory,
    *,
    include_all: bool = False,
) -> dict[str, Any]:
    """Convert inventory to a stable, JSON-compatible structure."""
    if include_all:
        devices = inventory.devices
    else:
        devices = [
            device
            for device in inventory.devices
            if device.is_physical_disk
        ]

    groups = []
    for group in inventory.filesystem_groups:
        filesystem = group.representative
        category = classify_filesystem(filesystem)

        if not include_all and category not in SUMMARY_CATEGORIES:
            continue

        groups.append(
            {
                "source": filesystem.source,
                "filesystem_type": filesystem.filesystem_type,
                "category": category,
                "device_id": filesystem.device_id,
                "total_bytes": group.total_bytes,
                "used_bytes": group.used_bytes,
                "available_bytes": group.available_bytes,
                "used_percent": round(filesystem.used_percent, 2),
                "mountpoints": group.mountpoints,
            }
        )

    mounts = (
        [_mount_to_dict(filesystem) for filesystem in inventory.filesystems]
        if include_all
        else []
    )

    return {
        "schema_version": 1,
        "mode": "all" if include_all else "simple",
        "devices": [_device_to_dict(device) for device in devices],
        "filesystems": groups,
        "mounts": mounts,
    }
