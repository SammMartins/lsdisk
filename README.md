<div align="center">

  <img src="img/lsdisk.png" alt="lsdisk — Linux Storage Explorer" width="760">

  <h1>lsdisk</h1>
  <p><strong>Cross-distro Linux Storage Explorer</strong></p>
  <p>Understand your disks, partitions, and filesystems — clearly, safely, and from the terminal.</p>

</div>

---

## About lsdisk

**lsdisk** is a Linux storage inspection tool designed to make information about HDDs, SSDs, partitions, and filesystems easier to understand.

It aims to present technical storage details in a clear, structured terminal interface, helping users explore how their storage is organized without needing to interpret raw system output manually.

> **Read-only by design.** lsdisk is intended to inspect storage, not modify it.

## Why lsdisk?

Linux provides powerful tools for inspecting storage, but their output can be fragmented across commands and system interfaces. lsdisk aims to bring relevant information together in one place and make the relationships between physical devices, partitions, and filesystems easier to follow.

### Key goals

- **Explore storage devices** — identify disks and understand how their partitions relate to them.
- **Understand capacity** — present total capacity, used space, and available space where the data is accessible.
- **Inspect filesystem information** — distinguish recognized filesystems from information that is unavailable or not yet identified.
- **Find unmounted partitions** — work toward identifying filesystem types without mounting partitions.
- **Read information at a glance** — use terminal colors, tables, progress bars, and hierarchical views.
- **Support multiple Linux distributions** — minimize reliance on distribution-specific behavior.

## Design principles

| Principle | What it means |
|---|---|
| **Read-only inspection** | Do not modify disks, partitions, or filesystems. |
| **Modular architecture** | Keep data collection, analysis, and presentation separated. |
| **Portability** | Avoid unnecessary dependencies on a specific Linux distribution. |
| **Transparency** | Clearly distinguish confirmed values from estimates or unavailable data. |
| **Testability** | Validate calculations and behavior with automated tests. |

## Technology

lsdisk is being developed with a practical, Linux-native approach:

- **Python** — application logic.
- **Rich** — terminal presentation.
- **Python standard library** — core APIs and supporting functionality.
- **Linux interfaces**, including `/sys` and `/proc`, where appropriate.
- **System utilities**, such as `lsblk` and `findmnt`, when justified.
- **`unittest`** — initial automated testing.

## Requirements

- Linux
- A compatible Python version for the project's dependencies
- A Python virtual environment is recommended

Some information may depend on available system utilities, permissions, and the storage configuration.

## Development status

**lsdisk is in early development.** Features and interfaces may change as the project evolves. The roadmap below describes planned improvements; they should not be considered fully implemented.

### Roadmap

- [ ] **Discover unmounted partitions** — identify filesystem types without mounting partitions.
- [ ] **Collect filesystem metadata** — retrieve labels and UUIDs when available.
- [ ] **Improve partition identification** — distinguish recognized filesystems from partitions whose filesystem information is unavailable or not yet identified.
- [ ] **Preserve read-only behavior** — keep storage discovery within the project's non-modifying scope.

These improvements are planned and are not fully implemented in version `0.1.0`.

## Project documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Development guide](docs/DEVELOPMENT.md)

## Safety scope

lsdisk is intended for **storage inspection only**. Formatting, partitioning, and filesystem modification are outside the project's scope.

## License

The project license has not yet been selected and will be defined before the first public distribution.

---

<div align="center">
  <sub>lsdisk — making Linux storage easier to explore.</sub>
</div>
