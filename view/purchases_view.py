"""Compras a proveedores: armar la compra a la izquierda, historial a la derecha."""

from __future__ import annotations

import customtkinter as ctk

from model.product import Product
from model.purchase import Purchase, PurchaseItem
from model.supplier import Supplier
from utils.formatters import format_price
from view import theme
from view.widgets import Card, HeaderBar, button, clear_entry, fill_table, make_table, section_label

RESULT_COLUMNS = (
    ("code", "Código", 120, "w", False),
    ("name", "Producto", 220, "w"),
    ("stock", "Stock", 60, "center", False),
    ("cost", "Costo actual", 100, "e", False),
)
ITEM_COLUMNS = (
    ("name", "Producto", 220, "w"),
    ("quantity", "Cantidad", 80, "center", False),
    ("cost", "Costo unit.", 100, "e", False),
    ("total", "Total", 110, "e", False),
)
HISTORY_COLUMNS = (
    ("date", "Fecha", 86, "w", False),
    ("supplier", "Proveedor", 130, "w"),
    ("invoice", "Factura", 72, "w", False),
    ("units", "Unid.", 52, "center", False),
    ("total", "Total", 90, "e", False),
    ("user", "Usuario", 78, "w", False),
)
ENTRY_STYLE = {
    "height": 40,
    "font": theme.font(14),
    "fg_color": theme.SURFACE_ALT,
    "border_color": theme.BORDER,
    "text_color": theme.TEXT,
    "placeholder_text_color": theme.MUTED,
}


