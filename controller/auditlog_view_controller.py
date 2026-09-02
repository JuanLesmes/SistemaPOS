"""Registro de auditoría: cambios del catálogo por día."""

from __future__ import annotations

import datetime as dt
import tkinter as tk

from controller.common import guarded
from model.db_connection import DBConnection
from view.auditlog_view import AuditLogView


class AuditLogViewController:
    def __init__(self, parent: tk.Frame, main_controller, db: DBConnection) -> None:
        self.main_controller = main_controller
        self.db = db
        self.view = AuditLogView(parent, self)

    def load_today(self) -> None:
        today = dt.date.today()
        self.view.set_date(today)
        self.event_load_logs(today)

    @guarded
    def event_load_logs(self, day: dt.date) -> None:
        self.view.show_logs(self.db.get_logs_by_date(day))

    def event_back(self) -> None:
        self.main_controller.show_menu()
