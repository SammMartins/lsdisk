"""Serialize storage inventory for machine-readable output."""

from typing import Any

from lsdisk import format_bytes
from lsdisk import classify_filesystem
from lsdisk import StorageInventory
from lsdisk import (
    BlockDevice,
    FilesystemUsage,
    StorageDeviceReference,
    StorageRelationship,
)
from lsdisk.models import storage_reference_identity


SUMMARY_CATEGORIES = {"persistent", "network"}


def _optional_text_key(value: str | None) -> tuple[bool, str]:
    """Sort present text values before consistently placed missing values."""
    return (value is None, value or "")


def _optional_scalar_key(value: Any) -> tuple[bool, Any]:
    """Sort optional scalar values without comparing None to a value."""
    return (value is None, value)


def _device_sort_key(device: BlockDevice) -> tuple[object, ...]:
    """Return stable scalar fields for device serialization order."""
    return (
        device.path,
        device.name,
        device.device_type,
        device.size_bytes,
        _optional_text_key(device.parent_name),
        _optional_scalar_key(device.physical),
        _optional_text_key(device.model),
        _optional_text_key(device.transport),
        _optional_scalar_key(device.rotational),
        _optional_text_key(device.filesystem_type),
        _optional_text_key(device.filesystem_label),
        _optional_text_key(device.filesystem_uuid),
        _optional_text_key(
            device.filesystem_probe_state.value
            if device.filesystem_probe_state is not None
            else None
        ),
        tuple(sorted(device.mountpoints)),
        (
            device.partition_metadata is None,
            (
                device.partition_metadata.partition_table,
                device.partition_metadata.logical_sector_size,
                device.partition_metadata.physical_sector_size,
                device.partition_metadata.start_sector,
                device.partition_metadata.end_sector,
                _optional_text_key(device.partition_metadata.partition_name),
                _optional_text_key(device.partition_metadata.partition_type),
                tuple(sorted(device.partition_metadata.flags)),
            )
            if device.partition_metadata is not None
            else (),
        ),
        tuple(_device_sort_key(child) for child in _sorted_devices(device.children)),
    )


def _sorted_devices(devices: list[BlockDevice]) -> list[BlockDevice]:
    """Return devices in stable order without mutating the inventory."""
    return sorted(devices, key=_device_sort_key)


def _device_to_dict(
    device: BlockDevice,
    *,
    include_all: bool,
) -> dict[str, Any]:
    """Convert a device and its children to JSON-compatible data."""
    result = {
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
        "filesystem_probe_state": (
            device.filesystem_probe_state.value
            if device.filesystem_probe_state is not None else None
        ),
        "mountpoints": sorted(device.mountpoints),
        "children": [
            _device_to_dict(child, include_all=include_all)
            for child in _sorted_devices(device.children)
        ],
    }
    if include_all:
        result["partition_metadata"] = (
            {
                "partition_table": device.partition_metadata.partition_table,
                "logical_sector_size": device.partition_metadata.logical_sector_size,
                "physical_sector_size": device.partition_metadata.physical_sector_size,
                "start_sector": device.partition_metadata.start_sector,
                "end_sector": device.partition_metadata.end_sector,
                "partition_name": device.partition_metadata.partition_name,
                "partition_type": device.partition_metadata.partition_type,
                "flags": list(device.partition_metadata.flags),
            }
            if device.partition_metadata is not None else None
        )
    return result


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


def _group_sort_key(group: Any) -> tuple[object, ...]:
    """Return stable scalar fields for filesystem group ordering."""
    filesystem = group.representative
    return (
        _optional_text_key(filesystem.device_id),
        filesystem.source,
        filesystem.filesystem_type,
        classify_filesystem(filesystem),
        filesystem.total_bytes,
        filesystem.used_bytes,
        filesystem.available_bytes,
        _optional_text_key(filesystem.filesystem_root),
        round(filesystem.used_percent, 2),
        tuple(sorted(group.mountpoints)),
    )


