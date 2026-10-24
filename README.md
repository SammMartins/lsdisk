# lsdisk — Linux Storage Explorer

<div align="center">

  <img src="https://raw.githubusercontent.com/SammMartins/lsdisk/main/img/lsdisk.png" alt="lsdisk — Linux Storage Explorer" width="760">

  <p><strong>Cross-distro Linux Storage Explorer</strong></p>
  <p>Understand your disks, partitions, and filesystems — clearly, safely, and from the terminal.</p>

</div>

<div align="center">

  <p>
    <a href="https://github.com/SammMartins/lsdisk/releases/latest"><img src="https://img.shields.io/github/v/release/SammMartins/lsdisk?color=blue" alt="Latest Release"></a>
    <a href="https://pypi.org/project/lsdisk/"><img src="https://img.shields.io/pypi/v/lsdisk?color=blue" alt="PyPI Version"></a>
    <a href="https://copr.fedorainfracloud.org/coprs/sammmartins/lsdisk/"><img src="https://img.shields.io/badge/Fedora-COPR-blue?logo=fedora&logoColor=white" alt="Fedora COPR"></a>
    <a href="https://github.com/SammMartins/lsdisk/blob/main/LICENSE"><img src="https://img.shields.io/github/license/SammMartins/lsdisk?color=green" alt="License"></a>
    <a href="https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white"><img src="https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white" alt="Python"></a>
    <a href="https://www.kernel.org/"><img src="https://img.shields.io/badge/platform-linux-lightgrey?logo=linux&logoColor=white" alt="Platform"></a>
    <a href="https://github.com/SammMartins/lsdisk/stargazers"><img src="https://img.shields.io/github/stars/SammMartins/lsdisk?color=yellow" alt="GitHub Stars"></a>
  </p>

</div>

---

## Table of Contents

