import customtkinter as ctk
from tkinter import ttk
from utils.formatters import format_price

class SalesView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#9db7b1")
        self.controller = controller

        # Colores
        self.fondo = "#9db7b1"
        self.barra_arriba = "#10a2a7"
        self.boton_volver = "#b57426"
        self.blanco = "#FFFFFF"
        self.negro = "#000000"
        self.rojo = "#FF0000"
        self.azul = "#0000FF"

        # Configuración de estilo para botones y entradas
        self.btn_cfg = {
            "corner_radius": 12,
            "height": 50,
            "width": 200,
            "font": ("Segoe UI", 16, "bold")
        }

        self.entry_cfg = {
            "corner_radius": 10,
            "height": 35,
            "width": 150,
            "font": ("Segoe UI", 14)
        }

        # Layout
        self.pack(fill="both", expand=True)
        self._create_tree_style()
        self._create_widgets()

        # Eventos
        self.tree.bind("<Button-1>", self._on_click)  
        self.bind("<Button-1>", self._on_click)  
        self.recibe_entry.bind("<Return>", lambda e: self._on_enter_recibe())
        self.recibe_entry.bind("<FocusIn>", lambda e: controller._pause_barcode_reader())
        self.recibe_entry.bind("<FocusOut>", lambda e: controller._resume_barcode_reader())

    
    def _on_click(self, event):
        """Restaura el foco al hacer clic en la vista"""
        widget = self.winfo_containing(event.x_root, event.y_root)
        if widget != self.recibe_entry:
            self.controller.force_focus_restore()

    def _on_enter_recibe(self):
        self.controller.process_payment()
        self.focus_set()

    def _create_tree_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Sales.Treeview.Heading",
                        background=self.barra_arriba,
                        foreground="white",
                        font=("Segoe UI", 14, "bold"))
        style.configure("Sales.Treeview",
                        font=("Segoe UI", 12),
                        rowheight=28,
                        fieldbackground=self.blanco,
                        background=self.blanco,
                        foreground=self.negro,
                        bordercolor="#CCCCCC",
                        borderwidth=1)
        style.map("Sales.Treeview",
                  background=[("selected", "#A0E7E5")],
                  foreground=[("selected", "black")])

    def _create_widgets(self):
        # 1) Cabecera
        header = ctk.CTkFrame(self, fg_color=self.barra_arriba, corner_radius=0)
        header.pack(side="top", fill="x", ipady=5)

        # Título y botón en cabecera
        ctk.CTkLabel(header,
                    text="Venta de Productos",
                    text_color=self.negro,
                    font=("Segoe UI", 20, "bold")
        ).pack(side="left", padx=20)

        ctk.CTkButton(header,
                    text="Volver al Menú",
                    fg_color=self.boton_volver,
                    hover_color="#c7853a",
                    text_color=self.negro,
                    command=self.controller.event_back,
                    **self.btn_cfg
        ).pack(side="right", padx=20)

        # 2) Contenedor principal (tabla + sidebar)
        main_container = ctk.CTkFrame(self, fg_color=self.fondo)
        main_container.pack(side="top", fill="both", expand=True, padx=20, pady=10)

        # 3) Contenedor de tabla (expandible)
        table_frame = ctk.CTkFrame(
            main_container,
            fg_color=self.blanco,
            corner_radius=8,
            border_width=1,
            border_color="#CCCCCC"
        )
        table_frame.pack(side="left", fill="both", expand=True, padx=(0, 20))

        # Configuración del Treeview
        cols = ("codigo", "nombre", "valor", "cantidad")
        self.tree = ttk.Treeview(
            table_frame,
            columns=cols,
            show="headings",
            style="Sales.Treeview",
            selectmode="browse"
        )

        # Scrollbar
        scrollbar = ctk.CTkScrollbar(table_frame)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.configure(command=self.tree.yview)

        # Configurar columnas
        for col, w, a, h in [
            ("codigo", 120, "w", "Código"),
            ("nombre", 250, "w", "Nombre"),
            ("valor", 120, "e", "Valor"),
            ("cantidad", 100, "center", "Cantidad"),
        ]:
            self.tree.heading(col, text=h)
            self.tree.column(col, width=w, anchor=a)
        
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        # 4) Sidebar derecho
        sidebar = ctk.CTkFrame(main_container, fg_color=self.fondo, width=280)
        sidebar.pack(side="right", fill="y", expand=False)

        # Botón eliminar producto
        ctk.CTkButton(sidebar,
                    text="Eliminar Producto",
                    fg_color=self.rojo,
                    hover_color="#cc0000",
                    text_color=self.blanco,
                    command=self.controller.event_remove_product,
                    **self.btn_cfg
        ).pack(fill="x", pady=5)

        # Sección de pago
        ctk.CTkLabel(sidebar,
                    text="Recibe:",
                    text_color=self.negro,
                    font=("Segoe UI", 14)
        ).pack(anchor="w", pady=(20,5))
        
        self.recibe_entry = ctk.CTkEntry(sidebar,
                                        placeholder_text="0",
                                        fg_color=self.blanco,
                                        text_color=self.negro,
                                        **self.entry_cfg)
        self.recibe_entry.pack(fill="x")

        self.total_label = ctk.CTkLabel(sidebar,
                                    text="Total Venta: $0",
                                    text_color=self.negro,
                                    font=("Segoe UI", 16, "bold"))
        self.total_label.pack(anchor="w", pady=(20,0))

        # 5) Botones de pago (parte inferior)
        pay_frame = ctk.CTkFrame(self, fg_color=self.fondo, height=80)
        pay_frame.pack(side="bottom", fill="x", padx=20, pady=10)

        btn_extra_cfg = {
            "width": 300,   # Más ancho
            "height": 40    # Un poco menos alto
        }

        # Botones de métodos de pago
        metodos_pago = [
            ("Pago con Efectivo", self.controller.event_cash_payment),
            ("Pago con Tarjeta", self.controller.event_card_payment),
            ("Transferencia", self.controller.event_transfer_payment)
        ]
        
        for texto, comando in metodos_pago:
            ctk.CTkButton(pay_frame,
                        text=texto,
                        fg_color=self.azul,
                        hover_color="#3333CC",
                        text_color=self.blanco,
                        command=comando,
                        **{**self.btn_cfg, **btn_extra_cfg}
            ).pack(side="left", padx=10, expand=True)

    # --------------------------------------------------------------------------
    # Métodos que el controller usa para actualizar la vista
    # --------------------------------------------------------------------------
    def load_table(self, sold_products):
        # Limpia la tabla
        for item in self.tree.get_children():
            self.tree.delete(item)
        # Inserta cada producto
        for sp in sold_products:
            self.tree.insert(
                "", "end",
                values=(
                    sp.product.code,
                    sp.product.name,
                    format_price(sp.product.price, decimals=0),
                    sp.quantity
                )
            )

    def set_total(self, total):
        # Formatea y muestra el total
        try:
            total_num = float(total)
            txt = format_price(total_num, decimals=0)
        except ValueError:
            txt = "0"
        self.total_label.configure(text=f"Total Venta: $ {txt}")

    def clear_received_amount(self):
        self.recibe_entry.delete(0, "end")

    def get_received_amount(self):
        return self.recibe_entry.get().strip()
