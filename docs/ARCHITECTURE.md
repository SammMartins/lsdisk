# Architecture

lsdisk is a Linux storage inventory application built around a simple
principle: collect facts from the host, normalize them, analyze them
carefully, and present them without hiding uncertainty.

## Design goals

-   **Cross-distribution:** avoid unnecessary assumptions about a
    particular Linux distribution.
-   **Read-only inspection:** do not modify disks, partitions, or
    filesystems.
-   **Data integrity:** distinguish physical devices, partitions,
    filesystem capacity, and mountpoints.
-   **Graceful degradation:** missing interfaces or inaccessible
    information should not crash the entire inventory where recovery is
    possible.
-   **Testability:** keep core logic separable from the developer's real
    storage devices and terminal.

## Data flow

``` text
Linux interfaces and available tools
                 |
                 v
              Collectors
                 |
                 v
        Normalized data models
                 |
                 v
               Analyzers
                 |
           +-----+-----+
           |           |
           v           v
       Terminal UI   JSON output
```

Collection and presentation are separate responsibilities. The UI should
consume the normalized inventory rather than call operating-system
interfaces directly.

## Components

### Collectors

Collectors retrieve information from the running system, including block
devices, partitions, mountpoints, and capacity statistics. A collector
should handle unavailable or malformed data deliberately and avoid
assuming that every device has a mounted filesystem.

### Models

Models provide consistent representations of block devices and
filesystem measurements. They preserve distinctions such as total
capacity, free space, and space available to an unprivileged user where
the source provides those values.

### Analyzers

Analyzers classify and group filesystem records and calculate derived
indicators. They must preserve unknown values and avoid misleading
totals, particularly when multiple mountpoints refer to the same
underlying filesystem.

### Inventory orchestration

The inventory layer combines collector results, associates filesystem
sources with discovered devices where possible, and exposes a unified
structure to the output layers.

### Serialization

The serialization layer converts the normalized inventory into
machine-readable JSON. Output modes should have explicit, testable
contracts.

### Terminal UI

The terminal layer uses Rich to render the storage summary, hierarchical
physical-storage view, expanded filesystem details, tables, and
utilization bars.

The compact storage summary distinguishes physical capacity from
mounted-filesystem capacity. Its usage line presents used and
user-available capacity, while the utilization bar displays the
percentage. Partition details follow the same pattern: the `Usage` line
shows used and available capacity, and the bar below it shows
utilization.

Utilization bars use these thresholds:

  Utilization        Color
  ------------------ --------
  Below 70%          Green
  70% to below 90%   Yellow
  90% or higher      Red

The bar and displayed percentage should use the same utilization color.
The empty portion of a bar remains visually subdued. When capacity data
is unavailable or invalid, the UI must not present a fabricated
utilization percentage.

The terminal layer is responsible for presentation, not for discovering
devices or interpreting raw kernel data.

## Data sources

lsdisk prioritizes Python and Linux interfaces, using external tools
when they provide necessary or more reliable information.

  -----------------------------------------------------------------------
  Source                              Intended use
  ----------------------------------- -----------------------------------
  `/sys`                              Kernel-exposed block-device
                                      properties and relationships.

  `/proc/self/mountinfo`              Mountpoints, filesystem sources,
                                      and mount metadata for the current
                                      process.

  `os.statvfs()`                      Capacity statistics for accessible
                                      mounted filesystems.

  `lsblk`                             Potential fallback or verification
                                      source for block-device topology.

  `findmnt`                           Potential supplementary source for
                                      mount information.

  `udev`                              Potential source of device
                                      properties when available.
  -----------------------------------------------------------------------

Availability and behavior can vary across systems. External tools should
be checked before use, and their output should be parsed defensively.

## Integrity rules

### Physical devices are not filesystems

A drive's physical capacity and a filesystem's usable capacity are
different measurements. The interface must not present them as
interchangeable.

### Unmounted does not mean empty

An unmounted partition may contain a filesystem even when its usage
cannot be measured through `statvfs()`. Until it is identified through a
reliable source, its filesystem status should remain unknown.

### Avoid double-counting

A physical device, a partition, a logical storage layer, and a mounted
filesystem can represent related views of the same storage. Btrfs
subvolumes can also expose the same filesystem capacity through multiple
mountpoints. Group related records where identity is sufficiently
established, and do not sum them indiscriminately.

### Unknown is a valid result

If a value cannot be collected reliably, preserve that uncertainty. Do
not substitute zero, infer an empty filesystem, or display a guess as
confirmed data.

### Least privilege

Read-only inventory collection should not require administrative
privileges by default. Any future requirement for elevated access must
be justified and documented.

## Current scope and planned work

The current MVP discovers block-device topology and collects capacity
information for mounted filesystems. The following are planned
improvements, not guarantees of the current implementation:

-   Filesystem identification on unmounted partitions.
-   More complete filesystem label and UUID collection.
-   Broader, validated handling of Btrfs, LVM, RAID, LUKS, and other
    storage layers.

These capabilities should be introduced incrementally, with tests for
both successful detection and unavailable information.
