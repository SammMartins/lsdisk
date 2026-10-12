<div align="center">

  <img src="img/lsdisk.png" alt="lsdisk — Linux Storage Explorer" width="760">

  <p><strong>Cross-distro Linux Storage Explorer</strong></p>
  <p>Understand your disks, partitions, and filesystems — clearly, safely, and from the terminal.</p>

</div>

---

## About lsdisk

**lsdisk** is a Linux storage inspection tool designed to make information about HDDs, SSDs, partitions, and filesystems easier to understand.

It brings storage topology and filesystem capacity information together in a structured terminal interface. lsdisk is read-only: it inspects storage and does not format, partition, mount, or modify filesystems.

## Features

- **Physical storage inventory** — show detected disks and their child partitions in a hierarchical view.
- **Device details** — display device names, capacity, model, physical/virtual classification, and HDD or SSD/Flash indicators when the system provides enough information.
- **Filesystem capacity** — report total, used, free, and user-available capacity for accessible mounted filesystems.
- **Mountpoint visibility** — associate filesystem information with mountpoints where the relationship can be established.
- **Filesystem grouping** — group related filesystem records to avoid repeating capacity for multiple mountpoints, including supported Btrfs subvolume cases.
- **Utilization bars** — display a compact visual usage bar and percentage in the terminal. The filled bar and percentage use utilization colors: green below 70%, yellow from 70% to below 90%, and red at 90% or above.
- **Multiple output modes** — provide a compact default view, expanded output, table output, and JSON output.
- **Graceful handling of missing data** — distinguish unavailable information from a confirmed zero value.

Capacity values depend on the information available from the running Linux system. Physical disk capacity and mounted filesystem capacity describe different layers and should not be treated as interchangeable.

## Design principles

| Principle | What it means |
|---|---|
| **Read-only inspection** | Do not modify disks, partitions, or filesystems. |
| **Modular architecture** | Keep data collection, analysis, serialization, and presentation separated. |
| **Portability** | Avoid unnecessary dependencies on a specific Linux distribution. |
| **Transparency** | Distinguish confirmed values from estimates or unavailable data. |
| **Testability** | Validate calculations and behavior with automated tests. |

## Technology

- **Python** — application logic.
- **Rich** — terminal presentation and colored utilization bars.
- **Python standard library** — core APIs and supporting functionality.
- **Linux interfaces**, including `/sys` and `/proc`, where appropriate.
- **`os.statvfs()`** — mounted filesystem capacity statistics.
- **`unittest`** — automated testing.

## Requirements

- Linux
- Python 3.11 or newer
- `curl` and `tar` for the shell installer

The installer creates an isolated Python virtual environment and installs the Python dependencies. Some storage information may depend on available system interfaces, permissions, and the storage configuration.

## Installation

The installation script downloads lsdisk, creates an isolated Python virtual environment, and installs the `lsdisk` command for the current user:

```bash
curl -sSL https://raw.githubusercontent.com/SammMartins/lsdisk/main/install.sh | bash
```

The installer does not require `sudo` and refuses to run as root. By default, it stores application data in `~/.local/share/lsdisk` and the executable in `~/.local/bin`. If `~/.local/bin` is not in your `PATH`, follow the instruction printed by the installer.

Run lsdisk:

```bash
lsdisk
```

Show available options:

```bash
lsdisk --help
```

To install from a different branch, set `LSDISK_BRANCH` before running the installer:

```bash
curl -sSL https://raw.githubusercontent.com/SammMartins/lsdisk/main/install.sh | LSDISK_BRANCH=main bash
```

## Uninstallation

If `uninstall.sh` is available locally, run it as your regular user, without `sudo`:

```bash
bash uninstall.sh
```

The uninstaller removes the per-user launcher and application data directory. It does not delete the local Git repository or project source files.

## Usage

```bash
lsdisk
lsdisk --all
lsdisk --table-mode
lsdisk --json
lsdisk --help
```

- `lsdisk` displays the default compact storage view.
- `lsdisk --all` displays expanded inventory details, including additional devices and mount information.
- `lsdisk --table-mode` selects table output.
- `lsdisk --json` emits machine-readable JSON without terminal UI formatting.
- `lsdisk --help` lists the options supported by the installed version.

Use the output of `lsdisk --help` as the source of truth for the options available in a specific release.

## Development status

**lsdisk is in early development.** Features and interfaces may change as the project evolves. The current implementation focuses on block-device topology and capacity information for mounted filesystems.

### Roadmap

- [ ] Identify filesystem types on unmounted partitions without mounting them.
- [ ] Collect filesystem labels and UUIDs more completely.
- [ ] Improve identification of partitions whose filesystem information is unavailable.
- [ ] Expand validated handling of Btrfs, LVM, RAID, LUKS, and other storage layers.

These items are planned improvements, not guarantees of the current implementation.

## Project documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Development guide](docs/DEVELOPMENT.md)
- [Changelog](CHANGELOG.md)

## Safety scope

lsdisk is intended for **storage inspection only**. Formatting, partitioning, filesystem modification, and automatic mounting are outside the project's scope.

## License

lsdisk is distributed under the [MIT License](LICENSE).

---

<div align="center">
  <sub>lsdisk — making Linux storage easier to explore.</sub>
</div>
