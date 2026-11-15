# lsdisk — Linux Storage Explorer

<div align="center">
  <img src="https://raw.githubusercontent.com/SammMartins/lsdisk/main/img/lsdisk.png" alt="lsdisk — Linux Storage Explorer" width="760">
  <p><strong>Cross-distro Linux Storage Explorer</strong></p>
  <p><strong>Understand Your Disks at a Glance.</strong></p>
</div>

<div align="center">
  <p>
    <a href="https://github.com/SammMartins/lsdisk/releases/latest"><img src="https://img.shields.io/github/v/release/SammMartins/lsdisk?color=blue" alt="Latest Release"></a>
    <a href="https://pypi.org/project/lsdisk/"><img src="https://img.shields.io/pypi/v/lsdisk?color=blue" alt="PyPI Version"></a>
    <a href="https://github.com/SammMartins/lsdisk/blob/main/LICENSE"><img src="https://img.shields.io/github/license/SammMartins/lsdisk?color=green" alt="License"></a>
    <a href="https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white"><img src="https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white" alt="Python"></a>
    <a href="https://www.kernel.org/"><img src="https://img.shields.io/badge/platform-linux-lightgrey?logo=linux&logoColor=white" alt="Platform"></a>
  </p>
</div>

lsdisk is a read-only Linux command-line tool for understanding disks,
partitions, storage relationships, mounted filesystems, and persistent
mount configuration. It is designed for multiple Linux distributions and
environments without assuming a particular distribution or package manager.

## Features

- Hierarchical physical disks and partitions, including size, model,
  transport, rotational status, and physical/logical classification when
  available.
- Mounted filesystem capacity from `mountinfo` and `statvfs()`, including
  total, used, free, user-available, mountpoint, source, filesystem root,
  and filesystem identity.
- Read-only filesystem signature probing for unmounted block devices,
  including type, label, UUID, and explicit probe outcomes.
- Filesystem grouping that avoids repeating capacity for repeated views such
  as Btrfs subvolume mounts.
- Filesystem categories: `persistent`, `network`, `application_image`,
  `temporary`, `virtual`, and `unknown`.
- Verified device relationships for kernel topology, encrypted mappings,
  LVM PV/VG/LV layers, and active Linux MD RAID members when metadata is
  available and unambiguous.
- Read-only partition metadata: partition-table type, logical and physical
  sector sizes, inclusive start/end sectors, partition name, type, and flags.
- Conservative unallocated disk regions, reported only for complete,
  aligned, non-overlapping geometry.
- Persistent `/etc/fstab` records kept separate from currently mounted
  filesystems.
- Compact, expanded, table, classic, and machine-readable JSON output.
- Adaptive terminal layouts, application-defined utilization colors, and
  explicit warnings when constrained width removes optional columns or
  abbreviates meaningful values.

lsdisk never formats, partitions, mounts, activates, repairs, or otherwise
modifies storage. Missing permissions, unavailable utilities, malformed
metadata, and unsupported layouts are represented as unavailable or unknown
where possible rather than fabricated as zero or empty values.

## Requirements and compatibility

- Linux with `/sys` and `/proc/self/mountinfo`.
- Python 3.11 or newer.
- The Python dependency `rich>=13.0`.

`lsblk` and `blkid` are used when available for partition and filesystem
metadata. `pvs`, `vgs`, and `lvs` are optional read-only LVM integrations.
`mdadm` is an optional fallback for MD RAID member metadata. Missing tools or
inaccessible interfaces do not normally prevent the rest of the inventory
from being displayed. The automated tests use fixtures and mocks; coverage
of real hardware, LVM, RAID, and every distribution remains environment
dependent.

## Installation

### PyPI

```bash
python3 -m pip install lsdisk
lsdisk --version
```

`pipx install lsdisk` is also suitable for an isolated command-line
installation.

Some Linux distributions mark the system Python environment as externally
managed. Prefer `pipx install lsdisk` for an isolated command-line
installation, or use a virtual environment for development or manual
installation; do not bypass these protections with
`--break-system-packages`.

### Per-user shell installer

