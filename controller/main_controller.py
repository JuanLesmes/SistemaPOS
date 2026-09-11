"""Controlador principal: inicio de sesión, permisos y navegación entre pantallas."""

from __future__ import annotations

import logging
import tkinter as tk
from collections.abc import Callable
from decimal import Decimal
from tkinter import messagebox

from controller.admin_view_controller import AdminViewController
from controller.auditlog_view_controller import AuditLogViewController
from controller.backups_controller import BackupsController
from controller.dashboard_view_controller import DashboardViewController
from controller.login_controller import LoginController
from controller.menu_controller import MenuController
from controller.product_management_view_controller import ProductManagementViewController
from controller.purchases_controller import PurchasesController
from controller.sales_report_view_controller import SalesReportViewController
from controller.sales_view_controller import SalesViewController
from controller.shift_controller import ShiftController
from controller.users_controller import UsersController
from controller.voucher_view_controller import VoucherViewController
from model import permissions
from model.db_connection import DBConnection
from model.product import Product
from model.receipt import Receipt
from model.shift import Shift, ShiftSummary
from model.user import User
from utils.config import Settings, save_window_state
from utils.paths import app_dir

logger = logging.getLogger(__name__)


class MainController:
    def __init__(self, root: tk.Tk, settings: Settings, db: DBConnection) -> None:
        self.root = root
        self.settings = settings
        self.db = db
        self.current_user: User | None = None
        root.title(f"{settings.business.name} · Punto de venta")
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        self._build_screens()
        self.show_login()
        self.backups_controller.run_daily_backup_if_due()

    def _build_screens(self) -> None:
        self.frame_login = tk.Frame(self.root)
        self.login_controller = LoginController(self.frame_login, self, self.db)

        self.frame_menu = tk.Frame(self.root)
        self.menu_controller = MenuController(self.frame_menu, self)

        self.frame_admin = tk.Frame(self.root)
        self.admin_controller = AdminViewController(self.frame_admin, self, self.db)

        self.frame_products = tk.Frame(self.root)
        self.product_controller = ProductManagementViewController(self.frame_products, self, self.db)

        self.frame_shift = tk.Frame(self.root)
        self.shift_controller = ShiftController(self.frame_shift, self, self.db)

        self.frame_sales = tk.Frame(self.root)
        self.sales_controller = SalesViewController(self.frame_sales, self, self.db)

        self.frame_report = tk.Frame(self.root)
        self.report_controller = SalesReportViewController(self.frame_report, self, self.db)

        self.frame_auditlog = tk.Frame(self.root)
        self.auditlog_controller = AuditLogViewController(self.frame_auditlog, self, self.db)

        self.frame_dashboard = tk.Frame(self.root)
        self.dashboard_controller = DashboardViewController(self.frame_dashboard, self, self.db)

        self.frame_users = tk.Frame(self.root)
        self.users_controller = UsersController(self.frame_users, self, self.db)

        self.frame_purchases = tk.Frame(self.root)
        self.purchases_controller = PurchasesController(self.frame_purchases, self, self.db)

        self.frame_backups = tk.Frame(self.root)
        self.backups_controller = BackupsController(self.frame_backups, self, self.db)

        self._frames = (
            self.frame_login,
            self.frame_menu,
            self.frame_admin,
            self.frame_products,
            self.frame_shift,
            self.frame_sales,
            self.frame_report,
            self.frame_auditlog,
            self.frame_dashboard,
            self.frame_users,
            self.frame_purchases,
            self.frame_backups,
        )

    # ------------------------------------------------------------------ ciclo de vida
    def on_close(self) -> None:
        logger.info("Cerrando aplicación")
        self.sales_controller.on_hide()
        self._remember_window()
        self.db.close()
        self.root.destroy()

    def _remember_window(self) -> None:
        """Guarda si la ventana estaba maximizada y su tamaño, para abrirla igual la próxima vez."""
        try:
            maximized = self.root.state() == "zoomed"
            save_window_state(app_dir(), maximized, self.root.winfo_width(), self.root.winfo_height())
        except Exception:
            logger.warning("No se pudo guardar el estado de la ventana", exc_info=True)

    # ------------------------------------------------------------------ sesión
    def on_login(self, user: User) -> None:
        self.current_user = user
        self.db.current_user = user.username
        self.menu_controller.view.set_user(user)
        logger.info("Sesión iniciada: %s (%s)", user.username, user.role)
        self.show_menu()

    def refresh_current_user(self) -> None:
        """Vuelve a leer el usuario actual tras editarlo (por ejemplo, su nombre o rol)."""
        if self.current_user is None:
            return
        user = self.db.get_user(self.current_user.username)
        if user is not None:
            self.current_user = user
            self.menu_controller.view.set_user(user)

    def logout(self) -> None:
        if self.current_user is not None:
            logger.info("Sesión cerrada: %s", self.current_user.username)
        self.current_user = None
        self.db.current_user = None
        self.menu_controller.view.set_user(None)
        self.show_login()

    def has_permission(self, permission: str) -> bool:
        return permissions.can(self.current_user, permission)

    def _require(self, permission: str) -> bool:
        if self.current_user is None:
            self.show_login()
            return False
        if self.has_permission(permission):
            return True
        label = permissions.PERMISSION_LABELS[permission]
        messagebox.showwarning(
            "Sin permiso", f"Su usuario ({self.current_user.role_label}) no tiene acceso a: {label}."
        )
        return False

    # ------------------------------------------------------------------ navegación
    def show_login(self) -> None:
        self.login_controller.on_show()
        self._show(self.frame_login)

    def show_menu(self) -> None:
        if self.current_user is None:
            self.show_login()
            return
        self._show(self.frame_menu)

    def show_admin_view(self, stock_filter: str | None = None) -> None:
        if not self._require(permissions.INVENTORY_VIEW):
            return
        self.admin_controller.set_can_edit(self.has_permission(permissions.INVENTORY_EDIT))
        self.admin_controller.refresh()
        self.admin_controller.set_stock_filter(stock_filter)
        self._show(self.frame_admin)

    def show_product_management_view(self, product: Product | None = None) -> None:
        if not self._require(permissions.INVENTORY_EDIT):
            return
        self.product_controller.refresh_categories()
        if product is not None:
            self.product_controller.open_product(product)
        self._show(self.frame_products)

    def show_purchases_view(self) -> None:
        if not self._require(permissions.INVENTORY_EDIT):
            return
        self.purchases_controller.refresh()
        self._show(self.frame_purchases)

    def show_sales_view(self) -> None:
        if not self._require(permissions.SELL):
            return
        self._show(self.frame_sales)
        if not self.sales_controller.on_show():
            self.show_menu()

    def show_shift_view(self) -> None:
        if not self._require(permissions.SELL):
            return
        self.shift_controller.refresh()
        self._show(self.frame_shift)

    def show_sales_report_view(self) -> None:
        if not self._require(permissions.REPORTS):
            return
        self._show(self.frame_report)

    def show_dashboard_view(self) -> None:
        if not self._require(permissions.DASHBOARD):
            return
        self.dashboard_controller.refresh()
        self._show(self.frame_dashboard)

    def show_auditlog_view(self) -> None:
        if not self._require(permissions.AUDIT):
            return
        self.auditlog_controller.load_today()
        self._show(self.frame_auditlog)

    def show_users_view(self) -> None:
        if not self._require(permissions.MANAGE_USERS):
            return
        self.users_controller.refresh()
        self._show(self.frame_users)

    def show_backups_view(self) -> None:
        if not self._require(permissions.SETTINGS):
            return
        self.backups_controller.refresh()
        self._show(self.frame_backups)

    def show_voucher_view(
        self,
        receipt: Receipt,
        received: Decimal | None,
        change: Decimal,
        on_print: Callable[[], None] | None = None,
    ) -> None:
        VoucherViewController(self.root, self.settings.business, receipt, received, change, on_print)

    def print_shift_close(self, summary: ShiftSummary, shift: Shift) -> None:
        self.sales_controller.print_shift_close(summary, shift)

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
