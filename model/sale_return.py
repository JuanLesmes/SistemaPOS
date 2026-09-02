"""Devolución parcial o total de un recibo."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal

ZERO = Decimal(0)


@dataclass(frozen=True)
class ReturnItem:
    code: str
    name: str
    quantity: int
    unit_price: Decimal

    @property
    def total(self) -> Decimal:
        return self.unit_price * self.quantity


@dataclass
class SaleReturn:
    id: int | None
    receipt_id: int
    reason: str = ""
    user: str | None = None
    created_at: dt.datetime | None = None
    items: list[ReturnItem] = field(default_factory=list)

    @property
    def total(self) -> Decimal:
        return sum((item.total for item in self.items), ZERO)
