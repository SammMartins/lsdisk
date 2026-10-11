# Development Guide

This guide describes the local development workflow for lsdisk. The project is in early development, so keep changes small, tested, and easy to review.

## 1. Development environment

lsdisk targets Linux and requires Python 3.11 or newer.

From the repository root:

```bash
python --version
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Confirm that the virtual environment is active:

```bash
which python
python --version
```

The Python executable should resolve to the project's `.venv` directory. Keep project dependencies isolated from the system Python installation.

## 2. Run lsdisk

With the virtual environment activated:

```bash
lsdisk --help
lsdisk
lsdisk --all
lsdisk --table-mode
lsdisk --json
```

Use `lsdisk --help` as the source of truth for the options available in the current checkout.

## 3. Run tests

Run the full test suite from the repository root:

```bash
python -m unittest discover -s tests -v
```

Tests should prefer controlled fixtures and mocked system interfaces over dependence on the developer's actual disks. This makes the results repeatable and reduces the risk of accidentally relying on one machine's storage layout.

Test coverage should include, where relevant:

- Capacity calculations, units, percentages, zero values, and invalid input.
- Device discovery, parent/child relationships, and physical-versus-virtual classification.
- Mount information parsing and filesystem capacity collection.
- Filesystem classification and grouping, including Btrfs subvolumes.
- JSON serialization and CLI behavior.
- Missing, inaccessible, or malformed system information.

## 4. Architecture and implementation workflow

Keep the main responsibilities separated:

1. **Collectors** gather information from Linux interfaces and available tools.
2. **Models** represent devices and filesystem measurements consistently.
3. **Analyzers** interpret and group collected data without inventing missing values.
4. **Serialization** exposes structured output such as JSON.
5. **UI** presents the inventory without coupling the terminal interface to collection details.

For each change:

1. Define a narrow objective.
2. Inspect the relevant code and tests before editing.
3. Add or update tests for the behavior.
4. Implement the smallest coherent change.
5. Run the relevant tests, then the full test suite.
6. Review the diff and document limitations or decisions that affect future work.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the data flow and integrity constraints.

## 5. Safety and data integrity

lsdisk is an inspection tool. Development and tests must not format, partition, modify filesystems, or automatically mount storage devices.

Follow these rules:

- Do not treat an unmounted partition as empty.
- Do not report unavailable data as a confirmed zero.
- Do not add together physical capacity and the capacity of logical layers without accounting for their relationship.
- Avoid requiring root privileges unless a concrete requirement is documented and reviewed.
- Prefer native Python and Linux interfaces when they provide reliable information; use external commands as justified fallbacks.

## 6. Git workflow

Before staging:

```bash
git status
git diff --check
git diff
```

Stage only the intended files, then inspect what will be committed:

```bash
git add <paths>
git diff --cached --check
git diff --cached --stat
git diff --cached
```

Use a descriptive commit message, for example:

```text
feat: identify filesystems on unmounted partitions
```

Do not commit virtual environments, caches, local secrets, or machine-specific output.

## 7. Current limitations

Filesystem discovery on unmounted partitions, complete label/UUID collection, and broader handling of storage layers are roadmap items. Do not describe these capabilities as complete until they have been implemented and covered by tests.
