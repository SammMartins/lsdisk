"""Discover LVM relationships through read-only machine-readable reports."""

import json
import subprocess
from collections.abc import Iterable

from lsdisk.device_paths import canonical_device_path
from lsdisk.models import (
    BlockDevice,
    StorageDeviceKind,
    StorageDeviceReference,
    StorageRelationship,
    StorageRelationshipType,
)


LVM_TIMEOUT_SECONDS = 2


def _walk(devices: list[BlockDevice]) -> Iterable[BlockDevice]:
    for device in devices:
        yield device
        yield from _walk(device.children)


def _run_report(command: str, columns: str) -> list[dict[str, object]]:
    """Run one read-only LVM report and return its rows, or no rows."""
    try:
        result = subprocess.run(
            [
                command,
                "--reportformat",
                "json",
                "--units",
                "b",
                "--nosuffix",
                "--readonly",
                "--options",
                columns,
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=LVM_TIMEOUT_SECONDS,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return []

    if result.returncode != 0:
        return []

    try:
        payload = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError):
        return []

    if not isinstance(payload, dict):
        return []

    report = payload.get("report")
    if not isinstance(report, list):
        return []

    rows: list[dict[str, object]] = []
    for item in report:
        if not isinstance(item, dict):
            continue
        for value in item.values():
            if isinstance(value, dict) and isinstance(value.get("rows"), list):
                rows.extend(
                    row for row in value["rows"] if isinstance(row, dict)
                )
    return rows


def _text(row: dict[str, object], key: str) -> str | None:
    value = row.get(key)
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _reference(
    identifier: str,
    *,
    kind: StorageDeviceKind,
    filesystem_uuid: str | None = None,
) -> StorageDeviceReference:
    canonical = canonical_device_path(identifier)
    return StorageDeviceReference(
        identifier=canonical or identifier,
        kind=kind,
        canonical_path=canonical,
        filesystem_uuid=filesystem_uuid,
    )


def _pv_reference(
    pv_name: str,
    pv_uuid: str | None,
) -> StorageDeviceReference:
    """Represent the LVM PV identity separately from its block-device path."""
    identity = f"lvm:pv:{pv_uuid}" if pv_uuid else f"lvm:pv:{pv_name}"
    return StorageDeviceReference(
        identifier=identity,
        kind=StorageDeviceKind.PARTITION,
        canonical_path=canonical_device_path(pv_name),
        filesystem_uuid=pv_uuid,
    )


def _relationship(
    relationship_type: StorageRelationshipType,
    upper: StorageDeviceReference,
    lower: tuple[StorageDeviceReference, ...],
) -> StorageRelationship | None:
    if not lower:
        return None
    try:
        return StorageRelationship(
            relationship_type=relationship_type,
            upper=upper,
            lower=lower,
        )
    except ValueError:
        return None


def collect_lvm_relationships(
    devices: list[BlockDevice],
) -> list[StorageRelationship]:
    """Collect verified PV/VG/LV relationships without activating LVM."""
    discovered = list(_walk(devices))
    by_identity: dict[str, list[BlockDevice]] = {}
    for device in discovered:
        identity = canonical_device_path(device.path) or device.path
        by_identity.setdefault(identity, []).append(device)

    pv_rows = _run_report("pvs", "pv_name,vg_name,pv_uuid")
    vg_rows = _run_report("vgs", "vg_name,vg_uuid")
    lv_rows = _run_report("lvs", "lv_path,lv_name,vg_name,lv_uuid")

    pv_by_vg: dict[str, list[StorageDeviceReference]] = {}
    relationships: list[StorageRelationship] = []
    seen: set[tuple[str, str, tuple[str, ...]]] = set()
    seen_pvs: set[str] = set()
    seen_pv_paths: set[str] = set()

    for row in pv_rows:
        pv_name = _text(row, "pv_name")
        vg_name = _text(row, "vg_name")
        if not pv_name or not vg_name:
            continue
        pv_uuid = _text(row, "pv_uuid")
        pv_reference = _pv_reference(pv_name, pv_uuid)
        pv_path_identity = canonical_device_path(pv_name) or pv_name
        if (
            pv_reference.identifier in seen_pvs
            or pv_path_identity in seen_pv_paths
        ):
            continue
        seen_pvs.add(pv_reference.identifier)
        seen_pv_paths.add(pv_path_identity)
        pv_by_vg.setdefault(vg_name, []).append(pv_reference)

        matches = by_identity.get(pv_path_identity, [])
        if len(matches) == 1:
            device_reference = _reference(
                matches[0].path,
                kind=matches[0].storage_kind,
                filesystem_uuid=matches[0].filesystem_uuid,
            )
            relationship = _relationship(
                StorageRelationshipType.LVM_PHYSICAL_VOLUME,
                pv_reference,
                (device_reference,),
            )
            if relationship is not None:
                relationships.append(relationship)

    vg_identifiers: dict[str, set[str]] = {}
    for row in vg_rows:
        name = _text(row, "vg_name")
        if name:
            vg_identifiers.setdefault(name, set()).add(
                _text(row, "vg_uuid") or ""
            )
    valid_vgs = {
        name for name, identifiers in vg_identifiers.items()
        if len(identifiers) == 1
    }
    for vg_name, pvs in pv_by_vg.items():
        if vg_name not in valid_vgs or len({pv.identifier for pv in pvs}) != len(pvs):
            continue
        vg_reference = _reference(
            f"lvm:vg:{vg_name}",
            kind=StorageDeviceKind.LOGICAL,
        )
        relationship = _relationship(
            StorageRelationshipType.LVM_PHYSICAL_VOLUME,
            vg_reference,
            tuple(pvs),
        )
        if relationship is not None:
            key = (
                relationship.relationship_type,
                relationship.upper.identifier,
                tuple(item.identifier for item in relationship.lower),
            )
            if key not in seen:
                seen.add(key)
                relationships.append(relationship)

    for row in lv_rows:
        vg_name = _text(row, "vg_name")
        lv_name = _text(row, "lv_name")
        lv_path = _text(row, "lv_path") or (
            f"/dev/{vg_name}/{lv_name}"
            if vg_name and lv_name
            else None
        )
        if not vg_name or not lv_name or not lv_path or vg_name not in valid_vgs:
            continue
        lv_reference = _reference(
            lv_path,
            kind=StorageDeviceKind.LOGICAL,
            filesystem_uuid=_text(row, "lv_uuid"),
        )
        vg_reference = _reference(
            f"lvm:vg:{vg_name}",
            kind=StorageDeviceKind.LOGICAL,
        )
        relationship = _relationship(
            StorageRelationshipType.LVM_LOGICAL_VOLUME,
            lv_reference,
            (vg_reference,),
        )
        if relationship is not None:
            key = (
                relationship.relationship_type,
                relationship.upper.identifier,
                tuple(item.identifier for item in relationship.lower),
            )
            if key not in seen:
                seen.add(key)
                relationships.append(relationship)

    return relationships
