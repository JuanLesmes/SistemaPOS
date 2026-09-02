"""Registro de auditoría: eventos del día con color según el tipo de cambio y detalle antes/después.

Verde: se creó o ingresó algo. Rojo: se eliminó, retiró o anuló. Amarillo: se
modificó un dato. Blanco: ventas y turnos, que son movimiento normal.
"""

from __future__ import annotations

import datetime as dt

import customtkinter as ctk
from tkcalendar import DateEntry

from model.audit_log import AuditEntry
from view import theme
from view.widgets import Card, HeaderBar, button, fill_table, make_table, section_label

SUMMARY_COLUMNS = (
    ("timestamp", "Fecha y hora", 150, "w", False),
    ("action", "Acción", 190, "w"),
    ("code", "Código o recibo", 140, "w", False),
    ("user", "Usuario", 110, "w", False),
)
DETAIL_COLUMNS = (
    ("field", "Campo", 130, "w", False),
    ("before", "Antes", 240, "w"),
    ("after", "Después", 240, "w"),
)

ACTION_LABELS = {
    "add_product": "Producto creado",
    "reactivate_product": "Producto reactivado",
    "modify_product": "Producto modificado",
    "deactivate_product": "Producto eliminado",
    "delete_product": "Producto eliminado",
    "stock_in": "Existencias agregadas",
    "stock_out": "Existencias retiradas",
    "update_stock": "Existencias ajustadas",
    "add_category": "Categoría creada",
    "delete_category": "Categoría eliminada",
    "sale": "Venta",
    "void_sale": "Venta anulada",
    "sale_return": "Devolución",
    "purchase": "Compra a proveedor",
    "add_supplier": "Proveedor creado",
    "modify_supplier": "Proveedor modificado",
    "add_user": "Usuario creado",
    "modify_user": "Usuario modificado",
    "change_password": "Contraseña cambiada",
    "shift_open": "Turno abierto",
    "shift_close": "Turno cerrado",
    "backup": "Copia de seguridad",
}

GREEN_ACTIONS = {
    "add_product",
    "reactivate_product",
    "stock_in",
    "add_category",
    "purchase",
    "add_supplier",
    "add_user",
}
RED_ACTIONS = {"deactivate_product", "delete_product", "stock_out", "delete_category", "void_sale", "sale_return"}
YELLOW_ACTIONS = {"modify_product", "modify_user", "change_password", "modify_supplier"}

FIELD_LABELS = {
    "name": "Nombre",
    "cost": "Costo",
    "price": "Precio",
    "stock": "Existencias",
    "min_stock": "Stock mínimo",
    "tax_rate": "IVA %",
    "category": "Categoría",
    "description": "Descripción",
    "category_name": "Categoría",
    "reason": "Motivo",
    "motivo": "Motivo",
    "recibo": "Recibo",
    "total": "Total",
    "pago": "Pago",
    "productos": "Productos",
    "devolucion": "Devolución",
    "compra": "Compra",
    "proveedor": "Proveedor",
    "factura": "Factura",
    "unidades": "Unidades",
    "turno": "Turno",
    "base": "Base inicial",
    "esperado": "Efectivo esperado",
    "contado": "Efectivo contado",
    "diferencia": "Diferencia",
    "username": "Usuario",
    "full_name": "Nombre",
    "role": "Rol",
    "active": "Activo",
    "nit": "NIT",
    "archivo": "Archivo",
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
        self.grid_columnconfigure(0, weight=3, uniform="panels")
        self.grid_columnconfigure(1, weight=2, uniform="panels")
        self.grid_rowconfigure(2, weight=1)

        header = HeaderBar(self, "Auditoría", "Todo lo que cambió en el sistema, por día y por usuario")
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
        self._legend(body).pack(side="right", padx=(0, 24))

        events = Card(self, "Eventos", padding=10)
        events.grid(row=2, column=0, sticky="nsew", padx=(16, 6), pady=(0, 16))
        events_box = ctk.CTkFrame(events.body, fg_color="transparent")
        events_box.pack(fill="both", expand=True)
        self.tree = make_table(events_box, SUMMARY_COLUMNS, "Audit")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        details = Card(self, "Detalle (antes y después)", padding=10)
        details.grid(row=2, column=1, sticky="nsew", padx=(6, 16), pady=(0, 16))
        details_box = ctk.CTkFrame(details.body, fg_color="transparent")
        details_box.pack(fill="both", expand=True)
        self.details = make_table(details_box, DETAIL_COLUMNS, "AuditDetail")

    @staticmethod
    def _legend(parent) -> ctk.CTkFrame:
        legend = ctk.CTkFrame(parent, fg_color="transparent")
        for color, text in (
            (theme.SUCCESS_SOFT, "Creó o ingresó"),
            (theme.DANGER_SOFT, "Eliminó, retiró o anuló"),
            (theme.WARNING_SOFT, "Modificó"),
            (theme.SURFACE, "Ventas y turnos"),
        ):
            ctk.CTkFrame(
                legend, fg_color=color, width=16, height=16, corner_radius=4, border_width=1, border_color=theme.BORDER
            ).pack(side="left", padx=(10, 4))
            ctk.CTkLabel(legend, text=text, font=theme.font(11), text_color=theme.MUTED).pack(side="left")
        return legend

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
                    entry.user or "",
                    entry.action,
                )
                for entry in self._entries
            ),
            extra_tags=lambda row: _color_tag(row[4]),
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


def _color_tag(action: str) -> tuple[str, ...]:
    if action in GREEN_ACTIONS:
        return ("ok",)
    if action in RED_ACTIONS:
        return ("bad",)
    if action in YELLOW_ACTIONS:
        return ("warn",)
    return ()
