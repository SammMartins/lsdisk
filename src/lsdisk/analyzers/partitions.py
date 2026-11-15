"""Derive conservative unallocated regions from complete partition geometry."""

from lsdisk.models import (
    PARTITION_SECTOR_SIZE_BYTES,
    BlockDevice,
    UnallocatedRegion,
)


def _walk(devices: list[BlockDevice]):
    for device in devices:
        yield device
        yield from _walk(device.children)


def _validated_geometry(
    disk: BlockDevice,
) -> tuple[list[tuple[int, int]], int] | None:
    """Return validated partition bounds and disk capacity, or None.

    Bounds use inclusive 512-byte sectors, the unit of lsblk's START column.
    Start offsets, end boundaries (and therefore the partition sizes implied
    by those bounds), and disk capacity must all be aligned to the reported
    logical sector size in bytes.
    """
    disk_meta = disk.partition_metadata
    if disk_meta is None or not disk_meta.logical_sector_size:
        return None
    logical = disk_meta.logical_sector_size
    if logical <= 0 or disk.size_bytes <= 0:
        return None
    if disk.size_bytes % PARTITION_SECTOR_SIZE_BYTES != 0:
        return None
    if disk.size_bytes % logical != 0:
        return None
    if not disk.children:
        return None

    disk_sectors = disk.size_bytes // PARTITION_SECTOR_SIZE_BYTES
    partitions: list[tuple[int, int]] = []
    for child in disk.children:
        meta = child.partition_metadata
        if meta is None:
            return None
        start = meta.start_sector
        end = meta.end_sector
        if (
            not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(end, int)
            or isinstance(end, bool)
        ):
            return None
        if start < 0 or end < start or end >= disk_sectors:
            return None
        start_bytes = start * PARTITION_SECTOR_SIZE_BYTES
        end_bytes = (end + 1) * PARTITION_SECTOR_SIZE_BYTES
        if start_bytes % logical != 0 or end_bytes % logical != 0:
            return None
        partitions.append((start, end))

    partitions.sort()
    previous = 0
    for start, end in partitions:
        if start < previous:
            return None
        previous = end + 1

    return partitions, disk_sectors


def find_unallocated_regions(
    devices: list[BlockDevice],
) -> list[UnallocatedRegion]:
    """Return gaps only when disk and every partition boundary is reliable."""
    regions: list[UnallocatedRegion] = []
    for disk in devices:
        if not disk.is_physical_disk:
            continue
        geometry = _validated_geometry(disk)
        if geometry is None:
            continue
        partitions, disk_sectors = geometry
        previous = 0
        for start, end in partitions:
            if start > previous:
                start_bytes = previous * PARTITION_SECTOR_SIZE_BYTES
                end_bytes = start * PARTITION_SECTOR_SIZE_BYTES - 1
                regions.append(UnallocatedRegion(
                    disk.path, start_bytes, end_bytes, end_bytes - start_bytes + 1
                ))
            previous = end + 1
        if previous < disk_sectors:
            start_bytes = previous * PARTITION_SECTOR_SIZE_BYTES
            end_bytes = disk_sectors * PARTITION_SECTOR_SIZE_BYTES - 1
            regions.append(UnallocatedRegion(
                disk.path, start_bytes, end_bytes, end_bytes - start_bytes + 1
            ))
    return regions
