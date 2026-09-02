"""Estructuras del reporte de ventas, derivadas de los recibos."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

from model.receipt import PAYMENT_CARD, PAYMENT_CASH, PAYMENT_TRANSFER, Receipt

ZERO = Decimal(0)


@dataclass(frozen=True)
class SalesReportRow:
    """Una fila del reporte: un producto dentro de un recibo."""

    receipt_id: int
    date: dt.date
    time: dt.time
    payment_method: str
    code: str
    name: str
    quantity: int
    unit_price: Decimal
    total: Decimal
    cashier: str | None = None
    voided: bool = False


@dataclass(frozen=True)
class SalesTotals:
    total: Decimal
    cash: Decimal
    card: Decimal
    transfer: Decimal
    receipt_count: int = 0
    returns: Decimal = ZERO
    voided_count: int = 0
    tax: Decimal = ZERO

    @property
    def net(self) -> Decimal:
        return self.total - self.returns


def rows_from_receipts(receipts: list[Receipt]) -> list[SalesReportRow]:
    """Una fila por producto y recibo; líneas repetidas del mismo producto se suman."""
    rows: list[SalesReportRow] = []
    for receipt in receipts:
        merged: dict[str, SalesReportRow] = {}
        for sp in receipt.sold_products:
            previous = merged.get(sp.code)
            quantity = sp.quantity + (previous.quantity if previous else 0)
            total = sp.total + (previous.total if previous else ZERO)
            merged[sp.code] = SalesReportRow(
                receipt_id=receipt.id or 0,
                date=receipt.date,
                time=receipt.time,
                payment_method=receipt.payment_method,
                code=sp.code,
                name=sp.product.name,
                quantity=quantity,
                unit_price=sp.unit_price,
                total=total,
                cashier=receipt.cashier,
                voided=receipt.is_voided,
            )
        rows.extend(merged.values())
    return rows


def totals_from_receipts(receipts: list[Receipt]) -> SalesTotals:
    """Totales de las ventas válidas: los recibos anulados no cuentan y las devoluciones se restan aparte."""
    completed = [r for r in receipts if not r.is_voided]
    return SalesTotals(
        total=sum((r.total for r in completed), ZERO),
        cash=sum((r.paid_with(PAYMENT_CASH) for r in completed), ZERO),
        card=sum((r.paid_with(PAYMENT_CARD) for r in completed), ZERO),
        transfer=sum((r.paid_with(PAYMENT_TRANSFER) for r in completed), ZERO),
        receipt_count=len(completed),
        returns=sum((r.returned_total for r in completed), ZERO),
        voided_count=len(receipts) - len(completed),
        tax=sum((r.tax_total for r in completed), ZERO),
    )
