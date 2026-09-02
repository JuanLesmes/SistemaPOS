"""Pantalla de ventas: catálogo, lectura de códigos, cola de ventas, descuentos y cobro.

La caja puede tener varias ventas abiertas (un cliente con afán, otro
indeciso). Solo una está activa; las demás esperan con sus productos y su
monto recibido intactos hasta que el cajero las retoma. Toda venta se
registra dentro del turno de caja abierto.
"""

from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
from collections.abc import Callable
from decimal import ROUND_HALF_UP, Decimal
from tkinter import messagebox

from controller.common import guarded
from model import permissions
from model.db_connection import DBConnection
from model.errors import AppError, PrinterError
from model.pending_sale import PendingSale
from model.product import Product
from model.receipt import (
    PAYMENT_CARD,
    PAYMENT_CASH,
    PAYMENT_METHODS,
    PAYMENT_MIXED,
    PAYMENT_TRANSFER,
    Payment,
    Receipt,
)
from model.shift import Shift, ShiftSummary
from model.sold_product import SoldProduct
from utils.barcode_reader import BarcodeReader
from utils.formatters import format_money_input, format_price, parse_money
from utils.printer_manager import ReceiptPrinter
from view.dialogs import ask_form
from view.sales_view import ALL_CATEGORIES, BEST_SELLERS, SalesView
from view.widgets import Keypad

logger = logging.getLogger(__name__)

PRINT_POLL_MS = 250
PRINT_THREAD_PREFIX = "printer-job-"
PAGE_SIZE = 60
SEARCH_DEBOUNCE_MS = 250
BEST_SELLER_DAYS = 30
MAX_PENDING_SALES = 8
ZERO = Decimal(0)

SCOPE_LINE = "Línea seleccionada"
SCOPE_SALE = "Toda la venta"
MODE_PERCENT = "Porcentaje"
MODE_AMOUNT = "Valor en pesos"


