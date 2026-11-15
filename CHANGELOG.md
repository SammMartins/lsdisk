# Changelog

All notable changes to lsdisk are documented in this file.

This project follows [Semantic Versioning](https://semver.org/).

## [0.1.3] - 2026-11-11

### Added

- Added read-only partition-table geometry, sector-size, partition-name,
  type, flag, and conservative unallocated-region inventory.
- Added persistent `/etc/fstab` entries as separate inventory records.
- Added the `-c`/`--classic` filesystem overview mode.
- Added a shared application palette and width-conscious table columns.

### Changed

- Clarified cross-distribution requirements, optional system utilities,
  privilege expectations, and the distinction between active mounts and
  persistent mount configuration.
- Pinned the per-user installer to an exact release version and added
  SHA-256 verification against PyPI metadata.
- Excluded development-only files from production source distributions.

### Fixed

- Reject incomplete or ambiguous MD RAID member relationships, including
  partially resolved sysfs topology and malformed `mdadm` output.
- Show partition geometry and persistent `/etc/fstab` configuration in
  expanded compact output without conflating configured and active mounts.
- Validate release tags and built artifact metadata before PyPI publication.
- Isolate malformed or out-of-range sysfs device sizes from valid devices.
- Corrected partition geometry and sector-boundary handling, including
  preservation of sector zero and rejection of invalid, overlapping,
  misaligned, or out-of-capacity geometry before unallocated regions are
  reported.
- Prevented duplicate filesystem probes by reusing complete `lsblk`
  metadata and probing each remaining eligible device once.
- Stabilized simple and expanded JSON serialization, including numeric
  capacity values, zero-valued sector boundaries, grouped filesystem
  capacity, and deterministic deduplicated relationship references.
- Improved adaptive terminal column allocation so optional values are
  abbreviated only when needed and width warnings are shown only when the
  layout is reduced.

### Documentation

- Expanded documentation for the simple and expanded JSON contracts,
  verified storage relationships, filesystem probe states, and adaptive
  terminal layouts.

## [0.1.2] - 2026-10-18

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
- Real-system LVM and RAID integration validation remains a known limitation
  of this release and should be completed in supported test environments.

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

- [0.1.2] — 2026-10-18 ([GitHub release](https://github.com/SammMartins/lsdisk/releases/tag/v0.1.2))
- [0.1.1] — 2026-10-12 ([GitHub release](https://github.com/SammMartins/lsdisk/releases/tag/v0.1.1))