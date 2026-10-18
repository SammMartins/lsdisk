"""Build a unified inventory of Linux storage."""

from dataclasses import dataclass, field
from collections.abc import Iterator

from lsdisk.analyzers.filesystems import (
    FilesystemGroup,
    group_filesystems,
)
from lsdisk.device_paths import canonical_device_path
from lsdisk.collectors.filesystem_metadata import (
    collect_lsblk_metadata,
    probe_filesystem,
)
from lsdisk.collectors.block_devices import collect_block_devices
from lsdisk.collectors.filesystems import collect_filesystems
from lsdisk.collectors.lvm import collect_lvm_relationships
from lsdisk.collectors.mdraid import collect_mdraid_relationships
from lsdisk.collectors.storage_relationships import (
    collect_storage_relationships,
)
from lsdisk.models import (
    BlockDevice,
    FilesystemUsage,
    StorageRelationship,
)


@dataclass
class StorageInventory:
    """Store discovered devices and filesystem information."""

    devices: list[BlockDevice]
    filesystems: list[FilesystemUsage]
    filesystem_groups: list[FilesystemGroup]
    relationships: list[StorageRelationship] = field(default_factory=list)


def walk_devices(
    devices: list[BlockDevice],
) -> Iterator[BlockDevice]:
    """Yield devices recursively, including partitions."""
    for device in devices:
        yield device
        yield from walk_devices(device.children)


def collect_storage_inventory() -> StorageInventory:
    """Collect devices and filesystems and associate their mountpoints."""
    devices = collect_block_devices()
    filesystems = collect_filesystems()

    devices_by_path: dict[str, BlockDevice] = {}

    for device in walk_devices(devices):
        devices_by_path[device.path] = device
        canonical_path = canonical_device_path(device.path)

        if canonical_path:
            devices_by_path[canonical_path] = device

    # Prefer lsblk metadata because it is available without elevated privileges.
    # Use blkid to complement fields that lsblk did not provide.
    lsblk_metadata = collect_lsblk_metadata()
    metadata_by_path = dict(lsblk_metadata)
    for path, metadata in lsblk_metadata.items():
        canonical_path = canonical_device_path(path)
        if canonical_path:
            metadata_by_path[canonical_path] = metadata

    for device in walk_devices(devices):
        metadata = metadata_by_path.get(device.path)
        if metadata is None:
            canonical_path = canonical_device_path(device.path)
            if canonical_path:
                metadata = metadata_by_path.get(canonical_path)

        if metadata is not None:
            if metadata.filesystem_type:
                device.filesystem_type = metadata.filesystem_type
            if metadata.label:
                device.filesystem_label = metadata.label
            if metadata.uuid:
                device.filesystem_uuid = metadata.uuid

        if (
            device.filesystem_type
            and device.filesystem_label
            and device.filesystem_uuid
        ):
            continue

        probed = probe_filesystem(device.path)
        if probed is None:
            continue

        if not device.filesystem_type and probed.filesystem_type:
            device.filesystem_type = probed.filesystem_type

        if not device.filesystem_label and probed.label:
            device.filesystem_label = probed.label

        if not device.filesystem_uuid and probed.uuid:
            device.filesystem_uuid = probed.uuid

    for filesystem in filesystems:
        device = devices_by_path.get(filesystem.source)

        if device is None:
            canonical_source = canonical_device_path(filesystem.source)
            if canonical_source:
                device = devices_by_path.get(canonical_source)

        if device is None:
            continue

        if not device.filesystem_type:
            device.filesystem_type = filesystem.filesystem_type

        if filesystem.mountpoint not in device.mountpoints:
            device.mountpoints.append(filesystem.mountpoint)

    return StorageInventory(
        devices=devices,
        filesystems=filesystems,
        filesystem_groups=group_filesystems(filesystems),
        relationships=(
            collect_storage_relationships(devices)
            + collect_lvm_relationships(devices)
            + collect_mdraid_relationships(devices)
        ),
    )
