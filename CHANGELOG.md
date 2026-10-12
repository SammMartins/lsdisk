# Changelog

All notable changes to lsdisk are documented in this file.

This project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

Changes planned or made after the latest versioned release will be recorded here.

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