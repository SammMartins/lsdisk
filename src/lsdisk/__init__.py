"""lsdisk: Cross-distro Linux Storage Explorer."""

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import tomllib


def _version_from_project_file() -> str | None:
    """Read the project version when installed metadata is unavailable."""
    package_path = Path(__file__).resolve()
    for parent in package_path.parents:
        project_file = parent / "pyproject.toml"
        try:
            with project_file.open("rb") as file:
                project = tomllib.load(file)
        except (FileNotFoundError, OSError, tomllib.TOMLDecodeError):
            continue

        try:
            project_version = project["project"]["version"]
        except (KeyError, TypeError):
            continue

        if isinstance(project_version, str) and project_version:
            return project_version

    return None


def _package_version() -> str:
    """Return the installed or source-tree package version."""
    project_version = _version_from_project_file()
    if project_version:
        return project_version

    try:
        return version("lsdisk")
    except PackageNotFoundError:
        return "unknown"


__version__ = _package_version()

from lsdisk.analyzers.capacity import (
    capacity_owners,
    format_bytes,
    owned_capacity_bytes,
)
from lsdisk.analyzers.filesystems import classify_filesystem
from lsdisk.inventory import StorageInventory, collect_storage_inventory
from lsdisk.models import (
    BlockDevice,
    FilesystemProbe,
    FilesystemUsage,
    ProbeState,
    StorageDeviceKind,
    StorageDeviceReference,
    StorageRelationship,
    StorageRelationshipType,
)
from lsdisk.serialization import inventory_to_dict
from lsdisk.ui.terminal import (
    create_console,
    render_all,
    render_compact,
    render_simple,
)

__all__ = [
    "BlockDevice",
    "FilesystemProbe",
    "FilesystemUsage",
    "ProbeState",
    "StorageInventory",
    "StorageDeviceKind",
    "StorageDeviceReference",
    "StorageRelationship",
    "StorageRelationshipType",
    "classify_filesystem",
    "capacity_owners",
    "collect_storage_inventory",
    "create_console",
    "format_bytes",
    "inventory_to_dict",
    "owned_capacity_bytes",
    "render_all",
    "render_compact",
    "render_simple",
]
