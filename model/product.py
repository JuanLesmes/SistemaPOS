from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Product:
    """Producto del catálogo. Los precios son Decimal para no perder centavos."""

    code: str
    name: str
    cost: Decimal
    price: Decimal
    stock: int
    category: str
    description: str = ""
    active: bool = True

    def __str__(self) -> str:
        return f"{self.code} | {self.name} | {self.category} | Stock: {self.stock} | Precio: ${self.price}"
