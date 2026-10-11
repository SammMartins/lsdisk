"""Core data models for Storix."""

from dataclasses import dataclass, field


@dataclass
class BlockDevice:
    """Represents a block device or partition discovered on Linux."""

    name: str
    path: str
    device_type: str
    size_bytes: int
    physical: bool | None = None
    parent_name: str | None = None
    model: str | None = None
    transport: str | None = None
    rotational: bool | None = None
    filesystem_type: str | None = None
    filesystem_label: str | None = None
    filesystem_uuid: str | None = None
    mountpoints: list[str] = field(default_factory=list)
    children: list["BlockDevice"] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.size_bytes < 0:
            raise ValueError("Device size cannot be negative.")

    @property
    def is_physical_disk(self) -> bool:
        """Return whether the collector identified this as a physical disk."""
        return self.device_type == "disk" and self.physical is True

    @property
    def is_partition(self) -> bool:
        """Return whether this represents a partition."""
        return self.device_type == "part"


@dataclass(frozen=True)
class FilesystemUsage:
    """Represents capacity statistics for a mounted filesystem."""

    mountpoint: str
    source: str
    filesystem_type: str
    total_bytes: int
    free_bytes: int
    available_bytes: int
    device_id: str | None = None
    filesystem_root: str = "/"

    def __post_init__(self) -> None:
        if min(
            self.total_bytes,
            self.free_bytes,
            self.available_bytes,
        ) < 0:
            raise ValueError("Filesystem capacity values cannot be negative.")

        if self.free_bytes > self.total_bytes:
            raise ValueError("Free space cannot exceed total capacity.")

        if self.available_bytes > self.free_bytes:
            raise ValueError("Available space cannot exceed free space.")

    @property
    def used_bytes(self) -> int:
        """Return used filesystem space in bytes."""
        return self.total_bytes - self.free_bytes

    @property
    def used_percent(self) -> float:
        """Return the percentage of filesystem space used."""
        if self.total_bytes == 0:
            return 0.0

        return self.used_bytes / self.total_bytes * 100
