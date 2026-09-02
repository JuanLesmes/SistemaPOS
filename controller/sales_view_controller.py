"""Pantalla de ventas: catálogo, lectura de códigos, armado de la venta y cobro."""

from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
from decimal import Decimal
from tkinter import messagebox

from controller.common import guarded
from model.db_connection import DBConnection
from model.errors import PrinterError
from model.product import Product
from model.receipt import PAYMENT_CARD, PAYMENT_CASH, PAYMENT_TRANSFER, Receipt
from model.sold_product import SoldProduct
from utils.barcode_reader import BarcodeReader
from utils.formatters import format_money_input, format_price, parse_money
from utils.printer_manager import ReceiptPrinter
from view.sales_view import ALL_CATEGORIES, BEST_SELLERS, SalesView
from view.widgets import Keypad

logger = logging.getLogger(__name__)

PRINT_POLL_MS = 250
PRINT_THREAD_PREFIX = "print-receipt-"
PAGE_SIZE = 60
SEARCH_DEBOUNCE_MS = 250
BEST_SELLER_DAYS = 30


class SalesViewController:
    def __init__(self, parent: tk.Frame, main_controller, db: DBConnection) -> None:
        self.main_controller = main_controller
        self.db = db
        self.lines: list[SoldProduct] = []
        self.view = SalesView(parent, self)

        settings = main_controller.settings
        self.printer = ReceiptPrinter(settings.printer, settings.business)
        self.view.set_printer_available(self.printer.enabled)
        self.reader = BarcodeReader(self.view.winfo_toplevel(), self.on_barcode)
        self._print_errors: queue.Queue[str] = queue.Queue()
        self._polling_printer = False
        self._category = ALL_CATEGORIES
        self._search_job: str | None = None
        self.refresh_catalog()
        self.reset_sale()

    # ------------------------------------------------------------------ ciclo de vida
    def on_show(self) -> None:
        self.reset_sale()
        self.refresh_catalog()
        self.reader.enable()
        self.view.focus_set()

    def on_hide(self) -> None:
        self.reader.disable()

    def reset_sale(self) -> None:
        self.lines.clear()
        self.view.clear_received_amount()
        self.view.reset_print_option()
        self._refresh()

    @guarded
    def refresh_catalog(self) -> None:
        self.view.set_categories(self.db.get_categories())
        self.view.clear_search()
        self._show_category(self._category)

    # ------------------------------------------------------------------ catálogo
    @guarded
    def event_select_category(self, key: str) -> None:
        self._category = key
        self.view.clear_search()
        self._show_category(key)

    def _show_category(self, key: str) -> None:
        note = ""
        if key == BEST_SELLERS:
            products = self.db.get_best_sellers(days=BEST_SELLER_DAYS, limit=PAGE_SIZE)
            note = (
                f"Más vendidos en los últimos {BEST_SELLER_DAYS} días" if products else "Aún no hay ventas registradas"
            )
        elif key == ALL_CATEGORIES:
            products = self.db.get_products()
        else:
            products = self.db.get_products(key)
        self.view.set_active_category(key)
        self._show_products(products, note)

    def _show_products(self, products: list[Product], note: str = "") -> None:
        shown = products[:PAGE_SIZE]
        if len(products) > PAGE_SIZE:
            note = f"Mostrando {PAGE_SIZE} de {len(products)}. Use la búsqueda para ver el resto."
        elif not note:
            note = f"{len(products)} productos"
        self.view.show_products(shown, note)

    def event_search_changed(self) -> None:
        """Espera a que el usuario deje de escribir antes de consultar."""
        if self._search_job is not None:
            self.view.after_cancel(self._search_job)
        self._search_job = self.view.after(SEARCH_DEBOUNCE_MS, self._run_search)

    @guarded
    def _run_search(self) -> None:
        self._search_job = None
        term = self.view.get_search_term()
        if not term:
            self._show_category(self._category)
            return
        products = self.db.search_products(term)
        note = f"{len(products)} resultados para '{term}'" if products else f"Sin resultados para '{term}'"
        self._show_products(products, note)

    @guarded
    def event_search_enter(self) -> None:
        """Enter en la búsqueda: si el texto es un código exacto, agrega el producto de una vez."""
        term = self.view.get_search_term()
        if not term:
            return
        product = self.db.get_product(term)
        if product is not None:
            if self._search_job is not None:
                self.view.after_cancel(self._search_job)
                self._search_job = None
            self.add_line(product)
            self.view.clear_search()
            self._show_category(self._category)
            return
        self._run_search()

    @guarded
    def event_product_selected(self, product: Product) -> None:
        fresh = self.db.get_product(product.code)
        if fresh is None:
            messagebox.showwarning("Producto no disponible", f"'{product.name}' ya no está activo.")
            self.refresh_catalog()
            return
        self.add_line(fresh)

    # ------------------------------------------------------------------ lector de códigos
    @guarded
    def on_barcode(self, code: str) -> None:
        product = self.db.get_product(code)
        if product is None:
            messagebox.showwarning("Producto no encontrado", f"No existe un producto activo con el código {code}.")
            return
        self.add_line(product)

    # ------------------------------------------------------------------ venta actual
    def add_line(self, product: Product, quantity: int = 1) -> None:
        """Agrega unidades de un producto; si ya está en la venta, suma a esa línea."""
        existing = next((sp for sp in self.lines if sp.code == product.code), None)
        wanted = quantity + (existing.quantity if existing else 0)
        if wanted > product.stock:
            messagebox.showwarning(
                "Sin existencias", f"'{product.name}' solo tiene {product.stock} unidades disponibles."
            )
            return
        if existing is not None:
            existing.quantity = wanted
        else:
            self.lines.append(SoldProduct(product=product, quantity=quantity))
        self._refresh()
        self.view.select_index(self.lines.index(existing) if existing is not None else len(self.lines) - 1)

    @guarded
    def event_increase(self) -> None:
        index = self._selected_line_index()
        if index is None:
            return
        line = self.lines[index]
        fresh = self.db.get_product(line.code)
        available = fresh.stock if fresh is not None else 0
        if line.quantity + 1 > available:
            messagebox.showwarning("Sin existencias", f"'{line.product.name}' solo tiene {available} unidades.")
            return
        line.quantity += 1
        self._refresh()
        self.view.select_index(index)

    @guarded
    def event_decrease(self) -> None:
        index = self._selected_line_index()
        if index is None:
            return
        line = self.lines[index]
        if line.quantity > 1:
            line.quantity -= 1
        else:
            del self.lines[index]
        self._refresh()
        self.view.select_index(min(index, len(self.lines) - 1))

    @guarded
    def event_remove_line(self) -> None:
        index = self._selected_line_index()
        if index is None:
            return
        del self.lines[index]
        self._refresh()
        self.view.select_index(min(index, len(self.lines) - 1))

    @guarded
    def event_clear_sale(self) -> None:
        if not self.lines:
            return
        if messagebox.askyesno("Vaciar venta", "¿Quitar todos los productos de la venta actual?"):
            self.reset_sale()

    def _selected_line_index(self) -> int | None:
        if not self.lines:
            messagebox.showwarning("Venta vacía", "Todavía no hay productos en la venta.")
            return None
        index = self.view.selected_index()
        if index is None or index >= len(self.lines):
            messagebox.showwarning("Seleccione un producto", "Seleccione en la tabla la línea que desea cambiar.")
            return None
        return index

    # ------------------------------------------------------------------ cobro
    def event_bill(self, amount: int) -> None:
        self.view.set_received_amount(format_money_input(self._received_or_zero() + amount))
        self._update_change()

    def event_exact(self) -> None:
        self.view.set_received_amount(format_money_input(self.total()))
        self._update_change()

    def event_keypad(self, key: str) -> None:
        digits = "".join(ch for ch in self.view.get_received_amount() if ch.isdigit())
        if key == Keypad.BACKSPACE:
            digits = digits[:-1]
        else:
            digits += key
        digits = digits.lstrip("0")
        self.view.set_received_amount(format_money_input(Decimal(digits)) if digits else "")
        self._update_change()

    def event_clear_received(self) -> None:
        self.view.clear_received_amount()
        self._update_change()

    def event_received_changed(self) -> None:
        self._update_change()

    @guarded
    def event_cash_payment(self) -> None:
        if not self.lines:
            self._warn_empty_sale()
            return
        received_text = self.view.get_received_amount()
        if not received_text:
            raise ValueError("Escriba o seleccione el monto recibido.")
        received = parse_money(received_text)
        total = self.total()
        if received < total:
            raise ValueError(f"Monto insuficiente: faltan ${format_price(total - received)}.")
        self._checkout(PAYMENT_CASH, received)

    @guarded
    def event_card_payment(self) -> None:
        self._checkout(PAYMENT_CARD)

    @guarded
    def event_transfer_payment(self) -> None:
        self._checkout(PAYMENT_TRANSFER)

    def event_back(self) -> None:
        self.main_controller.show_menu()

    # ------------------------------------------------------------------ apoyo
    def total(self) -> Decimal:
        return sum((sp.total for sp in self.lines), Decimal(0))

    def _received_or_zero(self) -> Decimal:
        try:
            return parse_money(self.view.get_received_amount())
        except ValueError:
            return Decimal(0)

    def _update_change(self) -> None:
        text = self.view.get_received_amount()
        if not text or not self.lines:
            self.view.set_change("")
            return
        try:
            received = parse_money(text)
        except ValueError:
            self.view.set_change("Monto inválido", ok=False)
            return
        difference = received - self.total()
        if difference >= 0:
            self.view.set_change(f"Cambio  ${format_price(difference)}")
        else:
            self.view.set_change(f"Faltan  ${format_price(-difference)}", ok=False)

    def _refresh(self) -> None:
        self.view.load_table(self.lines)
        self.view.set_total(self.total())
        self._update_change()

    def _warn_empty_sale(self) -> None:
        messagebox.showwarning("Venta vacía", "Agregue productos antes de cobrar.")

    def _checkout(self, payment_method: str, received: Decimal | None = None) -> None:
        if not self.lines:
            self._warn_empty_sale()
            return
        receipt = Receipt.create(payment_method, self.lines)
        receipt.id = self.db.add_receipt(receipt)
        change = received - receipt.total if received is not None else Decimal(0)
        wants_print = self.view.wants_receipt()
        if wants_print:
            self._print_in_background(receipt, received, change)
        self.reset_sale()
        self._show_category(self._category)
        on_print = (lambda: self._print_in_background(receipt, received, change)) if self.printer.enabled else None
        self.main_controller.show_voucher_view(receipt, received, change, on_print)

    def _print_in_background(self, receipt: Receipt, received: Decimal | None, change: Decimal) -> None:
        """Imprime en un hilo aparte para que la caja nunca se congele esperando la impresora."""
        if not self.printer.enabled:
            return

        def job() -> None:
            try:
                self.printer.print_receipt(receipt, received, change)
            except PrinterError as exc:
                self._print_errors.put(str(exc))
            except Exception:
                logger.exception("Error inesperado imprimiendo el recibo %s", receipt.id)
                self._print_errors.put("Error inesperado al imprimir. Revise logs/app.log.")

        threading.Thread(target=job, name=f"{PRINT_THREAD_PREFIX}{receipt.id}", daemon=True).start()
        if not self._polling_printer:
            self._polling_printer = True
            self.view.after(PRINT_POLL_MS, self._poll_print_errors)

    def _poll_print_errors(self) -> None:
        """Corre en el hilo de la interfaz: muestra los errores que dejaron los hilos de impresión."""
        self._show_pending_print_errors()
        still_printing = any(t.name.startswith(PRINT_THREAD_PREFIX) for t in threading.enumerate())
        if still_printing:
            self.view.after(PRINT_POLL_MS, self._poll_print_errors)
        else:
            self._show_pending_print_errors()
            self._polling_printer = False

    def _show_pending_print_errors(self) -> None:
        while True:
            try:
                message = self._print_errors.get_nowait()
            except queue.Empty:
                return
            messagebox.showwarning("Impresión", f"{message}\nLa venta quedó registrada.")