The installer requires `curl`, `tar`, Python 3.11+, and Python virtual
environment support. It installs the explicitly pinned `0.1.3` release by
default. Set `LSDISK_VERSION` to another exact published version when
installing that release:

```bash
curl -fsSL https://raw.githubusercontent.com/SammMartins/lsdisk/v0.1.3/install.sh \
  | LSDISK_VERSION=0.1.3 bash
```

This uses HTTPS and pins the bootstrap URL to the `v0.1.3` tag rather than a
moving branch, but Git tags are not inherently immutable and the bootstrap
script itself is not independently signed or checksummed here. The installer
retrieves the matching source distribution from PyPI, obtains its SHA-256
digest from PyPI's metadata, and verifies the downloaded artifact before
installation. That artifact check is separate from, and does not
cryptographically verify, the bootstrap script. The installer keeps the
previous installation and launcher as backups while replacing them and
restores both if replacement fails. This is a recovery guarantee, not a
fully atomic update across the separate application and launcher paths. It
installs application data under
`${XDG_DATA_HOME:-~/.local/share}/lsdisk` and a launcher under
`${XDG_BIN_HOME:-~/.local/bin}`. Add the latter to `PATH` if the installer
reports that it is not already there. Run it as a regular user.

The production source distribution contains the runtime package and required
build metadata, but excludes tests, generated egg-info, caches, virtual
environments, and local build artifacts.

### Debian package

Release assets include an architecture-independent `.deb` built by
`packaging/deb/build-deb.sh`. It declares dependencies on Python 3.11+ and
the distribution's `python3-rich` package:

```bash
sudo apt install ./lsdisk_*.deb
lsdisk --version
```

This is a downloaded package, not an APT repository. Package installation
commands are shown for Debian-family systems; PyPI or the shell installer
are distribution-neutral alternatives.

