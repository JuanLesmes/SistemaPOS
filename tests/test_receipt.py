import datetime as dt
from decimal import Decimal

import pytest

from model.product import Product
from model.receipt import PAYMENT_CARD, PAYMENT_CASH, PAYMENT_TRANSFER, Receipt
from model.report import rows_from_receipts, totals_from_receipts
from model.sold_product import SoldProduct


def make_product(code="A1", price="1000", cost="600", stock=10) -> Product:
    return Product(
        code=code, name=f"Producto {code}", cost=Decimal(cost), price=Decimal(price), stock=stock, category="General"
    )


def test_sold_product_keeps_price_at_sale_time():
    product = make_product()
    line = SoldProduct(product, 3)
    product.price = Decimal("5000")
    assert line.unit_price == Decimal("1000")
    assert line.total == Decimal("3000")


def test_sold_product_rejects_non_positive_quantity():
    with pytest.raises(ValueError):
        SoldProduct(make_product(), 0)


def test_receipt_create_sums_lines_and_has_no_id():
    lines = [SoldProduct(make_product("A"), 2), SoldProduct(make_product("B", price="250"), 4)]
    receipt = Receipt.create(PAYMENT_CASH, lines, when=dt.datetime(2026, 9, 1, 14, 30, 15, 999))
    assert receipt.id is None
    assert receipt.total == Decimal("3000")
    assert receipt.date == dt.date(2026, 9, 1)
    assert receipt.time == dt.time(14, 30, 15)


def test_receipt_create_rejects_unknown_payment_and_empty_sale():
    with pytest.raises(ValueError):
        Receipt.create("Cheque", [SoldProduct(make_product(), 1)])
    with pytest.raises(ValueError):
        Receipt.create(PAYMENT_CASH, [])


def test_report_rows_merge_repeated_product_within_receipt():
    receipt = Receipt.create(PAYMENT_CARD, [SoldProduct(make_product("A"), 1), SoldProduct(make_product("A"), 2)])
    receipt.id = 5
    rows = rows_from_receipts([receipt])
    assert len(rows) == 1
    assert rows[0].receipt_id == 5
    assert rows[0].quantity == 3
    assert rows[0].total == Decimal("3000")


def test_report_totals_split_by_payment_method():
    receipts = [
        Receipt.create(PAYMENT_CASH, [SoldProduct(make_product("A"), 1)]),
        Receipt.create(PAYMENT_CARD, [SoldProduct(make_product("B", price="2000"), 1)]),
        Receipt.create(PAYMENT_TRANSFER, [SoldProduct(make_product("C", price="500"), 2)]),
    ]
    totals = totals_from_receipts(receipts)
    assert totals.cash == Decimal("1000")
    assert totals.card == Decimal("2000")
    assert totals.transfer == Decimal("1000")
    assert totals.total == Decimal("4000")
