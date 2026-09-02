from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from model.product import Product


@dataclass
class SoldProduct:
    """Una línea de venta.

    Guarda el precio y el costo unitarios al momento de vender, de modo que los
    reportes históricos no cambien cuando el producto cambie de precio.
    """

    product: Product
    quantity: int
    unit_price: Decimal | None = None
    unit_cost: Decimal | None = None

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("La cantidad vendida debe ser mayor que cero.")
        if self.unit_price is None:
            self.unit_price = self.product.price
        if self.unit_cost is None:
            self.unit_cost = self.product.cost

    @property
    def code(self) -> str:
        return self.product.code

    @property
    def total(self) -> Decimal:
        return self.unit_price * self.quantity
