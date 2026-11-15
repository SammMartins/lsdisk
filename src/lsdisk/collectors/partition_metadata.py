"""Collect partition geometry from read-only lsblk JSON output."""

from __future__ import annotations

import json
import subprocess

from lsdisk.models import (
    PARTITION_SECTOR_SIZE_BYTES,
    BlockDevice,
    PartitionMetadata,
)

PROBE_TIMEOUT_SECONDS = 2


def _walk(rows: object):
    if not isinstance(rows, list):
        return
    for row in rows:
        if not isinstance(row, dict):
            continue
        yield row
        yield from _walk(row.get("children"))


def _integer(row: dict, key: str) -> int | None:
    value = row.get(key)
    if isinstance(value, bool):
        return None
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _text(row: dict, key: str) -> str | None:
    value = row.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else None


def collect_partition_metadata(
    *,
    command: str = "lsblk",
) -> dict[str, PartitionMetadata]:
    """Return verified geometry and partition-table metadata by device path."""
    columns = (
        "PATH,TYPE,SIZE,START,LOG-SEC,PHY-SEC,PTTYPE,PARTLABEL,"
        "PARTTYPE,PARTFLAGS"
    )
    try:
        result = subprocess.run(
            [command, "--json", "--bytes", "--output", columns],
            capture_output=True,
            text=True,
            check=False,
            timeout=PROBE_TIMEOUT_SECONDS,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return {}
    if result.returncode != 0:
        return {}
    try:
        payload = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError):
        return {}

    metadata: dict[str, PartitionMetadata] = {}
    for row in _walk(payload.get("blockdevices") if isinstance(payload, dict) else None):
        path = _text(row, "path")
        if not path or not path.startswith("/dev/"):
            continue
        logical = _integer(row, "log-sec")
        physical = _integer(row, "phy-sec")
        start = _integer(row, "start")
        size = _integer(row, "size")
        valid_geometry = (
            start is not None
            and start >= 0
            and size is not None
            and size > 0
            and size % PARTITION_SECTOR_SIZE_BYTES == 0
        )
        if valid_geometry and logical is not None:
            valid_geometry = (
                logical > 0
                and size % logical == 0
                and (start * PARTITION_SECTOR_SIZE_BYTES) % logical == 0
            )
        # lsblk reports START in 512-byte sectors and SIZE in bytes when
        # --bytes is used, so neither value is expressed in logical sectors.
        end = (
            start + size // PARTITION_SECTOR_SIZE_BYTES - 1
            if valid_geometry else None
        )
        flags = tuple(
            flag.strip() for flag in (_text(row, "partflags") or "").split(",")
            if flag.strip()
        )
        metadata[path] = PartitionMetadata(
            partition_table=_text(row, "pttype"),
            logical_sector_size=logical,
            physical_sector_size=physical,
            start_sector=start,
            end_sector=end,
            partition_name=_text(row, "partlabel"),
            partition_type=_text(row, "parttype"),
            flags=flags,
        )
    return metadata


def apply_partition_metadata(
    devices: list[BlockDevice],
    metadata: dict[str, PartitionMetadata],
) -> None:
    """Attach metadata to the existing normalized device hierarchy."""
    by_path = {device.path: device for device in _walk_devices(devices)}
    for path, value in metadata.items():
        device = by_path.get(path)
        if device is not None:
            device.partition_metadata = value


def _walk_devices(devices: list[BlockDevice]):
    for device in devices:
        yield device
        yield from _walk_devices(device.children)
