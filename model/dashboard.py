"""Indicadores del dashboard de ventas, pensados para tomar decisiones.

Todo se calcula a partir de los recibos del período (y del período anterior
para comparar) y de la lista de productos activos. Sin SQL: son funciones
puras y fáciles de probar.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from model.inventory import LOW_STOCK_THRESHOLD
from model.product import Product
from model.receipt import PAYMENT_METHODS, Receipt

TOP_PRODUCTS = 10
TOP_CATEGORIES = 6
RESTOCK_LIMIT = 10
DEAD_STOCK_LIMIT = 10
RESTOCK_DAYS = 7
ZERO = Decimal(0)
ONE = Decimal(1)

WEEKDAYS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")


@dataclass(frozen=True)
class TopProduct:
    code: str
    name: str
    units: int
    revenue: Decimal
    profit: Decimal


@dataclass(frozen=True)
class RestockItem:
    """Producto que se vende y está por agotarse."""

    code: str
    name: str
    stock: int
    units_sold: int
    days_left: Decimal | None  # None cuando no hay ritmo de venta para estimarlo


@dataclass(frozen=True)
class DeadStockItem:
    """Producto con existencias que no se vendió en el período."""

    code: str
    name: str
    stock: int
    value_at_cost: Decimal


@dataclass(frozen=True)
class PeriodSummary:
    total: Decimal = ZERO
    receipt_count: int = 0
    average_ticket: Decimal = ZERO


@dataclass(frozen=True)
class DashboardStats:
    start: dt.date
    end: dt.date
    total: Decimal = ZERO
    receipt_count: int = 0
    average_ticket: Decimal = ZERO
    units: int = 0
    profit: Decimal = ZERO
    margin_pct: Decimal = ZERO
    previous: PeriodSummary | None = None
    by_day: list[tuple[dt.date, Decimal]] = field(default_factory=list)
    by_hour: list[tuple[int, Decimal]] = field(default_factory=list)
    by_weekday: list[tuple[int, Decimal]] = field(default_factory=list)
    by_payment: list[tuple[str, Decimal]] = field(default_factory=list)
    by_category: list[tuple[str, Decimal]] = field(default_factory=list)
    top_products: list[TopProduct] = field(default_factory=list)
    top_profit: list[TopProduct] = field(default_factory=list)
    restock: list[RestockItem] = field(default_factory=list)
    dead_stock: list[DeadStockItem] = field(default_factory=list)
    dead_stock_count: int = 0
    dead_stock_value: Decimal = ZERO
    insights: list[str] = field(default_factory=list)

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1


def summarize(receipts: Sequence[Receipt]) -> PeriodSummary:
    total = sum((r.total for r in receipts), ZERO)
    count = len(receipts)
    return PeriodSummary(total=total, receipt_count=count, average_ticket=_avg(total, count))


def percent_change(current: Decimal, previous: Decimal) -> Decimal | None:
    """Variación porcentual redondeada; None cuando no hay base para comparar."""
    if previous <= 0:
        return None
    return ((current - previous) / previous * 100).quantize(ONE, rounding=ROUND_HALF_UP)


def build_dashboard(
    receipts: Sequence[Receipt],
    start: dt.date,
    end: dt.date,
    products: Sequence[Product] = (),
    previous_receipts: Sequence[Receipt] | None = None,
) -> DashboardStats:
    by_day: dict[dt.date, Decimal] = {start + dt.timedelta(days=i): ZERO for i in range((end - start).days + 1)}
    by_hour: dict[int, Decimal] = {hour: ZERO for hour in range(24)}
    by_weekday: dict[int, Decimal] = {day: ZERO for day in range(7)}
    by_payment: dict[str, Decimal] = {method: ZERO for method in PAYMENT_METHODS}
    by_category: dict[str, Decimal] = defaultdict(lambda: ZERO)
    units_by_code: dict[str, int] = defaultdict(int)
    revenue_by_code: dict[str, Decimal] = defaultdict(lambda: ZERO)
    profit_by_code: dict[str, Decimal] = defaultdict(lambda: ZERO)
    names: dict[str, str] = {}

    total = ZERO
    units = 0
    profit = ZERO
    for receipt in receipts:
        total += receipt.total
        by_day[receipt.date] = by_day.get(receipt.date, ZERO) + receipt.total
        by_hour[receipt.time.hour] += receipt.total
        by_weekday[receipt.date.weekday()] += receipt.total
        by_payment[receipt.payment_method] = by_payment.get(receipt.payment_method, ZERO) + receipt.total
        for sp in receipt.sold_products:
            line_profit = (sp.unit_price - sp.unit_cost) * sp.quantity
            units += sp.quantity
            profit += line_profit
            by_category[sp.product.category or "Sin categoría"] += sp.total
            units_by_code[sp.code] += sp.quantity
            revenue_by_code[sp.code] += sp.total
            profit_by_code[sp.code] += line_profit
            names[sp.code] = sp.product.name

    def top(code: str) -> TopProduct:
        return TopProduct(
            code=code,
            name=names[code],
            units=units_by_code[code],
            revenue=revenue_by_code[code],
            profit=profit_by_code[code],
        )

    by_units = sorted(units_by_code, key=lambda c: (-units_by_code[c], -revenue_by_code[c], names[c]))
    by_profit = sorted(profit_by_code, key=lambda c: (-profit_by_code[c], -units_by_code[c], names[c]))
    days = (end - start).days + 1
    restock, dead_stock, dead_count, dead_value = _inventory_actions(products, units_by_code, days)

    stats = DashboardStats(
        start=start,
        end=end,
        total=total,
        receipt_count=len(receipts),
        average_ticket=_avg(total, len(receipts)),
        units=units,
        profit=profit,
        margin_pct=(profit / total * 100).quantize(ONE, rounding=ROUND_HALF_UP) if total else ZERO,
        previous=summarize(previous_receipts) if previous_receipts is not None else None,
        by_day=sorted(by_day.items()),
        by_hour=sorted(by_hour.items()),
        by_weekday=sorted(by_weekday.items()),
        by_payment=sorted(by_payment.items(), key=lambda item: -item[1]),
        by_category=sorted(by_category.items(), key=lambda item: -item[1])[:TOP_CATEGORIES],
        top_products=[top(code) for code in by_units[:TOP_PRODUCTS]],
        top_profit=[top(code) for code in by_profit[:TOP_PRODUCTS] if profit_by_code[code] > 0],
        restock=restock,
        dead_stock=dead_stock,
        dead_stock_count=dead_count,
        dead_stock_value=dead_value,
    )
    return DashboardStats(**{**stats.__dict__, "insights": build_insights(stats)})


def build_insights(stats: DashboardStats) -> list[str]:
    """Frases cortas con lo más importante del período, listas para mostrar."""
    if stats.total <= 0:
        lines = ["No hay ventas registradas en el período."]
        if stats.dead_stock_count:
            lines.append(_dead_stock_sentence(stats))
        return lines

    lines: list[str] = []
    if stats.previous is not None:
        change = percent_change(stats.total, stats.previous.total)
        if change is None:
            lines.append("No hay ventas en el período anterior para comparar.")
        else:
            verb = "subieron" if change > 0 else "bajaron" if change < 0 else "se mantuvieron"
            detail = f" {abs(change)} %" if change != 0 else ""
            lines.append(
                f"Las ventas {verb}{detail} frente al período anterior "
                f"(${_money(stats.total)} contra ${_money(stats.previous.total)})."
            )

    hour, hour_total = max(stats.by_hour, key=lambda item: item[1])
    lines.append(
        f"La hora pico es de {hour:02d}:00 a {hour + 1:02d}:00, "
        f"con el {_share(hour_total, stats.total)} % de las ventas."
    )
    if stats.days >= 7:
        weekday, weekday_total = max(stats.by_weekday, key=lambda item: item[1])
        lines.append(f"El día que más se vende es el {WEEKDAYS[weekday]} ({_share(weekday_total, stats.total)} %).")
    if stats.by_category:
        category, category_total = stats.by_category[0]
        lines.append(
            f"La categoría que más vende es {category} ({_share(category_total, stats.total)} % de los ingresos)."
        )
    lines.append(
        f"El margen de utilidad promedio es {stats.margin_pct} %: por cada $100 vendidos quedan ${stats.margin_pct}."
    )
    if stats.top_profit and stats.top_products and stats.top_profit[0].code != stats.top_products[0].code:
        lines.append(
            f"El producto que más unidades vende es {stats.top_products[0].name}, "
            f"pero el que más utilidad deja es {stats.top_profit[0].name}."
        )
    if stats.restock:
        lines.append(
            f"{len(stats.restock)} productos se venden bien y están por agotarse: revise la lista de reposición."
        )
    if stats.dead_stock_count:
        lines.append(_dead_stock_sentence(stats))
    return lines


def _inventory_actions(
    products: Sequence[Product], units_by_code: dict[str, int], days: int
) -> tuple[list[RestockItem], list[DeadStockItem], int, Decimal]:
    restock: list[RestockItem] = []
    dead: list[DeadStockItem] = []
    for product in products:
        if not product.active:
            continue
        sold = units_by_code.get(product.code, 0)
        if sold > 0:
            per_day = Decimal(sold) / Decimal(days)
            days_left = (Decimal(product.stock) / per_day).quantize(ONE, rounding=ROUND_HALF_UP) if per_day else None
            if product.stock <= LOW_STOCK_THRESHOLD or (days_left is not None and days_left <= RESTOCK_DAYS):
                restock.append(RestockItem(product.code, product.name, product.stock, sold, days_left))
        elif product.stock > 0:
            dead.append(DeadStockItem(product.code, product.name, product.stock, product.cost * product.stock))

    restock.sort(key=lambda item: (item.days_left if item.days_left is not None else Decimal(10**6), item.stock))
    dead.sort(key=lambda item: -item.value_at_cost)
    dead_value = sum((item.value_at_cost for item in dead), ZERO)
    return restock[:RESTOCK_LIMIT], dead[:DEAD_STOCK_LIMIT], len(dead), dead_value


def _dead_stock_sentence(stats: DashboardStats) -> str:
    return (
        f"{stats.dead_stock_count} productos con existencias no se vendieron en el período; "
        f"tienen ${_money(stats.dead_stock_value)} inmovilizados a costo."
    )


def _avg(total: Decimal, count: int) -> Decimal:
    return (total / count).quantize(ONE, rounding=ROUND_HALF_UP) if count else ZERO


def _share(part: Decimal, total: Decimal) -> Decimal:
    return (part / total * 100).quantize(ONE, rounding=ROUND_HALF_UP) if total else ZERO


def _money(value: Decimal) -> str:
    return f"{value.quantize(ONE, rounding=ROUND_HALF_UP):,.0f}".replace(",", ".")
