"""Gestión de productos: búsqueda a la izquierda, formulario a la derecha."""

from __future__ import annotations

from decimal import Decimal

import customtkinter as ctk

from model.inventory import stock_tag
from model.product import Product
from utils.formatters import format_money_input, format_price, parse_money
from view import theme
from view.widgets import Card, HeaderBar, button, clear_entry, fill_table, make_table, section_label, set_entry_text

# La primera opción (vacía) significa "precio manual": no se recalcula solo.
GAIN_OPTIONS = ("", "10", "20", "25", "30", "40", "50", "100")

RESULT_COLUMNS = (
    ("code", "Código", 120, "w", False),
    ("name", "Nombre", 220, "w"),
    ("stock", "Stock", 60, "center", False),
    ("price", "Precio", 90, "e", False),
)

ENTRY_STYLE = {
    "height": 40,
    "fg_color": theme.SURFACE_ALT,
    "border_color": theme.BORDER,
    "text_color": theme.TEXT,
    "placeholder_text_color": theme.MUTED,
}


class ProductManagementView(ctk.CTkFrame):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent, fg_color=theme.BACKGROUND, corner_radius=0)
        self.controller = controller
        self._results: list[Product] = []
        self.pack(fill="both", expand=True)
        self._build()

    # ------------------------------------------------------------------ construcción
    def _build(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = HeaderBar(self, "Gestión de productos", "Buscar, crear, modificar y dar de baja productos")
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.add_action("Volver al inventario", self.controller.event_go_back)

        self._build_search().grid(row=1, column=0, sticky="nsew", padx=(16, 8), pady=14)
        self._build_form().grid(row=1, column=1, sticky="nsew", padx=(8, 16), pady=14)

    def _build_search(self) -> Card:
        card = Card(self, "Buscar producto", padding=12, width=520)
        card.grid_propagate(False)
        body = card.body
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=1)

        row = ctk.CTkFrame(body, fg_color="transparent")
        row.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        row.grid_columnconfigure(0, weight=1)
        self.entry_search = ctk.CTkEntry(row, placeholder_text="Nombre o código", font=theme.font(14), **ENTRY_STYLE)
        self.entry_search.grid(row=0, column=0, sticky="ew")
        self.entry_search.bind("<Return>", lambda _event: self.controller.event_search())
        button(row, "Buscar", self.controller.event_search, kind="primary", size="sm", height=40, width=100).grid(
            row=0, column=1, padx=(8, 0)
        )

        table_box = ctk.CTkFrame(body, fg_color="transparent")
        table_box.grid(row=1, column=0, sticky="nsew")
        self.results_tree = make_table(table_box, RESULT_COLUMNS, "ProductResults")
        self.results_tree.bind("<<TreeviewSelect>>", self._on_result_selected)
        self.results_hint = ctk.CTkLabel(
            body,
            text="Escriba y presione Enter. Toque un resultado para cargarlo en el formulario.",
            font=theme.font(12),
            text_color=theme.MUTED,
            anchor="w",
            wraplength=470,
            justify="left",
        )
        self.results_hint.grid(row=2, column=0, sticky="w", pady=(8, 0))
        return card

    def _build_form(self) -> Card:
        card = Card(self, "Datos del producto", padding=14)
        body = card.body
        for column in range(6):
            body.grid_columnconfigure(column, weight=1, uniform="form")

        def field(label: str, row: int, column: int, columnspan: int = 2, **kwargs) -> ctk.CTkEntry:
            section_label(body, label).grid(row=row * 2, column=column, columnspan=columnspan, sticky="w", pady=(10, 2))
            entry = ctk.CTkEntry(body, font=theme.font(14), **ENTRY_STYLE, **kwargs)
            entry.grid(row=row * 2 + 1, column=column, columnspan=columnspan, sticky="ew", padx=(0, 12))
            return entry

        self.entry_code = field("Código", 0, 0)
        self.entry_name = field("Nombre", 0, 2, columnspan=4)

        section_label(body, "Categoría").grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 2))
        category_row = ctk.CTkFrame(body, fg_color="transparent")
        category_row.grid(row=3, column=0, columnspan=3, sticky="ew", padx=(0, 12))
        category_row.grid_columnconfigure(0, weight=1)
        self.cmb_category = ctk.CTkComboBox(
            category_row,
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
        self.cmb_category.grid(row=0, column=0, sticky="ew")
        button(
            category_row,
            "Eliminar categoría",
            self.controller.event_delete_category,
            kind="danger-soft",
            size="sm",
            height=40,
        ).grid(row=0, column=1, padx=(8, 0))

        self.entry_stock = field("Stock", 1, 3, columnspan=1)
        button(body, "Agregar existencias", self.controller.event_add_stock, kind="success", size="sm", height=40).grid(
            row=3, column=4, columnspan=2, sticky="ew", padx=(0, 12)
        )

        self.entry_cost = field("Costo", 2, 0)
        self.entry_cost.bind("<FocusOut>", lambda _event: self._recalculate_price())
        section_label(body, "Ganancia %").grid(row=4, column=2, sticky="w", pady=(10, 2))
        self.cmb_gain = ctk.CTkComboBox(
            body,
            values=list(GAIN_OPTIONS),
            state="readonly",
            height=40,
            font=theme.font(14),
            dropdown_font=theme.font(13),
            fg_color=theme.SURFACE_ALT,
            border_color=theme.BORDER,
            button_color=theme.PRIMARY,
            button_hover_color=theme.PRIMARY_HOVER,
            text_color=theme.TEXT,
            command=lambda _value: self._recalculate_price(),
        )
        self.cmb_gain.set("")
        self.cmb_gain.grid(row=5, column=2, sticky="ew", padx=(0, 12))
        self.entry_price = field("Precio de venta", 2, 3, columnspan=3)

        section_label(body, "Descripción").grid(row=6, column=0, columnspan=6, sticky="w", pady=(10, 2))
        self.entry_description = ctk.CTkTextbox(
            body,
            height=70,
            font=theme.font(14),
            fg_color=theme.SURFACE_ALT,
            border_color=theme.BORDER,
            border_width=2,
            text_color=theme.TEXT,
            corner_radius=8,
        )
        self.entry_description.grid(row=7, column=0, columnspan=6, sticky="ew", padx=(0, 12))

        body.grid_rowconfigure(8, weight=1)
        actions = ctk.CTkFrame(body, fg_color="transparent")
        actions.grid(row=9, column=0, columnspan=6, sticky="ew", pady=(16, 0))
        button(actions, "Limpiar", self.controller.event_new, kind="ghost").pack(side="left")
        button(actions, "Agregar producto", self.controller.event_add_product, kind="success", width=170).pack(
            side="right"
        )
        button(actions, "Guardar cambios", self.controller.event_modify_product, kind="primary", width=160).pack(
            side="right", padx=(0, 10)
        )
        button(actions, "Eliminar", self.controller.event_delete_product, kind="danger-soft", width=120).pack(
            side="right", padx=(0, 10)
        )
        return card

    # ------------------------------------------------------------------ búsqueda
    def get_search_term(self) -> str:
        return self.entry_search.get().strip()

    def clear_search(self) -> None:
        clear_entry(self.entry_search)

    def show_search_results(self, products: list[Product]) -> None:
        self._results = list(products)
        fill_table(
            self.results_tree,
            ((p.code, p.name, p.stock, format_price(p.price)) for p in products),
            extra_tags=lambda row: stock_tag(int(row[2])),
            empty_message="Sin resultados",
        )

    def _on_result_selected(self, _event) -> None:
        selection = self.results_tree.selection()
        if not selection:
            return
        index = self.results_tree.index(selection[0])
        if index < len(self._results):
            self.controller.event_result_selected(self._results[index])

    # ------------------------------------------------------------------ formulario
    def get_code(self) -> str:
        return self.entry_code.get().strip()

    def get_name(self) -> str:
        return self.entry_name.get().strip()

    def get_stock(self) -> str:
        return self.entry_stock.get().strip()

    def get_cost(self) -> str:
        return self.entry_cost.get().strip()

    def get_price(self) -> str:
        return self.entry_price.get().strip()

    def get_category(self) -> str:
        return self.cmb_category.get().strip()

    def get_description(self) -> str:
        return self.entry_description.get("1.0", "end").strip()

    def set_form(self, product: Product) -> None:
        _set_entry(self.entry_code, product.code)
        _set_entry(self.entry_name, product.name)
        _set_entry(self.entry_stock, str(product.stock))
        _set_entry(self.entry_cost, format_money_input(product.cost))
        self.cmb_gain.set("")  # precio manual: no se recalcula al cargar
        _set_entry(self.entry_price, format_money_input(product.price))
        self.entry_description.delete("1.0", "end")
        self.entry_description.insert("1.0", product.description)
        if product.category in self.cmb_category.cget("values"):
            self.cmb_category.set(product.category)

    def clear_fields(self) -> None:
        for widget in (self.entry_code, self.entry_name, self.entry_stock, self.entry_cost, self.entry_price):
            _set_entry(widget, "")
        self.entry_description.delete("1.0", "end")
        self.cmb_gain.set("")
        values = self.cmb_category.cget("values")
        self.cmb_category.set(values[0] if values else "")

    def set_categories(self, categories: list[str]) -> None:
        current = self.cmb_category.get()
        self.cmb_category.configure(values=list(categories))
        if current in categories:
            self.cmb_category.set(current)
        else:
            self.cmb_category.set(categories[0] if categories else "")

    def focus_code(self) -> None:
        self.entry_code.focus_set()

    def _recalculate_price(self) -> None:
        """Precio = costo x (1 + ganancia). Solo cuando hay un porcentaje elegido."""
        gain_text = self.cmb_gain.get().strip()
        cost_text = self.get_cost()
        if not gain_text or not cost_text:
            return
        try:
            price = parse_money(cost_text) * (1 + Decimal(gain_text) / 100)
        except (ValueError, ArithmeticError):
            return
        _set_entry(self.entry_price, format_money_input(price))


def _set_entry(widget: ctk.CTkEntry, value: str) -> None:
    set_entry_text(widget, value)
