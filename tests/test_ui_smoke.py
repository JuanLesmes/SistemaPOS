"""Prueba de humo de la interfaz completa con una base de datos simulada.

Crea la ventana principal oculta, recorre todas las pantallas y hace una venta
de principio a fin. Sirve para atrapar errores de construcción de widgets y de
cableado entre vistas y controladores sin necesitar PostgreSQL ni impresora.
Se salta si no hay entorno gráfico disponible.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import tkinter as tk
from decimal import Decimal
from tkinter import messagebox

import pytest

from model.audit_log import AuditEntry
from model.errors import DuplicateProductError, ProductNotFoundError
from model.product import Product
from model.receipt import Receipt
from utils.config import BusinessSettings, DatabaseSettings, PrinterSettings, Settings


class FakeDB:
    """Implementa la misma interfaz que DBConnection, en memoria."""

    def __init__(self) -> None:
        self.products: dict[str, Product] = {}
        self.categories: list[str] = ["General", "Bebidas"]
        self.receipts: list[Receipt] = []
        self.closed = False

    def close(self) -> None:
        self.closed = True

    def get_categories(self) -> list[str]:
        return sorted(self.categories)

    def add_category(self, name: str) -> bool:
        if name in self.categories:
            return False
        self.categories.append(name)
        return True

    def delete_category(self, name: str) -> bool:
        if name not in self.categories:
            return False
        self.categories.remove(name)
        return True

    def get_products(self, category: str | None = None) -> list[Product]:
        return [p for p in self.products.values() if p.active and (category is None or p.category == category)]

    def get_product(self, code: str, include_inactive: bool = False) -> Product | None:
        product = self.products.get(code)
        if product is None or (not include_inactive and not product.active):
            return None
        return product

    def search_products(self, term: str) -> list[Product]:
        return [p for p in self.get_products() if term.lower() in p.name.lower()]

    def add_product(self, product: Product) -> None:
        if product.code in self.products and self.products[product.code].active:
            raise DuplicateProductError(f"Ya existe {product.code}")
        self.products[product.code] = product
        if product.category not in self.categories:
            self.categories.append(product.category)

    def update_product(self, product: Product) -> None:
        if self.get_product(product.code) is None:
            raise ProductNotFoundError(product.code)
        self.products[product.code] = product

    def add_stock(self, code: str, quantity: int) -> Product:
        product = self.get_product(code)
        if product is None:
            raise ProductNotFoundError(code)
        product.stock += quantity
        return product

    def deactivate_product(self, code: str) -> None:
        self.products[code].active = False

    def add_receipt(self, receipt: Receipt) -> int:
        for sp in receipt.sold_products:
            self.products[sp.code].stock -= sp.quantity
        self.receipts.append(receipt)
        return len(self.receipts)

    def get_receipts_in_range(self, start: dt.date, end: dt.date) -> list[Receipt]:
        return [r for r in self.receipts if start <= r.date <= end]

    def get_logs_by_date(self, day: dt.date) -> list[AuditEntry]:
        return [AuditEntry(dt.datetime.combine(day, dt.time(9)), "add_product", "A1", '{"after": {"name": "x"}}', None)]


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database=DatabaseSettings("localhost", 5432, "x", "x", "x"),
        business=BusinessSettings("Tienda Prueba", "1", "Calle", "3", "Gracias"),
        printer=PrinterSettings(True, 0x0483, 0x070B, 0x81, 0x02, 1000, 32),
        admin_password="admin",
    )


@pytest.fixture
def dialogs(monkeypatch) -> list[tuple[str, str]]:
    """Reemplaza los diálogos modales por un registro, para que la prueba no se bloquee."""
    calls: list[tuple[str, str]] = []
    for name in ("showinfo", "showwarning", "showerror"):
        monkeypatch.setattr(messagebox, name, lambda title, message, _n=name, **kw: calls.append((_n, message)))
    monkeypatch.setattr(messagebox, "askyesno", lambda *a, **kw: True)
    return calls


@pytest.fixture
def root():
    try:
        window = tk.Tk()
    except tk.TclError:
        pytest.skip("No hay entorno gráfico disponible.")
    window.withdraw()
    yield window
    with contextlib.suppress(tk.TclError):
        window.destroy()


def test_full_sale_flow_through_every_screen(root, settings, dialogs):
    from controller.main_controller import MainController

    db = FakeDB()
    db.add_product(Product("A1", "Gaseosa", Decimal(2000), Decimal(3000), 5, "Bebidas"))
    controller = MainController(root, settings, db)
    root.update()

    # Ventas: escaneo, cobro en efectivo con cambio y ventana de recibo.
    controller.show_sales_view()
    root.update()
    controller.sales_controller.on_barcode("A1")
    controller.sales_controller.on_barcode("A1")
    controller.sales_controller.on_barcode("ZZZ")
    root.update()
    assert [sp.quantity for sp in controller.sales_controller.lines] == [2]
    assert dialogs[-1][0] == "showwarning"

    print_jobs: list[Receipt] = []
    controller.sales_controller._print_in_background = lambda receipt, *_args: print_jobs.append(receipt)

    # Primera venta sin activar "Imprimir recibo": no debe imprimir.
    sales_view = controller.sales_controller.view
    assert sales_view.wants_receipt() is False
    sales_view.recibe_entry.insert(0, "10.000")
    controller.sales_controller.event_cash_payment()
    root.update()
    assert len(db.receipts) == 1
    assert db.receipts[0].total == Decimal(6000)
    assert db.products["A1"].stock == 3
    assert controller.sales_controller.lines == []
    assert print_jobs == []
    voucher = [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)]
    assert voucher, "Debe abrirse la ventana del recibo"
    voucher[0].destroy()

    # Segunda venta con el interruptor activado: imprime y el interruptor vuelve a apagarse.
    controller.sales_controller.on_barcode("A1")
    sales_view.print_var.set(True)
    controller.sales_controller.event_card_payment()
    root.update()
    assert len(db.receipts) == 2
    assert [r.id for r in print_jobs] == [2]
    assert sales_view.wants_receipt() is False
    for window in root.winfo_children():
        if isinstance(window, tk.Toplevel):
            window.destroy()

    # Inventario y gestión de productos.
    controller.show_admin_view()
    root.update()
    assert controller.admin_controller.view.tree.get_children()
    controller.admin_controller.view.new_category_entry.insert(0, "Aseo")
    controller.admin_controller.event_add_category()
    assert "Aseo" in db.categories

    controller.show_product_management_view()
    root.update()
    view = controller.product_controller.view
    view.entry_search.insert(0, "gas")
    controller.product_controller.event_search()
    assert view._result_labels
    controller.product_controller.fill_form(db.get_product("A1"))
    assert view.get_code() == "A1"
    assert view.get_price() == "3.000"
    view.entry_stock.delete(0, "end")
    view.entry_stock.insert(0, "4")
    controller.product_controller.event_add_stock()
    assert db.products["A1"].stock == 6  # 5 iniciales - 2 - 1 vendidas + 4 agregadas

    # Reporte del día y auditoría.
    controller.show_sales_report_view()
    root.update()
    controller.report_controller.event_search()
    assert len(controller.report_controller.rows) == 2
    assert controller.report_controller.totals.cash == Decimal(6000)
    assert controller.report_controller.totals.card == Decimal(3000)

    controller.show_auditlog_view()
    root.update()
    assert controller.auditlog_controller.view.tree.get_children()

    controller.show_menu()
    root.update()
    assert not any(kind == "showerror" for kind, _ in dialogs), dialogs
