import tkinter as tk
from tkinter import ttk
from utils.formatters import format_price

class SalesView(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        # 1. Definir todos los colores como atributos
        self.fondo = "#9db7b1"
        self.barra_arriba = "#10a2a7"
        self.boton_volver = "#b57426"
        self.blanco = "#FFFFFF"
        self.negro = "#000000"
        self.rojo = "#FF0000"
        self.azul = "#0000FF"
        self.gris_texto = "#808080"

        # 2. Configuración inicial del frame
        self.configure(width=800, height=600, bg=self.fondo)
        self.pack(fill="both", expand=True)
        
        # 3. Crear widgets
        self.create_widgets()
        
        # 4. Configurar eventos
        self.bind("<KeyRelease>", self.controller.handle_barcode_input)
        self.recibe_entry.bind("<Return>", self._on_enter_recibe)
        self.focus_set()

    def _on_enter_recibe(self, event):
        """Maneja el Enter en el campo Recibe"""
        self.controller.process_payment()
        self.focus_set()

    def create_widgets(self):
        """Crea todos los widgets usando los colores de los atributos"""
        # --------------------------------------------
        # 1. CABECERA
        # --------------------------------------------
        header_frame = tk.Frame(self, bg=self.barra_arriba, height=60)
        header_frame.pack(side="top", fill="x")
        header_frame.pack_propagate(False)

        # Título
        tk.Label(
            header_frame,
            text="Venta de Productos",
            bg=self.barra_arriba,
            fg=self.negro,
            font=("Sans-serif", 20, "bold")
        ).pack(side="left", padx=20)

        # Botón Volver
        tk.Button(
            header_frame,
            text="Volver al Menú",
            bg=self.boton_volver,
            fg=self.negro,
            font=("Sans-serif", 14, "bold"),
            width=12,
            height=1,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
            command=self.controller.event_back
        ).pack(side="right", padx=20)

        # --------------------------------------------
        # 2. SECCIÓN INFERIOR: MÉTODOS DE PAGO
        # --------------------------------------------
        payment_frame = tk.Frame(self, bg=self.fondo, height=60)
        payment_frame.pack(side="bottom", fill="x")
        payment_frame.pack_propagate(False)

        payment_container = tk.Frame(payment_frame, bg=self.fondo)
        payment_container.place(relx=0.5, rely=0.5, anchor="center")

        # Botón Efectivo
        tk.Button(
            payment_container,
            text="Pago con Efectivo",
            bg=self.azul,
            fg=self.blanco,
            font=("Sans-serif", 14, "bold"),
            width=20,
            height=2,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
            command=self.controller.event_cash_payment,
            takefocus=0
        ).pack(side="left", padx=10)

        # Botón Tarjeta
        tk.Button(
            payment_container,
            text="Pago con Tarjeta",
            bg=self.azul,
            fg=self.blanco,
            font=("Sans-serif", 14, "bold"),
            width=20,
            height=2,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
            command=self.controller.event_card_payment
        ).pack(side="left", padx=10)

        # Botón Transferencia
        tk.Button(
            payment_container,
            text="Transferencia",
            bg=self.azul,
            fg=self.blanco,
            font=("Sans-serif", 14, "bold"),
            width=20,
            height=2,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
            command=self.controller.event_transfer_payment
        ).pack(side="left", padx=10)

        # --------------------------------------------
        # 3. CUERPO PRINCIPAL
        # --------------------------------------------
        main_frame = tk.Frame(self, bg=self.fondo)
        main_frame.pack(side="top", fill="both", expand=True)

        # Tabla de productos (Izquierda)
        table_frame = tk.Frame(main_frame, bg=self.blanco, bd=1, relief="solid")
        table_frame.pack(side="left", fill="both", expand=True, padx=20, pady=20)

        # Crear Treeview (primero crearlo, luego configurar)
        columns = ("codigo", "nombre", "valor", "cantidad")
        self.tree = ttk.Treeview(
            table_frame, 
            columns=columns, 
            show="headings",
            selectmode="browse"  # Configurar selectmode aquí
        )

        # Configurar encabezados y columnas 
        self.tree.heading("codigo", text="Código")
        self.tree.heading("nombre", text="Nombre")
        self.tree.heading("valor", text="Valor")
        self.tree.heading("cantidad", text="Cantidad")
        self.tree.column("codigo", width=120, anchor="w")
        self.tree.column("nombre", width=250, anchor="w")
        self.tree.column("valor", width=120, anchor="e")
        self.tree.column("cantidad", width=100, anchor="center")

        self.tree.pack(fill="both", expand=True)

        # Sidebar derecha
        sidebar = tk.Frame(main_frame, bg=self.fondo)
        sidebar.pack(side="right", fill="y", padx=20, pady=20)
        
        # Panel de acciones
        actions_frame = tk.Frame(sidebar, bg=self.fondo)
        actions_frame.pack(fill="x", pady=10)
        
        # Botón Eliminar
        self.delete_btn = tk.Button(
            actions_frame,
            text="Eliminar Producto",
            bg=self.rojo,
            fg=self.blanco,
            font=("Sans-serif", 12, "bold"),
            command=self.controller.event_remove_product,
            takefocus=0
        )
        self.delete_btn.pack(fill="x", pady=5)
        
        # Panel de pago
        payment_sidebar_frame = tk.Frame(sidebar, bg=self.fondo)
        payment_sidebar_frame.pack(fill="x", pady=20)
        
        # Campo "Recibe"
        tk.Label(
            payment_sidebar_frame,
            text="Recibe:",
            bg=self.fondo,
            fg=self.negro,
            font=("Sans-serif", 14)
        ).pack(anchor="w", pady=(0,5))
        
        self.recibe_entry = tk.Entry(
            payment_sidebar_frame,
            width=15,
            bd=1,
            fg=self.negro,
            bg=self.blanco,
            font=("Sans-serif", 14)
        )
        self.recibe_entry.pack(anchor="w")
        
        # Total
        self.total_label = tk.Label(
            payment_sidebar_frame,
            text="Total: $0",
            bg=self.fondo,
            fg=self.negro,
            font=("Sans-serif", 16, "bold")
        )
        self.total_label.pack(anchor="w", pady=20)

    # -----------------------------------------------------------
    # Métodos para el controlador
    # -----------------------------------------------------------
    def load_table(self, sold_products):
        # Limpiar tabla
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Llenar con todos los ítems
        for sp in sold_products:
            self.tree.insert("", "end", values=(
                sp.product.code,
                sp.product.name,
                format_price(sp.product.price, decimals=0),
                sp.quantity
            ))

    def set_total(self, total):
        # Asegúrate de convertir "total" a float antes de formatear
        try:
            total_num = float(total)  # Convertir a número si es cadena
            formatted_total = format_price(total_num, decimals=0)
            self.total_label.config(text=f"Total Venta: $ {formatted_total}")
        except ValueError:
            # Manejar error si no se puede convertir a número
            self.total_label.config(text=f"Total Venta: $0")

    def clear_received_amount(self):
        self.recibe_entry.delete(0, tk.END)

    def get_received_amount(self):
        return self.recibe_entry.get().strip()
    