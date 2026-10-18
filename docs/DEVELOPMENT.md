# Development Guide

This guide describes the local development workflow for lsdisk. The
project targets Linux and is intended to work across distributions
rather than depend on one distribution's package layout.

## 1. Requirements

-   Linux
-   Python 3.11 or newer
-   Git
-   `curl` and `tar` are needed for the user-facing shell installer, but
    not for ordinary test execution

## 2. Create the development environment

Run these commands from the repository root:

``` bash
python --version
python -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .
```

Using `.venv/bin/python` directly avoids accidentally running tests with
the system interpreter if shell activation is not working as expected.

If you prefer activation, use:

``` bash
source .venv/bin/activate
which python
python --version
```

The executable should resolve to the `.venv` directory inside the
current repository. If the repository has moved since the virtual
environment was created, recreate `.venv`; virtual environments can
retain references to their original location.

## 3. Run lsdisk

From the repository root:

``` bash
.venv/bin/lsdisk --help
.venv/bin/lsdisk
.venv/bin/lsdisk --all
.venv/bin/lsdisk --table-mode
.venv/bin/lsdisk --json
```

Alternatively, activate `.venv` and use `lsdisk` directly. Check
`lsdisk --help` for the options available in the current checkout.

## 4. Run tests and checks

Run the complete test suite:

``` bash
.venv/bin/python -m unittest discover -s tests -v
```

Compile Python source and tests:

``` bash
.venv/bin/python -m compileall -q src tests
```

Check the patch for whitespace problems:

``` bash
git diff --check
```

Tests should prefer controlled fixtures and mocked system interfaces
over dependence on the developer's actual disks. This makes results
repeatable and avoids relying on one machine's storage layout.

Relevant test areas include:

-   Capacity calculations, units, percentages, zero values, and invalid
    input.
-   Device discovery, parent/child relationships, and
    physical-versus-virtual classification.
-   Mount information parsing and filesystem capacity collection.
-   Filesystem classification and grouping, including Btrfs subvolumes.
-   JSON serialization and CLI behavior.
-   Terminal output, utilization color thresholds, percentage clamping,
    and unavailable capacity.
-   Missing, inaccessible, or malformed system information.
-   Read-only `blkid` probing, including unmounted filesystems, missing tools, and probe timeouts.

## 5. Architecture and implementation workflow

Keep the main responsibilities separated:

1.  **Collectors** gather information from Linux interfaces and
    available tools.
2.  **Models** represent devices and filesystem measurements
    consistently.
3.  **Analyzers** interpret and group collected data without inventing
    missing values.
4.  **Serialization** exposes structured output such as JSON.
5.  **UI** presents the inventory without coupling terminal presentation
    to collection details.

For each change:

1.  Define a narrow objective.
2.  Inspect the relevant code and tests before editing.
3.  Add or update tests for the behavior.
4.  Implement the smallest coherent change.
5.  Run relevant tests, then the full test suite.
6.  Review the diff and document limitations or decisions that affect
    future work.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the data flow and integrity
constraints.

## 6. Safety and data integrity

lsdisk is an inspection tool. Development and tests must not format,
partition, modify filesystems, or automatically mount storage devices.

Follow these rules:

-   Do not treat an unmounted partition as empty.
-   Do not report unavailable data as a confirmed zero.
-   Do not add physical capacity and logical-layer capacity together
    without accounting for their relationship.
-   Avoid requiring root privileges unless a concrete requirement is
    documented and reviewed.
-   Prefer native Python and Linux interfaces when they provide reliable
    information; use external commands as justified fallbacks.
-   Keep installation and uninstallation scoped to the current user's
    lsdisk files.

## 7. Git workflow

Before staging:

``` bash
git status --short
git diff --check
git diff
```

Stage only intended files, then inspect the staged changes:

``` bash
git add <paths>
git diff --cached --check
git diff --cached --stat
git diff --cached
```

Do not commit virtual environments, caches, local secrets, or
machine-specific output. Do not include unrelated changes in the same
commit.

## 8. Current limitations

The current MVP discovers block-device topology and collects capacity
information for mounted filesystems. Read-only `blkid` probing now
collects filesystem signatures, labels, and UUIDs when available,
including on unmounted devices. Coverage across storage layers and
distributions still requires validation; do not describe that broader
compatibility as complete until implemented and tested.
