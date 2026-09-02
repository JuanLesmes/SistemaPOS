"""Registro de auditoría: lista de eventos del día y detalle antes/después."""

from __future__ import annotations

import datetime as dt
import tkinter as tk
from tkinter import ttk

import customtkinter as ctk
from tkcalendar import DateEntry

from model.audit_log import AuditEntry
from view import theme

SUMMARY_COLUMNS = (
    ("timestamp", "Fecha y hora", 150),
    ("action", "Acción", 150),
    ("code", "Código", 120),
)


class AuditLogView(tk.Frame):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent, bg=theme.BACKGROUND)
        self.controller = controller
        self._entries: list[AuditEntry] = []
        self._create_widgets()

    def _create_widgets(self) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)

        filters = ctk.CTkFrame(self, fg_color=theme.HEADER, corner_radius=0)
        filters.grid(row=0, column=0, columnspan=2, sticky="ew")
        filters.grid_columnconfigure(2, weight=1)
        ctk.CTkLabel(filters, text="Auditoría", text_color=theme.BLACK, font=theme.font(20, bold=True)).grid(
            row=0, column=0, padx=20, pady=12
        )
        self.date_picker = DateEntry(
            filters, date_pattern="yyyy-mm-dd", background="white", foreground="black", borderwidth=1, locale="es_CO"
        )
        self.date_picker.grid(row=0, column=1, padx=(0, 8), pady=12)
        ctk.CTkButton(
            filters,
            text="Cargar",
            width=110,
            fg_color=theme.PRIMARY,
            hover_color=theme.PRIMARY_HOVER,
            text_color=theme.WHITE,
            font=theme.font(13, bold=True),
            corner_radius=8,
            command=self._on_load_click,
        ).grid(row=0, column=2, sticky="w", pady=12)
        ctk.CTkButton(
            filters,
            text="Volver al menú",
            fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER,
            text_color=theme.BLACK,
            font=theme.font(13, bold=True),
            corner_radius=8,
            command=self.controller.event_back,
        ).grid(row=0, column=3, sticky="e", padx=20, pady=12)

        left = ctk.CTkFrame(self, fg_color=theme.WHITE, corner_radius=8)
        left.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=10)
        left.grid_rowconfigure(0, weight=1)
        left.grid_columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(
            left,
            columns=[c[0] for c in SUMMARY_COLUMNS],
            show="headings",
            selectmode="browse",
            style=theme.table_style("Audit", row_height=24),
        )
        for key, title, width in SUMMARY_COLUMNS:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, stretch=True)
        summary_scroll = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=summary_scroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        summary_scroll.grid(row=0, column=1, sticky="ns", pady=6)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        right = ctk.CTkFrame(self, fg_color=theme.WHITE, corner_radius=8)
        right.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=10)
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            right, text="Cambios (antes y después)", font=theme.font(13, bold=True), text_color=theme.BLACK
        ).grid(row=0, column=0, sticky="w", padx=8, pady=(8, 4))
        self.details = ttk.Treeview(
            right,
            columns=("field", "before", "after"),
            show="headings",
            style=theme.table_style("AuditDetail", row_height=24),
        )
        self.details.heading("field", text="Campo")
        self.details.heading("before", text="Antes")
        self.details.heading("after", text="Después")
        self.details.column("field", width=120, stretch=False)
        self.details.column("before", width=220, stretch=True)
        self.details.column("after", width=220, stretch=True)
        detail_scroll = ttk.Scrollbar(right, orient="vertical", command=self.details.yview)
        self.details.configure(yscrollcommand=detail_scroll.set)
        self.details.grid(row=1, column=0, sticky="nsew", padx=(6, 0), pady=(0, 6))
        detail_scroll.grid(row=1, column=1, sticky="ns", pady=(0, 6))

    # ------------------------------------------------------------------ API para el controlador
    def set_date(self, day: dt.date) -> None:
        self.date_picker.set_date(day)

    def show_logs(self, entries: list[AuditEntry]) -> None:
        self._entries = list(entries)
        theme.clear_table(self.tree)
        theme.clear_table(self.details)
        for index, entry in enumerate(self._entries):
            self.tree.insert(
                "",
                "end",
                iid=str(index),
                values=(entry.timestamp.strftime("%Y-%m-%d %H:%M:%S"), entry.action, entry.code or ""),
            )
        children = self.tree.get_children()
        if children:
            self.tree.selection_set(children[0])
            self._show_details(0)

    # ------------------------------------------------------------------ interno
    def _on_load_click(self) -> None:
        self.controller.event_load_logs(self.date_picker.get_date())

    def _on_select(self, _event) -> None:
        selection = self.tree.selection()
        if selection:
            self._show_details(int(selection[0]))

    def _show_details(self, index: int) -> None:
        theme.clear_table(self.details)
        before, after = self._entries[index].changes()
        for key in sorted(set(before) | set(after)):
            self.details.insert("", "end", values=(key, str(before.get(key, "")), str(after.get(key, ""))))
