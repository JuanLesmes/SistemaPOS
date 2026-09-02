import datetime as dt
from decimal import Decimal

import pytest

from controller.dashboard_view_controller import period_range, previous_range
from model.dashboard import build_dashboard, percent_change
from model.product import Product
from model.receipt import PAYMENT_CARD, PAYMENT_CASH, Receipt
from model.sold_product import SoldProduct


def make_product(code: str, price: str, cost: str, stock: int = 10, category: str = "Bebidas") -> Product:
    return Product(
        code=code, name=f"Producto {code}", cost=Decimal(cost), price=Decimal(price), stock=stock, category=category
    )


def make_receipt(day: dt.date, method: str, lines: list[SoldProduct], hour: int = 10) -> Receipt:
    return Receipt.create(method, lines, when=dt.datetime.combine(day, dt.time(hour)))


GASEOSA = make_product("A", "3000", "2000", stock=2)
PAN = make_product("B", "500", "300", stock=40, category="Panadería")
QUIETO = make_product("C", "10000", "7000", stock=5, category="Aseo")
AGOTADO = make_product("D", "1000", "800", stock=0)

START, END = dt.date(2026, 8, 31), dt.date(2026, 9, 6)  # lunes a domingo


def build():
    receipts = [
        make_receipt(dt.date(2026, 8, 31), PAYMENT_CASH, [SoldProduct(GASEOSA, 2), SoldProduct(PAN, 4)], hour=18),
        make_receipt(dt.date(2026, 9, 5), PAYMENT_CARD, [SoldProduct(GASEOSA, 1)], hour=18),
        make_receipt(dt.date(2026, 9, 5), PAYMENT_CASH, [SoldProduct(PAN, 2)], hour=9),
    ]
    previous = [make_receipt(dt.date(2026, 8, 25), PAYMENT_CASH, [SoldProduct(GASEOSA, 2)])]
    return build_dashboard(receipts, START, END, products=[GASEOSA, PAN, QUIETO, AGOTADO], previous_receipts=previous)


def test_totals_margin_and_comparison():
    stats = build()
    assert stats.total == Decimal(12000)
    assert stats.receipt_count == 3
    assert stats.average_ticket == Decimal(4000)
    assert stats.units == 9
    assert stats.profit == Decimal(2000 + 800 + 1000 + 400)
    assert stats.margin_pct == Decimal(35)
    assert stats.previous.total == Decimal(6000)
    assert percent_change(stats.total, stats.previous.total) == Decimal(100)


def test_when_sales_happen():
    stats = build()
    assert dict(stats.by_hour)[18] == Decimal(11000)
    assert dict(stats.by_hour)[9] == Decimal(1000)
    assert dict(stats.by_weekday)[5] == Decimal(4000)  # sábado
    assert dict(stats.by_weekday)[0] == Decimal(8000)  # lunes
    assert len(stats.by_day) == 7


def test_what_sells_and_what_earns():
    stats = build()
    assert [(p.code, p.units) for p in stats.top_products] == [("B", 6), ("A", 3)]
    assert [(p.code, p.profit) for p in stats.top_profit] == [("A", Decimal(3000)), ("B", Decimal(1200))]
    assert stats.by_category[0] == ("Bebidas", Decimal(9000))


def test_inventory_actions():
    stats = build()
    restock = {item.code: item for item in stats.restock}
    assert "A" in restock and restock["A"].stock == 2 and restock["A"].units_sold == 3
    assert restock["A"].days_left == Decimal(5)  # 2 unidades / (3 vendidas en 7 días)
    assert "B" not in restock  # 40 unidades para 6 vendidas por semana: no es urgente
    assert [item.code for item in stats.dead_stock] == ["C"]
    assert stats.dead_stock_value == Decimal(35000)
    assert stats.dead_stock_count == 1  # el agotado no cuenta: no hay dinero parado


def test_insights_are_readable_sentences():
    insights = build().insights
    assert any("subieron 100 %" in line for line in insights)
    assert any("18:00 a 19:00" in line for line in insights)
    assert any("lunes" in line for line in insights)
    assert any("Bebidas" in line for line in insights)
    assert any("margen" in line.lower() for line in insights)
    assert any("por agotarse" in line for line in insights)
    assert any("inmovilizados" in line for line in insights)


def test_dashboard_with_no_sales():
    stats = build_dashboard([], START, END, products=[QUIETO], previous_receipts=[])
    assert stats.total == Decimal(0)
    assert stats.insights[0] == "No hay ventas registradas en el período."
    assert stats.dead_stock_count == 1
    assert len(stats.by_day) == 7


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("today", (dt.date(2026, 9, 2), dt.date(2026, 9, 2))),
        ("week", (dt.date(2026, 8, 31), dt.date(2026, 9, 2))),
        ("month", (dt.date(2026, 9, 1), dt.date(2026, 9, 2))),
        ("last30", (dt.date(2026, 8, 4), dt.date(2026, 9, 2))),
    ],
)
def test_period_ranges(key, expected):
    assert period_range(key, today=dt.date(2026, 9, 2)) == expected


def test_previous_range_has_same_length():
    assert previous_range(dt.date(2026, 9, 1), dt.date(2026, 9, 7)) == (dt.date(2026, 8, 25), dt.date(2026, 8, 31))
    assert previous_range(dt.date(2026, 9, 2), dt.date(2026, 9, 2)) == (dt.date(2026, 9, 1), dt.date(2026, 9, 1))


def test_unknown_period_is_rejected():
    with pytest.raises(ValueError):
        period_range("año", today=dt.date(2026, 9, 2))


def test_percent_change_without_base():
    assert percent_change(Decimal(10), Decimal(0)) is None
    assert percent_change(Decimal(50), Decimal(100)) == Decimal(-50)
