"""Indicadores del inventario, derivados de la lista de productos."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from model.product import DEFAULT_MIN_STOCK, Product

LOW_STOCK_THRESHOLD = DEFAULT_MIN_STOCK  # umbral por defecto; cada producto puede tener el suyo


@dataclass(frozen=True)
class InventoryStats:
    product_count: int
    value_at_price: Decimal
    value_at_cost: Decimal
    low_stock_count: int
    out_of_stock_count: int


def inventory_stats(products: list[Product]) -> InventoryStats:
    return InventoryStats(
        product_count=len(products),
        value_at_price=sum((p.price * p.stock for p in products), Decimal(0)),
        value_at_cost=sum((p.cost * p.stock for p in products), Decimal(0)),
        low_stock_count=sum(1 for p in products if p.low_stock),
        out_of_stock_count=sum(1 for p in products if p.stock <= 0),
    )


def stock_tag(stock: int, min_stock: int = DEFAULT_MIN_STOCK) -> tuple[str, ...]:
    """Etiqueta de fila para resaltar existencias bajas o agotadas en las tablas."""
    if stock <= 0:
        return ("out",)
    if stock <= min_stock:
        return ("low",)
    return ()
