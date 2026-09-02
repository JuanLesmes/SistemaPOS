"""Menú principal."""

from __future__ import annotations

import tkinter as tk

from view.menu_view import MenuView


class MenuController:
    def __init__(self, parent: tk.Frame, main_controller) -> None:
        self.main_controller = main_controller
        self.view = MenuView(parent, self, business=main_controller.settings.business)

    def event_go_sales(self) -> None:
        self.main_controller.show_sales_view()

    def event_go_inventory(self) -> None:
        self.main_controller.show_admin_view()

    def event_go_purchases(self) -> None:
        self.main_controller.show_purchases_view()

    def event_go_dashboard(self) -> None:
        self.main_controller.show_dashboard_view()

    def event_go_report(self) -> None:
        self.main_controller.show_sales_report_view()

    def event_go_shift(self) -> None:
        self.main_controller.show_shift_view()

    def event_go_users(self) -> None:
        self.main_controller.show_users_view()

    def event_go_auditlog(self) -> None:
        self.main_controller.show_auditlog_view()

    def event_go_backups(self) -> None:
        self.main_controller.show_backups_view()

    def event_logout(self) -> None:
        self.main_controller.logout()

    def event_exit(self) -> None:
        self.main_controller.on_close()
