"""Collect filesystem metadata without mounting block devices."""

from collections.abc import Iterator
from dataclasses import dataclass
import json
import re
import subprocess

from lsdisk.models import FilesystemProbe, ProbeState


PROBE_TIMEOUT_SECONDS = 2
_HEX_ESCAPE = re.compile(r"\\x([0-9a-fA-F]{2})")


def _string_or_none(value: object) -> str | None:
    """Return a non-empty string value from command output."""
    return value if isinstance(value, str) and value else None


@dataclass(frozen=True)
class FilesystemMetadata:
    """Metadata read from a block device without mounting it."""

    filesystem_type: str | None = None
    label: str | None = None
    uuid: str | None = None


def _unescape_export_value(value: str) -> str:
    """Decode hexadecimal escapes emitted by blkid export output."""
    return _HEX_ESCAPE.sub(
        lambda match: chr(int(match.group(1), 16)),
        value,
    )


def _parse_export_output(output: str) -> FilesystemMetadata | None:
    """Parse key-value output from blkid."""

    values: dict[str, str] = {}

    for line in output.splitlines():
        key, separator, value = line.partition("=")
        if separator and key and value:
            values[key] = _unescape_export_value(value)

    metadata = FilesystemMetadata(
        filesystem_type=values.get("TYPE"),
        label=values.get("LABEL"),
        uuid=values.get("UUID"),
    )

    if not any((
        metadata.filesystem_type,
        metadata.label,
        metadata.uuid,
    )):
        return None

    return metadata


def _walk_lsblk_devices(devices: list[dict]) -> Iterator[dict]:
    """Yield devices recursively from lsblk JSON output."""

    for device in devices:
        if not isinstance(device, dict):
            continue
        yield device
        children = device.get("children") or []
        if isinstance(children, list):
            yield from _walk_lsblk_devices(children)


def collect_lsblk_metadata() -> dict[str, FilesystemMetadata]:
    """Collect filesystem metadata from lsblk for all visible block devices."""

    try:
        result = subprocess.run(
            [
                "lsblk",
                "--json",
                "--output",
                "PATH,FSTYPE,LABEL,UUID",
            ],
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
        devices = payload.get("blockdevices", [])
    except (json.JSONDecodeError, AttributeError, TypeError):
        return {}

    if not isinstance(devices, list):
        return {}

    metadata_by_path: dict[str, FilesystemMetadata] = {}

    for device in _walk_lsblk_devices(devices):
        path = device.get("path")
        if not isinstance(path, str) or not path.startswith("/dev/"):
            continue

        filesystem_type = _string_or_none(device.get("fstype"))
        label = _string_or_none(device.get("label"))
        uuid = _string_or_none(device.get("uuid"))

        metadata = FilesystemMetadata(
            filesystem_type=filesystem_type,
            label=label,
            uuid=uuid,
        )

        if any((
            metadata.filesystem_type,
            metadata.label,
            metadata.uuid,
        )):
            metadata_by_path[path] = metadata

    return metadata_by_path


def _parse_probe_output(output: str) -> FilesystemProbe:
    """Classify blkid export output without treating missing fields as zeros."""
    if not output.strip():
        return FilesystemProbe(ProbeState.NO_SIGNATURE)

    values: dict[str, str] = {}
    malformed = False
    for line in output.splitlines():
        key, separator, value = line.partition("=")
        if not separator or not key or not value:
            malformed = True
            continue
        values[key] = _unescape_export_value(value)

    if malformed or not values:
        return FilesystemProbe(ProbeState.ERROR)

    if not any(values.get(key) for key in ("TYPE", "LABEL", "UUID")):
        return FilesystemProbe(ProbeState.NO_SIGNATURE)

    metadata = FilesystemMetadata(
        filesystem_type=values.get("TYPE"),
        label=values.get("LABEL"),
        uuid=values.get("UUID"),
    )
    return FilesystemProbe(ProbeState.RECOGNIZED, metadata)


def probe_filesystem_outcome(device_path: str) -> FilesystemProbe:
    """Probe a device and preserve the reason its result is inconclusive."""
    if not device_path.startswith("/dev/"):
        return FilesystemProbe(ProbeState.UNAVAILABLE)

    try:
        result = subprocess.run(
            ["blkid", "--probe", "--output", "export", device_path],
            capture_output=True,
            text=True,
            check=False,
            timeout=PROBE_TIMEOUT_SECONDS,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError):
        return FilesystemProbe(ProbeState.UNAVAILABLE)
    except OSError:
        return FilesystemProbe(ProbeState.UNAVAILABLE)

    if result.returncode == 0:
        return _parse_probe_output(result.stdout)

    stderr = (result.stderr or "").lower()
    if any(term in stderr for term in ("permission denied", "operation not permitted", "access denied")):
        return FilesystemProbe(ProbeState.UNAVAILABLE)
    if result.returncode == 2 and not result.stdout.strip():
        return FilesystemProbe(ProbeState.NO_SIGNATURE)
    return FilesystemProbe(ProbeState.ERROR)


def probe_filesystem(device_path: str) -> FilesystemMetadata | None:
    """Probe a block device read-only; never mount or modify it."""
    outcome = probe_filesystem_outcome(device_path)
    return outcome.metadata
