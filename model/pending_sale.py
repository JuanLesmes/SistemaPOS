"""Venta en curso o en espera dentro de la caja.

Permite atender varios clientes a la vez: cada venta guarda sus productos, el
monto recibido y si el cliente quiere recibo, para retomarla tal cual.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from model.sold_product import SoldProduct


@dataclass
class PendingSale:
    number: int
    lines: list[SoldProduct] = field(default_factory=list)
    received_text: str = ""
    wants_receipt: bool = False
    db_id: int | None = None  # id en la tabla pending_sales cuando ya está guardada

    @property
    def is_empty(self) -> bool:
        return not self.lines and not self.received_text and not self.wants_receipt

    @property
    def total(self) -> Decimal:
        return sum((sp.total for sp in self.lines), Decimal(0))

    @property
    def item_count(self) -> int:
        return sum(sp.quantity for sp in self.lines)

    def quantity_of(self, code: str) -> int:
        return sum(sp.quantity for sp in self.lines if sp.code == code)
