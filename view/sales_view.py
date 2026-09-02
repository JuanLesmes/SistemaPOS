"""Pantalla de ventas."""

from __future__ import annotations

import tkinter as tk
from decimal import Decimal
from tkinter import ttk

import customtkinter as ctk

from model.sold_product import SoldProduct
from utils.formatters import format_price
from view import theme

COLUMNS = (
    ("codigo", "Código", 130, "w"),
    ("nombre", "Nombre", 320, "w"),
    ("precio", "Precio", 120, "e"),
    ("cantidad", "Cantidad", 90, "center"),
    ("subtotal", "Subtotal", 130, "e"),
)


class SalesView(ctk.CTkFrame):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent, fg_color=theme.BACKGROUND)
        self.controller = controller
        self.pack(fill="both", expand=True)
        self._create_widgets()
        self.recibe_entry.bind("<Return>", lambda _event: self.controller.event_cash_payment())

    def _create_widgets(self) -> None:
        button_style = {"corner_radius": 12, "height": 50, "width": 200, "font": theme.font(16, bold=True)}

        header = ctk.CTkFrame(self, fg_color=theme.HEADER, corner_radius=0)
        header.pack(side="top", fill="x", ipady=5)
        ctk.CTkLabel(header, text="Venta de productos", text_color=theme.BLACK, font=theme.font(20, bold=True)).pack(
            side="left", padx=20
        )
        ctk.CTkButton(
            header,
            text="Volver al menú",
            fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER,
            text_color=theme.BLACK,
            command=self.controller.event_back,
            **button_style,
        ).pack(side="right", padx=20)

        main = ctk.CTkFrame(self, fg_color=theme.BACKGROUND)
        main.pack(side="top", fill="both", expand=True, padx=20, pady=10)

        table_frame = ctk.CTkFrame(
            main, fg_color=theme.WHITE, corner_radius=8, border_width=1, border_color=theme.BORDER
        )
        table_frame.pack(side="left", fill="both", expand=True, padx=(0, 20))

        self.tree = ttk.Treeview(
            table_frame,
            columns=[c[0] for c in COLUMNS],
            show="headings",
            style=theme.table_style("Sales"),
            selectmode="browse",
        )
        scrollbar = ctk.CTkScrollbar(table_frame, command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
        for key, title, width, anchor in COLUMNS:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, anchor=anchor)
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        sidebar = ctk.CTkFrame(main, fg_color=theme.BACKGROUND, width=280)
        sidebar.pack(side="right", fill="y")

        ctk.CTkButton(
            sidebar,
            text="Quitar producto",
            fg_color=theme.DANGER,
            hover_color=theme.DANGER_HOVER,
            text_color=theme.WHITE,
            command=self.controller.event_remove_line,
            **button_style,
        ).pack(fill="x", pady=5)

        ctk.CTkLabel(sidebar, text="Recibe:", text_color=theme.BLACK, font=theme.font(14)).pack(
            anchor="w", pady=(20, 5)
        )
        self.recibe_entry = ctk.CTkEntry(
            sidebar,
            placeholder_text="0",
            fg_color=theme.WHITE,
            text_color=theme.BLACK,
            corner_radius=10,
            height=35,
            font=theme.font(14),
        )
        self.recibe_entry.pack(fill="x")

        self.total_label = ctk.CTkLabel(
            sidebar, text="Total: $0", text_color=theme.BLACK, font=theme.font(18, bold=True)
        )
        self.total_label.pack(anchor="w", pady=(20, 0))

        self._printer_available = True
        self.print_var = tk.BooleanVar(value=False)
        self.print_switch = ctk.CTkSwitch(
            sidebar,
            text="Imprimir recibo",
            variable=self.print_var,
            font=theme.font(14, bold=True),
            text_color=theme.BLACK,
            progress_color=theme.SUCCESS,
        )
        self.print_switch.pack(anchor="w", pady=(25, 4))
        self.print_hint = ctk.CTkLabel(
            sidebar,
            text="Actívelo antes de cobrar si el cliente quiere el recibo en papel.",
            text_color=theme.MUTED,
            font=theme.font(11),
            wraplength=260,
            justify="left",
        )
        self.print_hint.pack(anchor="w")

        pay_frame = ctk.CTkFrame(self, fg_color=theme.BACKGROUND, height=80)
        pay_frame.pack(side="bottom", fill="x", padx=20, pady=10)
        pay_style = {**button_style, "width": 300, "height": 40}
        for text, command in (
            ("Pago en efectivo", self.controller.event_cash_payment),
            ("Pago con tarjeta", self.controller.event_card_payment),
            ("Transferencia", self.controller.event_transfer_payment),
        ):
            ctk.CTkButton(
                pay_frame,
                text=text,
                fg_color=theme.PRIMARY,
                hover_color=theme.PRIMARY_HOVER,
                text_color=theme.WHITE,
                command=command,
                **pay_style,
            ).pack(side="left", padx=10, expand=True)

    # ------------------------------------------------------------------ API para el controlador
    def load_table(self, lines: list[SoldProduct]) -> None:
        theme.clear_table(self.tree)
        for sp in lines:
            self.tree.insert(
                "",
                "end",
                values=(
                    sp.code,
                    sp.product.name,
                    format_price(sp.unit_price),
                    sp.quantity,
                    format_price(sp.total),
                ),
            )

    def selected_index(self) -> int | None:
        selection = self.tree.selection()
        return self.tree.index(selection[0]) if selection else None

    def set_total(self, total: Decimal) -> None:
        self.total_label.configure(text=f"Total: ${format_price(total)}")

    def get_received_amount(self) -> str:
        return self.recibe_entry.get().strip()

    def clear_received_amount(self) -> None:
        self.recibe_entry.delete(0, "end")

    def wants_receipt(self) -> bool:
        """True solo si el cajero activó "Imprimir recibo" para esta venta."""
        return self._printer_available and bool(self.print_var.get())

    def reset_print_option(self) -> None:
        self.print_var.set(False)

    def set_printer_available(self, available: bool) -> None:
        self._printer_available = available
        if available:
            self.print_switch.configure(state="normal")
            self.print_hint.configure(text="Actívelo antes de cobrar si el cliente quiere el recibo en papel.")
        else:
            self.print_var.set(False)
            self.print_switch.configure(state="disabled")
            self.print_hint.configure(text="Impresora desactivada en config.json.")
