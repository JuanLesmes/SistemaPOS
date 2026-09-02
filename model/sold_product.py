from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from model.product import Product

ZERO = Decimal(0)
CENTS = Decimal("0.01")


@dataclass
class SoldProduct:
    """Una línea de venta.

    Guarda el precio, el costo y el IVA al momento de vender, de modo que los
    reportes históricos no cambien cuando el producto cambie. ``discount`` es
    el descuento en pesos aplicado a la línea completa.
    """

    product: Product
    quantity: int
    unit_price: Decimal | None = None
    unit_cost: Decimal | None = None
    tax_rate: Decimal | None = None
    discount: Decimal = ZERO

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("La cantidad vendida debe ser mayor que cero.")
        if self.unit_price is None:
            self.unit_price = self.product.price
        if self.unit_cost is None:
            self.unit_cost = self.product.cost
        if self.tax_rate is None:
            self.tax_rate = self.product.tax_rate
        if self.discount < 0 or self.discount > self.gross:
            raise ValueError("El descuento debe estar entre cero y el valor de la línea.")

    @property
    def code(self) -> str:
        return self.product.code

    @property
    def gross(self) -> Decimal:
        """Valor antes de descuento."""
        return self.unit_price * self.quantity

    @property
    def total(self) -> Decimal:
        return self.gross - self.discount

    @property
    def tax_amount(self) -> Decimal:
        """IVA incluido en el total de la línea."""
        if not self.tax_rate:
            return ZERO
        base = self.total / (1 + self.tax_rate / 100)
        return (self.total - base).quantize(CENTS, rounding=ROUND_HALF_UP)

    @property
    def profit(self) -> Decimal:
        return self.total - self.unit_cost * self.quantity
