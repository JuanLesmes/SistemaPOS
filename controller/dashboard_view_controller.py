"""Dashboard de ventas por período, con comparación contra el período anterior."""

from __future__ import annotations

import datetime as dt
import tkinter as tk

from controller.common import guarded
from model.dashboard import build_dashboard
from model.db_connection import DBConnection
from view.dashboard_view import DashboardView

DEFAULT_PERIOD = "month"


def period_range(key: str, today: dt.date | None = None) -> tuple[dt.date, dt.date]:
    today = today or dt.date.today()
    if key == "today":
        return today, today
    if key == "week":
        return today - dt.timedelta(days=today.weekday()), today
    if key == "month":
        return today.replace(day=1), today
    if key == "last30":
        return today - dt.timedelta(days=29), today
    raise ValueError(f"Período desconocido: {key}")


def previous_range(start: dt.date, end: dt.date) -> tuple[dt.date, dt.date]:
    """El tramo de igual duración inmediatamente anterior."""
    length = (end - start).days + 1
    previous_end = start - dt.timedelta(days=1)
    return previous_end - dt.timedelta(days=length - 1), previous_end


class DashboardViewController:
    def __init__(self, parent: tk.Frame, main_controller, db: DBConnection) -> None:
        self.main_controller = main_controller
        self.db = db
        self.period = DEFAULT_PERIOD
        self.view = DashboardView(parent, self)

    @guarded
    def refresh(self) -> None:
        start, end = period_range(self.period)
        previous_start, previous_end = previous_range(start, end)
        stats = build_dashboard(
            receipts=self.db.get_receipts_in_range(start, end),
            start=start,
            end=end,
            products=self.db.get_products(),
            previous_receipts=self.db.get_receipts_in_range(previous_start, previous_end),
        )
        self.view.set_period(self.period)
        self.view.show_stats(stats)

    def event_period(self, key: str) -> None:
        self.period = key
        self.refresh()

    def event_open_inventory(self, stock_filter: str) -> None:
        self.main_controller.show_admin_view(stock_filter=stock_filter)

    def event_back_to_report(self) -> None:
        self.main_controller.show_sales_report_view()

    def event_back(self) -> None:
        self.main_controller.show_menu()
