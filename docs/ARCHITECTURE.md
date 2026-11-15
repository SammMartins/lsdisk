# Architecture

lsdisk is a read-only Linux storage inventory application. Its architecture
collects host facts, normalizes them into models, derives conservative
relationships and capacity views, serializes stable JSON, and renders
terminal presentations without allowing UI code to query the operating
system directly.

## Design goals

- **Cross-distribution:** use standard Linux interfaces first and treat
  external utilities as optional integrations.
- **Read-only inspection:** never modify disks, filesystems, mounts, LVM, or
  RAID state.
- **Data integrity:** distinguish physical capacity, partition geometry,
  filesystem capacity, active mounts, and persistent configuration.
- **Graceful degradation:** isolate unavailable, malformed, ambiguous, or
  inaccessible data.
- **Testability:** keep collection, analysis, serialization, and rendering
  independently testable with fixtures and mocks.

## Execution flow

`lsdisk.main.main()` builds the argparse parser and handles `--help` and
`--version` before collection. Normal execution calls
`inventory.collect_storage_inventory()`, then selects one output path:

1. `--json` calls `serialization.inventory_to_dict()` and prints JSON.
2. `--classic` calls `ui.terminal.render_classic()`.
3. `--table-mode` calls `render_simple()` or `render_all()` depending on
   `--all`.
4. Otherwise `render_compact()` renders the default or expanded compact view.

Collection errors of type `OSError`, `RuntimeError`, or `ValueError` are
reported as `lsdisk: error: ...` and return status 1. Individual collectors
normally return empty or incomplete results for unavailable interfaces so one
device or optional utility does not abort the whole inventory.

## Collection and inventory

### `collectors/block_devices.py`

`collect_block_devices()` walks `/sys/class/block`, reads device size in
512-byte sectors, identifies disks, partitions, and optical devices, and
builds the parent/child hierarchy. It also reads model, rotational status,
transport hints, and whether a disk appears physical or virtual. Physical
classification requires a non-virtual disk with a device link; it is not
inferred from a device-name prefix.

### `collectors/filesystems.py`

`collect_filesystems()` parses `/proc/self/mountinfo` and uses
`os.statvfs()` for each still-accessible mountpoint. It records source,
filesystem type, mountpoint, device ID, filesystem root, total/free/available
bytes, and derives used bytes. A mount that disappears or has inconsistent
statistics is skipped.

### `collectors/filesystem_metadata.py`

`collect_lsblk_metadata()` reads `lsblk --json --output PATH,FSTYPE,LABEL,UUID`
when available. `probe_filesystem_outcome()` invokes
`blkid --probe --output export DEVICE` without mounting the device. Probe
states are `recognized`, `no_signature`, `unavailable`, and `error`.
Recognized probes may provide filesystem type, label, and UUID; inconclusive
states never become fabricated metadata.

### `collectors/partition_metadata.py`

`collect_partition_metadata()` reads `lsblk --json --bytes` for path, type,
size, start, logical/physical sector sizes, partition-table type, label,
type identifier, and flags. Geometry is attached to existing devices by
`apply_partition_metadata()`. Invalid or incomplete boundaries are retained
as `None`.

### `collectors/fstab.py`

`collect_fstab_entries()` parses valid rows from `/etc/fstab`, including
escaped fields, options, dump, and pass values. It preserves UUID, LABEL,
unresolved, and non-block sources as text. It never resolves, mounts, or
equates an fstab row with an active mount.

### Storage relationships

`collectors/storage_relationships.py` uses verified parent names and sysfs
`slaves` directories. A logical device backed by a lower device carrying a
`crypto_LUKS` signature is classified as `encrypted_mapping`; other verified
edges are `backed_by`. Ambiguous devices and cycles are omitted.

`collectors/lvm.py` optionally reads machine-readable, read-only `pvs`,
`vgs`, and `lvs` reports. It emits verified PV-to-device, VG-to-PV, and
LV-to-VG relationships, skipping missing, duplicate, malformed, or
ambiguous records.

`collectors/mdraid.py` discovers active MD arrays from `/sys/class/block`
slave directories, uses `/proc/mdstat` as supporting active-array metadata,
and optionally invokes `mdadm --detail --export` when sysfs resolution is
incomplete. It emits `raid_member` relationships only when every expected
member is resolved and validated; incomplete, duplicate, or malformed member
metadata causes that array to be omitted without affecting other arrays.
lsdisk never assembles, activates, stops, creates, repairs, or manages arrays.

`inventory.py` combines these collectors, associates mounted filesystem
sources with devices through canonical paths, applies filesystem metadata,
groups filesystem records, and returns `StorageInventory` containing devices,
filesystems, groups, relationships, fstab entries, and unallocated regions.

## Models and analysis

