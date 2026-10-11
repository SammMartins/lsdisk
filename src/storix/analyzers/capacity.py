"""Cálculos de capacidade para o Storix."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Capacity:
    """Representa uma medição de capacidade em bytes."""

    total_bytes: int
    available_bytes: int

    def __post_init__(self) -> None:
        if self.total_bytes < 0:
            raise ValueError("A capacidade total não pode ser negativa.")

        if self.available_bytes < 0:
            raise ValueError("O espaço disponível não pode ser negativo.")

        if self.available_bytes > self.total_bytes:
            raise ValueError(
                "O espaço disponível não pode superar a capacidade total."
            )

    @property
    def used_bytes(self) -> int:
        """Calcula o espaço ocupado em bytes."""
        return self.total_bytes - self.available_bytes

    @property
    def used_percent(self) -> float:
        """Calcula o percentual ocupado, de 0 a 100."""
        if self.total_bytes == 0:
            return 0.0

        return self.used_bytes / self.total_bytes * 100

    @property
    def available_percent(self) -> float:
        """Calcula o percentual disponível, de 0 a 100."""
        if self.total_bytes == 0:
            return 0.0

        return self.available_bytes / self.total_bytes * 100


def format_bytes(size_bytes: int) -> str:
    """Formata bytes usando unidades binárias (KiB, MiB, GiB e TiB)."""
    if size_bytes < 0:
        raise ValueError("O tamanho não pode ser negativo.")

    value = float(size_bytes)
    units = ("B", "KiB", "MiB", "GiB", "TiB", "PiB")

    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} B"

            return f"{value:.2f} {unit}"

        value /= 1024

    raise AssertionError("Unidade de tamanho não encontrada.")
