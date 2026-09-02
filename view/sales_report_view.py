"""Reporte de ventas por rango de fechas."""

from __future__ import annotations

import datetime as dt

import customtkinter as ctk
from tkcalendar import DateEntry

from model.report import SalesReportRow, SalesTotals
from utils.formatters import format_price
from view import theme
from view.widgets import Card, HeaderBar, StatCard, button, fill_table, make_table, section_label

COLUMNS = (
    ("recibo", "Recibo", 80, "center", False),
    ("fecha", "Fecha", 100, "center", False),
    ("hora", "Hora", 70, "center", False),
    ("codigo", "Código", 130, "w", False),
    ("nombre", "Producto", 300, "w"),
    ("cantidad", "Cantidad", 96, "center", False),
    ("precio", "Precio", 100, "e", False),
    ("total", "Total", 110, "e", False),
    ("pago", "Pago", 120, "center", False),
)

QUICK_RANGES = (("Hoy", "today"), ("Ayer", "yesterday"), ("Esta semana", "week"), ("Este mes", "month"))


class SalesReportView(ctk.CTkFrame):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent, fg_color=theme.BACKGROUND, corner_radius=0)
        self.controller = controller
        self.pack(fill="both", expand=True)
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        header = HeaderBar(self, "Reporte de ventas", "Ventas por rango de fechas y totales por método de pago")
        header.grid(row=0, column=0, sticky="ew")
        header.add_action("Ver dashboard", self.controller.event_dashboard, kind="accent")
        header.add_action("Exportar a Excel", self.controller.event_export)
        header.add_action("Volver al menú", self.controller.event_back)

        filters = Card(self, padding=12)
        filters.grid(row=1, column=0, sticky="ew", padx=16, pady=(14, 0))
        body = filters.body
        section_label(body, "Desde").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.start_date = _date_entry(body)
        self.start_date.grid(row=0, column=1, sticky="w")
        section_label(body, "Hasta").grid(row=0, column=2, sticky="w", padx=(16, 8))
        self.end_date = _date_entry(body)
        self.end_date.grid(row=0, column=3, sticky="w")
        button(body, "Consultar", self.controller.event_search, kind="primary", size="sm", height=40, width=130).grid(
            row=0, column=4, padx=(16, 0)
        )
        quick = ctk.CTkFrame(body, fg_color="transparent")
        quick.grid(row=0, column=5, sticky="e", padx=(24, 0))
        body.grid_columnconfigure(5, weight=1)
        for label, key in QUICK_RANGES:
            button(
                quick, label, lambda k=key: self.controller.event_quick_range(k), kind="ghost", size="sm", height=40
            ).pack(side="left", padx=(6, 0))

        stats = ctk.CTkFrame(self, fg_color="transparent")
        stats.grid(row=2, column=0, sticky="ew", padx=16, pady=12)
        cards = (
            ("total", "Total recaudado", theme.PRIMARY),
            ("cash", "Efectivo", theme.ACCENT),
            ("card", "Tarjeta", theme.HEADER),
            ("transfer", "Transferencia", theme.SUCCESS),
            ("count", "Recibos", theme.MUTED),
        )
        self.stat_cards: dict[str, StatCard] = {}
        for index, (key, label, accent) in enumerate(cards):
            stats.grid_columnconfigure(index, weight=1, uniform="stats")
            card = StatCard(stats, label, "$0" if key != "count" else "0", accent=accent)
            card.grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 10, 0))
            self.stat_cards[key] = card

        table_card = Card(self, padding=10)
        table_card.grid(row=3, column=0, sticky="nsew", padx=16, pady=(0, 16))
        table_box = ctk.CTkFrame(table_card.body, fg_color="transparent")
        table_box.pack(fill="both", expand=True)
        self.tree = make_table(table_box, COLUMNS, "SalesReport")

    # ------------------------------------------------------------------ API para el controlador
    def load_table(self, rows: list[SalesReportRow]) -> None:
        fill_table(
            self.tree,
            (
                (
                    row.receipt_id,
                    row.date.strftime("%Y-%m-%d"),
                    row.time.strftime("%H:%M"),
                    row.code,
                    row.name,
                    row.quantity,
                    format_price(row.unit_price),
                    format_price(row.total),
                    row.payment_method,
                )
                for row in rows
            ),
            empty_message="Consulte un rango de fechas para ver las ventas",
        )

    def set_totals(self, totals: SalesTotals) -> None:
        self.stat_cards["total"].set_value(f"${format_price(totals.total)}")
        self.stat_cards["cash"].set_value(f"${format_price(totals.cash)}")
        self.stat_cards["card"].set_value(f"${format_price(totals.card)}")
        self.stat_cards["transfer"].set_value(f"${format_price(totals.transfer)}")
        self.stat_cards["count"].set_value(str(totals.receipt_count))

    def get_start_date(self) -> dt.date:
        return self.start_date.get_date()

    def get_end_date(self) -> dt.date:
        return self.end_date.get_date()

    def set_dates(self, start: dt.date, end: dt.date) -> None:
        self.start_date.set_date(start)
        self.end_date.set_date(end)


def _date_entry(parent) -> DateEntry:
    return DateEntry(
        parent,
        width=12,
        font=theme.font(13),
        background=theme.PRIMARY,
        foreground=theme.ON_DARK,
        headersbackground=theme.SURFACE_ALT,
        normalbackground=theme.SURFACE,
        weekendbackground=theme.SURFACE,
        selectbackground=theme.PRIMARY,
        borderwidth=1,
        date_pattern="yyyy-mm-dd",
        locale="es_CO",
    )
