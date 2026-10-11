"""Classification and grouping of mounted filesystems."""

from dataclasses import dataclass, field

from lsdisk.models import FilesystemUsage


VIRTUAL_FILESYSTEMS = {
    "autofs",
    "bpf",
    "cgroup",
    "cgroup2",
    "configfs",
    "debugfs",
    "devpts",
    "devtmpfs",
    "efivarfs",
    "fusectl",
    "hugetlbfs",
    "mqueue",
    "proc",
    "pstore",
    "securityfs",
    "sysfs",
    "tmpfs",
    "tracefs",
}

NETWORK_FILESYSTEMS = {
    "9p",
    "ceph",
    "cifs",
    "glusterfs",
    "nfs",
    "nfs4",
    "smb3",
    "sshfs",
}

PERSISTENT_FILESYSTEMS = {
    "btrfs",
    "exfat",
    "ext2",
    "ext3",
    "ext4",
    "f2fs",
    "jfs",
    "ntfs",
    "ntfs3",
    "reiserfs",
    "udf",
    "vfat",
    "xfs",
    "zfs",
}


@dataclass
class FilesystemGroup:
    """Represent one filesystem with its associated mountpoints."""

    representative: FilesystemUsage
    mountpoints: list[str] = field(default_factory=list)

    @property
    def total_bytes(self) -> int:
        return self.representative.total_bytes

    @property
    def used_bytes(self) -> int:
        return self.representative.used_bytes

    @property
    def available_bytes(self) -> int:
        return self.representative.available_bytes


def classify_filesystem(filesystem: FilesystemUsage) -> str:
    """Classify a filesystem without hiding unrecognized types."""
    filesystem_type = filesystem.filesystem_type.lower()

    if filesystem_type in VIRTUAL_FILESYSTEMS:
        return "virtual"

    if filesystem_type in NETWORK_FILESYSTEMS:
        return "network"

    if filesystem_type in PERSISTENT_FILESYSTEMS:
        return "persistent"

    return "unknown"


def group_filesystems(
    filesystems: list[FilesystemUsage],
) -> list[FilesystemGroup]:
    """Group mounts that share the same filesystem identity."""
    groups: dict[tuple[str, str, str], FilesystemGroup] = {}

    for filesystem in filesystems:
        identity = (
            filesystem.device_id or filesystem.source,
            filesystem.filesystem_type,
            filesystem.source,
        )

        group = groups.get(identity)

        if group is None:
            group = FilesystemGroup(representative=filesystem)
            groups[identity] = group

        if filesystem.mountpoint not in group.mountpoints:
            group.mountpoints.append(filesystem.mountpoint)

    return list(groups.values())
