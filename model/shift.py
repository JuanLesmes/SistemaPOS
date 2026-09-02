"""Turno de caja: se abre con una base en efectivo y se cierra con un arqueo."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

ZERO = Decimal(0)

# Denominaciones colombianas para el conteo del arqueo (billetes y monedas).
DENOMINATIONS = (100000, 50000, 20000, 10000, 5000, 2000, 1000, 500, 200, 100, 50)


@dataclass(frozen=True)
class Shift:
    id: int
    opened_at: dt.datetime
    opened_by: str | None
    opening_cash: Decimal
    closed_at: dt.datetime | None = None
    closed_by: str | None = None
    expected_cash: Decimal | None = None
    counted_cash: Decimal | None = None
    difference: Decimal | None = None
    notes: str = ""

    @property
    def is_open(self) -> bool:
        return self.closed_at is None


@dataclass(frozen=True)
class ShiftSummary:
    """Movimiento del turno hasta el momento, calculado desde las ventas."""

    shift: Shift
    receipt_count: int
    cash_sales: Decimal
    card_sales: Decimal
    transfer_sales: Decimal
    returns: Decimal
    voided_count: int

    @property
    def total_sales(self) -> Decimal:
        return self.cash_sales + self.card_sales + self.transfer_sales

    @property
    def expected_cash(self) -> Decimal:
        """Base inicial más ventas en efectivo menos devoluciones (se asumen reembolsadas en efectivo)."""
        return self.shift.opening_cash + self.cash_sales - self.returns


def count_total(counts: dict[int, int]) -> Decimal:
    """Suma del conteo por denominación: {valor: cantidad}."""
    return sum((Decimal(value) * quantity for value, quantity in counts.items()), ZERO)
