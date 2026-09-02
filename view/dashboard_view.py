"""Dashboard de ventas: hallazgos, indicadores, cuándo y qué se vende, y acciones de inventario."""

from __future__ import annotations

from decimal import Decimal

import customtkinter as ctk

from model.dashboard import DashboardStats, percent_change
from model.receipt import PAYMENT_CARD, PAYMENT_CASH, PAYMENT_TRANSFER
from utils.formatters import format_price
from view import theme
from view.charts import BarChart, HorizontalBars
from view.widgets import Card, HeaderBar, StatCard, button, fill_table, make_table

PERIODS = (("today", "Hoy"), ("week", "Esta semana"), ("month", "Este mes"), ("last30", "Últimos 30 días"))
MONTHS_SHORT = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")
MONTHS_LONG = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)
WEEKDAYS_SHORT = ("Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom")
PAYMENT_COLORS = {PAYMENT_CASH: theme.ACCENT, PAYMENT_CARD: theme.HEADER, PAYMENT_TRANSFER: theme.SUCCESS}
CHART_HEIGHT = 250

TOP_COLUMNS = (
    ("rank", "#", 36, "center", False),
    ("name", "Producto", 200, "w"),
    ("units", "Unid.", 70, "center", False),
    ("revenue", "Ingresos", 100, "e", False),
)
PROFIT_COLUMNS = (
    ("rank", "#", 36, "center", False),
    ("name", "Producto", 200, "w"),
    ("profit", "Utilidad", 100, "e", False),
    ("margin", "Margen", 80, "e", False),
)
RESTOCK_COLUMNS = (
    ("name", "Producto", 260, "w"),
    ("stock", "Quedan", 80, "center", False),
    ("sold", "Vendidos", 90, "center", False),
    ("days", "Se agota en", 120, "center", False),
)
DEAD_COLUMNS = (
    ("name", "Producto", 200, "w"),
    ("stock", "Stock", 70, "center", False),
    ("value", "Costo parado", 120, "e", False),
)


