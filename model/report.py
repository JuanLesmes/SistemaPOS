"""Estructuras del reporte de ventas, derivadas de los recibos."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

from model.receipt import PAYMENT_CARD, PAYMENT_CASH, PAYMENT_TRANSFER, Receipt


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


@dataclass(frozen=True)
class SalesTotals:
    total: Decimal
    cash: Decimal
    card: Decimal
    transfer: Decimal
    receipt_count: int = 0


def rows_from_receipts(receipts: list[Receipt]) -> list[SalesReportRow]:
    """Una fila por producto y recibo; líneas repetidas del mismo producto se suman."""
    rows: list[SalesReportRow] = []
    for receipt in receipts:
        merged: dict[str, SalesReportRow] = {}
        for sp in receipt.sold_products:
            previous = merged.get(sp.code)
            quantity = sp.quantity + (previous.quantity if previous else 0)
            merged[sp.code] = SalesReportRow(
                receipt_id=receipt.id or 0,
                date=receipt.date,
                time=receipt.time,
                payment_method=receipt.payment_method,
                code=sp.code,
                name=sp.product.name,
                quantity=quantity,
                unit_price=sp.unit_price,
                total=sp.unit_price * quantity,
            )
        rows.extend(merged.values())
    return rows


def totals_from_receipts(receipts: list[Receipt]) -> SalesTotals:
    by_method: dict[str, Decimal] = {}
    for receipt in receipts:
        by_method[receipt.payment_method] = by_method.get(receipt.payment_method, Decimal(0)) + receipt.total
    return SalesTotals(
        total=sum(by_method.values(), Decimal(0)),
        cash=by_method.get(PAYMENT_CASH, Decimal(0)),
        card=by_method.get(PAYMENT_CARD, Decimal(0)),
        transfer=by_method.get(PAYMENT_TRANSFER, Decimal(0)),
        receipt_count=len(receipts),
    )
