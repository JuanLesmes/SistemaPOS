from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

DEFAULT_MIN_STOCK = 3
TAX_RATES = (Decimal(0), Decimal(5), Decimal(19))  # IVA en Colombia: exento, 5 % y 19 %


@dataclass
class Product:
    """Producto del catálogo. Los precios son Decimal para no perder centavos.

    ``tax_rate`` es el porcentaje de IVA incluido en el precio de venta y
    ``min_stock`` el umbral a partir del cual se avisa que quedan pocas unidades.
    """

    code: str
    name: str
    cost: Decimal
    price: Decimal
    stock: int
    category: str
    description: str = ""
    active: bool = True
    min_stock: int = DEFAULT_MIN_STOCK
    tax_rate: Decimal = Decimal(0)

    @property
    def low_stock(self) -> bool:
        return 0 < self.stock <= self.min_stock

    def __str__(self) -> str:
        return f"{self.code} | {self.name} | {self.category} | Stock: {self.stock} | Precio: ${self.price}"