class PurchasesView(ctk.CTkFrame):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent, fg_color=theme.BACKGROUND, corner_radius=0)
        self.controller = controller
        self._results: list[Product] = []
        self._suppliers: list[Supplier] = []
        self.pack(fill="both", expand=True)
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=3, uniform="cols")
        self.grid_columnconfigure(1, weight=2, uniform="cols")
        self.grid_rowconfigure(1, weight=1)

        header = HeaderBar(self, "Compras a proveedores", "La mercancía entra al inventario y el costo se actualiza")
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.add_action("Volver al menú", self.controller.event_back)

        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=1, column=0, sticky="nsew", padx=(16, 6), pady=14)
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(2, weight=1)

        head = Card(left, padding=12)
        head.grid(row=0, column=0, sticky="ew")
        body = head.body
        body.grid_columnconfigure(1, weight=1)
        section_label(body, "Proveedor").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.supplier_box = ctk.CTkComboBox(
            body,
            values=[],
            state="readonly",
            height=40,
            font=theme.font(14),
            dropdown_font=theme.font(13),
            fg_color=theme.SURFACE_ALT,
            border_color=theme.BORDER,
            button_color=theme.PRIMARY,
            button_hover_color=theme.PRIMARY_HOVER,
            text_color=theme.TEXT,
        )
        self.supplier_box.grid(row=0, column=1, sticky="ew")
        button(
            body, "Nuevo proveedor", self.controller.event_new_supplier, kind="secondary", size="sm", height=40
        ).grid(row=0, column=2, padx=(8, 0))
        section_label(body, "Factura N°").grid(row=0, column=3, sticky="w", padx=(16, 8))
        self.invoice_entry = ctk.CTkEntry(body, width=140, placeholder_text="opcional", **ENTRY_STYLE)
        self.invoice_entry.grid(row=0, column=4)

        search = Card(left, "Agregar productos a la compra", padding=12)
        search.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        row = ctk.CTkFrame(search.body, fg_color="transparent")
        row.pack(fill="x")
        row.grid_columnconfigure(0, weight=1)
        self.search_entry = ctk.CTkEntry(row, placeholder_text="Nombre o código; Enter para buscar", **ENTRY_STYLE)
        self.search_entry.grid(row=0, column=0, sticky="ew")
        self.search_entry.bind("<Return>", lambda _event: self.controller.event_search())
        button(row, "Buscar", self.controller.event_search, kind="primary", size="sm", height=40, width=100).grid(
            row=0, column=1, padx=(8, 0)
        )
        results_box = ctk.CTkFrame(search.body, fg_color="transparent")
        results_box.pack(fill="x", pady=(8, 0))
        self.results_tree = make_table(results_box, RESULT_COLUMNS, "PurchaseResults", height=5)
        self.results_tree.bind("<Double-1>", lambda _event: self.controller.event_pick_result())
        ctk.CTkLabel(
            search.body,
            text="Doble clic en un resultado para indicar cantidad y costo de compra.",
            font=theme.font(11),
            text_color=theme.MUTED,
            anchor="w",
        ).pack(anchor="w", pady=(6, 0))

        items = Card(left, "Productos de esta compra", padding=12)
        items.grid(row=2, column=0, sticky="nsew", pady=(10, 0))
        self.total_label = ctk.CTkLabel(
            items.title_row, text="Total $0", font=theme.font(15, bold=True), text_color=theme.TEXT
        )
        self.total_label.pack(side="right")
        items_box = ctk.CTkFrame(items.body, fg_color="transparent")
        items_box.pack(fill="both", expand=True)
        self.items_tree = make_table(items_box, ITEM_COLUMNS, "PurchaseItems", height=6)
        actions = ctk.CTkFrame(items.body, fg_color="transparent")
        actions.pack(fill="x", pady=(10, 0))
        button(actions, "Quitar línea", self.controller.event_remove_item, kind="secondary", size="sm").pack(
            side="left"
        )
        button(actions, "Limpiar", self.controller.event_clear, kind="ghost", size="sm").pack(side="left", padx=(6, 0))
        button(actions, "Registrar compra", self.controller.event_save, kind="success", width=190).pack(side="right")
        section_label(items.body, "Notas").pack(anchor="w", pady=(10, 4))
        self.notes_entry = ctk.CTkEntry(items.body, placeholder_text="opcional", **ENTRY_STYLE)
        self.notes_entry.pack(fill="x")

        history = Card(self, "Compras recientes (últimos 90 días)", padding=10)
        history.grid(row=1, column=1, sticky="nsew", padx=(6, 16), pady=14)
        history_box = ctk.CTkFrame(history.body, fg_color="transparent")
        history_box.pack(fill="both", expand=True)
        self.history_tree = make_table(history_box, HISTORY_COLUMNS, "PurchaseHistory")

    # ------------------------------------------------------------------ API para el controlador
    def set_suppliers(self, suppliers: list[Supplier], select: str | None = None) -> None:
        self._suppliers = list(suppliers)
        names = [s.name for s in suppliers]
        current = select or self.supplier_box.get()
        self.supplier_box.configure(values=names)
        self.supplier_box.set(current if current in names else (names[0] if names else ""))

    def selected_supplier(self) -> Supplier | None:
        name = self.supplier_box.get()
        return next((s for s in self._suppliers if s.name == name), None)

    def get_invoice(self) -> str:
        return self.invoice_entry.get().strip()

    def get_notes(self) -> str:
        return self.notes_entry.get().strip()

    def get_search_term(self) -> str:
        return self.search_entry.get().strip()

    def show_results(self, products: list[Product]) -> None:
        self._results = list(products)
        fill_table(
            self.results_tree,
            ((p.code, p.name, p.stock, format_price(p.cost)) for p in products),
            empty_message="Sin resultados",
        )

    def selected_result(self) -> Product | None:
        selection = self.results_tree.selection()
        if not selection:
            return None
        index = self.results_tree.index(selection[0])
        return self._results[index] if index < len(self._results) else None

    def show_items(self, items: list[PurchaseItem]) -> None:
        fill_table(
            self.items_tree,
            ((i.name, i.quantity, format_price(i.unit_cost), format_price(i.total)) for i in items),
            empty_message="Agregue productos desde la búsqueda",
        )
        total = sum((i.total for i in items), start=0)
        self.total_label.configure(text=f"Total ${format_price(total)}")

    def selected_item_index(self) -> int | None:
        selection = self.items_tree.selection()
        return self.items_tree.index(selection[0]) if selection else None

    def show_history(self, purchases: list[Purchase]) -> None:
        fill_table(
            self.history_tree,
            (
                (
                    p.purchased_at.strftime("%Y-%m-%d") if p.purchased_at else "",
                    p.supplier_name,
                    p.invoice_number,
                    p.units,
                    format_price(p.total),
                    p.user or "",
                )
                for p in purchases
            ),
            empty_message="Todavía no hay compras registradas",
        )

    def clear_form(self) -> None:
        clear_entry(self.invoice_entry)
        clear_entry(self.notes_entry)
        clear_entry(self.search_entry)
        self.show_results([])
        self.show_items([])
