"""Discover Linux MD RAID relationships through read-only interfaces."""

import re
import subprocess
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
MDSTAT_PATH = Path("/proc/mdstat")
MDADM_TIMEOUT_SECONDS = 2
_MDSTAT_ACTIVE = re.compile(r"^(\S+)\s+:\s+active(?:\s|$)")
_MDADM_MEMBER = re.compile(r"^MD_DEVICE_\d+_DEV=(\S+)$")


def _walk(devices: list[BlockDevice]) -> Iterator[BlockDevice]:
    for device in devices:
        yield device
        yield from _walk(device.children)


def _active_arrays(mdstat_path: Path) -> set[str] | None:
    """Return active array names, or None when mdstat is unavailable."""
    try:
        content = mdstat_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None

    return {
        match.group(1)
        for line in content.splitlines()
        if (match := _MDSTAT_ACTIVE.match(line))
    }


def _mdadm_members(array_path: str) -> list[str]:
    """Read optional mdadm export metadata without changing array state."""
    try:
        result = subprocess.run(
            ["mdadm", "--detail", "--export", array_path],
            capture_output=True,
            text=True,
            check=False,
            timeout=MDADM_TIMEOUT_SECONDS,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return []

    if result.returncode != 0:
        return []

    return [
        match.group(1)
        for line in result.stdout.splitlines()
        if (match := _MDADM_MEMBER.match(line))
    ]


def _reference(device: BlockDevice) -> StorageDeviceReference:
    canonical = canonical_device_path(device.path)
    return StorageDeviceReference(
        identifier=canonical or device.path,
        kind=device.storage_kind,
        canonical_path=canonical,
        filesystem_uuid=device.filesystem_uuid,
    )


def _array_reference(name: str) -> StorageDeviceReference:
    path = f"/dev/{name}"
    canonical = canonical_device_path(path)
    return StorageDeviceReference(
        identifier=canonical or path,
        kind=StorageDeviceKind.LOGICAL,
        canonical_path=canonical,
    )


def _would_cycle(
    upper: StorageDeviceReference,
    lower: tuple[StorageDeviceReference, ...],
    accepted: dict[str, set[str]],
) -> bool:
    """Return whether adding an array edge would create a topology cycle."""
    upper_id = upper.identifier
    lower_ids = {device.identifier for device in lower}
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


def collect_mdraid_relationships(
    devices: list[BlockDevice],
    *,
    sysfs_path: Path = SYSFS_BLOCK_PATH,
    mdstat_path: Path = MDSTAT_PATH,
) -> list[StorageRelationship]:
    """Return verified MD array-to-member relationships without activation."""
    discovered = list(_walk(devices))
    by_name: dict[str, list[BlockDevice]] = {}
    by_identity: dict[str, list[BlockDevice]] = {}
    for device in discovered:
        by_name.setdefault(device.name, []).append(device)
        identity = canonical_device_path(device.path) or device.path
        by_identity.setdefault(identity, []).append(device)

    active_arrays = _active_arrays(mdstat_path)
    try:
        array_dirs = sorted(
            entry for entry in sysfs_path.iterdir()
            if entry.is_dir() and entry.name.startswith("md")
        )
    except OSError:
        return []

    relationships: list[StorageRelationship] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()
    accepted: dict[str, set[str]] = {}
    for array_dir in array_dirs:
        name = array_dir.name
        if active_arrays is not None and active_arrays and name not in active_arrays:
            # sysfs remains authoritative for topology; mdstat only filters
            # clearly inactive arrays when it provides active-array data.
            continue

        member_names: list[str]
        slave_dir = array_dir / "slaves"
        try:
            member_names = sorted(entry.name for entry in slave_dir.iterdir())
        except OSError:
            member_names = []

        members: list[BlockDevice] = []
        unresolved = False
        for member_name in member_names:
            candidates = by_name.get(member_name, [])
            if len(candidates) != 1:
                unresolved = True
                continue
            members.append(candidates[0])

        if not member_names or unresolved and not members:
            mdadm_names = _mdadm_members(f"/dev/{name}")
            for member_path in mdadm_names:
                identity = canonical_device_path(member_path) or member_path
                candidates = by_identity.get(identity, [])
                if len(candidates) == 1:
                    members.append(candidates[0])

        unique_members: list[BlockDevice] = []
        member_ids: set[str] = set()
        for member in members:
            identity = canonical_device_path(member.path) or member.path
            if identity not in member_ids:
                member_ids.add(identity)
                unique_members.append(member)
        if not unique_members:
            continue

        upper = _array_reference(name)
        lower = tuple(_reference(member) for member in unique_members)
        if _would_cycle(upper, lower, accepted):
            continue
        try:
            relationship = StorageRelationship(
                relationship_type=StorageRelationshipType.RAID_MEMBER,
                upper=upper,
                lower=lower,
            )
        except ValueError:
            continue

        key = (relationship.upper.identifier, tuple(
            member.identifier for member in relationship.lower
        ))
        if key not in seen:
            seen.add(key)
            relationships.append(relationship)
            accepted.setdefault(upper.identifier, set()).update(
                member.identifier for member in lower
            )

    return relationships