`models.py` defines `BlockDevice`, `FilesystemUsage`, `PartitionMetadata`,
`FstabEntry`, `FilesystemProbe`, `StorageDeviceReference`,
`StorageRelationship`, and `UnallocatedRegion`. Device kinds are
`physical`, `partition`, `logical`, and `unknown`; relationship types include
`backed_by`, `encrypted_mapping`, `lvm_physical_volume`,
`lvm_logical_volume`, `raid_member`, and `unknown`.

`analyzers/filesystems.py` classifies mounted filesystems as
`persistent`, `network`, `application_image`, `temporary`, `virtual`, or
`unknown`, and groups records by device ID plus filesystem type when
available, otherwise source plus filesystem type. Grouping prevents repeated
mount views such as Btrfs subvolumes from multiplying capacity.

`analyzers/capacity.py` formats binary byte units and identifies physical
disks as physical-capacity owners. Partitions and logical layers remain in
detailed inventory but are not independently added to physical totals.

### Partition geometry and unallocated regions

`analyzers/partitions.py` accepts a disk only when it has a positive size,
logical sector size, children, and complete child geometry. `lsblk` start
values and derived end values use inclusive 512-byte sectors, even when the
device logical sector size is 4096 bytes. Conversion is:

```text
start_bytes = start_sector * 512
end_bytes   = (end_sector + 1) * 512 - 1
size_bytes  = end_bytes - start_bytes + 1
```

The disk size and every partition boundary must be divisible by 512 and
aligned to the reported logical sector size. A partition must satisfy
`0 <= start <= end < disk_sectors`. Sorted partitions must not overlap.
Invalid, reversed, duplicate, overlapping, out-of-capacity, or misaligned
geometry invalidates gap analysis for that disk. The invalid disk does not
suppress valid regions found on other disks.

For valid geometry, gaps before, between, and after partitions are emitted
as byte-valued `UnallocatedRegion` records. These are verified address
gaps, not free filesystem capacity and not advice that a region is safe to
partition.

## Serialization

`serialization.py` produces schema version 1. Both modes always include
`schema_version`, `mode`, `devices`, `filesystems`, `mounts`, and
`relationships`.

Simple JSON selects physical disk roots, recursively includes their children,
groups only persistent and network filesystems, leaves `mounts` empty, and
omits partition metadata, fstab, and unallocated regions. Expanded JSON
selects all root devices, includes all filesystem groups and mount records,
and adds partition metadata, `fstab`, and `unallocated_regions`. Device and
mount field contracts are documented in the README.

Relationship references contain `identifier`, `kind`, `canonical_path`, and
`filesystem_uuid`. The serializer deduplicates aliases by canonical identity
and sorts relationships and lower references for deterministic output.

## Terminal rendering

`ui/terminal.py` is a Rich presentation layer. `render_compact()` shows the
summary, physical or all-device tree, and optional expanded filesystem and
topology panels. `render_simple()` and `render_all()` use tables. Their
width allocator removes optional columns first, then gives retained columns
fixed widths and uses ellipsis overflow. The full compact/table targets are
100 columns for normal layouts and 120 columns for expanded layouts; the
actual console width is authoritative.

`render_classic()` displays mounted filesystem records with the stable
seven-column schema `Filesystem`, `Type`, `Size`, `Used`, `Avail`, `Use%`,
and `Mounted on`. It retains all headers at narrow widths and reduces cell
widths. A general width warning is emitted only when non-mountpoint
information is degraded; mountpoint truncation alone does not trigger it.
Terminal reduction affects presentation only, never inventory or JSON.

`ui/styles.py` centralizes the application `PALETTE` and utilization
thresholds: green below 70%, yellow from 70% to below 90%, and red at 90%
or higher. `--color never` disables styling without changing values;
`--color always` forces terminal styling, and `auto` delegates to Rich.

## Operating-system interfaces and dependencies

| Interface or utility | Responsibility |
|---|---|
| `/sys/class/block` | Block devices, hierarchy, topology, and MD slaves |
| `/proc/self/mountinfo` | Active mountpoints, sources, filesystem roots, and IDs |
| `/etc/fstab` | Persistent mount configuration, parsed without mounting |
| `os.statvfs()` | Capacity for accessible active mountpoints |
| `lsblk` | Filesystem metadata and partition geometry |
| `blkid` | Read-only signatures on devices, including unmounted devices |
| `pvs`, `vgs`, `lvs` | Optional read-only LVM reports |
| `/proc/mdstat` and `mdadm` | Optional/supporting MD RAID metadata |
| Python 3.11+ and Rich 13+ | Runtime and terminal rendering |

No root privilege is required by default. Permissions, device visibility,
utility availability, and kernel/storage configuration determine which facts
can be verified. lsdisk does not use a distribution-specific package manager
or require `findmnt`, `udev`, or a particular desktop environment.