class DashboardView(ctk.CTkFrame):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent, fg_color=theme.BACKGROUND, corner_radius=0)
        self.controller = controller
        self._period_buttons: dict[str, ctk.CTkButton] = {}
        self._insight_labels: list[ctk.CTkLabel] = []
        self.pack(fill="both", expand=True)
        self._build()

    # ------------------------------------------------------------------ construcción
    def _build(self) -> None:
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.header = HeaderBar(self, "Dashboard de ventas", "")
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.add_action("Volver al reporte", self.controller.event_back_to_report)
        self.header.add_action("Volver al menú", self.controller.event_back)

        filters = Card(self, padding=10)
        filters.grid(row=1, column=0, sticky="ew", padx=16, pady=(12, 0))
        for key, label in PERIODS:
            widget = button(
                filters.body, label, lambda k=key: self.controller.event_period(k), kind="ghost", size="sm", height=38
            )
            widget.pack(side="left", padx=(0, 6))
            self._period_buttons[key] = widget
        self.range_label = ctk.CTkLabel(filters.body, text="", font=theme.font(12), text_color=theme.MUTED)
        self.range_label.pack(side="right")

        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent", scrollbar_button_color=theme.BORDER)
        self.body.grid(row=2, column=0, sticky="nsew", padx=8, pady=(6, 8))
        body = self.body
        for column in range(3):
            body.grid_columnconfigure(column, weight=1, uniform="cols")

        # Fila 0: hallazgos
        insights = Card(body, "Hallazgos del período", padding=12)
        insights.grid(row=0, column=0, columnspan=3, sticky="ew", padx=8, pady=(4, 8))
        self.insights_box = insights.body

        # Fila 1: indicadores con comparación
        kpis = ctk.CTkFrame(body, fg_color="transparent")
        kpis.grid(row=1, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        cards = (
            ("total", "Ventas del período", theme.PRIMARY),
            ("receipts", "Recibos", theme.HEADER),
            ("ticket", "Ticket promedio", theme.HEADER),
            ("profit", "Utilidad estimada", theme.SUCCESS),
            ("units", "Unidades vendidas", theme.MUTED),
        )
        self.kpi_cards: dict[str, StatCard] = {}
        for index, (key, label, accent) in enumerate(cards):
            kpis.grid_columnconfigure(index, weight=1, uniform="kpis")
            card = StatCard(kpis, label, "", accent=accent)
            card.grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 10, 0))
            card.set_note("")
            self.kpi_cards[key] = card

        # Fila 2: cuándo se vende
        self.hour_chart = BarChart(body, "Ventas por hora del día", height=CHART_HEIGHT)
        self.hour_chart.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=8, pady=(0, 8))
        self.weekday_chart = BarChart(body, "Ventas por día de la semana", height=CHART_HEIGHT)
        self.weekday_chart.grid(row=2, column=2, sticky="nsew", padx=8, pady=(0, 8))

        # Fila 3: evolución y pagos
        self.daily_chart = BarChart(body, "Ventas por día", height=CHART_HEIGHT)
        self.daily_chart.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=8, pady=(0, 8))
        self.payment_bars = HorizontalBars(
            body, "Métodos de pago", colors=lambda label: PAYMENT_COLORS.get(label, theme.PRIMARY)
        )
        self.payment_bars.grid(row=3, column=2, sticky="nsew", padx=8, pady=(0, 8))

        # Fila 4: qué se vende
        top = Card(body, "Más vendidos (unidades)", padding=10)
        top.grid(row=4, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.top_tree = make_table(_box(top), TOP_COLUMNS, "TopProducts", height=8)

        self.category_bars = HorizontalBars(body, "Ventas por categoría")
        self.category_bars.grid(row=4, column=1, sticky="nsew", padx=8, pady=(0, 8))

        profit = Card(body, "Más rentables (utilidad)", padding=10)
        profit.grid(row=4, column=2, sticky="nsew", padx=8, pady=(0, 8))
        self.profit_tree = make_table(_box(profit), PROFIT_COLUMNS, "TopProfit", height=8)

        # Fila 5: qué hacer con el inventario
        restock = Card(body, "Reposición urgente: se venden y están por agotarse", padding=10)
        restock.grid(row=5, column=0, columnspan=2, sticky="nsew", padx=8, pady=(0, 8))
        button(
            restock.title_row,
            "Ver agotados",
            lambda: self.controller.event_open_inventory("out"),
            kind="danger-soft",
            size="sm",
        ).pack(side="right")
        button(
            restock.title_row,
            "Ver pocas existencias",
            lambda: self.controller.event_open_inventory("low"),
            kind="ghost",
            size="sm",
        ).pack(side="right", padx=(0, 6))
        self.restock_tree = make_table(_box(restock), RESTOCK_COLUMNS, "Restock", height=8)

        dead = Card(body, "Sin movimiento en el período", padding=10)
        dead.grid(row=5, column=2, sticky="nsew", padx=8, pady=(0, 8))
        self.dead_note = ctk.CTkLabel(dead.title_row, text="", font=theme.font(12), text_color=theme.MUTED)
        self.dead_note.pack(side="right")
        self.dead_tree = make_table(_box(dead), DEAD_COLUMNS, "DeadStock", height=8)

    # ------------------------------------------------------------------ API para el controlador
    def set_period(self, key: str) -> None:
        for name, widget in self._period_buttons.items():
            active = name == key
            widget.configure(
                fg_color=theme.PRIMARY if active else theme.SURFACE_ALT,
                hover_color=theme.PRIMARY_HOVER if active else theme.SURFACE_HOVER,
                text_color=theme.ON_DARK if active else theme.TEXT,
            )

    def show_stats(self, stats: DashboardStats) -> None:
        range_text = (
            _long_date(stats.start)
            if stats.start == stats.end
            else f"Del {_long_date(stats.start)} al {_long_date(stats.end)}"
        )
        self.range_label.configure(text=range_text)
        self.header.set_subtitle(range_text)

        self._show_insights(stats.insights)
        self._show_kpis(stats)

        self.hour_chart.set_data([f"{hour:02d}" for hour, _ in stats.by_hour], [value for _, value in stats.by_hour])
        self.weekday_chart.set_data(
            [WEEKDAYS_SHORT[day] for day, _ in stats.by_weekday], [value for _, value in stats.by_weekday]
        )
        day_labels = [
            f"{day.day} {MONTHS_SHORT[day.month - 1]}" if len(stats.by_day) <= 14 else str(day.day)
            for day, _ in stats.by_day
        ]
        self.daily_chart.set_data(day_labels, [value for _, value in stats.by_day])
        self.payment_bars.set_data(stats.by_payment)
        self.category_bars.set_data(stats.by_category)

        fill_table(
            self.top_tree,
            ((i, item.name, item.units, format_price(item.revenue)) for i, item in enumerate(stats.top_products, 1)),
            empty_message="Sin ventas en el período",
        )
        fill_table(
            self.profit_tree,
            (
                (i, item.name, format_price(item.profit), f"{_margin(item.profit, item.revenue)} %")
                for i, item in enumerate(stats.top_profit, 1)
            ),
            empty_message="Sin ventas en el período",
        )
        fill_table(
            self.restock_tree,
            ((item.name, item.stock, item.units_sold, _days_text(item.days_left)) for item in stats.restock),
            extra_tags=lambda row: ("out",) if row[1] == 0 else ("low",) if row[1] <= 3 else (),
            empty_message="Nada urgente: ningún producto vendido está por agotarse",
        )
        fill_table(
            self.dead_tree,
            ((item.name, item.stock, format_price(item.value_at_cost)) for item in stats.dead_stock),
            empty_message="Todo el inventario tuvo ventas",
        )
        self.dead_note.configure(
            text=f"{stats.dead_stock_count} productos · ${format_price(stats.dead_stock_value)} a costo"
            if stats.dead_stock_count
            else ""
        )

    # ------------------------------------------------------------------ interno
    def _show_insights(self, insights: list[str]) -> None:
        for label in self._insight_labels:
            label.destroy()
        self._insight_labels = []
        for text in insights:
            label = ctk.CTkLabel(
                self.insights_box,
                text=f"•  {text}",
                font=theme.font(13),
                text_color=theme.TEXT,
                anchor="w",
                justify="left",
                wraplength=1380,
            )
            label.pack(anchor="w", pady=1)
            self._insight_labels.append(label)

    def _show_kpis(self, stats: DashboardStats) -> None:
        self.kpi_cards["total"].set_value(f"${format_price(stats.total)}")
        self.kpi_cards["receipts"].set_value(str(stats.receipt_count))
        self.kpi_cards["ticket"].set_value(f"${format_price(stats.average_ticket)}")
        self.kpi_cards["profit"].set_value(f"${format_price(stats.profit)}")
        self.kpi_cards["units"].set_value(str(stats.units))
        self.kpi_cards["profit"].set_note(f"Margen {stats.margin_pct} %" if stats.total else "", theme.MUTED)
        per_receipt = (
            f"{Decimal(stats.units) / stats.receipt_count:.1f}".replace(".", ",") if stats.receipt_count else ""
        )
        self.kpi_cards["units"].set_note(f"{per_receipt} por recibo" if per_receipt else "", theme.MUTED)

        previous = stats.previous
        if previous is None:
            for key in ("total", "receipts", "ticket"):
                self.kpi_cards[key].set_note("", theme.MUTED)
            return
        for key, current, before in (
            ("total", stats.total, previous.total),
            ("receipts", Decimal(stats.receipt_count), Decimal(previous.receipt_count)),
            ("ticket", stats.average_ticket, previous.average_ticket),
        ):
            change = percent_change(current, before)
            if change is None:
                self.kpi_cards[key].set_note("Sin período anterior", theme.MUTED)
            elif change > 0:
                self.kpi_cards[key].set_note(f"▲ {change} % vs anterior", theme.SUCCESS)
            elif change < 0:
                self.kpi_cards[key].set_note(f"▼ {abs(change)} % vs anterior", theme.DANGER)
            else:
                self.kpi_cards[key].set_note("Igual que el período anterior", theme.MUTED)


def _box(card: Card) -> ctk.CTkFrame:
    box = ctk.CTkFrame(card.body, fg_color="transparent")
    box.pack(fill="both", expand=True)
    return box


def _margin(profit: Decimal, revenue: Decimal) -> Decimal:
    return (profit / revenue * 100).quantize(Decimal(1)) if revenue else Decimal(0)


def _days_text(days_left: Decimal | None) -> str:
    if days_left is None:
        return "-"
    if days_left <= 0:
        return "Ya agotado"
    if days_left == 1:
        return "1 día"
    return f"{days_left} días"


def _long_date(day) -> str:
    return f"{day.day} de {MONTHS_LONG[day.month - 1]} de {day.year}"
