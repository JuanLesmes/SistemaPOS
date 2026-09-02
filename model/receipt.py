from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal

from model.sold_product import SoldProduct

PAYMENT_CASH = "Efectivo"
PAYMENT_CARD = "Tarjeta"
PAYMENT_TRANSFER = "Transferencia"
PAYMENT_MIXED = "Mixto"
PAYMENT_METHODS = (PAYMENT_CASH, PAYMENT_CARD, PAYMENT_TRANSFER)

STATUS_COMPLETED = "completed"
STATUS_VOIDED = "voided"

ZERO = Decimal(0)


@dataclass(frozen=True)
class Payment:
    method: str
    amount: Decimal


@dataclass
class Receipt:
    """Recibo de venta con sus líneas y sus pagos."""

    id: int | None
    date: dt.date
    time: dt.time
    payment_method: str
    total: Decimal
    sold_products: list[SoldProduct] = field(default_factory=list)
    cashier: str | None = None  # usuario que atendió la venta
    status: str = STATUS_COMPLETED
    discount_total: Decimal = ZERO  # descuento sobre la venta completa, además de los de cada línea
    payments: list[Payment] = field(default_factory=list)
    shift_id: int | None = None
    void_reason: str | None = None
    voided_by: str | None = None
    returned_total: Decimal = ZERO  # suma de las devoluciones hechas sobre este recibo

    @classmethod
    def create(
        cls,
        payment_method: str,
        sold_products: list[SoldProduct],
        when: dt.datetime | None = None,
        discount_total: Decimal = ZERO,
        payments: list[Payment] | None = None,
        shift_id: int | None = None,
    ) -> Receipt:
        """Arma un recibo nuevo (sin id) con la fecha actual y el total calculado."""
        if not sold_products:
            raise ValueError("Un recibo necesita al menos un producto.")
        gross = sum((sp.total for sp in sold_products), ZERO)
        if discount_total < 0 or discount_total > gross:
            raise ValueError("El descuento debe estar entre cero y el total de la venta.")
        total = gross - discount_total
        if payments is None:
            if payment_method not in PAYMENT_METHODS:
                raise ValueError(f"Método de pago desconocido: {payment_method}")
            payments = [Payment(payment_method, total)]
        else:
            if any(p.method not in PAYMENT_METHODS or p.amount < 0 for p in payments):
                raise ValueError("Pago inválido.")
            if sum((p.amount for p in payments), ZERO) != total:
                raise ValueError("La suma de los pagos debe ser igual al total de la venta.")
            payments = [p for p in payments if p.amount > 0]
            payment_method = payments[0].method if len(payments) == 1 else PAYMENT_MIXED
        now = when or dt.datetime.now()
        return cls(
            id=None,
            date=now.date(),
            time=now.time().replace(microsecond=0),
            payment_method=payment_method,
            total=total,
            sold_products=list(sold_products),
            discount_total=discount_total,
            payments=payments,
            shift_id=shift_id,
        )

    @property
    def is_voided(self) -> bool:
        return self.status == STATUS_VOIDED

    @property
    def gross_total(self) -> Decimal:
        """Antes del descuento general (los descuentos por línea ya están aplicados)."""
        return sum((sp.total for sp in self.sold_products), ZERO)

    @property
    def tax_total(self) -> Decimal:
        """IVA incluido en el total. El descuento general reduce el impuesto en proporción."""
        gross = self.gross_total
        line_tax = sum((sp.tax_amount for sp in self.sold_products), ZERO)
        if not gross or not line_tax:
            return ZERO
        return (line_tax * self.total / gross).quantize(Decimal("0.01"))

    @property
    def net_total(self) -> Decimal:
        """Lo que efectivamente quedó después de devoluciones."""
        return self.total - self.returned_total

    def paid_with(self, method: str) -> Decimal:
        return sum((p.amount for p in self.payments if p.method == method), ZERO)
