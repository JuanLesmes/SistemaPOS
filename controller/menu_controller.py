"""Menú principal."""

from __future__ import annotations

import tkinter as tk

from view.menu_view import MenuView


class MenuController:
    def __init__(self, parent: tk.Frame, main_controller) -> None:
        self.main_controller = main_controller
        self.view = MenuView(parent, self, business_name=main_controller.settings.business.name)

    def event_go_sales(self) -> None:
        self.main_controller.show_sales_view()

    def event_go_inventory(self) -> None:
        self.main_controller.show_admin_view()

    def event_go_report(self) -> None:
        self.main_controller.show_sales_report_view()

    def event_go_auditlog(self) -> None:
        self.main_controller.request_auditlog_access()

    def event_exit(self) -> None:
        self.main_controller.on_close()
