"""Prueba de humo de la interfaz completa con una base de datos simulada.

Crea la ventana principal oculta, recorre todas las pantallas y hace ventas de
principio a fin: turno de caja, descuentos, pago mixto, cola de clientes,
anulaciones, devoluciones, compras, cierre con arqueo y copias de seguridad.
Sirve para atrapar errores de construcción de widgets y de cableado entre
vistas y controladores sin necesitar PostgreSQL ni impresora.
Se salta si no hay entorno gráfico disponible.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import time
import tkinter as tk
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from tkinter import filedialog, messagebox

import pytest

from model.audit_log import AuditEntry
from model.errors import DuplicateProductError, ProductNotFoundError
from model.pending_sale import PendingSale
from model.product import Product
from model.purchase import Purchase
from model.receipt import PAYMENT_CARD, PAYMENT_CASH, PAYMENT_MIXED, PAYMENT_TRANSFER, STATUS_VOIDED, Receipt
from model.sale_return import ReturnItem, SaleReturn
from model.shift import Shift, ShiftSummary
from model.supplier import Supplier
from model.user import ROLE_ADMIN, ROLE_CASHIER, User
from utils import excel_import
from utils.config import BackupSettings, BusinessSettings, DatabaseSettings, PrinterSettings, Settings

ZERO = Decimal(0)


class FakeDB:
    """Implementa la misma interfaz que DBConnection, en memoria."""

    def __init__(self) -> None:
        self.products: dict[str, Product] = {}
        self.categories: list[str] = ["General", "Bebidas"]
        self.receipts: list[Receipt] = []
        self.returns: list[SaleReturn] = []
        self.pending: dict[int, PendingSale] = {}
        self.users: dict[str, tuple[User, str]] = {}
        self.shifts: list[Shift] = []
        self.suppliers: list[Supplier] = []
        self.purchases: list[Purchase] = []
        self.backups: list[str] = []
        self.current_user: str | None = None
        self.closed = False
        self.reconnects = 0

    def close(self) -> None:
        self.closed = True

    def reconnect(self) -> None:
        self.reconnects += 1

    # ------------------------------------------------------------------ catálogo
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
            if receipt.is_voided:
                continue
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

    def adjust_stock(self, code: str, quantity: int, reason: str = "") -> Product:
        product = self.get_product(code)
        if product is None:
            raise ProductNotFoundError(code)
        product.stock += quantity
        return product

    def get_stock_movements(self, code=None, start=None, end=None, limit=300):
        return []

    def deactivate_product(self, code: str) -> None:
        self.products[code].active = False

    # ------------------------------------------------------------------ ventas
    def add_receipt(self, receipt: Receipt) -> int:
        for sp in receipt.sold_products:
            self.products[sp.code].stock -= sp.quantity
        self.receipts.append(receipt)
        receipt.id = len(self.receipts)
        return receipt.id

    def get_receipt(self, receipt_id: int) -> Receipt | None:
        return next((r for r in self.receipts if r.id == receipt_id), None)

    def get_receipts_in_range(self, start: dt.date, end: dt.date) -> list[Receipt]:
        return [r for r in self.receipts if start <= r.date <= end]

    def void_receipt(self, receipt_id: int, reason: str) -> Receipt:
        receipt = self.get_receipt(receipt_id)
        assert receipt is not None
        receipt.status = STATUS_VOIDED
        receipt.void_reason = reason
        receipt.voided_by = self.current_user
        for sp in receipt.sold_products:
            self.products[sp.code].stock += sp.quantity
        return receipt

    def add_return(self, receipt_id: int, items: list[tuple[str, int]], reason: str) -> SaleReturn:
        receipt = self.get_receipt(receipt_id)
        assert receipt is not None
        returned = []
        for code, quantity in items:
            if quantity <= 0:
                continue
            line = next(sp for sp in receipt.sold_products if sp.code == code)
            self.products[code].stock += quantity
            returned.append(ReturnItem(code, line.product.name, quantity, line.unit_price))
        sale_return = SaleReturn(
            len(self.returns) + 1, receipt_id, reason, self.current_user, dt.datetime.now(), returned
        )
        self.returns.append(sale_return)
        receipt.returned_total += sale_return.total
        return sale_return

    def returned_quantities(self, receipt_id: int) -> dict[str, int]:
        counts: dict[str, int] = {}
        for sale_return in self.returns:
            if sale_return.receipt_id == receipt_id:
                for item in sale_return.items:
                    counts[item.code] = counts.get(item.code, 0) + item.quantity
        return counts

    def get_returns_in_range(self, start: dt.date, end: dt.date) -> list[SaleReturn]:
        return [r for r in self.returns if start <= r.created_at.date() <= end]

    # ------------------------------------------------------------------ turnos
    def get_open_shift(self) -> Shift | None:
        return next((s for s in self.shifts if s.closed_at is None), None)

    def open_shift(self, opening_cash: Decimal) -> Shift:
        shift = Shift(len(self.shifts) + 1, dt.datetime.now(), self.current_user, opening_cash)
        self.shifts.append(shift)
        return shift

    def shift_summary(self, shift_id: int) -> ShiftSummary:
        shift = next(s for s in self.shifts if s.id == shift_id)
        receipts = [r for r in self.receipts if r.shift_id == shift_id]
        valid = [r for r in receipts if not r.is_voided]
        return ShiftSummary(
            shift=shift,
            receipt_count=len(valid),
            cash_sales=sum((r.paid_with(PAYMENT_CASH) for r in valid), ZERO),
            card_sales=sum((r.paid_with(PAYMENT_CARD) for r in valid), ZERO),
            transfer_sales=sum((r.paid_with(PAYMENT_TRANSFER) for r in valid), ZERO),
            returns=sum((r.returned_total for r in valid), ZERO),
            voided_count=len(receipts) - len(valid),
        )

    def close_shift(self, shift_id: int, counted_cash: Decimal, notes: str = "") -> Shift:
        summary = self.shift_summary(shift_id)
        closed = replace(
            summary.shift,
            closed_at=dt.datetime.now(),
            closed_by=self.current_user,
            expected_cash=summary.expected_cash,
            counted_cash=counted_cash,
            difference=counted_cash - summary.expected_cash,
            notes=notes,
        )
        self.shifts[[s.id for s in self.shifts].index(shift_id)] = closed
        return closed

    def list_shifts(self, limit: int = 20) -> list[Shift]:
        return [s for s in reversed(self.shifts) if s.closed_at is not None][:limit]

    # ------------------------------------------------------------------ proveedores y compras
    def list_suppliers(self, include_inactive: bool = False) -> list[Supplier]:
        return sorted(self.suppliers, key=lambda s: s.name.lower())

    def save_supplier(self, supplier: Supplier) -> Supplier:
        if supplier.id is None:
            supplier.id = len(self.suppliers) + 1
            self.suppliers.append(supplier)
        return supplier

    def add_purchase(self, purchase: Purchase) -> int:
        for item in purchase.items:
            product = self.products[item.code]
            units = product.stock + item.quantity
            product.cost = ((product.cost * product.stock + item.unit_cost * item.quantity) / units).quantize(
                Decimal("0.01")
            )
            product.stock = units
        purchase.id = len(self.purchases) + 1
        purchase.purchased_at = dt.datetime.now()
        purchase.user = self.current_user
        self.purchases.append(purchase)
        return purchase.id

    def list_purchases(self, start: dt.date, end: dt.date) -> list[Purchase]:
        return [p for p in self.purchases if start <= p.purchased_at.date() <= end]

    # ------------------------------------------------------------------ usuarios
    def count_users(self) -> int:
        return len(self.users)

    def list_users(self) -> list[User]:
        return [user for user, _ in self.users.values()]

    def get_user(self, username: str) -> User | None:
        entry = self.users.get(username)
        return entry[0] if entry else None

    def create_user(self, username: str, full_name: str, role: str, password: str) -> User:
        user = User(id=len(self.users) + 1, username=username, full_name=full_name, role=role)
        self.users[username] = (user, password)
        return user

    def update_user(self, user_id: int, full_name: str, role: str, active: bool) -> None:
        for username, (user, password) in self.users.items():
            if user.id == user_id:
                self.users[username] = (User(user.id, username, full_name, role, active), password)

    def set_password(self, user_id: int, password: str) -> None:
        for username, (user, _) in self.users.items():
            if user.id == user_id:
                self.users[username] = (user, password)

    def authenticate(self, username: str, password: str) -> User | None:
        entry = self.users.get(username)
        if entry is None or entry[1] != password or not entry[0].active:
            return None
        self.current_user = username
        return entry[0]

    # ------------------------------------------------------------------ ventas en espera, auditoría, copias
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

    def record_backup(self, filename: str) -> None:
        self.backups.append(filename)


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        database=DatabaseSettings("localhost", 5432, "x", "x", "x"),
        business=BusinessSettings("Tienda Prueba", "1", "Calle", "3", "Gracias"),
        printer=PrinterSettings(True, 0x0483, 0x070B, 0x81, 0x02, 1000, 32, open_drawer=True),
        admin_password="admin",
        backup=BackupSettings(enabled=False, directory=str(tmp_path / "copias")),
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


def wait_until(root, condition, seconds: float = 5.0) -> None:
    deadline = time.monotonic() + seconds
    while not condition() and time.monotonic() < deadline:
        root.update()
        time.sleep(0.05)
    assert condition(), "la operación en segundo plano no terminó a tiempo"


def test_full_sale_flow_through_every_screen(root, settings, dialogs, monkeypatch, tmp_path):
    from controller.main_controller import MainController
    from controller.sales_view_controller import MODE_AMOUNT, MODE_PERCENT, SCOPE_LINE, SCOPE_SALE

    db = FakeDB()
    db.add_product(Product("A1", "Gaseosa", Decimal(2000), Decimal(3000), 6, "Bebidas"))
    db.add_product(Product("B2", "Pan", Decimal(300), Decimal(500), 0, "General"))
    db.create_user("admin", "Administrador", ROLE_ADMIN, "admin1")
    db.create_user("caja", "Cajera", ROLE_CASHIER, "caja1")
    controller = MainController(root, settings, db)
    root.update()

    # ---------------------------------------------------------------- inicio de sesión
    login = controller.login_controller
    assert_visible(controller, login.view)
    login.view.username_entry.insert(0, "admin")
    login.view.password_entry.insert(0, "mala")
    login.event_login()
    assert login.view.error_label.cget("text")
    login.view.password_entry.delete(0, "end")
    login.view.password_entry.insert(0, "admin1")
    login.event_login()
    root.update()
    menu = controller.menu_controller.view
    assert_visible(controller, menu)
    assert controller.current_user.username == "admin" and db.current_user == "admin"
    assert len(menu._tiles) == 9 and all(tile.enabled for _permission, tile in menu._tiles)

    # ---------------------------------------------------------------- ventas: la primera entrada abre el turno
    controller.shift_controller.ask_form = lambda *args, **kwargs: {"opening_cash": "50.000"}
    controller.show_sales_view()
    root.update()
    sales = controller.sales_controller
    sales_view = sales.view
    assert_visible(controller, sales_view)
    assert sales.shift is not None and sales.shift.opening_cash == Decimal(50000)
    assert db.get_open_shift().opened_by == "admin"
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

    # Descuentos: 10 % sobre la línea y 400 pesos sobre toda la venta.
    sales_view.select_index(0)
    sales.ask_form = lambda *args, **kwargs: {"scope": SCOPE_LINE, "mode": MODE_PERCENT, "value": "10"}
    sales.event_discount()
    assert sales.lines[0].discount == Decimal(600) and sales.total() == Decimal(5400)
    sales.ask_form = lambda *args, **kwargs: {"scope": SCOPE_SALE, "mode": MODE_AMOUNT, "value": "400"}
    sales.event_discount()
    assert sales.total() == Decimal(5000)
    assert "1.000" in sales_view.discount_label.cget("text")

    # Cobro: billetes, teclado, cambio en vivo.
    sales.event_bill(5000)
    sales.event_bill(2000)
    assert sales_view.get_received_amount() == "7.000"
    assert sales_view.change_label.cget("text").startswith("Cambio")
    sales.event_keypad("←")
    assert sales_view.get_received_amount() == "700"
    assert sales_view.change_label.cget("text").startswith("Faltan")
    sales.event_exact()
    assert sales_view.get_received_amount() == "5.000"
    sales.event_bill(10000)

    print_jobs: list[str] = []
    sales._run_print_job = lambda name, job: print_jobs.append(name)
    sales._print_in_background = lambda receipt, *_args: print_jobs.append(f"recibo-{receipt.id}")

    # Primera venta sin activar "Imprimir recibo": abre el cajón, no imprime, muestra el recibo con el cambio.
    assert sales_view.wants_receipt() is False
    sales.event_cash_payment()
    root.update()
    assert len(db.receipts) == 1
    first_receipt = db.receipts[0]
    assert first_receipt.total == Decimal(5000)
    assert first_receipt.discount_total == Decimal(400) and first_receipt.sold_products[0].discount == Decimal(600)
    assert first_receipt.cashier == "admin" and first_receipt.shift_id == sales.shift.id
    assert db.products["A1"].stock == 4
    assert sales.lines == [] and sales.active.discount_total == ZERO
    assert print_jobs == ["cajon-1"]
    voucher = [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)]
    assert voucher, "Debe abrirse la ventana del recibo"
    close_toplevels(root)

    # Segunda venta con el interruptor activado: imprime y el interruptor vuelve a apagarse.
    sales.on_barcode("A1")
    sales_view.print_var.set(True)
    sales.event_card_payment()
    root.update()
    assert len(db.receipts) == 2
    assert print_jobs == ["cajon-1", "recibo-2"], "con tarjeta no se abre el cajón"
    assert sales_view.wants_receipt() is False
    close_toplevels(root)

    sales.event_select_category("__mas_vendidos__")
    assert [card.product.code for card in sales_view._cards] == ["A1"]

    # Cola de ventas: dos clientes a la vez, con existencias apartadas entre ventas (quedan 3 en stock).
    sales.on_barcode("A1")
    sales.on_barcode("A1")
    first = sales.active.number
    sales.event_new_sale()
    assert len(sales.sales) == 2 and sales.active.number != first and sales.lines == []
    sales.on_barcode("A1")
    sales.on_barcode("A1")  # la cuarta unidad no existe: dos están apartadas en la otra venta
    assert [sp.quantity for sp in sales.lines] == [1]
    assert "otra venta" in dialogs[-1][1]
    sales.event_switch_sale(first)
    assert sales.active.number == first and [sp.quantity for sp in sales.lines] == [2]
    assert len(db.pending) == 2, "las dos ventas abiertas deben estar guardadas en la base"
    sales.event_cancel_sale()  # askyesno devuelve True
    assert len(sales.sales) == 1 and sales.active.number != first
    assert sales_view.cart_title.cget("text") == f"Venta {sales.active.number}"
    sales.event_card_payment()
    root.update()
    close_toplevels(root)
    assert len(db.receipts) == 3 and len(sales.sales) == 1 and sales.lines == []
    assert db.pending == {}, "al cobrar o cancelar, la venta sale de la base"

    # Pago mixto: parte en efectivo y parte con tarjeta.
    sales.on_barcode("A1")
    sales.ask_form = lambda *args, **kwargs: {PAYMENT_CASH: "1.000", PAYMENT_CARD: "2.000", PAYMENT_TRANSFER: ""}
    sales.event_mixed_payment()
    root.update()
    close_toplevels(root)
    mixed = db.receipts[3]
    assert mixed.payment_method == PAYMENT_MIXED
    assert mixed.paid_with(PAYMENT_CASH) == Decimal(1000) and mixed.paid_with(PAYMENT_CARD) == Decimal(2000)
    assert db.products["A1"].stock == 1
    assert print_jobs[-1] == "cajon-4", "hay efectivo en el pago mixto: se abre el cajón"

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

    # Importar Excel: crea C3, cambia el precio de A1 y ajusta sus existencias (1 -> 3).
    excel_path = tmp_path / "productos.xlsx"
    excel_import.write_catalog(
        excel_path,
        [
            replace(db.products["A1"], price=Decimal(3500), stock=3),
            Product("C3", "Jabón", Decimal(1000), Decimal(1500), 12, "Aseo"),
        ],
    )
    monkeypatch.setattr(filedialog, "askopenfilename", lambda **kwargs: str(excel_path))
    admin.event_import_excel()
    assert db.products["C3"].stock == 12 and db.products["A1"].price == Decimal(3500)
    assert db.products["A1"].stock == 3
    assert len(admin.view.tree.get_children()) == 3
    assert dialogs[-1][0] == "showinfo" and "creados: 1" in dialogs[-1][1] and "ajustadas: 1" in dialogs[-1][1]

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
    assert view.get_price() == "3.500"
    products.ask_form = lambda *args, **kwargs: {"quantity": "4", "reason": "llegó pedido"}
    products.event_adjust_stock()
    assert db.products["A1"].stock == 7  # 3 tras la importación + 4 agregadas
    products.event_new()
    assert view.get_code() == ""

    # ---------------------------------------------------------------- compras a proveedores
    controller.show_purchases_view()
    root.update()
    purchases = controller.purchases_controller
    assert_visible(controller, purchases.view)
    purchases.ask_form = lambda *args, **kwargs: {
        "name": "Distribuidora Sur",
        "nit": "900.1",
        "phone": "310",
        "email": "",
    }
    purchases.event_new_supplier()
    assert [s.name for s in db.suppliers] == ["Distribuidora Sur"]
    assert purchases.view.selected_supplier().name == "Distribuidora Sur"
    purchases.view.search_entry.insert(0, "gas")
    purchases.event_search()
    results = purchases.view.results_tree.get_children()
    assert len(results) == 1
    purchases.view.results_tree.selection_set(results[0])
    purchases.ask_form = lambda *args, **kwargs: {"quantity": "10", "unit_cost": "1.800"}
    purchases.event_pick_result()
    assert [(item.code, item.quantity) for item in purchases.items] == [("A1", 10)]
    purchases.view.invoice_entry.insert(0, "F-77")
    purchases.event_save()
    assert db.products["A1"].stock == 17
    assert db.products["A1"].cost < Decimal(2000), "el costo promedio baja al comprar más barato"
    assert db.purchases[0].invoice_number == "F-77" and db.purchases[0].supplier_name == "Distribuidora Sur"
    assert purchases.items == [] and len(purchases.view.history_tree.get_children()) == 1

    # ---------------------------------------------------------------- reporte: anular y devolver
    controller.show_sales_report_view()
    root.update()
    report = controller.report_controller
    assert_visible(controller, report.view)
    report.event_quick_range("today")
    assert len(report.rows) == 4
    assert report.totals.cash == Decimal(6000)
    assert report.totals.card == Decimal(8000)
    assert report.totals.receipt_count == 4

    report.view.selected_row = lambda: report.rows[1]  # recibo 2 (tarjeta, 3.000)
    report.ask_form = lambda *args, **kwargs: {"reason": "se cobró dos veces"}
    report.event_void()
    assert db.receipts[1].is_voided and db.products["A1"].stock == 18
    assert report.totals.receipt_count == 3 and report.totals.voided_count == 1
    assert report.totals.card == Decimal(5000)

    report.view.selected_row = lambda: report.rows[2]  # recibo 3 (tarjeta, 3.000)
    report.ask_return = lambda parent, receipt, already: ([("A1", 1)], "no era lo que quería")
    report.event_return()
    assert db.products["A1"].stock == 19 and db.receipts[2].returned_total == Decimal(3000)
    assert report.totals.returns == Decimal(3000)
    del report.view.selected_row

    # ---------------------------------------------------------------- dashboard
    report.event_dashboard()
    root.update()
    dashboard = controller.dashboard_controller
    assert_visible(controller, dashboard.view)
    dashboard.event_period("today")
    assert dashboard.view.kpi_cards["total"].value_label.cget("text") == "$11.000"  # sin el recibo anulado
    assert dashboard.view.kpi_cards["receipts"].value_label.cget("text") == "3"
    assert dashboard.view.kpi_cards["profit"].value_label.cget("text") == "$3.400"
    assert len(dashboard.view.top_tree.get_children()) == 1
    assert dashboard.view._insight_labels, "debe haber hallazgos"
    assert dashboard.view.restock_tree.get_children()
    dashboard.event_open_inventory("out")
    root.update()
    assert_visible(controller, admin.view)
    assert [admin.view.tree.item(i, "values")[0] for i in admin.view.tree.get_children()] == ["B2"]
    admin.set_stock_filter(None)

    # ---------------------------------------------------------------- cierre de caja con arqueo
    controller.show_shift_view()
    root.update()
    shift = controller.shift_controller
    assert_visible(controller, shift.view)
    shift.view.get_counts = lambda: {50000: 1, 5000: 1, 1000: 1}  # 56.000 contados
    shift_prints: list[tuple[ShiftSummary, Shift]] = []
    controller.print_shift_close = lambda summary, closed: shift_prints.append((summary, closed))
    shift.event_close_shift()
    closed = db.shifts[0]
    assert closed.closed_at is not None and closed.closed_by == "admin"
    assert closed.expected_cash == Decimal(53000)  # 50.000 base + 6.000 efectivo - 3.000 devueltos
    assert closed.counted_cash == Decimal(56000) and closed.difference == Decimal(3000)
    assert shift_prints and shift_prints[0][0].cash_sales == Decimal(6000)
    assert "Sobran" in dialogs[-1][1]
    assert db.get_open_shift() is None
    assert len(shift.view.history_tree.get_children()) == 1

    # ---------------------------------------------------------------- copias de seguridad
    made: list[Path] = []

    def fake_backup(database, backup_settings, base_dir):
        directory = Path(backup_settings.directory)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "x_20260901_120000.backup"
        path.write_bytes(b"pgdump")
        made.append(path)
        return path

    monkeypatch.setattr("utils.backup.run_backup", fake_backup)
    controller.show_backups_view()
    root.update()
    backups = controller.backups_controller
    assert_visible(controller, backups.view)
    assert backups.view.last_card.value_label.cget("text") == "Nunca"
    backups.event_backup_now()
    wait_until(root, lambda: not backups._busy)
    assert made and db.backups == ["x_20260901_120000.backup"]
    assert len(backups.view.tree.get_children()) == 1
    assert backups.view.last_card.value_label.cget("text") != "Nunca"
    assert dialogs[-1] == ("showinfo", "Copia creada correctamente.")

    # ---------------------------------------------------------------- auditoría
    controller.show_auditlog_view()
    root.update()
    assert_visible(controller, controller.auditlog_controller.view)
    assert controller.auditlog_controller.view.tree.get_children()
    controller.auditlog_controller.event_back()
    root.update()
    assert_visible(controller, menu)

    # ---------------------------------------------------------------- usuarios y permisos
    controller.show_users_view()
    root.update()
    users = controller.users_controller
    assert_visible(controller, users.view)
    assert len(users.view.tree.get_children()) == 2
    users.view.username_entry.insert(0, "nuevo")
    users.view.name_entry.insert(0, "Nuevo Cajero")
    users.view.password_entry.insert(0, "nuevo1")
    users.event_save()
    assert "nuevo" in db.users and len(users.view.tree.get_children()) == 3

    controller.logout()
    root.update()
    assert_visible(controller, login.view)
    assert db.current_user is None
    login.view.username_entry.insert(0, "caja")
    login.view.password_entry.insert(0, "caja1")
    login.event_login()
    root.update()
    assert_visible(controller, menu)
    enabled = [tile.title_label.cget("text") for _permission, tile in menu._tiles if tile.enabled]
    assert enabled == ["Ventas", "Inventario", "Compras", "Cierre de caja"]

    controller.show_users_view()  # la cajera no tiene permiso
    root.update()
    assert dialogs[-1][0] == "showwarning" and "Usuarios" in dialogs[-1][1]
    assert_visible(controller, menu)
    controller.show_sales_view()  # abre un turno nuevo porque el anterior está cerrado
    root.update()
    assert_visible(controller, sales_view)
    assert db.get_open_shift().opened_by == "caja"
    sales.on_barcode("A1")
    sales_view.select_index(0)
    sales.event_discount()  # sin permiso para descuentos
    assert dialogs[-1][0] == "showwarning" and "descuentos" in dialogs[-1][1]
    assert sales.lines[0].discount == ZERO
    sales.event_remove_line()
    controller.show_admin_view()
    root.update()
    assert controller.admin_controller.view.manage_button.cget("state") == "normal"  # la cajera ingresa pedidos
    controller.show_purchases_view()
    root.update()
    assert_visible(controller, purchases.view)
    controller.show_dashboard_view()  # pero no ve el dashboard
    root.update()
    assert dialogs[-1][0] == "showwarning" and "Dashboard" in dialogs[-1][1]
    controller.show_backups_view()  # ni las copias de seguridad
    root.update()
    assert dialogs[-1][0] == "showwarning"
    controller.show_menu()
    root.update()

    assert not any(kind == "showerror" for kind, _ in dialogs), dialogs
