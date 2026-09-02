"""Controlador principal: crea las pantallas una sola vez y decide cuál se muestra."""

from __future__ import annotations

import hmac
import logging
import tkinter as tk
from decimal import Decimal
from tkinter import messagebox, simpledialog

from controller.admin_view_controller import AdminViewController
from controller.auditlog_view_controller import AuditLogViewController
from controller.menu_controller import MenuController
from controller.product_management_view_controller import ProductManagementViewController
from controller.sales_report_view_controller import SalesReportViewController
from controller.sales_view_controller import SalesViewController
from controller.voucher_view_controller import VoucherViewController
from model.db_connection import DBConnection
from model.receipt import Receipt
from utils.config import Settings

logger = logging.getLogger(__name__)


class MainController:
    def __init__(self, root: tk.Tk, settings: Settings, db: DBConnection) -> None:
        self.root = root
        self.settings = settings
        self.db = db
        root.title(f"{settings.business.name} · Punto de venta")
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        self._build_screens()
        self.show_menu()

    def _build_screens(self) -> None:
        self.frame_menu = tk.Frame(self.root)
        self.menu_controller = MenuController(self.frame_menu, self)

        self.frame_admin = tk.Frame(self.root)
        self.admin_controller = AdminViewController(self.frame_admin, self, self.db)

        self.frame_products = tk.Frame(self.root)
        self.product_controller = ProductManagementViewController(self.frame_products, self, self.db)

        self.frame_sales = tk.Frame(self.root)
        self.sales_controller = SalesViewController(self.frame_sales, self, self.db)

        self.frame_report = tk.Frame(self.root)
        self.report_controller = SalesReportViewController(self.frame_report, self, self.db)

        self.frame_auditlog = tk.Frame(self.root)
        self.auditlog_controller = AuditLogViewController(self.frame_auditlog, self, self.db)

        self._frames = (
            self.frame_menu,
            self.frame_admin,
            self.frame_products,
            self.frame_sales,
            self.frame_report,
            self.frame_auditlog,
        )

    # ------------------------------------------------------------------ ciclo de vida
    def on_close(self) -> None:
        logger.info("Cerrando aplicación")
        self.db.close()
        self.root.destroy()

    # ------------------------------------------------------------------ navegación
    def show_menu(self) -> None:
        self._show(self.frame_menu)

    def show_admin_view(self) -> None:
        self.admin_controller.refresh()
        self._show(self.frame_admin)

    def show_product_management_view(self) -> None:
        self.product_controller.refresh_categories()
        self._show(self.frame_products)

    def show_sales_view(self) -> None:
        self._show(self.frame_sales)
        self.sales_controller.on_show()

    def show_sales_report_view(self) -> None:
        self._show(self.frame_report)

    def show_auditlog_view(self) -> None:
        self.auditlog_controller.load_today()
        self._show(self.frame_auditlog)

    def show_voucher_view(self, receipt: Receipt, received: Decimal | None, change: Decimal) -> None:
        VoucherViewController(self.root, self.settings.business, receipt, received, change)

    def request_auditlog_access(self) -> None:
        expected = self.settings.admin_password
        if not expected:
            messagebox.showerror(
                "Acceso",
                "Configure ADMIN_PASSWORD en el archivo .env para entrar a la auditoría.",
            )
            return
        typed = simpledialog.askstring("Autenticación", "Contraseña de administrador:", show="*", parent=self.root)
        if typed is None:
            return
        if hmac.compare_digest(typed.encode("utf-8"), expected.encode("utf-8")):
            self.show_auditlog_view()
        else:
            messagebox.showerror("Acceso denegado", "Contraseña incorrecta.")

    # ------------------------------------------------------------------ datos compartidos
    def refresh_all_categories(self) -> None:
        categories = self.db.get_categories()
        self.admin_controller.view.set_categories(categories)
        self.product_controller.view.set_categories(categories)

    # ------------------------------------------------------------------ interno
    def _show(self, frame: tk.Frame) -> None:
        self.sales_controller.on_hide()
        for other in self._frames:
            other.pack_forget()
        frame.pack(fill="both", expand=True)
