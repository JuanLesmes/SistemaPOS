"""Compra a proveedor: entra mercancía y actualiza el costo del producto."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal

ZERO = Decimal(0)


@dataclass
class PurchaseItem:
    code: str
    name: str
    quantity: int
    unit_cost: Decimal

    @property
    def total(self) -> Decimal:
        return self.unit_cost * self.quantity


@dataclass
class Purchase:
    id: int | None
    supplier_id: int | None
    supplier_name: str
    invoice_number: str = ""
    purchased_at: dt.datetime | None = None
    user: str | None = None
    notes: str = ""
    items: list[PurchaseItem] = field(default_factory=list)

    @property
    def total(self) -> Decimal:
        return sum((item.total for item in self.items), ZERO)

    @property
    def units(self) -> int:
        return sum(item.quantity for item in self.items)
