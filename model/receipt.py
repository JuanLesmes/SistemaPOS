from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal

from model.sold_product import SoldProduct

PAYMENT_CASH = "Efectivo"
PAYMENT_CARD = "Tarjeta"
PAYMENT_TRANSFER = "Transferencia"
PAYMENT_METHODS = (PAYMENT_CASH, PAYMENT_CARD, PAYMENT_TRANSFER)


@dataclass
class Receipt:
    """Recibo de venta con sus líneas."""

    id: int | None
    date: dt.date
    time: dt.time
    payment_method: str
    total: Decimal
    sold_products: list[SoldProduct] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        payment_method: str,
        sold_products: list[SoldProduct],
        when: dt.datetime | None = None,
    ) -> Receipt:
        """Arma un recibo nuevo (sin id) con la fecha actual y el total calculado."""
        if payment_method not in PAYMENT_METHODS:
            raise ValueError(f"Método de pago desconocido: {payment_method}")
        if not sold_products:
            raise ValueError("Un recibo necesita al menos un producto.")
        now = when or dt.datetime.now()
        total = sum((sp.total for sp in sold_products), Decimal(0))
        return cls(
            id=None,
            date=now.date(),
            time=now.time().replace(microsecond=0),
            payment_method=payment_method,
            total=total,
            sold_products=list(sold_products),
        )
