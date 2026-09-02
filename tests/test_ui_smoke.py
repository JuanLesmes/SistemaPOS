"""Prueba de humo de la interfaz completa con una base de datos simulada.

Crea la ventana principal oculta, recorre todas las pantallas y hace ventas de
principio a fin. Sirve para atrapar errores de construcción de widgets y de
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
from model.pending_sale import PendingSale
from model.product import Product
from model.receipt import Receipt
from utils.config import BusinessSettings, DatabaseSettings, PrinterSettings, Settings


class FakeDB:
    """Implementa la misma interfaz que DBConnection, en memoria."""

    def __init__(self) -> None:
        self.products: dict[str, Product] = {}
        self.categories: list[str] = ["General", "Bebidas"]
        self.receipts: list[Receipt] = []
        self.pending: dict[int, PendingSale] = {}
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
        return sorted(
            (p for p in self.products.values() if p.active and (category is None or p.category == category)),
            key=lambda p: p.name.lower(),
        )

    def get_best_sellers(self, days: int = 30, limit: int = 60) -> list[Product]:
        sold: dict[str, int] = {}
        for receipt in self.receipts:
            for sp in receipt.sold_products:
                sold[sp.code] = sold.get(sp.code, 0) + sp.quantity
        ranked = sorted(sold, key=lambda code: -sold[code])
        return [self.products[code] for code in ranked if self.products[code].active][:limit]

    def get_product(self, code: str, include_inactive: bool = False) -> Product | None:
        product = self.products.get(code)
        if product is None or (not include_inactive and not product.active):
            return None
        return product

    def search_products(self, term: str) -> list[Product]:
        return [p for p in self.get_products() if term.lower() in p.name.lower() or term.lower() in p.code.lower()]

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

    def load_pending_sales(self) -> list[PendingSale]:
        return list(self.pending.values())

    def save_pending_sale(self, sale: PendingSale) -> int:
        sale_id = sale.db_id or (max(self.pending, default=0) + 1)
        self.pending[sale_id] = sale
        return sale_id

    def delete_pending_sale(self, sale_id: int) -> None:
        self.pending.pop(sale_id, None)

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


def assert_visible(controller, view) -> None:
    """La vista debe estar colocada en su marco y el marco en la ventana; si no, la pantalla sale en blanco."""
    view.winfo_toplevel().update()
    assert view.winfo_manager() == "pack", f"{type(view).__name__} no está colocada en su marco"
    assert view.master.winfo_manager() == "pack", f"El marco de {type(view).__name__} no está en la ventana"
    shown = [f for f in controller._frames if f.winfo_manager() == "pack"]
    assert shown == [view.master], "Solo debe haber una pantalla visible a la vez"


def close_toplevels(root) -> None:
    for window in root.winfo_children():
        if isinstance(window, tk.Toplevel):
            window.destroy()


def test_full_sale_flow_through_every_screen(root, settings, dialogs):
    from controller.main_controller import MainController

    db = FakeDB()
    db.add_product(Product("A1", "Gaseosa", Decimal(2000), Decimal(3000), 5, "Bebidas"))
    db.add_product(Product("B2", "Pan", Decimal(300), Decimal(500), 0, "General"))
    controller = MainController(root, settings, db)
    root.update()
    assert_visible(controller, controller.menu_controller.view)

    # ---------------------------------------------------------------- ventas
    controller.show_sales_view()
    root.update()
    sales = controller.sales_controller
    sales_view = sales.view
    assert_visible(controller, sales_view)
    assert len(sales_view._cards) == 2, "el catálogo debe mostrar todos los productos"

    sales.event_select_category("Bebidas")
    assert [card.product.code for card in sales_view._cards] == ["A1"]
    sales.event_product_selected(sales_view._cards[0].product)
    sales.on_barcode("A1")
    sales.on_barcode("ZZZ")
    root.update()
    assert [sp.quantity for sp in sales.lines] == [2]
    assert dialogs[-1][0] == "showwarning"

    sales.event_increase()
    sales.event_decrease()
    assert [sp.quantity for sp in sales.lines] == [2]

    # Cobro: billetes, teclado, cambio en vivo.
    sales.event_bill(5000)
    sales.event_bill(2000)
    assert sales_view.get_received_amount() == "7.000"
    assert sales_view.change_label.cget("text").startswith("Cambio")
    sales.event_keypad("←")
    assert sales_view.get_received_amount() == "700"
    assert sales_view.change_label.cget("text").startswith("Faltan")
    sales.event_exact()
    assert sales_view.get_received_amount() == "6.000"
    sales.event_bill(10000)

    print_jobs: list[Receipt] = []
    sales._print_in_background = lambda receipt, *_args: print_jobs.append(receipt)

    # Primera venta sin activar "Imprimir recibo": no imprime, abre el recibo con el cambio.
    assert sales_view.wants_receipt() is False
    sales.event_cash_payment()
    root.update()
    assert len(db.receipts) == 1
    assert db.receipts[0].total == Decimal(6000)
    assert db.products["A1"].stock == 3
    assert sales.lines == []
    assert print_jobs == []
    voucher = [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)]
    assert voucher, "Debe abrirse la ventana del recibo"
    close_toplevels(root)

    # Segunda venta con el interruptor activado: imprime y el interruptor vuelve a apagarse.
    sales.on_barcode("A1")
    sales_view.print_var.set(True)
    sales.event_card_payment()
    root.update()
    assert len(db.receipts) == 2
    assert [r.id for r in print_jobs] == [2]
    assert sales_view.wants_receipt() is False
    close_toplevels(root)

    sales.event_select_category("__mas_vendidos__")
    assert [card.product.code for card in sales_view._cards] == ["A1"]

    # Cola de ventas: dos clientes a la vez, con existencias apartadas entre ventas.
    sales.on_barcode("A1")  # venta en curso con 1 unidad (quedan 2 en stock)
    first = sales.active.number
    sales.event_new_sale()
    assert len(sales.sales) == 2 and sales.active.number != first and sales.lines == []
    sales.on_barcode("A1")
    sales.on_barcode("A1")  # la segunda unidad ya está apartada en la otra venta
    assert [sp.quantity for sp in sales.lines] == [1]
    assert "otra venta" in dialogs[-1][1]
    sales.event_switch_sale(first)
    assert sales.active.number == first and [sp.quantity for sp in sales.lines] == [1]
    assert len(db.pending) == 2, "las dos ventas abiertas deben estar guardadas en la base"
    sales.event_cancel_sale()  # askyesno devuelve True
    assert len(sales.sales) == 1 and sales.active.number != first
    assert sales_view.cart_title.cget("text") == f"Venta {sales.active.number}"
    sales.event_card_payment()
    root.update()
    close_toplevels(root)
    assert len(db.receipts) == 3 and len(sales.sales) == 1 and sales.lines == []
    assert db.pending == {}, "al cobrar o cancelar, la venta sale de la base"

    # ---------------------------------------------------------------- inventario
    controller.show_admin_view()
    root.update()
    admin = controller.admin_controller
    assert_visible(controller, admin.view)
    assert len(admin.view.tree.get_children()) == 2
    admin.view.search_entry.insert(0, "gas")
    admin.event_filter_changed()
    assert len(admin.view.tree.get_children()) == 1
    admin.view.new_category_entry.insert(0, "Aseo")
    admin.event_add_category()
    assert "Aseo" in db.categories
    assert admin.view.stat_cards["out"].value_label.cget("text") == "1"

    # Clic en "Agotados" filtra la tabla; el segundo clic quita el filtro.
    admin.view.search_entry.delete(0, "end")
    admin.event_filter_changed()
    admin.event_toggle_stock_filter("out")
    assert [admin.view.tree.item(i, "values")[0] for i in admin.view.tree.get_children()] == ["B2"]
    assert admin.view.filter_note.winfo_manager() == "pack"
    admin.event_toggle_stock_filter("out")
    assert len(admin.view.tree.get_children()) == 2
    assert admin.view.filter_note.winfo_manager() == ""

    # ---------------------------------------------------------------- productos
    controller.show_product_management_view()
    root.update()
    products = controller.product_controller
    view = products.view
    assert_visible(controller, view)
    view.entry_search.insert(0, "gas")
    products.event_search()
    assert len(view.results_tree.get_children()) == 1
    products.fill_form(db.get_product("A1"))
    assert view.get_code() == "A1"
    assert view.get_price() == "3.000"
    view.entry_stock.delete(0, "end")
    view.entry_stock.insert(0, "4")
    products.event_add_stock()
    assert db.products["A1"].stock == 5  # 5 iniciales - 2 - 1 - 1 vendidas + 4 agregadas
    products.event_new()
    assert view.get_code() == ""

    # ---------------------------------------------------------------- reporte
    controller.show_sales_report_view()
    root.update()
    report = controller.report_controller
    assert_visible(controller, report.view)
    report.event_quick_range("today")
    assert len(report.rows) == 3
    assert report.totals.cash == Decimal(6000)
    assert report.totals.card == Decimal(6000)
    assert report.totals.receipt_count == 3

    # ---------------------------------------------------------------- dashboard
    report.event_dashboard()
    root.update()
    dashboard = controller.dashboard_controller
    assert_visible(controller, dashboard.view)
    dashboard.event_period("today")
    assert dashboard.view.kpi_cards["total"].value_label.cget("text") == "$12.000"
    assert dashboard.view.kpi_cards["receipts"].value_label.cget("text") == "3"
    assert dashboard.view.kpi_cards["profit"].value_label.cget("text") == "$4.000"
    assert len(dashboard.view.top_tree.get_children()) == 1
    assert dashboard.view._insight_labels, "debe haber hallazgos"
    assert dashboard.view.restock_tree.get_children()
    dashboard.event_open_inventory("out")
    root.update()
    assert_visible(controller, admin.view)
    assert [admin.view.tree.item(i, "values")[0] for i in admin.view.tree.get_children()] == ["B2"]
    admin.set_stock_filter(None)

    # ---------------------------------------------------------------- auditoría
    controller.show_auditlog_view()
    root.update()
    assert_visible(controller, controller.auditlog_controller.view)
    assert controller.auditlog_controller.view.tree.get_children()
    controller.auditlog_controller.event_back()
    root.update()
    assert_visible(controller, controller.menu_controller.view)

    assert not any(kind == "showerror" for kind, _ in dialogs), dialogs
