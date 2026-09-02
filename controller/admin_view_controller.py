"""Inventario: listado de productos, filtros, indicadores y categorías."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from controller.common import guarded
from model.db_connection import DBConnection
from model.inventory import inventory_stats
from model.product import Product
from view.admin_view import ALL_CATEGORIES, AdminView


class AdminViewController:
    def __init__(self, parent: tk.Frame, main_controller, db: DBConnection) -> None:
        self.main_controller = main_controller
        self.db = db
        self.products: list[Product] = []
        self.view = AdminView(parent, self)
        self.refresh()

    @guarded
    def refresh(self) -> None:
        """Recarga categorías y productos; se llama cada vez que se muestra la pantalla."""
        self.products = self.db.get_products()
        self.view.set_categories(self.db.get_categories())
        self.view.set_stats(inventory_stats(self.products))
        self._apply_filters()

    def event_back(self) -> None:
        self.main_controller.show_menu()

    def event_manage_products(self) -> None:
        self.main_controller.show_product_management_view()

    def event_open_selected(self) -> None:
        product = self.view.selected_product()
        if product is not None:
            self.main_controller.show_product_management_view(product)

    def event_filter_changed(self) -> None:
        self._apply_filters()

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

    def _apply_filters(self) -> None:
        category = self.view.get_selected_category()
        term = self.view.get_search_term().lower()
        filtered = [
            p
            for p in self.products
            if (category == ALL_CATEGORIES or p.category == category)
            and (not term or term in p.name.lower() or term in p.code.lower())
        ]
        self.view.load_table(filtered)
