"""Parse persistent mount configuration without resolving or mounting it."""

from __future__ import annotations

import shlex
import re
from pathlib import Path

from lsdisk.models import FstabEntry

FSTAB_PATH = Path("/etc/fstab")
_OCTAL_ESCAPE = re.compile(r"\\([0-7]{3})")


def collect_fstab_entries(path: Path = FSTAB_PATH) -> list[FstabEntry]:
    """Parse valid fstab rows and preserve unresolved sources."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return []

    entries: list[FstabEntry] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        try:
            protected = _OCTAL_ESCAPE.sub(
                lambda match: "\x1f" + match.group(1),
                stripped,
            )
            fields = shlex.split(
                protected,
                comments=True,
                posix=True,
            )
        except ValueError:
            continue
        if len(fields) < 4:
            continue
        fields = [
            field.replace("\x1f040", " ")
            .replace("\x1f011", "\t")
            .replace("\x1f134", "\\")
            for field in fields
        ]
        entries.append(
            FstabEntry(
                source=fields[0],
                mountpoint=fields[1],
                filesystem_type=fields[2],
                options=tuple(item for item in fields[3].split(",") if item),
                dump=fields[4] if len(fields) > 4 else None,
                pass_number=fields[5] if len(fields) > 5 else None,
            )
        )
    return entries
