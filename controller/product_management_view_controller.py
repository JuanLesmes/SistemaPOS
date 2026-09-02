"""Gestión de productos: buscar, crear, modificar, agregar existencias y desactivar."""

from __future__ import annotations

import tkinter as tk
from decimal import Decimal
from tkinter import messagebox

from controller.common import guarded
from model.db_connection import DBConnection
from model.product import DEFAULT_MIN_STOCK, Product
from utils.formatters import format_price, parse_int, parse_money
from view.dialogs import TableDialog, ask_form
from view.product_management_view import ProductManagementView

KARDEX_COLUMNS = (
    ("date", "Fecha y hora", 150, "w", False),
    ("kind", "Tipo", 110, "w", False),
    ("quantity", "Cantidad", 90, "center", False),
    ("after", "Quedaron", 90, "center", False),
    ("reference", "Referencia", 170, "w"),
    ("reason", "Motivo", 200, "w"),
    ("user", "Usuario", 100, "w", False),
)


class ProductManagementViewController:
    def __init__(self, parent: tk.Frame, main_controller, db: DBConnection) -> None:
        self.main_controller = main_controller
        self.db = db
        self.view = ProductManagementView(parent, self)
        self.ask_form = ask_form  # reemplazable en pruebas
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
    def event_adjust_stock(self) -> None:
        code = self.view.get_code()
        if not code:
            raise ValueError("Cargue o escriba el código del producto que desea ajustar.")
        product = self.db.get_product(code)
        if product is None:
            messagebox.showinfo("Producto", f"No existe un producto activo con el código {code}.")
            return
        data = self.ask_form(
            self.view,
            f"Ajustar existencias de {product.name}",
            [("quantity", "Cantidad (use signo menos para retirar, ej. -2)", ""), ("reason", "Motivo", "")],
            intro=f"Existencias actuales: {product.stock}",
            submit_text="Ajustar",
        )
        if data is None:
            return
        try:
            quantity = int(data["quantity"].strip().replace(".", ""))
        except ValueError as exc:
            raise ValueError("La cantidad debe ser un número entero, por ejemplo 12 o -3.") from exc
        reason = data["reason"].strip()
        if not reason:
            raise ValueError("Escriba el motivo del ajuste (pedido, conteo, daño, vencido...).")
        updated = self.db.adjust_stock(code, quantity, reason)
        self.fill_form(updated)
        verb = "Se agregaron" if quantity > 0 else "Se retiraron"
        messagebox.showinfo(
            "Existencias actualizadas",
            f"{verb} {abs(quantity)} unidades de '{updated.name}'. Ahora hay {updated.stock}.",
        )

    @guarded
    def event_kardex(self) -> None:
        code = self.view.get_code()
        if not code:
            raise ValueError("Cargue un producto para ver su kárdex.")
        product = self.db.get_product(code)
        if product is None:
            messagebox.showinfo("Producto", f"No existe un producto activo con el código {code}.")
            return
        movements = self.db.get_stock_movements(code)
        rows = [
            (
                m.created_at.strftime("%Y-%m-%d %H:%M"),
                m.kind_label,
                f"{m.quantity:+d}",
                m.stock_after,
                m.reference,
                m.reason,
                m.user or "",
            )
            for m in movements
        ]
        TableDialog(
            self.view,
            f"Kárdex de {product.name}",
            KARDEX_COLUMNS,
            rows,
            subtitle=(
                f"Existencias actuales: {product.stock}  ·  Costo: ${format_price(product.cost)}"
                f"  ·  {len(rows)} movimientos"
            ),
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
        min_stock_text = self.view.get_min_stock()
        return Product(
            code=code,
            name=name,
            cost=parse_money(cost_text) if cost_text else parse_money("0"),
            price=parse_money(price_text) if price_text else parse_money("0"),
            stock=parse_int(stock_text, minimum=0) if stock_text else 0,
            category=category,
            description=self.view.get_description(),
            min_stock=parse_int(min_stock_text, minimum=0) if min_stock_text else DEFAULT_MIN_STOCK,
            tax_rate=Decimal(self.view.get_tax_rate() or "0"),
        )
