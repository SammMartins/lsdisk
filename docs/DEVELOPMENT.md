# Development Guide

This guide covers development of lsdisk, a read-only Linux storage explorer
intended for multiple distributions and environments.

## Requirements

- Linux with normal access to `/sys` and `/proc`.
- Python 3.11 or newer (`pyproject.toml` is authoritative).
- Git.
- Internet access only when installing dependencies or building release
  artifacts.

Runtime dependencies are declared in `pyproject.toml`: `rich>=13.0`.
`lsblk`, `blkid`, and the optional LVM/MD tools improve metadata coverage but
are not required for every test or every inventory path. Distribution package
names differ; install the equivalent Python, Rich, and optional system tools
using the host distribution's documentation rather than assuming a package
manager.

## Repository setup

```bash
git clone https://github.com/SammMartins/lsdisk.git
cd lsdisk
python3 --version
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .
```

Using `.venv/bin/python` and `.venv/bin/lsdisk` avoids accidentally using a
different interpreter. Activation is optional:

```bash
source .venv/bin/activate
python --version
```

## Run the application

```bash
.venv/bin/lsdisk --help
.venv/bin/lsdisk
.venv/bin/lsdisk --all
.venv/bin/lsdisk --all --table-mode
.venv/bin/lsdisk --json
.venv/bin/lsdisk --all --json
.venv/bin/lsdisk --classic --no-color
```

The application is read-only. Do not use development or test commands to
format, partition, mount, activate, repair, or otherwise modify storage.

## Tests and checks

Run the complete suite:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Run an individual module or test case:

```bash
.venv/bin/python -m unittest tests.test_serialization -v
.venv/bin/python -m unittest tests.test_partition_inventory -v
.venv/bin/python -m unittest tests.test_terminal -v
```

Compile source and tests:

```bash
.venv/bin/python -m compileall -q src tests
```

Validate Git whitespace:

```bash
git diff --check
```

Tests use fixtures and mocks for Linux interfaces and optional tools. They
cover capacity ownership, filesystem grouping and probes, device paths,
relationships, LVM/MD metadata handling, partition geometry, fstab parsing,
serialization, CLI behavior, and terminal width/color behavior. Real-system
LVM and RAID validation remains environment-dependent and must use a
disposable test host.

## Build and packaging

Build the Python source and wheel distributions (requires the `build` package):

```bash
.venv/bin/python -m pip install build
.venv/bin/python -m build
```

Build the Debian package on a Debian-family system with `dpkg-deb`, Python
3.11+, and the `python3-rich` dependency available:

```bash
bash packaging/deb/build-deb.sh
```

The script reads the version from `pyproject.toml`, writes
`dist/lsdisk_<version>_all.deb`, and accepts an optional `RELEASE_TAG` that
must match the project version with or without a leading `v`. It does not
remove unrelated artifacts. GitHub Actions runs tests and package builds for
published releases. The Debian package workflow also supports manual
dispatch; the PyPI publishing workflow is release-only.

The project entry point is `lsdisk = lsdisk.main:main`. The shell installer
and Debian packaging script are distribution mechanisms, not prerequisites
for source development.

The per-user installer uses the exact `LSDISK_VERSION` selected by the
installer (currently `0.1.3` by default), retrieves the matching PyPI source
distribution, and verifies its SHA-256 digest from PyPI metadata before
installation. It fails before installation when the version, artifact, or
digest cannot be validated. Production source distributions exclude tests,
generated metadata, caches, virtual environments, and local build artifacts.

## Contribution workflow

1. Inspect the relevant implementation and tests before editing.
2. Keep collection, models, analysis, serialization, and UI responsibilities
   separate.
3. Add focused tests for behavior introduced or corrected.
4. Run the targeted tests, full suite, compilation, and whitespace checks.
5. Review the complete diff and document externally visible behavior.
6. Stage only intended files; do not commit generated environments, caches,
   secrets, or machine-specific output.

Useful pre-staging commands:

```bash
git status --short
git diff --check
git diff
git diff --stat
```

## Data-integrity rules

- Preserve unknown and unavailable values; do not turn them into zero.
- Do not treat an unmounted device as an empty filesystem.
- Do not add partition or logical-layer capacity independently to physical
  disk totals.
- Keep active mounts distinct from `/etc/fstab` configuration.
- Keep partition geometry read-only and conservative.
- Never infer a storage relationship from an ambiguous or incomplete edge.

See [ARCHITECTURE.md](ARCHITECTURE.md) for module responsibilities and
mathematical details, and [CHANGELOG.md](../CHANGELOG.md) for release history.
