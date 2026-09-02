"""Registro de auditoría: eventos del día y detalle antes/después."""

from __future__ import annotations

import datetime as dt

import customtkinter as ctk
from tkcalendar import DateEntry

from model.audit_log import AuditEntry
from view import theme
from view.widgets import Card, HeaderBar, button, fill_table, make_table, section_label

SUMMARY_COLUMNS = (
    ("timestamp", "Fecha y hora", 160, "w", False),
    ("action", "Acción", 190, "w"),
    ("code", "Código", 140, "w", False),
)
DETAIL_COLUMNS = (
    ("field", "Campo", 130, "w", False),
    ("before", "Antes", 240, "w"),
    ("after", "Después", 240, "w"),
)

ACTION_LABELS = {
    "add_product": "Producto creado",
    "modify_product": "Producto modificado",
    "deactivate_product": "Producto eliminado",
    "delete_product": "Producto eliminado",
    "reactivate_product": "Producto reactivado",
    "update_stock": "Existencias ajustadas",
    "add_category": "Categoría creada",
    "delete_category": "Categoría eliminada",
}

FIELD_LABELS = {
    "name": "Nombre",
    "cost": "Costo",
    "price": "Precio",
    "stock": "Existencias",
    "category": "Categoría",
    "description": "Descripción",
    "category_name": "Categoría",
    "detalle": "Detalle",
}


class AuditLogView(ctk.CTkFrame):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent, fg_color=theme.BACKGROUND, corner_radius=0)
        self.controller = controller
        self._entries: list[AuditEntry] = []
        self.pack(fill="both", expand=True)
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=2, uniform="panels")
        self.grid_columnconfigure(1, weight=3, uniform="panels")
        self.grid_rowconfigure(2, weight=1)

        header = HeaderBar(self, "Auditoría", "Cambios del catálogo registrados por día")
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.add_action("Volver al menú", self.controller.event_back)

        filters = Card(self, padding=12)
        filters.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=(14, 12))
        body = filters.body
        section_label(body, "Fecha").pack(side="left", padx=(0, 8))
        self.date_picker = DateEntry(
            body,
            width=12,
            font=theme.font(13),
            background=theme.PRIMARY,
            foreground=theme.ON_DARK,
            headersbackground=theme.SURFACE_ALT,
            normalbackground=theme.SURFACE,
            weekendbackground=theme.SURFACE,
            selectbackground=theme.PRIMARY,
            borderwidth=1,
            date_pattern="yyyy-mm-dd",
            locale="es_CO",
        )
        self.date_picker.pack(side="left")
        button(body, "Cargar", self._on_load_click, kind="primary", size="sm", height=40, width=110).pack(
            side="left", padx=(12, 0)
        )
        button(body, "Hoy", lambda: self.controller.load_today(), kind="ghost", size="sm", height=40, width=80).pack(
            side="left", padx=(6, 0)
        )
        self.count_label = ctk.CTkLabel(body, text="", font=theme.font(12), text_color=theme.MUTED)
        self.count_label.pack(side="right")

        events = Card(self, "Eventos", padding=10)
        events.grid(row=2, column=0, sticky="nsew", padx=(16, 6), pady=(0, 16))
        events_box = ctk.CTkFrame(events.body, fg_color="transparent")
        events_box.pack(fill="both", expand=True)
        self.tree = make_table(events_box, SUMMARY_COLUMNS, "Audit")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        details = Card(self, "Cambios (antes y después)", padding=10)
        details.grid(row=2, column=1, sticky="nsew", padx=(6, 16), pady=(0, 16))
        details_box = ctk.CTkFrame(details.body, fg_color="transparent")
        details_box.pack(fill="both", expand=True)
        self.details = make_table(details_box, DETAIL_COLUMNS, "AuditDetail")

    # ------------------------------------------------------------------ API para el controlador
    def set_date(self, day: dt.date) -> None:
        self.date_picker.set_date(day)

    def show_logs(self, entries: list[AuditEntry]) -> None:
        self._entries = list(entries)
        fill_table(
            self.tree,
            (
                (
                    entry.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    ACTION_LABELS.get(entry.action, entry.action),
                    entry.code or "",
                )
                for entry in self._entries
            ),
            empty_message="No hay eventos en esta fecha",
        )
        self.count_label.configure(text=f"{len(self._entries)} eventos")
        theme.clear_table(self.details)
        children = self.tree.get_children()
        if self._entries and children:
            self.tree.selection_set(children[0])
            self._show_details(0)

    # ------------------------------------------------------------------ interno
    def _on_load_click(self) -> None:
        self.controller.event_load_logs(self.date_picker.get_date())

    def _on_select(self, _event) -> None:
        selection = self.tree.selection()
        if selection:
            index = self.tree.index(selection[0])
            if index < len(self._entries):
                self._show_details(index)

    def _show_details(self, index: int) -> None:
        before, after = self._entries[index].changes()
        fill_table(
            self.details,
            (
                (FIELD_LABELS.get(key, key), str(before.get(key, "")), str(after.get(key, "")))
                for key in sorted(set(before) | set(after))
            ),
            empty_message="Sin detalle",
        )
