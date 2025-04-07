import tkinter as tk
from tkinter import ttk
from utils.formatters import format_price

class VoucherView(tk.Toplevel):
    def __init__(self, parent, controller, receipt, change_due):
        super().__init__(parent)
        self.controller = controller
        self.receipt = receipt
        self.change_due = change_due
        
        # Configuración de la ventana
        self.title("Recibo de Venta")
        self.geometry("680x600")  # Aumentamos tamaño para mejor visualización
        self.create_widgets()
        self.load_receipt_data_from_objects()

    def create_widgets(self):
        gris_claro = "#E0E0E0"
        verde = "#28A745"
        negro = "#000000"
        fuente_titulo = ("Sans-serif", 14, "bold")
        fuente_normal = ("Sans-serif", 12)

        self.config(bg=gris_claro)

        # --------------------------------------------
        # Sección Superior: Información de la tienda
        # --------------------------------------------
        header_frame = tk.Frame(self, bg=gris_claro)
        header_frame.pack(side="top", fill="x", padx=15, pady=10)

        tk.Label(
            header_frame,
            text="CIGARRERÍA ANTARES",
            bg=gris_claro,
            fg=negro,
            font=("Sans-serif", 16, "bold")
        ).pack(anchor="w")

        tk.Label(
            header_frame,
            text="NIT: 80881386-8 | Tel: 350-701-6084",
            bg=gris_claro,
            fg=negro,
            font=fuente_normal
        ).pack(anchor="w", pady=(5,0))

        # --------------------------------------------
        # Datos del Recibo
        # --------------------------------------------
        data_frame = tk.Frame(self, bg=gris_claro)
        data_frame.pack(side="top", fill="x", padx=15, pady=10)

        # Número de Recibo y Fecha
        tk.Label(
            data_frame,
            text=f"Recibo N°: {str(self.receipt.id).zfill(10)}",
            bg=gris_claro,
            fg=negro,
            font=fuente_titulo
        ).grid(row=0, column=0, sticky="w")

        tk.Label(
            data_frame,
            text=f"Fecha: {self.receipt.date.strftime('%d/%m/%Y')}",
            bg=gris_claro,
            fg=negro,
            font=fuente_normal
        ).grid(row=1, column=0, sticky="w", pady=(5,0))

        tk.Label(
            data_frame,
            text=f"Hora: {self.receipt.time.strftime('%H:%M')}",
            bg=gris_claro,
            fg=negro,
            font=fuente_normal
        ).grid(row=2, column=0, sticky="w")

        # --------------------------------------------
        # Tabla de Productos
        # --------------------------------------------
        table_frame = tk.Frame(self, bg=gris_claro)
        table_frame.pack(side="top", fill="both", expand=True, padx=15, pady=10)

        columns = ("cantidad", "nombre", "precio_unitario", "total_parcial")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=8)
        
        # Configurar columnas
        self.tree.heading("cantidad", text="CANTIDAD", anchor="w")
        self.tree.heading("nombre", text="PRODUCTO", anchor="w")
        self.tree.heading("precio_unitario", text="PRECIO UNITARIO", anchor="e")
        self.tree.heading("total_parcial", text="TOTAL PARCIAL", anchor="e")
        
        self.tree.column("cantidad", width=80, anchor="center")
        self.tree.column("nombre", width=250, anchor="w")
        self.tree.column("precio_unitario", width=150, anchor="e")
        self.tree.column("total_parcial", width=150, anchor="e")

        self.tree.pack(side="left", fill="both", expand=True)

        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # --------------------------------------------
        # Totales y Método de Pago
        # --------------------------------------------
        totales_frame = tk.Frame(self, bg=gris_claro)
        totales_frame.pack(side="top", fill="x", padx=15, pady=10)

        # Labels Dinámicas (se actualizarán con los datos)
        self.lbl_total = tk.Label(
            totales_frame,
            text="TOTAL COMPRA: $0",
            bg=gris_claro,
            fg=negro,
            font=fuente_titulo
        )
        self.lbl_total.pack(anchor="e")

        self.lbl_recibido = tk.Label(
            totales_frame,
            text="RECIBIDO: $0",
            bg=gris_claro,
            fg=negro,
            font=fuente_normal
        )
        self.lbl_recibido.pack(anchor="e")

        self.lbl_vueltas = tk.Label(
            totales_frame,
            text="VUELTAS: $0",
            bg=gris_claro,
            fg=negro,
            font=fuente_normal
        )
        self.lbl_vueltas.pack(anchor="e")

        # --------------------------------------------
        # Botón de Volver
        # --------------------------------------------
        btn_frame = tk.Frame(self, bg=gris_claro)
        btn_frame.pack(side="bottom", fill="x", padx=15, pady=15)

        tk.Button(
            btn_frame,
            text="Volver a Ventas",
            bg=verde,
            fg="white",
            font=("Sans-serif", 12, "bold"),
            width=20,
            command=self.controller.event_go_back_to_sales
        ).pack(side="right")

    def load_receipt_data_from_objects(self):
        """Carga los datos del recibo en la vista"""
        productos = [
            (
                sp.quantity, 
                sp.product.name, 
                format_price(sp.product.price), 
                format_price(sp.total_partial)
            ) 
            for sp in self.receipt.sold_products
        ]

        # Calcular valores
        total_compra = self.receipt.total  # Total de la compra
        recibido = total_compra + self.change_due  # Total + Vueltas = Recibido

        # Actualizar labels
        self.lbl_total.config(text=f"TOTAL COMPRA: {format_price(total_compra)}")
        self.lbl_recibido.config(text=f"RECIBIDO: {format_price(recibido)}")
        self.lbl_vueltas.config(text=f"VUELTAS: {format_price(self.change_due)}")

        # Insertar datos en la tabla
        for item in self.tree.get_children():
            self.tree.delete(item)

        for producto in productos:
            self.tree.insert("", "end", values=producto)