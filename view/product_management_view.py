"""Formulario de gestión de productos."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from decimal import Decimal
from tkinter import ttk

import customtkinter as ctk

from model.product import Product
from utils.formatters import format_price, parse_money
from view import theme

# La primera opción (vacía) significa "precio manual": no se recalcula solo.
GAIN_OPTIONS = ("", "10", "20", "30", "40", "50", "100", "200")


class ProductManagementView(tk.Frame):
    """Usa 'place' con coordenadas relativas para conservar el diseño original."""

    def __init__(self, parent, controller) -> None:
        super().__init__(parent, bg=theme.BACKGROUND)
        self.controller = controller
        self.pack(fill="both", expand=True)
        self._result_labels: list[ctk.CTkLabel] = []
        self._create_widgets()

    def _create_widgets(self) -> None:
        font_label = theme.font(15, bold=True)
        font_entry = theme.font(15)
        font_button = theme.font(15, bold=True)

        header = ctk.CTkFrame(self, fg_color=theme.HEADER, corner_radius=0)
        header.place(relx=0, rely=0, relwidth=1, relheight=0.10)
        ctk.CTkLabel(header, text="Gestión de productos", text_color=theme.BLACK, font=theme.font(20, bold=True)).place(
            relx=0.5, rely=0.5, anchor="center"
        )

        body = ctk.CTkFrame(self, fg_color=theme.BACKGROUND, corner_radius=0)
        body.place(relx=0, rely=0.15, relwidth=1, relheight=0.7)

        row_gap = 0.18
        label_offset = 0.05
        entry_offset = 0.10

        def label(text: str, relx: float, row: int) -> None:
            ctk.CTkLabel(body, text=text, text_color=theme.BLACK, font=font_label).place(
                relx=relx, rely=row * row_gap + label_offset
            )

        def entry(width: int, relx: float, row: int, **kwargs) -> ctk.CTkEntry:
            widget = ctk.CTkEntry(body, width=width, height=30, corner_radius=15, font=font_entry, **kwargs)
            widget.place(relx=relx, rely=row * row_gap + entry_offset)
            return widget

        label("Código", 0.02, 0)
        self.entry_code = entry(200, 0.02, 0)
        label("Nombre", 0.17, 0)
        self.entry_name = entry(250, 0.17, 0)

        label("Descripción", 0.02, 1)
        self.entry_description = ctk.CTkTextbox(body, width=500, height=50, corner_radius=15, font=font_entry)
        self.entry_description.place(relx=0.02, rely=1 * row_gap + entry_offset)

        label("Categoría", 0.02, 2)
        self.cmb_category = ttk.Combobox(body, values=[], state="readonly", width=20)
        self.cmb_category.place(relx=0.02, rely=2 * row_gap + entry_offset)
        ctk.CTkButton(
            body,
            text="Eliminar categoría",
            corner_radius=15,
            fg_color=theme.DANGER,
            hover_color=theme.DANGER_HOVER,
            font=font_button,
            command=self.controller.event_delete_category,
        ).place(relx=0.02, rely=2 * row_gap + entry_offset + 0.07)

        label("Stock", 0.22, 2)
        self.entry_stock = entry(150, 0.22, 2)
        ctk.CTkButton(
            body,
            text="Agregar existencias",
            corner_radius=15,
            fg_color=theme.SUCCESS,
            hover_color=theme.SUCCESS_HOVER,
            font=font_button,
            command=self.controller.event_add_stock,
        ).place(relx=0.22, rely=2 * row_gap + entry_offset + 0.07)

        label("Costo", 0.02, 3)
        self.entry_cost = entry(150, 0.02, 3)
        self.entry_cost.bind("<FocusOut>", lambda _event: self._recalculate_price())

        label("Ganancia %", 0.14, 3)
        self.cmb_gain = ttk.Combobox(body, values=GAIN_OPTIONS, state="readonly", width=10)
        self.cmb_gain.current(0)
        self.cmb_gain.place(relx=0.14, rely=3 * row_gap + entry_offset)
        self.cmb_gain.bind("<<ComboboxSelected>>", lambda _event: self._recalculate_price())

        label("Precio", 0.22, 3)
        self.entry_price = entry(150, 0.22, 3)

        buttons = ctk.CTkFrame(body, fg_color=theme.BACKGROUND, corner_radius=0)
        buttons.place(relx=0.5, rely=0.05, relwidth=0.25, relheight=0.9, anchor="n")
        ctk.CTkLabel(buttons, text="Nombre o código del producto:", font=font_label, text_color=theme.BLACK).pack(
            pady=(10, 5)
        )
        self.entry_search = ctk.CTkEntry(buttons, width=200, height=30, corner_radius=15, font=font_entry)
        self.entry_search.pack(pady=(10, 5))
        self.entry_search.bind("<Return>", lambda _event: self.controller.event_search())
        for text, color, hover, command in (
            ("Buscar", theme.PRIMARY, theme.PRIMARY_HOVER, self.controller.event_search),
            ("Agregar producto", theme.SUCCESS, theme.SUCCESS_HOVER, self.controller.event_add_product),
            ("Modificar producto", theme.WARNING, theme.WARNING_HOVER, self.controller.event_modify_product),
            ("Eliminar producto", theme.DANGER, theme.DANGER_HOVER, self.controller.event_delete_product),
        ):
            ctk.CTkButton(
                buttons,
                text=text,
                text_color=theme.BLACK,
                corner_radius=15,
                fg_color=color,
                hover_color=hover,
                font=font_button,
                command=command,
                height=40,
            ).pack(fill="x", pady=5)

        results = ctk.CTkFrame(body, fg_color=theme.WHITE, corner_radius=10, border_width=2, border_color=theme.BORDER)
        results.place(relx=0.65, rely=0.05, relwidth=0.33, relheight=0.9)
        ctk.CTkLabel(results, text="Resultados de búsqueda", font=font_label, text_color=theme.BLACK).pack(pady=(10, 5))
        self.results_container = ctk.CTkScrollableFrame(results, fg_color=theme.WHITE, corner_radius=0)
        self.results_container.pack(fill="both", expand=True, padx=10, pady=5)

        ctk.CTkButton(
            self,
            text="Volver al inventario",
            text_color=theme.BLACK,
            corner_radius=15,
            fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER,
            font=font_button,
            command=self.controller.event_go_back,
        ).place(relx=0.35, rely=0.87, relwidth=0.3, relheight=0.08)

    # ------------------------------------------------------------------ lectura del formulario
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

    def get_search_term(self) -> str:
        return self.entry_search.get().strip()

    # ------------------------------------------------------------------ escritura del formulario
    def set_form(self, product: Product) -> None:
        _set_entry(self.entry_code, product.code)
        _set_entry(self.entry_name, product.name)
        _set_entry(self.entry_stock, str(product.stock))
        _set_entry(self.entry_cost, _money_text(product.cost))
        self.cmb_gain.current(0)  # precio manual: no se recalcula al cargar
        _set_entry(self.entry_price, _money_text(product.price))
        self.entry_description.delete("1.0", "end")
        self.entry_description.insert("1.0", product.description)
        categories = list(self.cmb_category.cget("values"))
        if product.category in categories:
            self.cmb_category.current(categories.index(product.category))

    def clear_fields(self) -> None:
        for widget in (self.entry_code, self.entry_name, self.entry_stock, self.entry_cost, self.entry_price):
            _set_entry(widget, "")
        self.entry_description.delete("1.0", "end")
        self.cmb_gain.current(0)
        self.clear_search()
        self.show_search_results([], lambda _product: None)
        if self.cmb_category.cget("values"):
            self.cmb_category.current(0)

    def clear_search(self) -> None:
        self.entry_search.delete(0, "end")

    def set_categories(self, categories: list[str]) -> None:
        current = self.cmb_category.get()
        self.cmb_category.configure(values=list(categories))
        if current in categories:
            self.cmb_category.current(categories.index(current))
        elif categories:
            self.cmb_category.current(0)
        else:
            self.cmb_category.set("")

    def show_search_results(self, products: list[Product], on_select: Callable[[Product], None]) -> None:
        for label in self._result_labels:
            label.destroy()
        self._result_labels.clear()
        if not products:
            return
        for product in products:
            text = (
                f"{product.name}   |   {product.category}   |   "
                f"Stock: {product.stock}   |   Precio: ${format_price(product.price)}"
            )
            label = ctk.CTkLabel(
                self.results_container,
                text=text,
                font=theme.font(12),
                text_color=theme.BLACK,
                anchor="w",
                cursor="hand2",
                wraplength=380,
                justify="left",
            )
            label.pack(fill="x", pady=2)
            label.bind("<Button-1>", lambda _event, p=product: on_select(p))
            self._result_labels.append(label)

    # ------------------------------------------------------------------ interno
    def _recalculate_price(self) -> None:
        """Precio = costo x (1 + ganancia). Solo cuando hay un porcentaje elegido."""
        gain_text = self.cmb_gain.get().strip()
        cost_text = self.get_cost()
        if not gain_text or not cost_text:
            return
        try:
            cost = parse_money(cost_text)
            gain = Decimal(gain_text)
        except ValueError:
            return
        price = cost * (1 + gain / 100)
        _set_entry(self.entry_price, _money_text(price))


def _set_entry(widget: ctk.CTkEntry, value: str) -> None:
    widget.delete(0, "end")
    widget.insert(0, value)


def _money_text(value: Decimal) -> str:
    """Muestra centavos solo cuando existen."""
    decimals = 0 if value == value.to_integral_value() else 2
    return format_price(value, decimals)
