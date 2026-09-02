"""Movimiento de inventario (kárdex)."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

KIND_SALE = "sale"
KIND_VOID = "void"
KIND_RETURN = "return"
KIND_PURCHASE = "purchase"
KIND_ADJUSTMENT = "adjustment"
KIND_INITIAL = "initial"

KIND_LABELS = {
    KIND_SALE: "Venta",
    KIND_VOID: "Anulación",
    KIND_RETURN: "Devolución",
    KIND_PURCHASE: "Compra",
    KIND_ADJUSTMENT: "Ajuste",
    KIND_INITIAL: "Inicial",
}


@dataclass(frozen=True)
class StockMovement:
    id: int
    code: str
    product_name: str
    kind: str
    quantity: int  # positivo entra, negativo sale
    stock_after: int
    reference: str
    reason: str
    user: str | None
    created_at: dt.datetime

    @property
    def kind_label(self) -> str:
        return KIND_LABELS.get(self.kind, self.kind)
