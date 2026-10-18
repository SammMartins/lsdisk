"""Helpers for best-effort Linux device identity resolution."""

from pathlib import Path


def canonical_device_path(path: str) -> str | None:
    """Return a resolved device path only when the path currently exists."""
    if not path.startswith("/dev/"):
        return None

    candidate = Path(path)
    try:
        if not candidate.exists():
            return None
        return str(candidate.resolve(strict=True))
    except (OSError, RuntimeError):
        return None
