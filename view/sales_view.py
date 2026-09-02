"""Pantalla de ventas.

Tres zonas: categorías a la izquierda, catálogo de productos en el centro y,
a la derecha, la venta actual con el cobro (recibido, billetes, teclado y
métodos de pago).
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal

import customtkinter as ctk

from model.inventory import LOW_STOCK_THRESHOLD
from model.product import Product
from model.sold_product import SoldProduct
from utils.formatters import format_price
from view import theme
from view.widgets import Card, HeaderBar, Keypad, button, clear_entry, fill_table, make_table, set_entry_text

ALL_CATEGORIES = "__todas__"
BEST_SELLERS = "__mas_vendidos__"
BILLS = (1000, 2000, 5000, 10000, 20000, 50000, 100000)

CATEGORY_WIDTH = 176
CART_WIDTH = 470
CARD_MIN_WIDTH = 178
CARD_HEIGHT = 108
CARD_GAP = 10
REFLOW_DELAY_MS = 120

CART_COLUMNS = (
    ("nombre", "Producto", 190, "w"),
    ("cantidad", "Cant.", 52, "center", False),
    ("precio", "Precio", 82, "e", False),
    ("subtotal", "Subtotal", 92, "e", False),
)


class SalesView(ctk.CTkFrame):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent, fg_color=theme.BACKGROUND, corner_radius=0)
        self.controller = controller
        self._category_buttons: dict[str, ctk.CTkButton] = {}
        self._cards: list[ProductCard] = []
        self._columns = 0
        self._reflow_job: str | None = None
        self._printer_available = True
        self.pack(fill="both", expand=True)
        self._build()

    # ------------------------------------------------------------------ construcción
    def _build(self) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

        header = HeaderBar(self, "Ventas", "Escanee, busque o toque un producto para agregarlo a la venta")
        header.grid(row=0, column=0, columnspan=3, sticky="ew")
        header.add_action("Volver al menú", self.controller.event_back)

        self._build_categories().grid(row=1, column=0, sticky="ns", padx=(16, 0), pady=14)
        self._build_catalog().grid(row=1, column=1, sticky="nsew", padx=12, pady=14)
        self._build_cart().grid(row=1, column=2, sticky="ns", padx=(0, 16), pady=14)

    def _build_categories(self) -> ctk.CTkFrame:
        self.category_panel = ctk.CTkScrollableFrame(
            self, fg_color="transparent", width=CATEGORY_WIDTH, scrollbar_button_color=theme.BORDER
        )
        return self.category_panel

    def _build_catalog(self) -> Card:
        card = Card(self, padding=12)
        card.body.grid_rowconfigure(1, weight=1)
        card.body.grid_columnconfigure(0, weight=1)

        toolbar = ctk.CTkFrame(card.body, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        toolbar.grid_columnconfigure(0, weight=1)
        self.search_entry = ctk.CTkEntry(
            toolbar,
            placeholder_text="Buscar producto por nombre o código",
            placeholder_text_color=theme.MUTED,
            height=42,
            font=theme.font(14),
            fg_color=theme.SURFACE_ALT,
            border_color=theme.BORDER,
            text_color=theme.TEXT,
        )
        self.search_entry.grid(row=0, column=0, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self._on_search_key)
        self.search_entry.bind("<Return>", lambda _event: self.controller.event_search_enter())
        self.catalog_note = ctk.CTkLabel(toolbar, text="", font=theme.font(12), text_color=theme.MUTED, anchor="e")
        self.catalog_note.grid(row=0, column=1, sticky="e", padx=(12, 4))

        self.catalog_grid = ctk.CTkScrollableFrame(
            card.body, fg_color="transparent", scrollbar_button_color=theme.BORDER
        )
        self.catalog_grid.grid(row=1, column=0, sticky="nsew")
        card.body.bind("<Configure>", self._on_catalog_resize)
        return card

    def _build_cart(self) -> ctk.CTkFrame:
        panel = ctk.CTkFrame(self, fg_color="transparent", width=CART_WIDTH)
        panel.grid_propagate(False)
        panel.grid_rowconfigure(0, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        cart = Card(panel, "Venta actual", padding=12)
        cart.grid(row=0, column=0, sticky="nsew")
        self.count_label = ctk.CTkLabel(cart.title_row, text="0 productos", font=theme.font(12), text_color=theme.MUTED)
        self.count_label.pack(side="right")

        table_box = ctk.CTkFrame(cart.body, fg_color="transparent")
        table_box.pack(fill="both", expand=True)
        self.tree = make_table(table_box, CART_COLUMNS, "Cart", height=4)
        self.tree.bind("<Delete>", lambda _event: self.controller.event_remove_line())

        line_actions = ctk.CTkFrame(cart.body, fg_color="transparent")
        line_actions.pack(fill="x", pady=(8, 0))
        button(line_actions, "−", self.controller.event_decrease, kind="secondary", size="sm", width=46).pack(
            side="left"
        )
        button(line_actions, "+", self.controller.event_increase, kind="secondary", size="sm", width=46).pack(
            side="left", padx=(6, 0)
        )
        button(line_actions, "Quitar", self.controller.event_remove_line, kind="secondary", size="sm", width=90).pack(
            side="left", padx=(6, 0)
        )
        button(line_actions, "Vaciar", self.controller.event_clear_sale, kind="ghost", size="sm", width=80).pack(
            side="right"
        )

        total_row = ctk.CTkFrame(cart.body, fg_color="transparent")
        total_row.pack(fill="x", pady=(10, 0))
        ctk.CTkLabel(total_row, text="Total", font=theme.font(15, bold=True), text_color=theme.MUTED).pack(side="left")
        self.total_label = ctk.CTkLabel(total_row, text="$0", font=theme.font(26, bold=True), text_color=theme.TEXT)
        self.total_label.pack(side="right")

        pay = Card(panel, padding=12)
        pay.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        self._build_payment(pay.body)
        return panel

    def _build_payment(self, body: ctk.CTkFrame) -> None:
        received_row = ctk.CTkFrame(body, fg_color="transparent")
        received_row.pack(fill="x")
        ctk.CTkLabel(
            received_row, text="Recibe", font=theme.font(14, bold=True), text_color=theme.TEXT, width=60, anchor="w"
        ).pack(side="left")
        self.received_entry = ctk.CTkEntry(
            received_row,
            placeholder_text="0",
            justify="right",
            height=44,
            font=theme.font(20, bold=True),
            fg_color=theme.SURFACE_ALT,
            border_color=theme.BORDER,
            text_color=theme.TEXT,
        )
        self.received_entry.pack(side="left", fill="x", expand=True, padx=(4, 6))
        self.received_entry.bind("<KeyRelease>", lambda _event: self.controller.event_received_changed())
        self.received_entry.bind("<Return>", lambda _event: self.controller.event_cash_payment())
        button(received_row, "C", self.controller.event_clear_received, kind="ghost", size="md", width=46).pack(
            side="left"
        )

        self.change_label = ctk.CTkLabel(
            body, text="", font=theme.font(15, bold=True), text_color=theme.SUCCESS, anchor="e"
        )
        self.change_label.pack(fill="x", pady=(4, 6))

        money = ctk.CTkFrame(body, fg_color="transparent")
        money.pack(fill="x")
        money.grid_columnconfigure(0, weight=1, uniform="money")
        money.grid_columnconfigure(1, weight=1, uniform="money")

        bills = ctk.CTkFrame(money, fg_color="transparent")
        bills.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        for column in (0, 1):
            bills.grid_columnconfigure(column, weight=1, uniform="bills")
        cells = [(amount, f"${format_price(amount)}") for amount in BILLS] + [(None, "Exacto")]
        for index, (amount, label) in enumerate(cells):
            if amount is None:
                widget = button(bills, label, self.controller.event_exact, kind="ghost", height=38)
            else:
                color = theme.BILL_COLORS[amount]
                widget = button(
                    bills,
                    label,
                    lambda value=amount: self.controller.event_bill(value),
                    kind="primary",
                    height=38,
                    fg_color=color,
                    hover_color=_darken(color),
                    text_color=theme.ON_DARK,
                )
            widget.grid(row=index // 2, column=index % 2, sticky="nsew", padx=3, pady=3)

        Keypad(money, self.controller.event_keypad, key_height=38).grid(row=0, column=1, sticky="nsew")

        options = ctk.CTkFrame(body, fg_color="transparent")
        options.pack(fill="x", pady=(8, 0))
        self._printer_available = True
        self.print_var = ctk.BooleanVar(value=False)
        self.print_switch = ctk.CTkSwitch(
            options,
            text="Imprimir recibo",
            variable=self.print_var,
            font=theme.font(13, bold=True),
            text_color=theme.TEXT,
            progress_color=theme.SUCCESS,
        )
        self.print_switch.pack(side="left")
        self.print_hint = ctk.CTkLabel(options, text="", font=theme.font(11), text_color=theme.MUTED)
        self.print_hint.pack(side="left", padx=(10, 0))

        pay_row = ctk.CTkFrame(body, fg_color="transparent")
        pay_row.pack(fill="x", pady=(8, 0))
        for column in range(3):
            pay_row.grid_columnconfigure(column, weight=1, uniform="pay")
        button(pay_row, "Efectivo", self.controller.event_cash_payment, kind="accent", size="lg", height=50).grid(
            row=0, column=0, sticky="ew", padx=(0, 4)
        )
        button(pay_row, "Tarjeta", self.controller.event_card_payment, kind="primary", size="lg", height=50).grid(
            row=0, column=1, sticky="ew", padx=4
        )
        button(
            pay_row, "Transferencia", self.controller.event_transfer_payment, kind="primary", size="lg", height=50
        ).grid(row=0, column=2, sticky="ew", padx=(4, 0))

    # ------------------------------------------------------------------ catálogo
    def set_categories(self, categories: list[str]) -> None:
        for widget in self.category_panel.winfo_children():
            widget.destroy()
        self._category_buttons.clear()
        entries = [(ALL_CATEGORIES, "Todos"), (BEST_SELLERS, "Más vendidos")] + [(name, name) for name in categories]
        for key, label in entries:
            widget = button(
                self.category_panel,
                label,
                lambda k=key: self.controller.event_select_category(k),
                kind="secondary",
                height=42,
                anchor="w",
                font=theme.font(13, bold=True),
            )
            widget.pack(fill="x", pady=(0, 6))
            self._category_buttons[key] = widget

    def set_active_category(self, key: str) -> None:
        for name, widget in self._category_buttons.items():
            active = name == key
            widget.configure(
                fg_color=theme.PRIMARY if active else theme.SURFACE,
                hover_color=theme.PRIMARY_HOVER if active else theme.SURFACE_HOVER,
                text_color=theme.ON_DARK if active else theme.TEXT,
                border_width=0 if active else 1,
            )

    def show_products(self, products: list[Product], note: str = "") -> None:
        for card in self._cards:
            card.destroy()
        self._cards = [
            ProductCard(self.catalog_grid, product, self.controller.event_product_selected) for product in products
        ]
        self.catalog_note.configure(text=note)
        self._columns = 0
        self._reflow()

    def get_search_term(self) -> str:
        return self.search_entry.get().strip()

    def clear_search(self) -> None:
        clear_entry(self.search_entry)

    def _on_search_key(self, event) -> None:
        if event.keysym in ("Return", "KP_Enter"):
            return
        self.controller.event_search_changed()

    def _on_catalog_resize(self, _event) -> None:
        if self._reflow_job is not None:
            self.after_cancel(self._reflow_job)
        self._reflow_job = self.after(REFLOW_DELAY_MS, self._reflow)

    def _reflow(self) -> None:
        self._reflow_job = None
        available = max(self.catalog_grid.winfo_width(), 1)
        columns = max(1, (available + CARD_GAP) // (CARD_MIN_WIDTH + CARD_GAP))
        if columns == self._columns:
            return
        self._columns = columns
        for column in range(columns):
            self.catalog_grid.grid_columnconfigure(column, weight=1, uniform="cards")
        for index, card in enumerate(self._cards):
            card.grid(
                row=index // columns, column=index % columns, sticky="nsew", padx=CARD_GAP // 2, pady=CARD_GAP // 2
            )

    # ------------------------------------------------------------------ venta actual
    def load_table(self, lines: list[SoldProduct]) -> None:
        selected = self.selected_index()
        fill_table(
            self.tree,
            ((sp.product.name, sp.quantity, format_price(sp.unit_price), format_price(sp.total)) for sp in lines),
            empty_message="Sin productos",
        )
        children = self.tree.get_children()
        if lines and children:
            index = selected if selected is not None and selected < len(children) else len(children) - 1
            self.tree.selection_set(children[index])
        self.count_label.configure(text=f"{sum(sp.quantity for sp in lines)} productos")

    def selected_index(self) -> int | None:
        selection = self.tree.selection()
        return self.tree.index(selection[0]) if selection else None

    def select_index(self, index: int) -> None:
        children = self.tree.get_children()
        if 0 <= index < len(children):
            self.tree.selection_set(children[index])

    def set_total(self, total: Decimal) -> None:
        self.total_label.configure(text=f"${format_price(total)}")

    # ------------------------------------------------------------------ cobro
    def get_received_amount(self) -> str:
        return self.received_entry.get().strip()

    def set_received_amount(self, text: str) -> None:
        set_entry_text(self.received_entry, text)

    def clear_received_amount(self) -> None:
        clear_entry(self.received_entry)

    def set_change(self, text: str, ok: bool = True) -> None:
        self.change_label.configure(text=text, text_color=theme.SUCCESS if ok else theme.DANGER)

    def wants_receipt(self) -> bool:
        return self._printer_available and bool(self.print_var.get())

    def reset_print_option(self) -> None:
        self.print_var.set(False)

    def set_printer_available(self, available: bool) -> None:
        self._printer_available = available
        if available:
            self.print_switch.configure(state="normal")
            self.print_hint.configure(text="Actívelo antes de cobrar")
        else:
            self.print_var.set(False)
            self.print_switch.configure(state="disabled")
            self.print_hint.configure(text="Impresora desactivada en config.json")


class ProductCard(ctk.CTkFrame):
    """Tarjeta de producto del catálogo. Un clic la agrega a la venta."""

    def __init__(self, parent, product: Product, on_select: Callable[[Product], None]) -> None:
        self.product = product
        self._on_select = on_select
        out_of_stock = product.stock <= 0
        self._normal = theme.SURFACE_ALT if out_of_stock else theme.SURFACE
        self._hover = theme.SURFACE_ALT if out_of_stock else theme.SURFACE_HOVER
        super().__init__(
            parent,
            fg_color=self._normal,
            corner_radius=12,
            border_width=1,
            border_color=theme.BORDER,
            cursor="arrow" if out_of_stock else "hand2",
            height=CARD_HEIGHT,
        )
        self.grid_propagate(False)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        text_color = theme.MUTED if out_of_stock else theme.TEXT
        ctk.CTkLabel(
            self,
            text=product.name,
            font=theme.font(13, bold=True),
            text_color=text_color,
            anchor="nw",
            justify="left",
            wraplength=CARD_MIN_WIDTH - 26,
        ).grid(row=0, column=0, sticky="nw", padx=12, pady=(10, 0))
        ctk.CTkLabel(
            self,
            text=f"${format_price(product.price)}",
            font=theme.font(16, bold=True),
            text_color=theme.MUTED if out_of_stock else theme.PRIMARY,
            anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=12)
        stock_text, stock_color = _stock_badge(product)
        ctk.CTkLabel(self, text=stock_text, font=theme.font(11), text_color=stock_color, anchor="w").grid(
            row=2, column=0, sticky="w", padx=12, pady=(0, 8)
        )
        for widget in (self, *self.winfo_children()):
            widget.bind("<Button-1>", self._on_click)
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)

    def _on_click(self, _event) -> None:
        self._on_select(self.product)

    def _on_enter(self, _event) -> None:
        self.configure(fg_color=self._hover)

    def _on_leave(self, event) -> None:
        under = self.winfo_containing(event.x_root, event.y_root)
        if under is None or not str(under).startswith(str(self)):
            self.configure(fg_color=self._normal)


def _stock_badge(product: Product) -> tuple[str, str]:
    if product.stock <= 0:
        return "Agotado", theme.DANGER
    if product.stock <= LOW_STOCK_THRESHOLD:
        return f"Quedan {product.stock}", theme.WARNING
    return f"{product.stock} disponibles", theme.MUTED


def _darken(hex_color: str, factor: float = 0.82) -> str:
    value = hex_color.lstrip("#")
    channels = (int(value[i : i + 2], 16) for i in (0, 2, 4))
    return "#" + "".join(f"{max(0, min(255, round(channel * factor))):02X}" for channel in channels)
