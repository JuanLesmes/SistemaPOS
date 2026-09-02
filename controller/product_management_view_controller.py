"""Gestión de productos: buscar, crear, modificar, agregar existencias y desactivar."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from controller.common import guarded
from model.db_connection import DBConnection
from model.product import Product
from utils.formatters import parse_int, parse_money
from view.product_management_view import ProductManagementView


class ProductManagementViewController:
    def __init__(self, parent: tk.Frame, main_controller, db: DBConnection) -> None:
        self.main_controller = main_controller
        self.db = db
        self.view = ProductManagementView(parent, self)
        self.refresh_categories()

    # ------------------------------------------------------------------ navegación
    def event_go_back(self) -> None:
        self.main_controller.show_admin_view()

    def open_product(self, product: Product) -> None:
        """Carga un producto elegido desde otra pantalla."""
        self.fill_form(product)
        self.view.show_search_results([product])

    # ------------------------------------------------------------------ búsqueda
    @guarded
    def event_search(self) -> None:
        term = self.view.get_search_term()
        if not term:
            messagebox.showwarning("Búsqueda", "Escriba un nombre o un código para buscar.")
            return
        exact = self.db.get_product(term)
        if exact is not None:
            self.view.show_search_results([exact])
            self.fill_form(exact)
            return
        matches = self.db.search_products(term)
        self.view.show_search_results(matches)
        if not matches:
            messagebox.showinfo("Búsqueda", f"No se encontraron productos para '{term}'.")

    def event_result_selected(self, product: Product) -> None:
        self.fill_form(product)

    def event_new(self) -> None:
        self.view.clear_fields()
        self.view.focus_code()

    # ------------------------------------------------------------------ cambios
    @guarded
    def event_add_stock(self) -> None:
        code = self.view.get_code()
        if not code:
            raise ValueError("Cargue o escriba el código del producto al que desea agregar existencias.")
        quantity = parse_int(self.view.get_stock(), minimum=1)
        product = self.db.add_stock(code, quantity)
        self.fill_form(product)
        messagebox.showinfo(
            "Existencias actualizadas",
            f"Se agregaron {quantity} unidades a '{product.name}'. Ahora hay {product.stock}.",
        )

    @guarded
    def event_add_product(self) -> None:
        product = self._product_from_form()
        self.db.add_product(product)
        self._after_change()
        messagebox.showinfo("Producto agregado", f"'{product.name}' quedó registrado.")

    @guarded
    def event_modify_product(self) -> None:
        product = self._product_from_form()
        self.db.update_product(product)
        self._after_change()
        messagebox.showinfo("Producto modificado", f"'{product.name}' quedó actualizado.")

    @guarded
    def event_delete_product(self) -> None:
        code = self.view.get_code()
        if not code:
            raise ValueError("Cargue o escriba el código del producto que desea eliminar.")
        product = self.db.get_product(code)
        if product is None:
            messagebox.showinfo("Producto", f"No existe un producto activo con el código {code}.")
            return
        confirmed = messagebox.askyesno(
            "Confirmar",
            f"¿Eliminar '{product.name}' (código {code})?\n\n"
            "El producto dejará de aparecer y de venderse. "
            "Sus ventas anteriores se conservan en los reportes.",
        )
        if not confirmed:
            return
        self.db.deactivate_product(code)
        self._after_change()
        messagebox.showinfo("Producto eliminado", f"'{product.name}' ya no está disponible.")

    @guarded
    def event_delete_category(self) -> None:
        category = self.view.get_category()
        if not category:
            messagebox.showwarning("Categoría", "Seleccione la categoría que desea eliminar.")
            return
        confirmed = messagebox.askyesno(
            "Confirmar",
            f"¿Eliminar la categoría '{category}'?\n\nSolo se puede eliminar si no tiene productos asociados.",
        )
        if not confirmed:
            return
        if self.db.delete_category(category):
            messagebox.showinfo("Categoría eliminada", f"'{category}' fue eliminada.")
        else:
            messagebox.showinfo("Categoría", f"La categoría '{category}' ya no existía.")
        self.refresh_categories()
        self.main_controller.refresh_all_categories()

    # ------------------------------------------------------------------ apoyo
    def refresh_categories(self) -> None:
        self.view.set_categories(self.db.get_categories())

    def fill_form(self, product: Product) -> None:
        self.view.set_form(product)

    def _after_change(self) -> None:
        self.refresh_categories()
        self.main_controller.refresh_all_categories()
        self.view.clear_fields()
        self.view.clear_search()
        self.view.show_search_results([])

    def _product_from_form(self) -> Product:
        """Lee y valida el formulario. Lanza ValueError con un mensaje claro si algo falta."""
        code = self.view.get_code()
        name = self.view.get_name()
        if not code:
            raise ValueError("El código es obligatorio.")
        if not name:
            raise ValueError("El nombre es obligatorio.")
        category = self.view.get_category()
        if not category:
            raise ValueError("Seleccione una categoría.")
        stock_text = self.view.get_stock()
        cost_text = self.view.get_cost()
        price_text = self.view.get_price()
        return Product(
            code=code,
            name=name,
            cost=parse_money(cost_text) if cost_text else parse_money("0"),
            price=parse_money(price_text) if price_text else parse_money("0"),
            stock=parse_int(stock_text, minimum=0) if stock_text else 0,
            category=category,
            description=self.view.get_description(),
        )
