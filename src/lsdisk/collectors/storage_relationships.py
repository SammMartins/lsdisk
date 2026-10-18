"""Discover read-only storage relationships exposed by Linux sysfs."""

from collections.abc import Iterator
from pathlib import Path

from lsdisk.device_paths import canonical_device_path
from lsdisk.models import (
    BlockDevice,
    StorageDeviceKind,
    StorageDeviceReference,
    StorageRelationship,
    StorageRelationshipType,
)


SYSFS_BLOCK_PATH = Path("/sys/class/block")


def _walk(devices: list[BlockDevice]) -> Iterator[BlockDevice]:
    for device in devices:
        yield device
        yield from _walk(device.children)


def _reference(device: BlockDevice) -> StorageDeviceReference:
    """Build a relationship reference from stable facts already collected."""
    canonical_path = canonical_device_path(device.path)
    return StorageDeviceReference(
        identifier=canonical_path or device.path,
        kind=device.storage_kind,
        canonical_path=canonical_path,
        filesystem_uuid=device.filesystem_uuid,
    )


def _identity(device: BlockDevice) -> str:
    """Return a canonical identity, falling back to the original path."""
    return canonical_device_path(device.path) or device.path


def _would_cycle(
    upper: BlockDevice,
    lower: list[BlockDevice],
    accepted: dict[str, set[str]],
) -> bool:
    """Return whether adding the proposed edges would create a cycle."""
    upper_id = _identity(upper)
    lower_ids = {_identity(device) for device in lower}
    if upper_id in lower_ids:
        return True

    graph = {key: set(value) for key, value in accepted.items()}
    graph.setdefault(upper_id, set()).update(lower_ids)

    def reaches(start: str, target: str, seen: set[str]) -> bool:
        if start == target:
            return True
        if start in seen:
            return False
        seen.add(start)
        return any(
            reaches(next_node, target, seen)
            for next_node in graph.get(start, ())
        )

    return any(reaches(lower_id, upper_id, set()) for lower_id in lower_ids)


def _relationship_type(
    upper: BlockDevice,
    lower: tuple[BlockDevice, ...],
) -> str:
    """Classify only the encrypted mapping case proven by signatures."""
    if (
        upper.storage_kind is StorageDeviceKind.LOGICAL
        and any(device.filesystem_type == "crypto_LUKS" for device in lower)
    ):
        return StorageRelationshipType.ENCRYPTED_MAPPING
    return StorageRelationshipType.BACKED_BY


def collect_storage_relationships(
    devices: list[BlockDevice],
    *,
    sysfs_path: Path = SYSFS_BLOCK_PATH,
) -> list[StorageRelationship]:
    """Return verified parent and sysfs-slave relationships without activation."""
    discovered = list(_walk(devices))
    devices_by_name: dict[str, list[BlockDevice]] = {}
    for device in discovered:
        devices_by_name.setdefault(device.name, []).append(device)
    relationships: list[StorageRelationship] = []
    accepted: dict[str, set[str]] = {}

    for device in discovered:
        lower: list[BlockDevice] = []
        if device.parent_name:
            parents = devices_by_name.get(device.parent_name, [])
            if len(parents) == 1:
                parent = parents[0]
                lower.append(parent)

        slave_dir = sysfs_path / device.name / "slaves"
        try:
            slave_names = sorted(entry.name for entry in slave_dir.iterdir())
        except OSError:
            slave_names = []
        lower_ids = {_identity(item) for item in lower}
        for name in slave_names:
            candidates = devices_by_name.get(name, [])
            if len(candidates) != 1:
                continue
            candidate = candidates[0]
            identity = _identity(candidate)
            if identity not in lower_ids:
                lower.append(candidate)
                lower_ids.add(identity)

        if not lower:
            continue

        if _would_cycle(device, lower, accepted):
            continue

        try:
            relationship = StorageRelationship(
                relationship_type=_relationship_type(device, tuple(lower)),
                upper=_reference(device),
                lower=tuple(_reference(item) for item in lower),
            )
        except ValueError:
            continue

        relationships.append(relationship)
        accepted.setdefault(_identity(device), set()).update(
            _identity(item) for item in lower
        )

    return relationships
