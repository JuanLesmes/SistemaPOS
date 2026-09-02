"""Inventario: listado de productos, filtros, indicadores y categorías."""

from __future__ import annotations

import datetime as dt
import logging
import tkinter as tk
from dataclasses import replace
from pathlib import Path
from tkinter import filedialog, messagebox

from controller.common import guarded
from model.db_connection import DBConnection
from model.inventory import LOW_STOCK_THRESHOLD, inventory_stats
from model.product import Product
from utils import excel_import
from view.admin_view import ALL_CATEGORIES, AdminView

logger = logging.getLogger(__name__)
IMPORT_REASON = "Importación desde Excel"

STOCK_FILTERS = {
    "low": ("con pocas existencias", lambda p: 0 < p.stock <= LOW_STOCK_THRESHOLD),
    "out": ("agotados", lambda p: p.stock <= 0),
}


class AdminViewController:
    def __init__(self, parent: tk.Frame, main_controller, db: DBConnection) -> None:
        self.main_controller = main_controller
        self.db = db
        self.products: list[Product] = []
        self.stock_filter: str | None = None
        self.can_edit = True
        self.view = AdminView(parent, self)
        self.refresh()

    @guarded
    def refresh(self) -> None:
        """Recarga categorías y productos; se llama cada vez que se muestra la pantalla."""
        self.products = self.db.get_products()
        self.view.set_categories(self.db.get_categories())
        self.view.set_stats(inventory_stats(self.products))
        self._apply_filters()

    def set_can_edit(self, can_edit: bool) -> None:
        self.can_edit = can_edit
        self.view.set_can_edit(can_edit)

    def set_stock_filter(self, key: str | None) -> None:
        """Muestra solo los productos con pocas existencias o agotados; None quita el filtro."""
        self.stock_filter = key if key in STOCK_FILTERS else None
        self.view.set_stock_filter(self.stock_filter)
        self._apply_filters()

    def event_back(self) -> None:
        self.main_controller.show_menu()

    def event_manage_products(self) -> None:
        self.main_controller.show_product_management_view()

    def event_open_selected(self) -> None:
        product = self.view.selected_product()
        if product is not None and self.can_edit:
            self.main_controller.show_product_management_view(product)

    def event_filter_changed(self) -> None:
        self._apply_filters()

    def event_toggle_stock_filter(self, key: str) -> None:
        """Clic en un indicador: filtra por ese estado; un segundo clic quita el filtro."""
        self.set_stock_filter(None if self.stock_filter == key else key)

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

    @guarded
    def event_export_excel(self) -> None:
        filename = filedialog.asksaveasfilename(
            title="Exportar inventario",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=f"inventario_{dt.date.today():%Y%m%d}.xlsx",
        )
        if not filename:
            return
        excel_import.write_catalog(Path(filename), self.db.get_products())
        messagebox.showinfo(
            "Inventario exportado",
            f"El archivo quedó en:\n{filename}\n\nSirve también de plantilla: edítelo y vuelva a importarlo.",
        )

    @guarded
    def event_import_excel(self) -> None:
        if not self.can_edit:
            messagebox.showwarning("Sin permiso", "Su usuario no puede modificar el inventario.")
            return
        filename = filedialog.askopenfilename(title="Importar productos", filetypes=[("Excel", "*.xlsx")])
        if not filename:
            return
        result = excel_import.read_products(Path(filename))
        if not result.ok:
            messagebox.showwarning(
                "Archivo con errores", "No se importó nada. Corrija y vuelva a intentar:\n\n" + "\n".join(result.errors)
            )
            return
        plan = [(row, self.db.get_product(row.product.code, include_inactive=True)) for row in result.rows]
        new_count = sum(1 for _row, current in plan if current is None or not current.active)
        update_count = len(plan) - new_count
        if not messagebox.askyesno(
            "Importar productos",
            f"Se crearán {new_count} productos y se actualizarán {update_count}.\n¿Continuar?",
        ):
            return
        stock_changes = 0
        for row, current in plan:
            product = row.product
            if current is None or not current.active:
                self.db.add_product(product)
                continue
            self.db.update_product(replace(product, stock=current.stock))
            if row.stock is not None and row.stock != current.stock:
                self.db.adjust_stock(product.code, row.stock - current.stock, IMPORT_REASON)
                stock_changes += 1
        logger.info("Importación Excel: %s nuevos, %s actualizados (%s)", new_count, update_count, filename)
        self.main_controller.refresh_all_categories()
        self.refresh()
        messagebox.showinfo(
            "Importación terminada",
            f"Productos creados: {new_count}\nProductos actualizados: {update_count}\n"
            f"Existencias ajustadas: {stock_changes}",
        )

    def _apply_filters(self) -> None:
        category = self.view.get_selected_category()
        term = self.view.get_search_term().lower()
        stock_ok = STOCK_FILTERS[self.stock_filter][1] if self.stock_filter else (lambda _p: True)
        filtered = [
            p
            for p in self.products
            if (category == ALL_CATEGORIES or p.category == category)
            and (not term or term in p.name.lower() or term in p.code.lower())
            and stock_ok(p)
        ]
        self.view.load_table(filtered)
        if self.stock_filter:
            self.view.set_filter_note(f"Mostrando {len(filtered)} productos {STOCK_FILTERS[self.stock_filter][0]}")
        else:
            self.view.set_filter_note("")
