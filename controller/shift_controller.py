"""Cierre de caja por turno con arqueo."""

from __future__ import annotations

import tkinter as tk
from decimal import Decimal
from tkinter import messagebox

from controller.common import guarded
from model.db_connection import DBConnection
from model.shift import Shift, count_total
from utils.formatters import format_price, parse_money
from view.dialogs import ask_form
from view.shift_view import ShiftView


class ShiftController:
    def __init__(self, parent: tk.Frame, main_controller, db: DBConnection) -> None:
        self.main_controller = main_controller
        self.db = db
        self.view = ShiftView(parent, self)
        self.ask_form = ask_form  # reemplazable en pruebas

    @guarded
    def refresh(self) -> None:
        shift = self.db.get_open_shift()
        self.view.show_summary(self.db.shift_summary(shift.id) if shift else None)
        self.view.show_history(self.db.list_shifts())

    def event_back(self) -> None:
        self.main_controller.show_menu()

    @guarded
    def event_open_shift(self) -> None:
        self.open_shift_interactively()
        self.refresh()

    def open_shift_interactively(self) -> Shift | None:
        """Pide la base inicial y abre el turno. Devuelve None si el usuario cancela."""
        data = self.ask_form(
            self.view,
            "Abrir turno de caja",
            [("opening_cash", "Base inicial en efectivo", "")],
            intro="Dinero con el que arranca la caja para dar cambio.",
            submit_text="Abrir turno",
        )
        if data is None:
            return None
        opening = parse_money(data["opening_cash"]) if data["opening_cash"].strip() else Decimal(0)
        shift = self.db.open_shift(opening)
        messagebox.showinfo("Turno abierto", f"Turno {shift.id} abierto con base ${format_price(opening)}.")
        return shift

    @guarded
    def event_close_shift(self) -> None:
        shift = self.db.get_open_shift()
        if shift is None:
            messagebox.showinfo("Cierre de caja", "No hay un turno abierto.")
            return
        summary = self.db.shift_summary(shift.id)
        counted = count_total(self.view.get_counts())
        difference = counted - summary.expected_cash
        if difference == 0:
            detail = "El efectivo cuadra exacto."
        elif difference > 0:
            detail = f"Sobran ${format_price(difference)}."
        else:
            detail = f"Faltan ${format_price(-difference)}."
        if not messagebox.askyesno(
            "Cerrar turno",
            f"Efectivo esperado: ${format_price(summary.expected_cash)}\n"
            f"Efectivo contado: ${format_price(counted)}\n{detail}\n\n¿Cerrar el turno?",
        ):
            return
        closed = self.db.close_shift(shift.id, counted, self.view.get_notes())
        self.main_controller.print_shift_close(summary, closed)
        self.view.reset_counts()
        self.refresh()
        messagebox.showinfo("Turno cerrado", f"Turno {closed.id} cerrado. {detail}")
