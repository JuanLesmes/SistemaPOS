"""Control de inventario: listado de productos, filtro por categoría y valorización."""

from __future__ import annotations

from decimal import Decimal
from tkinter import ttk

import customtkinter as ctk

from model.product import Product
from utils.formatters import format_price
from view import theme

ALL_CATEGORIES = "Todas"

COLUMNS = (
    ("code", "Código", 110, "w"),
    ("name", "Nombre", 200, "w"),
    ("stock", "Stock", 70, "center"),
    ("cost", "Costo", 100, "e"),
    ("price", "Precio", 100, "e"),
    ("category", "Categoría", 130, "w"),
    ("description", "Descripción", 240, "w"),
)
EMPTY_ROW = ("", "Sin productos para mostrar", "", "", "", "", "")


class AdminView(ctk.CTkFrame):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent, fg_color=theme.BACKGROUND)
        self.controller = controller
        self.pack_propagate(False)
        self.pack(fill="both", expand=True)
        self._create_widgets()

    def _create_widgets(self) -> None:
        button_style = {"font": theme.font(15, bold=True), "corner_radius": 20, "height": 40}
        font_label = theme.font(14, bold=True)

        header = ctk.CTkFrame(self, fg_color=theme.HEADER, corner_radius=0)
        header.pack(side="top", fill="x", ipady=15)
        ctk.CTkLabel(header, text="Control de inventario", text_color=theme.BLACK, font=theme.font(20, bold=True)).pack(
            side="left", padx=20
        )
        ctk.CTkButton(
            header,
            text="Volver al menú",
            fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER,
            text_color=theme.BLACK,
            font=theme.font(14, bold=True),
            corner_radius=10,
            command=self.controller.event_back,
        ).pack(side="right", padx=20)

        main = ctk.CTkFrame(self, fg_color=theme.BACKGROUND, corner_radius=0)
        main.pack(side="top", fill="both", expand=True, padx=10, pady=10)

        sidebar = ctk.CTkFrame(main, fg_color=theme.BACKGROUND, corner_radius=0, width=220)
        sidebar.pack(side="left", fill="y", padx=(0, 10))
        sidebar.pack_propagate(False)

        ctk.CTkLabel(sidebar, text="Categoría:", text_color=theme.BLACK, font=font_label).pack(anchor="w", pady=(10, 5))
        self.category_combobox = ttk.Combobox(sidebar, values=[ALL_CATEGORIES], state="readonly", width=18)
        self.category_combobox.current(0)
        self.category_combobox.pack(pady=(0, 10))
        ctk.CTkButton(
            sidebar,
            text="Filtrar",
            fg_color=theme.PRIMARY,
            hover_color=theme.PRIMARY_HOVER,
            text_color=theme.WHITE,
            command=self.controller.event_filter,
            **button_style,
        ).pack(fill="x", pady=5)

        ctk.CTkLabel(sidebar, text="Nueva categoría:", text_color=theme.BLACK, font=font_label).pack(
            anchor="w", pady=(10, 5)
        )
        self.new_category_entry = ctk.CTkEntry(sidebar, font=theme.font(12), corner_radius=8)
        self.new_category_entry.pack(fill="x", pady=(0, 10))
        self.new_category_entry.bind("<Return>", lambda _event: self.controller.event_add_category())
        ctk.CTkButton(
            sidebar,
            text="Agregar categoría",
            fg_color=theme.SUCCESS,
            hover_color=theme.SUCCESS_HOVER,
            text_color=theme.WHITE,
            command=self.controller.event_add_category,
            **button_style,
        ).pack(fill="x", pady=5)
        ctk.CTkButton(
            sidebar,
            text="Gestionar productos",
            fg_color=theme.WARNING,
            hover_color=theme.WARNING_HOVER,
            text_color=theme.BLACK,
            command=self.controller.event_manage_products,
            **button_style,
        ).pack(fill="x", pady=5)

        ctk.CTkLabel(sidebar, text="Valor del inventario", text_color=theme.BLACK, font=font_label).pack(
            anchor="w", pady=(20, 5)
        )
        self.valuation_label = ctk.CTkLabel(sidebar, text="$0", text_color=theme.BLACK, font=theme.font(16, bold=True))
        self.valuation_label.pack(pady=(0, 10), anchor="center", fill="x")

        content = ctk.CTkFrame(main, fg_color=theme.BACKGROUND, corner_radius=0)
        content.pack(side="right", fill="both", expand=True)
        ctk.CTkLabel(
            content, text="Productos en inventario", text_color=theme.BLACK, font=theme.font(16, bold=True)
        ).pack(anchor="w", pady=(10, 5))
        table_frame = ctk.CTkFrame(content, fg_color=theme.WHITE, corner_radius=8)
        table_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.tree = ttk.Treeview(
            table_frame,
            columns=[c[0] for c in COLUMNS],
            show="headings",
            style=theme.table_style("Inventory"),
        )
        for key, title, width, anchor in COLUMNS:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, anchor=anchor)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

    # ------------------------------------------------------------------ API para el controlador
    def load_table(self, products: list[Product]) -> None:
        theme.clear_table(self.tree)
        if not products:
            self.tree.insert("", "end", values=EMPTY_ROW)
            return
        for p in products:
            self.tree.insert(
                "",
                "end",
                values=(
                    p.code,
                    p.name,
                    p.stock,
                    format_price(p.cost),
                    format_price(p.price),
                    p.category,
                    p.description,
                ),
            )

    def set_inventory_value(self, value: Decimal) -> None:
        self.valuation_label.configure(text=f"${format_price(value)}")

    def set_categories(self, categories: list[str]) -> None:
        values = [ALL_CATEGORIES] + [c for c in categories if c != ALL_CATEGORIES]
        current = self.category_combobox.get()
        self.category_combobox.configure(values=values)
        self.category_combobox.current(values.index(current) if current in values else 0)

    def get_selected_category(self) -> str:
        return self.category_combobox.get()

    def get_new_category(self) -> str:
        return self.new_category_entry.get().strip()

    def clear_new_category(self) -> None:
        self.new_category_entry.delete(0, "end")
