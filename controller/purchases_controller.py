"""Compras a proveedores."""

from __future__ import annotations

import datetime as dt
import tkinter as tk
from tkinter import messagebox

from controller.common import guarded
from model.db_connection import DBConnection
from model.purchase import Purchase, PurchaseItem
from model.supplier import Supplier
from utils.formatters import format_money_input, format_price, parse_int, parse_money
from view.dialogs import ask_form
from view.purchases_view import PurchasesView

HISTORY_DAYS = 90


class PurchasesController:
    def __init__(self, parent: tk.Frame, main_controller, db: DBConnection) -> None:
        self.main_controller = main_controller
        self.db = db
        self.items: list[PurchaseItem] = []
        self.view = PurchasesView(parent, self)
        self.ask_form = ask_form  # reemplazable en pruebas

    @guarded
    def refresh(self) -> None:
        self.view.set_suppliers(self.db.list_suppliers())
        today = dt.date.today()
        self.view.show_history(self.db.list_purchases(today - dt.timedelta(days=HISTORY_DAYS), today))
        self.view.show_items(self.items)

    def event_back(self) -> None:
        self.main_controller.show_menu()

    @guarded
    def event_new_supplier(self) -> None:
        data = self.ask_form(
            self.view,
            "Nuevo proveedor",
            [("name", "Nombre", ""), ("nit", "NIT", ""), ("phone", "Teléfono", ""), ("email", "Correo", "")],
            submit_text="Guardar",
        )
        if data is None:
            return
        supplier = self.db.save_supplier(
            Supplier(id=None, name=data["name"], nit=data["nit"], phone=data["phone"], email=data["email"])
        )
        self.view.set_suppliers(self.db.list_suppliers(), select=supplier.name)
        messagebox.showinfo("Proveedor creado", f"'{supplier.name}' quedó registrado.")

    @guarded
    def event_search(self) -> None:
        term = self.view.get_search_term()
        if not term:
            return
        exact = self.db.get_product(term)
        self.view.show_results([exact] if exact else self.db.search_products(term))

    @guarded
    def event_pick_result(self) -> None:
        product = self.view.selected_result()
        if product is None:
            return
        data = self.ask_form(
            self.view,
            f"Comprar {product.name}",
            [
                ("quantity", "Cantidad que llega", ""),
                ("unit_cost", "Costo unitario de compra", format_money_input(product.cost)),
            ],
            intro=f"Existencias actuales: {product.stock}  ·  Costo actual: ${format_price(product.cost)}",
            submit_text="Agregar",
        )
        if data is None:
            return
        quantity = parse_int(data["quantity"], minimum=1)
        unit_cost = parse_money(data["unit_cost"]) if data["unit_cost"].strip() else product.cost
        existing = next((item for item in self.items if item.code == product.code), None)
        if existing is not None:
            existing.quantity += quantity
            existing.unit_cost = unit_cost
        else:
            self.items.append(PurchaseItem(product.code, product.name, quantity, unit_cost))
        self.view.show_items(self.items)

    @guarded
    def event_remove_item(self) -> None:
        index = self.view.selected_item_index()
        if index is None or index >= len(self.items):
            messagebox.showwarning("Quitar línea", "Seleccione la línea que desea quitar.")
            return
        del self.items[index]
        self.view.show_items(self.items)

    def event_clear(self) -> None:
        self.items.clear()
        self.view.clear_form()

    @guarded
    def event_save(self) -> None:
        if not self.items:
            raise ValueError("Agregue al menos un producto a la compra.")
        supplier = self.view.selected_supplier()
        purchase = Purchase(
            id=None,
            supplier_id=supplier.id if supplier else None,
            supplier_name=supplier.name if supplier else "",
            invoice_number=self.view.get_invoice(),
            notes=self.view.get_notes(),
            items=list(self.items),
        )
        units, total = purchase.units, purchase.total
        purchase_id = self.db.add_purchase(purchase)
        self.event_clear()
        self.refresh()
        messagebox.showinfo(
            "Compra registrada",
            f"Compra {purchase_id}: entraron {units} unidades por ${format_price(total)}. "
            "Las existencias y los costos ya están actualizados.",
        )
