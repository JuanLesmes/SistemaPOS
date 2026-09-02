"""Diálogo para devolver productos de un recibo: cantidad por línea y motivo."""

from __future__ import annotations

import customtkinter as ctk

from model.receipt import Receipt
from utils.formatters import format_price
from view import theme
from view.dialogs import ENTRY_STYLE, _center_over
from view.widgets import button, section_label


class ReturnDialog(ctk.CTkToplevel):
    """``result`` es (items, motivo) con items = [(código, cantidad)], o None si se cancela."""

    def __init__(self, parent, receipt: Receipt, already_returned: dict[str, int] | None = None) -> None:
        super().__init__(parent)
        self.result: tuple[list[tuple[str, int]], str] | None = None
        self._entries: dict[str, ctk.CTkEntry] = {}
        already_returned = already_returned or {}
        self.title(f"Devolución del recibo {receipt.id}")
        self.configure(fg_color=theme.SURFACE)
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=20)
        ctk.CTkLabel(
            body, text=f"Devolución del recibo {receipt.id}", font=theme.font(18, bold=True), text_color=theme.TEXT
        ).pack(anchor="w")
        ctk.CTkLabel(
            body,
            text="Escriba cuántas unidades devuelve el cliente. Vuelven al inventario y se reembolsa su valor.",
            font=theme.font(12),
            text_color=theme.MUTED,
            anchor="w",
            wraplength=520,
            justify="left",
        ).pack(anchor="w", pady=(2, 10))

        grid = ctk.CTkFrame(body, fg_color="transparent")
        grid.pack(fill="x")
        grid.grid_columnconfigure(0, weight=1)
        for column, text in enumerate(("Producto", "Vendidas", "Devueltas", "Devolver ahora")):
            section_label(grid, text).grid(row=0, column=column, sticky="w", padx=(0, 12), pady=(0, 4))
        merged: dict[str, tuple[str, int]] = {}
        for sp in receipt.sold_products:
            name, qty = merged.get(sp.code, (sp.product.name, 0))
            merged[sp.code] = (name, qty + sp.quantity)
        for row, (code, (name, sold)) in enumerate(merged.items(), start=1):
            returned = already_returned.get(code, 0)
            ctk.CTkLabel(grid, text=name, font=theme.font(13), text_color=theme.TEXT, anchor="w").grid(
                row=row, column=0, sticky="w", padx=(0, 12), pady=3
            )
            ctk.CTkLabel(grid, text=str(sold), font=theme.font(13), text_color=theme.MUTED).grid(
                row=row, column=1, padx=(0, 12)
            )
            ctk.CTkLabel(grid, text=str(returned), font=theme.font(13), text_color=theme.MUTED).grid(
                row=row, column=2, padx=(0, 12)
            )
            entry = ctk.CTkEntry(grid, width=110, placeholder_text="0", **ENTRY_STYLE)
            entry.grid(row=row, column=3, pady=3)
            if sold - returned <= 0:
                entry.configure(state="disabled")
            self._entries[code] = entry

        section_label(body, "Motivo").pack(anchor="w", pady=(14, 4))
        self.reason_entry = ctk.CTkEntry(body, width=520, placeholder_text="ej. producto defectuoso", **ENTRY_STYLE)
        self.reason_entry.pack(fill="x")
        ctk.CTkLabel(
            body, text=f"Total del recibo: ${format_price(receipt.total)}", font=theme.font(12), text_color=theme.MUTED
        ).pack(anchor="w", pady=(8, 0))

        actions = ctk.CTkFrame(body, fg_color="transparent")
        actions.pack(fill="x", pady=(18, 0))
        button(actions, "Registrar devolución", self._submit, kind="danger", width=200).pack(side="right")
        button(actions, "Cancelar", self._cancel, kind="ghost", width=120).pack(side="right", padx=(0, 10))
        self.bind("<Escape>", lambda _event: self._cancel())
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        _center_over(self, parent.winfo_toplevel())
        self.grab_set()

    def _submit(self) -> None:
        items: list[tuple[str, int]] = []
        for code, entry in self._entries.items():
            text = entry.get().strip()
            if text:
                items.append((code, int(text) if text.isdigit() else -1))
        self.result = (items, self.reason_entry.get().strip())
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()


def ask_return(parent, receipt: Receipt, already_returned: dict[str, int] | None = None):
    dialog = ReturnDialog(parent, receipt, already_returned)
    parent.wait_window(dialog)
    return dialog.result