class SalesViewController:
    def __init__(self, parent: tk.Frame, main_controller, db: DBConnection) -> None:
        self.main_controller = main_controller
        self.db = db
        self.sales: list[PendingSale] = self._load_pending_sales()
        self._next_number = max((sale.number for sale in self.sales), default=0) + 1
        self.active: PendingSale = self.sales[0] if self.sales else self._create_sale()
        self.shift: Shift | None = None
        self.view = SalesView(parent, self)
        self.ask_form = ask_form  # reemplazable en pruebas

        settings = main_controller.settings
        self.printer = ReceiptPrinter(settings.printer, settings.business)
        self.view.set_printer_available(self.printer.enabled)
        self.reader = BarcodeReader(self.view.winfo_toplevel(), self.on_barcode)
        self._print_errors: queue.Queue[str] = queue.Queue()
        self._polling_printer = False
        self._category = ALL_CATEGORIES
        self._search_job: str | None = None
        self.refresh_catalog()
        self._activate(self.active)

    @property
    def lines(self) -> list[SoldProduct]:
        return self.active.lines

    def _load_pending_sales(self) -> list[PendingSale]:
        try:
            sales = self.db.load_pending_sales()
        except AppError:
            logger.exception("No se pudieron recuperar las ventas en espera")
            return []
        if sales:
            logger.info("Ventas en espera recuperadas: %s", len(sales))
        return sales

    # ------------------------------------------------------------------ ciclo de vida
    def on_show(self) -> bool:
        """Prepara la pantalla. Devuelve False si no hay turno abierto y el cajero no abrió uno."""
        if not self._ensure_shift():
            return False
        self.refresh_catalog()
        self._refresh()
        self.reader.enable()
        self.view.focus_set()
        return True

    def on_hide(self) -> None:
        self.reader.disable()
        self._store_active_inputs()
        self._persist(self.active)

    # ------------------------------------------------------------------ turno de caja
    def _ensure_shift(self) -> bool:
        self.shift = self.db.get_open_shift()
        if self.shift is None:
            self.shift = self.main_controller.shift_controller.open_shift_interactively()
        if self.shift is None:
            messagebox.showwarning("Turno de caja", "Para vender hay que abrir un turno con la base inicial.")
            return False
        opened = self.shift.opened_at.strftime("%H:%M")
        self.view.set_shift_text(
            f"Turno {self.shift.id} abierto a las {opened} por {self.shift.opened_by or '-'}  ·  "
            f"base ${format_price(self.shift.opening_cash)}"
        )
        return True

    def event_shift(self) -> None:
        self.main_controller.show_shift_view()

    def print_shift_close(self, summary: ShiftSummary, shift: Shift) -> None:
        self._run_print_job(f"cierre-{shift.id}", lambda: self.printer.print_shift_close(summary, shift))

    # ------------------------------------------------------------------ cola de ventas
    def _create_sale(self) -> PendingSale:
        sale = PendingSale(number=self._next_number)
        self._next_number += 1
        self.sales.append(sale)
        return sale

    def _activate(self, sale: PendingSale) -> None:
        self.active = sale
        self.view.set_received_amount(sale.received_text)
        self.view.print_var.set(sale.wants_receipt)
        self._refresh()

    def _store_active_inputs(self) -> None:
        self.active.received_text = self.view.get_received_amount()
        self.active.wants_receipt = bool(self.view.print_var.get())

    def _persist(self, sale: PendingSale) -> None:
        """Guarda la venta en la base para que sobreviva a un cierre; nunca bloquea la caja."""
        try:
            if sale.is_empty:
                if sale.db_id is not None:
                    self.db.delete_pending_sale(sale.db_id)
                    sale.db_id = None
            else:
                sale.db_id = self.db.save_pending_sale(sale)
        except AppError:
            logger.exception("No se pudo guardar la venta en espera %s", sale.number)

    def _close_active(self) -> None:
        """Saca la venta activa de la cola y pasa a la más antigua en espera, o a una nueva."""
        closing = self.active
        self.sales.remove(closing)
        if closing.db_id is not None:
            try:
                self.db.delete_pending_sale(closing.db_id)
            except AppError:
                logger.exception("No se pudo borrar la venta en espera %s", closing.number)
        self._activate(self.sales[0] if self.sales else self._create_sale())

    @guarded
    def event_new_sale(self) -> None:
        if len(self.sales) >= MAX_PENDING_SALES:
            messagebox.showwarning(
                "Cola llena", f"Ya hay {MAX_PENDING_SALES} ventas abiertas. Cobre o cancele alguna antes de abrir otra."
            )
            return
        self._store_active_inputs()
        self._persist(self.active)
        self._activate(self._create_sale())
        self.view.focus_set()

    @guarded
    def event_switch_sale(self, number: int) -> None:
        if number == self.active.number:
            return
        target = next((sale for sale in self.sales if sale.number == number), None)
        if target is None:
            return
        self._store_active_inputs()
        self._persist(self.active)
        self._activate(target)
        self.view.focus_set()

    @guarded
    def event_cancel_sale(self) -> None:
        """Cancela la venta activa. Si es la única, simplemente la deja vacía."""
        if self.lines and not messagebox.askyesno(
            "Cancelar venta", f"¿Cancelar la venta {self.active.number} con {self.active.item_count} productos?"
        ):
            return
        self._close_active()

    def _reserved_elsewhere(self, code: str) -> int:
        """Unidades del producto que ya están en otras ventas en espera."""
        return sum(sale.quantity_of(code) for sale in self.sales if sale is not self.active)

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

    @guarded
    def refresh_catalog(self) -> None:
        self.view.set_categories(self.db.get_categories())
        self.view.clear_search()
        self._show_category(self._category)

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

    # ------------------------------------------------------------------ venta activa
    def add_line(self, product: Product, quantity: int = 1) -> None:
        """Agrega unidades de un producto; si ya está en la venta, suma a esa línea."""
        existing = next((sp for sp in self.lines if sp.code == product.code), None)
        wanted = quantity + (existing.quantity if existing else 0)
        if not self._stock_allows(product, wanted):
            return
        if existing is not None:
            existing.quantity = wanted
        else:
            self.lines.append(SoldProduct(product=product, quantity=quantity))
        self._refresh()
        self.view.select_index(self.lines.index(existing) if existing is not None else len(self.lines) - 1)

    def _stock_allows(self, product: Product, wanted: int) -> bool:
        reserved = self._reserved_elsewhere(product.code)
        if wanted + reserved <= product.stock:
            return True
        if reserved:
            messagebox.showwarning(
                "Sin existencias",
                f"'{product.name}' tiene {product.stock} unidades y {reserved} ya están en otra venta en espera.",
            )
        else:
            messagebox.showwarning(
                "Sin existencias", f"'{product.name}' solo tiene {product.stock} unidades disponibles."
            )
        return False

    @guarded
    def event_increase(self) -> None:
        index = self._selected_line_index()
        if index is None:
            return
        line = self.lines[index]
        fresh = self.db.get_product(line.code)
        if fresh is None or not self._stock_allows(fresh, line.quantity + 1):
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
            line.discount = min(line.discount, line.gross)
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
    def event_discount(self) -> None:
        if not self.main_controller.has_permission(permissions.DISCOUNT):
            messagebox.showwarning("Sin permiso", "Solo un supervisor o administrador puede aplicar descuentos.")
            return
        if not self.lines:
            self._warn_empty_sale()
            return
        selected = self.view.selected_index()
        data = self.ask_form(
            self.view,
            "Aplicar descuento",
            [
                ("scope", "Aplicar a", SCOPE_LINE if selected is not None else SCOPE_SALE, (SCOPE_LINE, SCOPE_SALE)),
                ("mode", "Tipo", MODE_PERCENT, (MODE_PERCENT, MODE_AMOUNT)),
                ("value", "Valor (porcentaje o pesos). 0 quita el descuento", ""),
            ],
            intro=f"Total actual de la venta: ${format_price(self.total())}",
            submit_text="Aplicar",
        )
        if data is None:
            return
        value = parse_money(data["value"]) if data["value"].strip() else ZERO
        if data["scope"] == SCOPE_LINE:
            if selected is None or selected >= len(self.lines):
                raise ValueError("Seleccione en la tabla la línea a la que aplica el descuento.")
            line = self.lines[selected]
            amount = _discount_amount(line.gross, data["mode"], value)
            line.discount = amount
        else:
            self.active.discount_total = _discount_amount(self.active.gross, data["mode"], value)
        self._refresh()
        if selected is not None:
            self.view.select_index(selected)

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

    @guarded
    def event_mixed_payment(self) -> None:
        if not self.lines:
            self._warn_empty_sale()
            return
        total = self.total()
        data = self.ask_form(
            self.view,
            "Pago mixto",
            [
                (method, method, format_money_input(total) if method == PAYMENT_CASH else "")
                for method in PAYMENT_METHODS
            ],
            intro=f"Reparta el total de ${format_price(total)} entre los métodos de pago.",
            submit_text="Cobrar",
        )
        if data is None:
            return
        payments = [
            Payment(method, parse_money(data[method]) if data[method].strip() else ZERO) for method in PAYMENT_METHODS
        ]
        paid = sum((p.amount for p in payments), ZERO)
        if paid != total:
            raise ValueError(f"Los pagos suman ${format_price(paid)} y la venta vale ${format_price(total)}.")
        self._checkout(PAYMENT_MIXED, payments=payments)

    def event_back(self) -> None:
        self.main_controller.show_menu()

    # ------------------------------------------------------------------ apoyo
    def total(self) -> Decimal:
        return self.active.total

    def _received_or_zero(self) -> Decimal:
        try:
            return parse_money(self.view.get_received_amount())
        except ValueError:
            return ZERO

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
        self.view.set_discount(self.active.line_discounts, self.active.discount_total)
        self.view.set_total(self.total())
        self.view.show_queue(self.sales, self.active.number)
        self._update_change()
        self._store_active_inputs()
        self._persist(self.active)

    def _warn_empty_sale(self) -> None:
        messagebox.showwarning("Venta vacía", "Agregue productos antes de cobrar.")

    def _checkout(
        self, payment_method: str, received: Decimal | None = None, payments: list[Payment] | None = None
    ) -> None:
        if not self.lines:
            self._warn_empty_sale()
            return
        if self.shift is None and not self._ensure_shift():
            return
        receipt = Receipt.create(
            payment_method,
            self.lines,
            discount_total=self.active.discount_total,
            payments=payments,
            shift_id=self.shift.id if self.shift else None,
        )
        user = self.main_controller.current_user
        receipt.cashier = user.username if user is not None else None
        receipt.id = self.db.add_receipt(receipt)
        change = received - receipt.total if received is not None else ZERO
        if receipt.paid_with(PAYMENT_CASH) > 0 and self.printer.drawer_enabled:
            self._run_print_job(f"cajon-{receipt.id}", self.printer.open_drawer)
        if self.view.wants_receipt():
            self._print_in_background(receipt, received, change)
        self._close_active()
        self._show_category(self._category)
        on_print = (lambda: self._print_in_background(receipt, received, change)) if self.printer.enabled else None
        self.main_controller.show_voucher_view(receipt, received, change, on_print)

    def _print_in_background(self, receipt: Receipt, received: Decimal | None, change: Decimal) -> None:
        """Imprime en un hilo aparte para que la caja nunca se congele esperando la impresora."""
        if not self.printer.enabled:
            return
        self._run_print_job(f"recibo-{receipt.id}", lambda: self.printer.print_receipt(receipt, received, change))

    def _run_print_job(self, name: str, job: Callable[[], None]) -> None:
        def run() -> None:
            try:
                job()
            except PrinterError as exc:
                self._print_errors.put(str(exc))
            except Exception:
                logger.exception("Error inesperado en la impresora (%s)", name)
                self._print_errors.put("Error inesperado al imprimir. Revise logs/app.log.")

        threading.Thread(target=run, name=f"{PRINT_THREAD_PREFIX}{name}", daemon=True).start()
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


def _discount_amount(base: Decimal, mode: str, value: Decimal) -> Decimal:
    """Convierte el valor del diálogo en pesos de descuento, acotado al valor base."""
    if value < 0:
        raise ValueError("El descuento no puede ser negativo.")
    if mode == MODE_PERCENT:
        if value > 100:
            raise ValueError("El porcentaje no puede ser mayor que 100.")
        amount = (base * value / 100).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    else:
        amount = value
    if amount > base:
        raise ValueError(f"El descuento no puede superar ${format_price(base)}.")
    return amount