def _mount_sort_key(filesystem: FilesystemUsage) -> tuple[object, ...]:
    """Return stable scalar fields for expanded mount ordering."""
    return (
        filesystem.mountpoint,
        filesystem.source,
        filesystem.filesystem_type,
        classify_filesystem(filesystem),
        _optional_text_key(filesystem.device_id),
        _optional_text_key(filesystem.filesystem_root),
        filesystem.total_bytes,
        filesystem.free_bytes,
        filesystem.available_bytes,
        filesystem.used_bytes,
        round(filesystem.used_percent, 2),
    )


def _reference_to_dict(reference: StorageDeviceReference) -> dict[str, Any]:
    """Convert a normalized storage reference without changing its identity."""
    return {
        "identifier": reference.identifier,
        "kind": reference.kind.value,
        "canonical_path": reference.canonical_path,
        "filesystem_uuid": reference.filesystem_uuid,
    }


def _relationship_to_dict(
    relationship: StorageRelationship,
) -> dict[str, Any]:
    """Convert one relationship to a deterministic JSON structure."""
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
        lower_by_identity.setdefault(storage_reference_identity(reference), reference)
    lower = [
        lower_by_identity[identity]
        for identity in sorted(lower_by_identity)
    ]
    return {
        "relationship_type": relationship.relationship_type,
        "upper": _reference_to_dict(relationship.upper),
        "lower": [_reference_to_dict(reference) for reference in lower],
    }


def _relationships_to_dict(
    relationships: list[StorageRelationship],
) -> list[dict[str, Any]]:
    """Deduplicate and sort relationships for reproducible output."""
    entries = []
    for relationship in relationships:
        item = _relationship_to_dict(relationship)
        if not item["lower"]:
            continue
        key = (
            item["relationship_type"],
            item["upper"]["canonical_path"] or item["upper"]["identifier"],
            tuple(
                reference["canonical_path"] or reference["identifier"]
                for reference in item["lower"]
            ),
        )
        entries.append((key, item))

    serialized: dict[tuple[Any, ...], dict[str, Any]] = {}
    for key, item in sorted(
        entries,
        key=lambda entry: (
            entry[0],
            entry[1]["upper"]["identifier"]
            != entry[1]["upper"]["canonical_path"],
            entry[1]["upper"]["identifier"],
            repr(entry[1]),
        ),
    ):
        serialized.setdefault(key, item)
    return [
        serialized[key]
        for key in sorted(serialized)
    ]


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
    for group in sorted(inventory.filesystem_groups, key=_group_sort_key):
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
                "mountpoints": sorted(group.mountpoints),
            }
        )

    mounts = (
        [
            _mount_to_dict(filesystem)
            for filesystem in sorted(
                inventory.filesystems,
                key=_mount_sort_key,
            )
        ]
        if include_all
        else []
    )

    result = {
        "schema_version": 1,
        "mode": "all" if include_all else "simple",
        "devices": [
            _device_to_dict(device, include_all=include_all)
            for device in _sorted_devices(devices)
        ],
        "filesystems": groups,
        "mounts": mounts,
        "relationships": _relationships_to_dict(inventory.relationships),
    }
    if include_all:
        result["fstab"] = [
            {
                "source": entry.source,
                "mountpoint": entry.mountpoint,
                "filesystem_type": entry.filesystem_type,
                "options": list(entry.options),
                "dump": entry.dump,
                "pass_number": entry.pass_number,
            }
            for entry in sorted(
                inventory.fstab_entries,
                key=lambda item: (item.mountpoint, item.source),
            )
        ]
        result["unallocated_regions"] = [
            {
                "disk_path": region.disk_path,
                "start_bytes": region.start_bytes,
                "end_bytes": region.end_bytes,
                "size_bytes": region.size_bytes,
            }
            for region in sorted(
                inventory.unallocated_regions,
                key=lambda item: (item.disk_path, item.start_bytes),
            )
        ]
    return result
