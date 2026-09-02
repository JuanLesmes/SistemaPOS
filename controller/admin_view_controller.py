"""Control de inventario: listado de productos, filtro por categoría y valorización."""

from __future__ import annotations

import tkinter as tk
from decimal import Decimal
from tkinter import messagebox

from controller.common import guarded
from model.db_connection import DBConnection
from model.product import Product
from view.admin_view import AdminView

ALL_CATEGORIES = "Todas"


class AdminViewController:
    def __init__(self, parent: tk.Frame, main_controller, db: DBConnection) -> None:
        self.main_controller = main_controller
        self.db = db
        self.view = AdminView(parent, self)
        self.refresh()

    @guarded
    def refresh(self) -> None:
        """Recarga categorías y productos; se llama cada vez que se muestra la pantalla."""
        self.view.set_categories(self.db.get_categories())
        self._load_products(None)

    def event_back(self) -> None:
        self.main_controller.show_menu()

    @guarded
    def event_filter(self) -> None:
        category = self.view.get_selected_category()
        self._load_products(None if category == ALL_CATEGORIES else category)

    @guarded
    def event_add_category(self) -> None:
        name = self.view.get_new_category()
        if not name:
            raise ValueError("Escriba el nombre de la nueva categoría.")
        if not self.db.add_category(name):
            messagebox.showwarning("Categoría", f"La categoría '{name}' ya existe.")
            return
        self.view.clear_new_category()
        self.main_controller.refresh_all_categories()
        messagebox.showinfo("Categoría agregada", f"'{name}' quedó registrada.")

    def event_manage_products(self) -> None:
        self.main_controller.show_product_management_view()

    def _load_products(self, category: str | None) -> None:
        products = self.db.get_products(category)
        self.view.load_table(products)
        self.view.set_inventory_value(inventory_value(products))


def inventory_value(products: list[Product]) -> Decimal:
    """Valor del inventario a precio de venta."""
    return sum((p.price * p.stock for p in products), Decimal(0))