### From a checkout

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/lsdisk --help
```

## Usage

```bash
lsdisk
lsdisk --simple
lsdisk --all
lsdisk --table-mode
lsdisk --all --table-mode
lsdisk --classic
lsdisk --json
lsdisk --all --json
```

The default and `--simple` modes render the compact view of physical disks.
`--all` includes all discovered root devices and additional mount, topology,
partition, and persistent-configuration information in compact/table/JSON
contexts. `--table-mode` selects tabular output. `--classic` renders a
df-like overview of mounted filesystems and is mutually exclusive with JSON
and table mode. `--help` and `--version` exit without collecting inventory.

### Command-line options

| Option | Behavior | Example |
|---|---|---|
| `--simple` | Select the simplified compact view; this is the default and is mutually exclusive with `--all`. | `lsdisk --simple` |
| `-a`, `--all` | Include all devices and expanded inventory data. | `lsdisk --all` |
| `--json` | Emit indented machine-readable JSON instead of terminal UI. | `lsdisk --json` |
| `-T`, `--table-mode` | Use tabular terminal output. With `--all`, include all mounted records and expanded metadata. | `lsdisk -T` |
| `-c`, `--classic` | Show the mounted-filesystem capacity overview. | `lsdisk -c` |
| `--color {auto,always,never}` | Select Rich color behavior; default is `auto`. | `lsdisk --color never` |
| `--no-color` | Alias for `--color never`. | `lsdisk --no-color` |
| `--version` | Print `lsdisk 0.1.3` and exit. | `lsdisk --version` |
| `-h`, `--help` | Print the installed command's help and exit. | `lsdisk --help` |

The mode groups are mutually exclusive as enforced by the parser: `--simple`
and `--all` cannot be combined, and JSON, table, and classic output cannot be
combined. Invalid combinations return argparse status 2.

### JSON contracts

Every JSON response contains:

```json
{
  "schema_version": 1,
  "mode": "simple",
  "devices": [],
  "filesystems": [],
  "mounts": [],
  "relationships": []
}
```

`--json` uses `"mode": "simple"`. `devices` contains physical disk roots and
their recursively serialized children; each device always includes `name`,
`path`, `type`, `size_bytes`, `size_human`, `physical`, `parent_name`,
`model`, `transport`, `rotational`, `filesystem_type`,
`filesystem_label`, `filesystem_uuid`, `filesystem_probe_state`,
`mountpoints`, and `children`. `filesystems` contains only grouped
`persistent` and `network` records, with `source`, `filesystem_type`,
`category`, `device_id`, `total_bytes`, `used_bytes`, `available_bytes`,
`used_percent`, and `mountpoints`. `mounts` is an empty array. Partition
metadata, `/etc/fstab`, and unallocated regions are omitted.

`--all --json` uses `"mode": "all"`. It includes all root devices, every
filesystem group, and a `mounts` entry for every collected mounted
filesystem. A mount record contains `mountpoint`, `source`,
`filesystem_type`, `category`, `device_id`, `filesystem_root`,
`total_bytes`, `free_bytes`, `available_bytes`, `used_bytes`, and
`used_percent`. Each device additionally contains `partition_metadata`,
whose value is an object with `partition_table`, `logical_sector_size`,
`physical_sector_size`, `start_sector`, `end_sector`, `partition_name`,
`partition_type`, and `flags`, or `null`.

Expanded JSON also adds `fstab`, with `source`, `mountpoint`,
`filesystem_type`, `options`, `dump`, and `pass_number`, and
`unallocated_regions`, with `disk_path`, `start_bytes`, `end_bytes`, and
`size_bytes`. An fstab record is configuration only; it is not evidence that
the source is mounted.

Both modes include `relationships`. Each relationship has `relationship_type`,
an `upper` reference, and a `lower` array. A reference has `identifier`,
`kind`, `canonical_path`, and `filesystem_uuid`; unavailable values are
`null`. Relationships are included only when collectors verify them, and
serialized references are deduplicated and sorted by canonical identity.

Partition `start_sector` and `end_sector` are inclusive numbers in 512-byte
sectors, independent of the reported logical sector size. Region offsets and
sizes are bytes. JSON is independent of terminal width and color settings.

In expanded compact and table views, partition geometry and conservative
unallocated regions are shown when complete metadata is available. Persistent
`/etc/fstab` entries are shown in a separate configuration section and are
clearly labeled as not proving that a mount is currently active. MD RAID
relationships are shown only when every expected member is resolved through
sysfs or the validated `mdadm` fallback; incomplete or ambiguous arrays are
omitted.

### Terminal behavior

The compact and table renderers use the console's reported width. At narrow
widths they first remove optional metadata columns, then abbreviate long
secondary values with `...`; device identity, type, capacity, filesystem,
mountpoint, and hierarchy remain represented where the layout permits. The
general width warning is printed only when the presentation is reduced.

Classic mode always uses the seven headers `Filesystem`, `Type`, `Size`,
`Used`, `Avail`, `Use%`, and `Mounted on`. It reduces cell widths and
abbreviates values when needed, but keeps the schema and filesystem records.
Truncating only a mountpoint value does not trigger the general width warning.
`--color never` and `--no-color` remove styling without changing data.

## Uninstallation

For a shell installation, run the matching uninstaller as the same regular
user:

```bash
curl -fsSL https://raw.githubusercontent.com/SammMartins/lsdisk/main/uninstall.sh \
  -o /tmp/lsdisk-uninstall.sh
bash /tmp/lsdisk-uninstall.sh
```

For PyPI or pipx installations:

```bash
python3 -m pip uninstall lsdisk
pipx uninstall lsdisk
```

For a Debian package:

```bash
sudo apt remove lsdisk
```

## Development and documentation

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for setup, tests, compilation,
packaging, and contribution workflow. See
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for collection, analysis,
serialization, and rendering responsibilities. Release notes are in
[CHANGELOG.md](CHANGELOG.md).

## Safety and license

lsdisk is an inspection tool. It does not modify disks, partitions,
filesystems, mounts, LVM state, or RAID state. Elevated privileges are not
required by the application by default, although permissions and available
system metadata affect what can be reported.

Contributions should preserve read-only behavior, explicit unknown states,
cross-distribution portability, and focused tests. The project is distributed
under the [MIT License](LICENSE).
