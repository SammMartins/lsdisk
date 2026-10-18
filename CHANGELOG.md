# Changelog

All notable changes to lsdisk are documented in this file.

This project follows [Semantic Versioning](https://semver.org/).

## [0.1.2] - Unreleased

### Added

- Added read-only filesystem metadata collection for unmounted block devices,
  including filesystem labels, UUIDs, and recognized storage signatures.
- Added explicit filesystem probe outcomes for recognized signatures, no
  signature, unavailable probes, and malformed or failed probes.
- Added canonical device identity and conservative storage relationship
  discovery for partitions, encrypted mappings, LVM PV/VG/LV layers, and
  Linux MD RAID arrays when the available metadata verifies them.

### Changed

- Improved physical-capacity ownership so physical disks are counted once
  while partitions and logical storage layers remain visible in detailed
  inventory.
- Improved filesystem grouping and relationship handling for aliases,
  duplicate references, incomplete metadata, and invalid topology.
- Preserved read-only behavior and safely degrade when optional interfaces or
  tools are unavailable.

### Validation

- Added deterministic regression coverage for filesystem probes, canonical
  identities, storage relationships, LVM and MD RAID metadata handling, and
  capacity ownership.
- Real-system LVM and RAID integration validation remains outside this
  release preparation.

## [0.1.1] - 2026-10-12

### Added

- Added a per-user installation script that creates an isolated Python environment and installs the `lsdisk` command.
- Added an uninstallation script for removing the installed launcher and application data without deleting the source repository.
- Added color-coded utilization bars to the terminal storage summary and partition details.
- Added utilization percentages alongside the bars.
- Added tests for utilization color thresholds, percentage clamping, and unavailable capacity data.

### Changed

- Simplified the storage summary so used and user-available capacity are shown without duplicating the percentage displayed by the bar.
- Improved the terminal presentation of physical disks, partitions, filesystem usage, and mountpoints.
- Documented installation, uninstallation, supported command examples, and the current development scope.

### Validation

- The test suite passed with 52 tests after the utilization-bar changes.
- Python syntax compilation completed successfully.
- `git diff --check` completed without reporting whitespace errors.

## Release history

No published release is documented in this changelog yet.