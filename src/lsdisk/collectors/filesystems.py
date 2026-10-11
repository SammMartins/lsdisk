"""Discover mounted filesystems using Linux mountinfo and statvfs."""

import os
import re
from pathlib import Path

from lsdisk.models import FilesystemUsage


MOUNTINFO_PATH = Path("/proc/self/mountinfo")
_OCTAL_ESCAPE = re.compile(r"\\([0-7]{3})")


def _unescape_mountinfo(value: str) -> str:
    """Decode octal escapes used in mountinfo fields."""
    return _OCTAL_ESCAPE.sub(
        lambda match: chr(int(match.group(1), 8)),
        value,
    )


def _parse_mountinfo_line(line: str) -> dict[str, str] | None:
    """Parse one mountinfo line into normalized fields."""
    try:
        before_separator, after_separator = line.split(" - ", 1)
        left = before_separator.split()
        right = after_separator.split()

        if len(left) < 6 or len(right) < 3:
            return None

        return {
            "device_id": left[2],
            "filesystem_root": _unescape_mountinfo(left[3]),
            "mountpoint": _unescape_mountinfo(left[4]),
            "filesystem_type": right[0],
            "source": _unescape_mountinfo(right[1]),
        }
    except (ValueError, IndexError):
        return None


def collect_filesystems(
    mountinfo_path: Path = MOUNTINFO_PATH,
) -> list[FilesystemUsage]:
    """Collect capacity statistics for accessible mounted filesystems."""
    try:
        lines = mountinfo_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return []

    filesystems: list[FilesystemUsage] = []

    for line in lines:
        mount = _parse_mountinfo_line(line)
        if mount is None:
            continue

        mountpoint = mount["mountpoint"]

        try:
            stats = os.statvfs(mountpoint)
        except OSError:
            # A mount can disappear between reading mountinfo and statvfs.
            continue

        fragment_size = stats.f_frsize or stats.f_bsize
        total_bytes = stats.f_blocks * fragment_size
        free_bytes = stats.f_bfree * fragment_size
        available_bytes = stats.f_bavail * fragment_size

        try:
            usage = FilesystemUsage(
                mountpoint=mountpoint,
                source=mount["source"],
                filesystem_type=mount["filesystem_type"],
                total_bytes=total_bytes,
                free_bytes=free_bytes,
                available_bytes=available_bytes,
                device_id=mount["device_id"],
                filesystem_root=mount["filesystem_root"],
            )
        except ValueError:
            # Ignore inconsistent statistics rather than reporting bad data.
            continue

        filesystems.append(usage)

    return filesystems
