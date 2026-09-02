"""Inventario: indicadores, filtros y tabla de productos activos."""

from __future__ import annotations

import customtkinter as ctk

from model.inventory import InventoryStats, stock_tag
from model.product import Product
from utils.formatters import format_price
from view import theme
from view.widgets import Card, HeaderBar, StatCard, button, clear_entry, fill_table, make_table, section_label

ALL_CATEGORIES = "Todas"

COLUMNS = (
    ("code", "Código", 130, "w", False),
    ("name", "Nombre", 260, "w"),
    ("category", "Categoría", 160, "w"),
    ("stock", "Stock", 80, "center", False),
    ("cost", "Costo", 100, "e", False),
    ("price", "Precio", 100, "e", False),
    ("description", "Descripción", 300, "w"),
)


class AdminView(ctk.CTkFrame):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent, fg_color=theme.BACKGROUND, corner_radius=0)
        self.controller = controller
        self.pack(fill="both", expand=True)
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self.header = HeaderBar(self, "Inventario", "Productos activos y valor de las existencias")
        self.header.grid(row=0, column=0, sticky="ew")
        self.manage_button = self.header.add_action(
            "Gestionar productos", self.controller.event_manage_products, kind="accent"
        )
        self.import_button = self.header.add_action("Importar Excel", self.controller.event_import_excel)
        self.header.add_action("Exportar Excel", self.controller.event_export_excel)
        self.header.add_action("Volver al menú", self.controller.event_back)

        stats = ctk.CTkFrame(self, fg_color="transparent")
        stats.grid(row=1, column=0, sticky="ew", padx=16, pady=(14, 0))
        cards = (
            ("count", "Productos activos", theme.PRIMARY),
            ("value_price", "Valor a precio de venta", theme.PRIMARY),
            ("value_cost", "Valor a costo", theme.MUTED),
            ("low", "Con pocas existencias", theme.WARNING),
            ("out", "Agotados", theme.DANGER),
        )
        self.stat_cards: dict[str, StatCard] = {}
        for index, (key, label, accent) in enumerate(cards):
            stats.grid_columnconfigure(index, weight=1, uniform="stats")
            card = StatCard(stats, label, "0", accent=accent)
            card.grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 10, 0))
            self.stat_cards[key] = card
        self.stat_cards["low"].set_command(lambda: self.controller.event_toggle_stock_filter("low"))
        self.stat_cards["out"].set_command(lambda: self.controller.event_toggle_stock_filter("out"))
        self.stat_cards["count"].set_command(lambda: self.controller.set_stock_filter(None))

        toolbar = Card(self, padding=12)
        toolbar.grid(row=2, column=0, sticky="ew", padx=16, pady=12)
        body = toolbar.body
        body.grid_columnconfigure(1, weight=1)

        section_label(body, "Buscar").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.search_entry = ctk.CTkEntry(
            body,
            placeholder_text="Nombre o código",
            placeholder_text_color=theme.MUTED,
            height=40,
            font=theme.font(14),
            fg_color=theme.SURFACE_ALT,
            border_color=theme.BORDER,
            text_color=theme.TEXT,
        )
        self.search_entry.grid(row=0, column=1, sticky="ew")
        self.search_entry.bind("<KeyRelease>", lambda _event: self.controller.event_filter_changed())

        section_label(body, "Categoría").grid(row=0, column=2, sticky="w", padx=(18, 8))
        self.category_box = ctk.CTkComboBox(
            body,
            values=[ALL_CATEGORIES],
            state="readonly",
            width=220,
            height=40,
            font=theme.font(14),
            dropdown_font=theme.font(13),
            fg_color=theme.SURFACE_ALT,
            border_color=theme.BORDER,
            button_color=theme.PRIMARY,
            button_hover_color=theme.PRIMARY_HOVER,
            text_color=theme.TEXT,
            command=lambda _value: self.controller.event_filter_changed(),
        )
        self.category_box.set(ALL_CATEGORIES)
        self.category_box.grid(row=0, column=3, sticky="w")

        section_label(body, "Nueva categoría").grid(row=0, column=4, sticky="w", padx=(24, 8))
        self.new_category_entry = ctk.CTkEntry(
            body,
            placeholder_text="Nombre",
            placeholder_text_color=theme.MUTED,
            width=200,
            height=40,
            font=theme.font(14),
            fg_color=theme.SURFACE_ALT,
            border_color=theme.BORDER,
            text_color=theme.TEXT,
        )
        self.new_category_entry.grid(row=0, column=5, sticky="w")
        self.new_category_entry.bind("<Return>", lambda _event: self.controller.event_add_category())
        button(
            body, "Agregar", self.controller.event_add_category, kind="success", size="sm", height=40, width=110
        ).grid(row=0, column=6, sticky="w", padx=(8, 0))

        table_card = Card(self, padding=10)
        table_card.grid(row=3, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.filter_note = ctk.CTkLabel(
            table_card.body, text="", font=theme.font(12, bold=True), text_color=theme.WARNING, anchor="w"
        )
        table_box = ctk.CTkFrame(table_card.body, fg_color="transparent")
        table_box.pack(fill="both", expand=True)
        self.tree = make_table(table_box, COLUMNS, "Inventory")
        self.tree.bind("<Double-1>", lambda _event: self.controller.event_open_selected())

    # ------------------------------------------------------------------ API para el controlador
    def load_table(self, products: list[Product]) -> None:
        self._products = list(products)
        fill_table(
            self.tree,
            (
                (
                    p.code,
                    p.name,
                    p.category,
                    p.stock,
                    format_price(p.cost),
                    format_price(p.price),
                    p.description,
                    p.min_stock,
                )
                for p in products
            ),
            extra_tags=lambda row: stock_tag(int(row[3]), int(row[7])),
            empty_message="No hay productos que coincidan",
        )

    def selected_product(self) -> Product | None:
        selection = self.tree.selection()
        if not selection:
            return None
        index = self.tree.index(selection[0])
        return self._products[index] if index < len(self._products) else None

    def set_stats(self, stats: InventoryStats) -> None:
        self.stat_cards["count"].set_value(str(stats.product_count))
        self.stat_cards["value_price"].set_value(f"${format_price(stats.value_at_price)}")
        self.stat_cards["value_cost"].set_value(f"${format_price(stats.value_at_cost)}")
        self.stat_cards["low"].set_value(str(stats.low_stock_count))
        self.stat_cards["out"].set_value(str(stats.out_of_stock_count))
        self.header.set_subtitle(f"{stats.product_count} productos activos")

    def set_can_edit(self, can_edit: bool) -> None:
        state = "normal" if can_edit else "disabled"
        self.manage_button.configure(state=state)
        self.import_button.configure(state=state)

    def set_stock_filter(self, key: str | None) -> None:
        self.stat_cards["low"].set_active(key == "low")
        self.stat_cards["out"].set_active(key == "out")

    def set_filter_note(self, text: str) -> None:
        """Aviso sobre la tabla cuando hay un filtro de existencias activo."""
        if text:
            self.filter_note.configure(text=f"{text}. Toque el indicador de nuevo para quitar el filtro.")
            self.filter_note.pack(fill="x", padx=6, pady=(0, 6), before=self.tree.master)
        else:
            self.filter_note.pack_forget()

    def set_categories(self, categories: list[str]) -> None:
        values = [ALL_CATEGORIES] + [c for c in categories if c != ALL_CATEGORIES]
        current = self.category_box.get()
        self.category_box.configure(values=values)
        self.category_box.set(current if current in values else ALL_CATEGORIES)

    def get_selected_category(self) -> str:
        return self.category_box.get()

    def get_search_term(self) -> str:
        return self.search_entry.get().strip()

    def get_new_category(self) -> str:
        return self.new_category_entry.get().strip()

    def clear_new_category(self) -> None:
        clear_entry(self.new_category_entry)
