"""Capacity calculations for lsdisk."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Capacity:
    """Represent a capacity measurement in bytes."""

    total_bytes: int
    available_bytes: int

    def __post_init__(self) -> None:
        if self.total_bytes < 0:
            raise ValueError("Total capacity cannot be negative.")

        if self.available_bytes < 0:
            raise ValueError("Available space cannot be negative.")

        if self.available_bytes > self.total_bytes:
            raise ValueError(
                "Available space cannot exceed total capacity."
            )

    @property
    def used_bytes(self) -> int:
        """Calculate used space in bytes."""
        return self.total_bytes - self.available_bytes

    @property
    def used_percent(self) -> float:
        """Calculate the percentage used, from 0 to 100."""
        if self.total_bytes == 0:
            return 0.0

        return self.used_bytes / self.total_bytes * 100

    @property
    def available_percent(self) -> float:
        """Calculate the percentage available, from 0 to 100."""
        if self.total_bytes == 0:
            return 0.0

        return self.available_bytes / self.total_bytes * 100


def format_bytes(size_bytes: int) -> str:
    """Format bytes using binary units (KiB, MiB, GiB, and TiB)."""
    if size_bytes < 0:
        raise ValueError("Size cannot be negative.")

    value = float(size_bytes)
    units = ("B", "KiB", "MiB", "GiB", "TiB", "PiB")

    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} B"

            return f"{value:.2f} {unit}"

        value /= 1024

    raise AssertionError("Size unit not found.")