- [About lsdisk](#about-lsdisk)
- [Features](#features)
- [Design Principles](#design-principles)
- [Technology](#technology)
- [Requirements](#requirements)
- [Installation](#installation)
  - [Debian and Ubuntu Package](#debian-and-ubuntu-package)
  - [Install Using the Shell Script](#install-using-the-shell-script)
  - [Install from PyPI](#install-from-pypi)
  - [Install Using Fedora COPR](#install-using-fedora-copr)
- [Usage](#usage)
- [Uninstallation](#uninstallation)
- [Roadmap](#roadmap)
- [Project Documentation](#project-documentation)
- [Safety Scope](#safety-scope)
- [License](#license)

---

## About lsdisk

**lsdisk — Linux Storage Explorer** is a cross-distro Linux CLI tool that makes storage information easier to inspect and understand.

It brings disk devices, partitions, storage topology, and filesystem usage into a clear, structured terminal interface, helping users understand their storage at a glance.

- **Cross-distro:** Designed for use across different Linux distributions.
- **Read-only:** Inspects storage without formatting disks, modifying partitions, mounting filesystems, or changing storage configurations.
- **Multiple output modes:** Supports compact, expanded, table, and JSON output for different workflows.
- **Built for clarity:** Presents storage information in a readable terminal interface.

**Understand Your Disks at a Glance.**

![lsdisk Demo](https://raw.githubusercontent.com/SammMartins/lsdisk/main/img/lsdisk_0_1_1.gif)

<p align="center"><sub>lsdisk v0.1.1 — Live terminal demonstration of Linux storage inspection.</sub></p>

## Features

- **Physical storage inventory** — display detected disks and their child partitions in a hierarchical view.
- **Device information** — show device names, capacity, model, physical or virtual classification, and HDD or SSD/Flash indicators when sufficient system information is available.
- **Filesystem metadata discovery** — identify filesystem signatures on unmounted block devices and retrieve labels and UUIDs when available, without mounting them.
- **Filesystem capacity reporting** — display total, used, free, and user-available capacity for accessible mounted filesystems.
- **Mountpoint association** — link filesystem information to mountpoints whenever the relationship can be reliably established.
- **Filesystem grouping** — group related filesystem records to avoid duplicating capacity figures across multiple mountpoints, including supported Btrfs subvolume configurations.
- **Filesystem classification** — categorize filesystems as persistent, network, application-image, temporary, virtual, or unknown while preserving mountpoint visibility.
- **Visual utilization indicators** — display compact usage bars and percentages with color-coded thresholds: green below 70%, yellow from 70% to below 90%, and red at 90% or higher.
- **Multiple output modes** — provide compact default, expanded, table, and JSON output for different inspection and integration needs.
- **Graceful handling of incomplete data** — distinguish unavailable information from confirmed zero values instead of presenting missing data as valid measurements.

Capacity figures depend on the information exposed by the running Linux system. Physical disk capacity and mounted filesystem capacity represent different storage layers and must be interpreted separately.

## Design Principles

| Principle | What it means |
|---|---|
| **Read-only inspection** | Inspect storage without modifying disks, partitions, or filesystems. |
| **Modular architecture** | Separate data collection, analysis, serialization, and presentation into distinct components. |
| **Cross-distribution portability** | Minimize dependencies on distribution-specific tools and conventions. |
| **Data transparency** | Distinguish confirmed values, unavailable information, and estimates where applicable. |
| **Testability** | Validate calculations, data handling, and application behavior through automated tests. |
| **Consistent presentation** | Use a deliberate color palette, clear visual hierarchy, and predictable formatting across output modes. |

## Technology

- **Python** — core application logic and storage data processing.
- **Rich** — terminal rendering, structured layouts, and colored utilization indicators.
- **Python standard library** — filesystem access, system integration, and supporting functionality.
- **Linux system interfaces** — `/sys` and `/proc` for system and device information where appropriate.
- **`os.statvfs()`** — mounted filesystem capacity statistics.
- **`unittest`** — automated testing of application behavior and calculations.


## Requirements

- Linux
- Python 3.11 or newer

Additional requirements depend on the installation method:

- **Debian/Ubuntu package:** Python 3.11+ and the distribution's `python3-rich` package.
- **Shell installer:** `curl`, `tar`, Python 3.11+, and access to the required download sources.
- **PyPI:** Python 3.11+ and a supported Python installation tool.
- **Fedora COPR:** a supported Fedora release and the dependencies specified by the RPM package.

Some storage information may depend on available system interfaces, permissions, and the storage configuration.

## Installation

Choose the installation method that best fits your Linux distribution and environment.

### Debian and Ubuntu Package

The GitHub Release provides an architecture-independent `.deb` package for Debian and Ubuntu systems that meet the package requirements.

The package targets Debian 12 or newer and Ubuntu 24.04 or newer, provided Python 3.11+ and the distribution package `python3-rich` are available.

**Important:** This is direct `.deb` installation, not a signed APT repository. You must download the package from the Releases page before using `apt install ./...`. The package is not available through the default Debian or Ubuntu repositories.

#### Option 1: Manual Download

1. Go to the [lsdisk GitHub Releases](https://github.com/SammMartins/lsdisk/releases) page.
2. Download the `.deb` file from the latest release.
3. Open a terminal in the directory where the file was downloaded and run:

```bash
sudo apt install ./lsdisk_*.deb
```

#### Option 2: Download and install directly via terminal (Latest Version)
Alternatively, you can fetch the latest `.deb` package and install it using a single command:

```bash
curl -s https://api.github.com/repos/SammMartins/lsdisk/releases/latest \
  | grep "browser_download_url.*deb" \
  | cut -d : -f 2,3 \
  | tr -d ' "' \
  | xargs curl -Lo /tmp/lsdisk_latest.deb && sudo apt install /tmp/lsdisk_latest.deb && rm -f /tmp/lsdisk_latest.deb
```

Verify the installation:

```bash
lsdisk --version
lsdisk --help
```

The package installs the `lsdisk` command system-wide. The package manager handles the declared dependencies and tracks the installed files.

### Install Using the Shell Script

The official installation script downloads lsdisk from GitHub, creates an isolated Python virtual environment, and installs the `lsdisk` command for the current user.

```bash
curl -fsSL https://raw.githubusercontent.com/SammMartins/lsdisk/main/install.sh | bash
```

The installer does not require `sudo` and refuses to run as root. By default, application files are stored in `~/.local/share/lsdisk`, and the executable launcher is installed in `~/.local/bin`.

If `~/.local/bin` is not in your `PATH`, follow the instructions printed by the installer or add the directory to your shell configuration.

Verify the installation:

```bash
lsdisk --version
lsdisk --help
lsdisk --all --json
```

This method is suitable for Linux distributions that meet the Python and system requirements, without relying on a distribution-specific package.

### Install from PyPI

You can also install lsdisk through Python's package ecosystem.

Using `pipx`:

```bash
pipx install lsdisk
```

Using `pip` in a Python environment where pip is available:

```bash
python -m pip install lsdisk
```

To upgrade a pipx installation:

```bash
pipx upgrade lsdisk
```

To upgrade a pip installation:

```bash
python -m pip install --upgrade lsdisk
```

If `pip` or `pipx` is not available, install the required tool using your distribution's package manager or use the shell script above.

### Install Using Fedora COPR

Fedora users can install lsdisk through the community-maintained COPR repository.

**COPR repository:** [sammmartins/lsdisk](https://copr.fedorainfracloud.org/coprs/sammmartins/lsdisk/)

Enable the repository:

```bash
sudo dnf copr enable sammmartins/lsdisk
```

Install the package:

```bash
sudo dnf install python3-lsdisk
```

Verify the installation:

```bash
lsdisk --version
lsdisk --help
```

The initial COPR build targets Fedora 44 x86_64. Support for additional Fedora releases and architectures depends on the available build configurations.

## Usage

Run the default compact view:

```bash
lsdisk
```

Available commands:

```bash
lsdisk --all
lsdisk --table-mode
lsdisk --json
lsdisk --help
```

- `lsdisk` displays the default compact storage view.
- `lsdisk --all` displays expanded inventory details, including additional devices and mount information.
- `lsdisk --table-mode` selects table output.
- `lsdisk --json` emits machine-readable JSON without terminal UI formatting.
- `lsdisk --all --json` includes every discovered mount and exposes its
  stable lowercase `category` (`persistent`, `network`,
  `application_image`, `temporary`, `virtual`, or `unknown`).
- `lsdisk --help` lists the options supported by the installed version.

Application-image capacity is retained for inspection, but its usage is not
included in physical-storage summaries; a read-only image reported at 100%
does not mean a physical disk is full.

Use the output of `lsdisk --help` as the source of truth for the options available in a specific release.

## Uninstallation

Use the instructions for the installation method you selected.

### Debian and Ubuntu Package

Remove the installed package:

```bash
sudo apt remove lsdisk
```

To remove the package and its package-manager configuration files, if any:

```bash
sudo apt purge lsdisk
```

The `purge` command does not remove user data outside the package's managed files.

### Shell Script Installation

Download and run the official uninstaller as the same regular user who installed lsdisk. Do not use `sudo`:

```bash
curl -fsSL https://raw.githubusercontent.com/SammMartins/lsdisk/main/uninstall.sh \
  -o /tmp/lsdisk-uninstall.sh
bash /tmp/lsdisk-uninstall.sh
```

The uninstaller removes the per-user launcher (`~/.local/bin/lsdisk`) and application data directory (`~/.local/share/lsdisk`). It does not remove the local Git repository or project source files. If you customized `XDG_BIN_HOME` or `XDG_DATA_HOME` during installation, use the same values when running the uninstaller.

### PyPI or pip Installation

If you installed lsdisk using pip, uninstall it from the same Python environment:

```bash
python -m pip uninstall lsdisk
```

If you installed it with pipx:

```bash
pipx uninstall lsdisk
```

### Fedora COPR Installation

Remove the RPM package:

```bash
sudo dnf remove python3-lsdisk
```

To disable the COPR repository:

```bash
sudo dnf copr disable sammmartins/lsdisk
```

Disabling the repository does not remove the installed package. Remove the package separately if necessary.

## Roadmap

### Storage Discovery and Topology

- [ ] Improve identification of partitions whose filesystem information is unavailable, including partitions without filesystems and devices with incomplete metadata.
- [x] Add deterministic, read-only relationship discovery for LVM PV/VG/LV layers and Linux MD RAID arrays where system metadata verifies them.
- [ ] Validate LVM and Linux MD RAID discovery against real storage configurations and across supported Linux distributions; automated coverage does not replace end-to-end testing on real arrays and volume groups.
- [ ] Identify and display disk connection/interface information (for example, SATA, NVMe, USB, or other available bus information) in the default view, not only in expanded inventory mode.
- [ ] Improve filesystem metadata discovery for supported filesystems, including unmounted filesystems and cases where information is currently unavailable.

### Comprehensive Storage Inventory and Architecture

The architectural foundation is implemented: lsdisk has modular collectors, normalized models, inventory orchestration, analyzers, serialization, and separate terminal presentation. The remaining work is to broaden the inventory and validate more storage configurations.

- [x] Separate data collection, normalized models, analysis, serialization, and terminal presentation into distinct components.
- [x] Correlate devices, partitions, filesystems, mountpoints, and storage layers when relationships can be verified, while preserving unknown relationships.
- [x] Prefer standard Linux interfaces and optional external utilities, handling missing tools and incomplete data gracefully.
- [x] Preserve read-only behavior and distinguish unavailable data from confirmed zero values.
- [ ] Expand `--all` into a more comprehensive, read-only storage inventory for diagnostics, storage analysis, and partition planning.
- [ ] Discover partition-table formats, logical and physical sector sizes, partition start and end offsets, partition names, type identifiers (`PARTTYPE`), and available partition flags.
- [ ] Identify unallocated disk regions, including their start offsets, end offsets, and sizes, without confusing them with free space inside filesystems.
- [ ] Extend filesystem and mount inventory to include persistent mount configuration from `/etc/fstab` where available, alongside existing UUID, label, mountpoint, and capacity information.
- [ ] Preserve a consistent data model across compact, expanded, table, classic, and JSON output modes while allowing each presentation to expose an appropriate level of detail.

### Filesystem Capacity and Health Indicators

- [ ] Add a compact Storage Summary section that lists up to three filesystems with critically high utilization (95% used or more). Show fewer than three entries when fewer filesystems meet the threshold, and show no list when none qualify.
- [ ] Complete advanced storage-layer accounting for Btrfs multi-device filesystems, LVM extents, RAID usable capacity and rebuild state, LUKS layers, and additional Linux configurations.

### Command-Line Modes and Filtering

- [ ] Add a classic filesystem overview mode (`lsdisk -c`) inspired by the information density of tools such as `df`, `lsblk`, and `fdisk`, while retaining lsdisk's own layout and visual style.
- [ ] Add a search/filter option for a specific block device, partition, filesystem type, or mountpoint. Proposed examples: `lsdisk -s sda1`, `lsdisk --search sdb`, and `lsdisk --search btrfs`. Final syntax and matching behavior will be documented after implementation.
- [ ] Include the installed lsdisk version in the title of each terminal view, for example `lsdisk  Linux Storage Explorer v0.1.2`.
- [ ] In `--all` mode, check whether a newer release is available and display a clearly visible yellow update notice when an update is found. The check should fail gracefully when the network is unavailable and must not block local storage inspection.

### Directory Usage Analysis

- [ ] Add an optional directory usage analysis mode (`--du`) to inspect directory sizes and identify which directories consume the most space within a selected filesystem.
- [ ] Display directory paths, total size, and usage relative to the scanned filesystem, with results ordered by disk usage.
- [ ] Support configurable scan depth and an option to select the starting directory.
- [ ] Respect filesystem boundaries by default to avoid crossing into other mounted filesystems.
- [ ] Handle permission errors, symbolic links, inaccessible directories, and files that change during scanning without aborting the entire operation.
- [ ] Provide clear progress feedback and distinguish incomplete results from successful scans.
- [ ] Keep directory scanning separate from the default storage inventory to preserve fast, predictable execution.

#### Examples of Directory Usage Analysis

```bash
# Analyze directories from the root filesystem
lsdisk --du /

# Analyze the user's home directory
lsdisk --du /home/user

# Limit the scan to two directory levels
lsdisk --du / --depth 2
```

### User Interface and User Experience

- [ ] **Table mode redesign:** improve spacing, column sizing, alignment, readability, and hierarchy. This is a dedicated UI/UX subcategory, informed by the information density of utilities such as `duf` without copying its interface.
- [ ] **Deterministic color palette:** use an application-defined palette with explicit colors and contrast choices instead of depending on terminal theme colors that may be indistinct or unsuitable.
- [ ] Improve the overall consistency of the compact, expanded, table, and classic filesystem views while keeping output readable in different terminal environments.

These items describe planned improvements, not guarantees of the current implementation. Command examples are proposals until implemented and documented in a release.

## Project Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Development Guide](docs/DEVELOPMENT.md)
- [Changelog](CHANGELOG.md)

## Safety Scope

lsdisk is intended for **storage inspection only**.

Formatting, partitioning, filesystem modification, and automatic mounting are outside the project's scope.

## License

lsdisk is distributed under the [MIT License](LICENSE).

---

<div align="center">
  <sub>lsdisk — making Linux storage easier to explore.</sub>
</div>
