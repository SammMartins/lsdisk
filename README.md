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
- [Development Status](#development-status)
- [Project Documentation](#project-documentation)
- [Safety Scope](#safety-scope)
- [License](#license)

---

## About lsdisk

**lsdisk** is a Linux storage inspection tool designed to make information about HDDs, SSDs, partitions, and filesystems easier to understand.

It brings storage topology and filesystem capacity information together in a structured terminal interface.

lsdisk is read-only: it inspects storage and does not format, partition, mount, or modify filesystems.

![lsdisk Demo](https://raw.githubusercontent.com/SammMartins/lsdisk/main/img/lsdisk_0_1_1.gif)

<p><sub><em>Live demonstration of lsdisk v0.1.1 inspecting Linux storage devices in the terminal.</em></sub></p>

## Features

- **Physical storage inventory** — show detected disks and their child partitions in a hierarchical view.
- **Device details** — display device names, capacity, model, physical/virtual classification, and HDD or SSD/Flash indicators when the system provides enough information.
- **Filesystem metadata** — identify filesystem signatures on unmounted block devices and collect labels and UUIDs when available, without mounting them.
- **Filesystem capacity** — report total, used, free, and user-available capacity for accessible mounted filesystems.
- **Mountpoint visibility** — associate filesystem information with mountpoints where the relationship can be established.
- **Filesystem grouping** — group related filesystem records to avoid repeating capacity for multiple mountpoints, including supported Btrfs subvolume cases.
- **Filesystem classification** — distinguish persistent storage, network,
  application-image, temporary, virtual, and unknown filesystems without
  hiding their mountpoints.
- **Utilization bars** — display a compact visual usage bar and percentage in the terminal. Green indicates below 70% utilization, yellow indicates 70% to below 90%, and red indicates 90% or higher.
- **Multiple output modes** — provide a compact default view, expanded output, table output, and JSON output.
- **Graceful handling of missing data** — distinguish unavailable information from a confirmed zero value.

Capacity values depend on the information available from the running Linux system. Physical disk capacity and mounted filesystem capacity describe different layers and should not be treated as interchangeable.

## Design Principles

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
- **Linux interfaces** — including `/sys` and `/proc`, where appropriate.
- **`os.statvfs()`** — mounted filesystem capacity statistics.
- **`unittest`** — automated testing.

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
  | xargs curl -LO && sudo apt install ./lsdisk_*.deb
```

Verify the installation:

```bash
lsdisk --version
lsdisk --help
```

The package installs the `lsdisk` command system-wide. The package manager handles the declared dependencies and tracks the installed files.

### Install Using the Shell Script

The official installation script downloads lsdisk, creates an isolated Python virtual environment, and installs the `lsdisk` command for the current user.

```bash
curl -sSL https://raw.githubusercontent.com/SammMartins/lsdisk/main/install.sh | bash
```

The installer does not require `sudo` and refuses to run as root.

By default, application files are stored in `~/.local/share/lsdisk`, and the executable is installed in `~/.local/bin`.

If `~/.local/bin` is not in your `PATH`, follow the instructions printed by the installer.

Verify the installation:

```bash
lsdisk --version
lsdisk --help
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

If `uninstall.sh` is available locally, run it as your regular user, without `sudo`:

```bash
bash uninstall.sh
```

The uninstaller removes the per-user launcher and application data directory. It does not delete the local Git repository or project source files.

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

## Development Status

**lsdisk is in early development.** Features and interfaces may change as the project evolves.

The current implementation covers block-device topology, read-only filesystem
metadata probing, and capacity information for mounted filesystems.

### Roadmap

- [ ] Improve identification of partitions whose filesystem information is unavailable.
- [x] Add deterministic, read-only relationship discovery for LVM PV/VG/LV
  layers and Linux MD RAID arrays where system metadata verifies them.
- [ ] Complete advanced storage-layer accounting and broader validation for
  Btrfs multi-device filesystems, LVM extents, RAID usable capacity and
  rebuild state, LUKS layers, and additional Linux configurations.
- [ ] Improve the UI and UX.

These items are planned improvements, not guarantees of the current implementation.

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
