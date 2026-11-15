"""Core data models for lsdisk."""

from dataclasses import dataclass, field
from enum import StrEnum


# lsblk reports partition start and end offsets in 512-byte sectors,
# regardless of the device's logical sector size.
PARTITION_SECTOR_SIZE_BYTES = 512


class ProbeState(StrEnum):
    """Outcome of a read-only filesystem signature probe."""

    RECOGNIZED = "recognized"
    NO_SIGNATURE = "no_signature"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


@dataclass(frozen=True)
class PartitionMetadata:
    """Partition-table and geometry facts reported by Linux interfaces.

    ``start_sector`` and ``end_sector`` are inclusive 512-byte sector
    numbers, matching the unit used by lsblk's START column. Both are
    independent of ``logical_sector_size``, which is measured in bytes.
    """

    partition_table: str | None = None
    logical_sector_size: int | None = None
    physical_sector_size: int | None = None
    start_sector: int | None = None
    end_sector: int | None = None
    partition_name: str | None = None
    partition_type: str | None = None
    flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class UnallocatedRegion:
    """A verified gap in a disk partition table, measured in bytes."""

    disk_path: str
    start_bytes: int
    end_bytes: int
    size_bytes: int

    def __post_init__(self) -> None:
        if min(self.start_bytes, self.end_bytes, self.size_bytes) < 0:
            raise ValueError("Unallocated regions cannot have negative offsets.")
        if self.end_bytes < self.start_bytes:
            raise ValueError("Unallocated region end must not precede its start.")
        if self.size_bytes != self.end_bytes - self.start_bytes + 1:
            raise ValueError("Unallocated region size does not match its bounds.")


@dataclass(frozen=True)
class FstabEntry:
    """One persistent mount configuration entry, without mounting it."""

    source: str
    mountpoint: str
    filesystem_type: str
    options: tuple[str, ...] = ()
    dump: str | None = None
    pass_number: str | None = None


class StorageDeviceKind(StrEnum):
    """Coarse storage-layer kinds independent of Linux device names."""

    PHYSICAL = "physical"
    PARTITION = "partition"
    LOGICAL = "logical"
    UNKNOWN = "unknown"


class StorageRelationshipType(StrEnum):
    """Known and intentionally open-ended storage relationship types."""

    BACKED_BY = "backed_by"
    ENCRYPTED_MAPPING = "encrypted_mapping"
    LVM_PHYSICAL_VOLUME = "lvm_physical_volume"
    LVM_LOGICAL_VOLUME = "lvm_logical_volume"
    RAID_MEMBER = "raid_member"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class FilesystemProbe:
    """The result of probing a device, including inconclusive outcomes."""

    state: ProbeState
    metadata: "FilesystemMetadata | None" = None

    def __post_init__(self) -> None:
        if self.state is ProbeState.RECOGNIZED and self.metadata is None:
            raise ValueError("Recognized probes require filesystem metadata.")

        if self.state is not ProbeState.RECOGNIZED and self.metadata is not None:
            raise ValueError("Only recognized probes may contain metadata.")


@dataclass(frozen=True)
class StorageDeviceReference:
    """Stable, best-effort identity for one storage layer."""

    identifier: str
    kind: StorageDeviceKind = StorageDeviceKind.UNKNOWN
    canonical_path: str | None = None
    filesystem_uuid: str | None = None

    def __post_init__(self) -> None:
        if not self.identifier.strip():
            raise ValueError("Storage device identifiers cannot be empty.")


def storage_reference_identity(reference: StorageDeviceReference) -> str:
    """Return the strongest available identity for a storage reference."""
    return reference.canonical_path or reference.identifier


@dataclass(frozen=True)
class StorageRelationship:
    """Describe one upper storage layer backed by one or more lower layers."""

    relationship_type: str
    upper: StorageDeviceReference
    lower: tuple[StorageDeviceReference, ...]

    def __post_init__(self) -> None:
        if not self.relationship_type.strip():
            raise ValueError("Storage relationship types cannot be empty.")
        if not self.lower:
            raise ValueError("Storage relationships require a lower layer.")
        lower_ids = {device.identifier for device in self.lower}
        if self.upper.identifier in lower_ids:
            raise ValueError("Storage relationships cannot reference themselves.")


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
    filesystem_probe_state: ProbeState | None = None
    partition_metadata: PartitionMetadata | None = None
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

    @property
    def storage_kind(self) -> StorageDeviceKind:
        """Return the model kind without inferring from a device-name prefix."""
        if self.is_partition:
            return StorageDeviceKind.PARTITION
        if self.physical is True:
            return StorageDeviceKind.PHYSICAL
        if self.physical is False:
            return StorageDeviceKind.LOGICAL
        return StorageDeviceKind.UNKNOWN


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
