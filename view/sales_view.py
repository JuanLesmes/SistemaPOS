import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry  # Para mostrar un calendario desplegable
from utils.formatters import format_price  # Importamos la función para formatear precios

class SalesView(tk.Frame):
    """
    Vista de la Venta de Productos.
    Tiene:
     - Cabecera con título y botón "Volver al Menú".
     - Tabla de productos a la izquierda.
     - Barra lateral derecha con campos para ingresar Código y Cantidad, botones para Agregar/Eliminar, Total y Entry "Recibe".
     - Barra inferior con botones de pago.
    """
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        # Colores personalizados
        fondo = "#9db7b1"
        barra_arriba = "#10a2a7"
        boton_volver = "#b57426"
        
        self.configure(width=800, height=600, bg=fondo)
        self.pack(fill="both", expand=True)
        
        self.create_widgets(fondo, barra_arriba, boton_volver)
    
    def create_widgets(self, fondo, barra_arriba, boton_volver):
        # Colores secundarios (no se modifican)
        blanco = "#FFFFFF"
        negro = "#000000"
        verde = "#28A745"
        rojo = "#FF0000"
        azul = "#0000FF"
        gris_texto = "#808080"
        
        # 1. Cabecera
        header_frame = tk.Frame(self, bg=barra_arriba, height=60)
        header_frame.pack(side="top", fill="x")
        header_frame.pack_propagate(False)

        title_label = tk.Label(
            header_frame,
            text="Venta de Productos",
            fg="#000000",
            bg=barra_arriba,
            font=("Sans-serif", 20, "bold")
        )
        title_label.pack(side="left", padx=20)

        volver_button = tk.Button(
            header_frame,
            text="Volver al Menú",
            bg=boton_volver,  # Botón en color café
            fg= "#113949",
            font=("Sans-serif", 14, "bold"),
            width=12,
            height=1,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
            command=self.controller.event_back  # Llama al método del controller
        )
        volver_button.pack(side="right", padx=20)

        # 2. Sección inferior: métodos de pago
        payment_frame = tk.Frame(self, bg=fondo, height=60)
        payment_frame.pack(side="bottom", fill="x")
        payment_frame.pack_propagate(False)

        payment_container = tk.Frame(payment_frame, bg=fondo)
        payment_container.place(relx=0.5, rely=0.5, anchor="center")

        efectivo_button = tk.Button(
            payment_container,
            text="Pago con Efectivo",
            bg=azul,
            fg=blanco,
            font=("Sans-serif", 14, "bold"),
            width=20,
            height=2,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
            command=self.controller.event_cash_payment  # Lógica en el controller
        )
        efectivo_button.pack(side="left", padx=10)

        tarjeta_button = tk.Button(
            payment_container,
            text="Pago con Tarjeta",
            bg=azul,
            fg=blanco,
            font=("Sans-serif", 14, "bold"),
            width=20,
            height=2,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
            command=self.controller.event_card_payment
        )
        tarjeta_button.pack(side="left", padx=10)

        transferencia_button = tk.Button(
            payment_container,
            text="Transferencia",
            bg=azul,
            fg=blanco,
            font=("Sans-serif", 14, "bold"),
            width=20,
            height=2,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
            command=self.controller.event_transfer_payment
        )
        transferencia_button.pack(side="left", padx=10)

        # 3. Cuerpo principal
        main_frame = tk.Frame(self, bg=fondo)
        main_frame.pack(side="top", fill="both", expand=True)

        # Tabla (a la izquierda)
        table_frame = tk.Frame(main_frame, bg=blanco, bd=1, relief="solid")
        table_frame.pack(side="left", fill="both", expand=True, padx=20, pady=20)

        columns = ("codigo", "nombre", "valor", "cantidad")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        self.tree.heading("codigo", text="Código Producto")
        self.tree.heading("nombre", text="Nombre Producto")
        self.tree.heading("valor", text="Valor Producto")
        self.tree.heading("cantidad", text="Cantidad Producto")

        style = ttk.Style()
        style.configure("Treeview", background=blanco, foreground=negro, rowheight=25, fieldbackground=blanco)
        style.map('Treeview', background=[('selected', fondo)])

        self.tree.pack(fill="both", expand=True)
        self.tree.insert("", "end", values=("", "Tabla sin contenido", "", ""), tags=("placeholder",))
        self.tree.tag_configure("placeholder", foreground=gris_texto, anchor="center")

        # Barra lateral (a la derecha)
        sidebar = tk.Frame(main_frame, bg=fondo)
        sidebar.pack(side="right", fill="y", padx=20, pady=20)

        # --- Bloque para Agregar Producto en la misma pestaña ---
        input_frame = tk.Frame(sidebar, bg=fondo)
        input_frame.pack(pady=10, anchor="w")

        # Etiqueta y Entry para el Código del Producto
        tk.Label(input_frame, text="Código:", bg=fondo, font=("Sans-serif", 12)).grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.product_code_entry = tk.Entry(input_frame, width=20)
        self.product_code_entry.grid(row=0, column=1, padx=5, pady=2)

        # Etiqueta y Entry para la Cantidad
        tk.Label(input_frame, text="Cantidad:", bg=fondo, font=("Sans-serif", 12)).grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.product_qty_entry = tk.Entry(input_frame, width=10)
        self.product_qty_entry.grid(row=1, column=1, padx=5, pady=2)

        # Botón para agregar el producto usando los datos de los Entry
        add_button = tk.Button(
            sidebar,
            text="Agregar Producto",
            bg=verde,  # Se mantiene el color original
            fg=blanco,
            font=("Sans-serif", 14, "bold"),
            width=15,
            height=2,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
            command=self.controller.event_add_product  # Llama a la lógica en el controller
        )
        add_button.pack(pady=10)

        # Botón para eliminar producto
        delete_button = tk.Button(
            sidebar,
            text="Eliminar Producto",
            bg=rojo,  # Se mantiene el color original
            fg=blanco,
            font=("Sans-serif", 14, "bold"),
            width=15,
            height=2,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
            command=self.controller.event_remove_product
        )
        delete_button.pack(pady=10)

        summary_frame = tk.Frame(sidebar, bg=fondo)
        summary_frame.pack(pady=20, anchor="w")

        # Etiqueta del total (se formatea el número usando format_price)
        self.total_label = tk.Label(
            summary_frame,
            text="Total Venta: $ 0",
            bg=fondo,
            fg=negro,
            font=("Sans-serif", 16, "bold")
        )
        self.total_label.pack(anchor="w")

        # Campo "Recibe"
        recibe_label = tk.Label(
            summary_frame,
            text="Recibe:",
            bg=fondo,
            fg=negro,
            font=("Sans-serif", 14)
        )
        recibe_label.pack(anchor="w", pady=(20, 5))

        self.recibe_entry = tk.Entry(
            summary_frame,
            width=20,
            bd=1,
            fg=negro,
            bg=blanco
        )
        self.recibe_entry.pack(anchor="w")

    # -----------------------------------------------------------
    # Métodos para que el controller pueda manipular la vista
    # -----------------------------------------------------------
    def load_table(self, sold_products):
        """
        Carga la tabla con la lista de productos vendidos.
        Si está vacía, muestra un placeholder.
        """
        # Limpiar tabla
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not sold_products:
            self.tree.insert("", "end", values=("", "Tabla sin contenido", "", ""), tags=("placeholder",))
        else:
            # Llenar con productos: formateamos el valor con separador de miles
            for sp in sold_products:
                code = sp.product.code
                name = sp.product.name
                price = format_price(sp.product.price, decimals=0)
                quantity = sp.quantity
                self.tree.insert("", "end", values=(code, name, price, quantity))

    def set_total(self, total_str):
        """
        Actualiza la etiqueta del total de la venta.
        """
        self.total_label.config(text=f"Total Venta: $ {total_str}")

    def clear_received_amount(self):
        """Limpia el campo de monto recibido."""
        self.recibe_entry.delete(0, tk.END)

    def get_received_amount(self):
        """Obtiene el valor ingresado en el campo 'Recibe'."""
        return self.recibe_entry.get().strip()
