"""Testes unitários do analisador de capacidade."""

import unittest

from storix.analyzers.capacity import Capacity, format_bytes


class TestCapacity(unittest.TestCase):
    def test_calcula_espaco_usado(self):
        capacity = Capacity(total_bytes=1000, available_bytes=250)
        self.assertEqual(capacity.used_bytes, 750)

    def test_calcula_percentual_usado(self):
        capacity = Capacity(total_bytes=1000, available_bytes=280)
        self.assertAlmostEqual(capacity.used_percent, 72.0)

    def test_calcula_percentual_disponivel(self):
        capacity = Capacity(total_bytes=1000, available_bytes=280)
        self.assertAlmostEqual(capacity.available_percent, 28.0)

    def test_capacidade_vazia(self):
        capacity = Capacity(total_bytes=0, available_bytes=0)
        self.assertEqual(capacity.used_percent, 0.0)

    def test_rejeita_capacidade_total_negativa(self):
        with self.assertRaises(ValueError):
            Capacity(total_bytes=-1, available_bytes=0)

    def test_rejeita_disponibilidade_negativa(self):
        with self.assertRaises(ValueError):
            Capacity(total_bytes=100, available_bytes=-1)

    def test_rejeita_disponibilidade_acima_do_total(self):
        with self.assertRaises(ValueError):
            Capacity(total_bytes=100, available_bytes=101)

    def test_formata_gib(self):
        self.assertEqual(format_bytes(1024**3), "1.00 GiB")

    def test_formata_zero(self):
        self.assertEqual(format_bytes(0), "0 B")


if __name__ == "__main__":
    unittest.main()
