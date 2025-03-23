import tkinter as tk
from tkinter import ttk
from utils.formatters import format_price  # Importamos la función para formatear precios

class VoucherView(tk.Toplevel):
    """
    Ventana emergente (Toplevel) que muestra el Recibo:
      - Número de voucher
      - Fecha de emisión (fecha/hora)
      - Tabla de productos (Cantidad, Nombre, Total Parcial)
      - Total, Vueltas
      - Botón "Volver a Ventas"
    """
    def __init__(self, parent, controller):
        """
        parent: la ventana o frame padre (normalmente root o un frame).
        controller: el objeto controlador que maneja la lógica (por ejemplo, un 
                    método event_go_back_to_sales() para cerrar esta ventana y volver).
        """
        super().__init__(parent)
        self.title("Recibo de Venta")
        self.controller = controller

        # Ajuste de tamaño, opcional
        self.geometry("600x500")

        # Creamos widgets
        self.create_widgets()

    def create_widgets(self):
        # Paleta de colores (ajusta a tu gusto)
        gris_claro = "#E0E0E0"
        verde = "#28A745"
        negro = "#000000"
        fuente_header = ("Sans-serif", 16, "bold")
        fuente_normal = ("Sans-serif", 12)

        self.config(bg=gris_claro)

        # ----------------------------------------------------------------------
        # ENCABEZADO: Voucher n°, Fecha/Hora de emisión
        # ----------------------------------------------------------------------
        header_frame = tk.Frame(self, bg=gris_claro)
        header_frame.pack(side="top", fill="x", padx=10, pady=10)

        # Voucher n°
        self.voucher_num_label = tk.Label(
            header_frame,
            text="Voucher n°: 0000000000",
            bg=gris_claro,
            fg=negro,
            font=("Sans-serif", 14, "bold")
        )
        self.voucher_num_label.pack(anchor="w")

        # Fecha / Hora
        self.fecha_hora_label = tk.Label(
            header_frame,
            text="Fecha de emisión: 00/00/0000  00:00",
            bg=gris_claro,
            fg=negro,
            font=fuente_normal
        )
        self.fecha_hora_label.pack(anchor="w", pady=(5,0))

        # Separador visual
        sep = ttk.Separator(self, orient="horizontal")
        sep.pack(fill="x", padx=10, pady=5)

        # ----------------------------------------------------------------------
        # TABLA de productos
        # ----------------------------------------------------------------------
        table_frame = tk.Frame(self, bg=gris_claro)
        table_frame.pack(side="top", fill="both", expand=True, padx=10, pady=5)

        columns = ("cantidad", "nombre", "total_parcial")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=10)
        self.tree.heading("cantidad", text="Cantidad")
        self.tree.heading("nombre", text="Nombre Producto")
        self.tree.heading("total_parcial", text="Total Parcial")

        self.tree.column("cantidad", width=80, anchor="center")
        self.tree.column("nombre", width=220, anchor="w")
        self.tree.column("total_parcial", width=120, anchor="e")

        self.tree.pack(side="left", fill="both", expand=True)

        # Scrollbar vertical
        scrollbar_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar_y.set)
        scrollbar_y.pack(side="right", fill="y")

        # ----------------------------------------------------------------------
        # Sección inferior: Total, Vueltas, Botón "Volver"
        # ----------------------------------------------------------------------
        bottom_frame = tk.Frame(self, bg=gris_claro)
        bottom_frame.pack(side="bottom", fill="x", padx=10, pady=10)

        # Separador
        sep2 = ttk.Separator(bottom_frame, orient="horizontal")
        sep2.pack(fill="x", pady=(0,10))

        # Labels de total y vueltas
        self.total_label = tk.Label(
            bottom_frame,
            text="Total: $0",
            bg=gris_claro,
            fg=negro,
            font=("Sans-serif", 14, "bold")
        )
        self.total_label.pack(anchor="w")

        self.vueltas_label = tk.Label(
            bottom_frame,
            text="Vueltas: $0",
            bg=gris_claro,
            fg=negro,
            font=fuente_normal
        )
        self.vueltas_label.pack(anchor="w", pady=(0,10))

        # Botón "Volver a Ventas"
        self.back_button = tk.Button(
            bottom_frame,
            text="Volver a Ventas",
            bg=verde,
            fg="white",
            font=("Sans-serif", 12, "bold"),
            width=15,
            height=1,
            bd=0,
            cursor="hand2",
            command=self.controller.event_go_back_to_sales  # Ajusta el nombre
        )
        self.back_button.pack(anchor="e")

    def load_receipt_data(self, receipt_id, fecha_emision, hora_emision, productos, total, vueltas):
        """
        Rellena la info del voucher:
          - voucher_num_label
          - fecha_hora_label
          - tabla con productos (cantidad, nombre, total_parcial)
          - total_label y vueltas_label
        :param receipt_id: (str) Ej: "0000000001"
        :param fecha_emision: (str) "11/11/2021"
        :param hora_emision: (str) "19:20"
        :param productos: lista de tuplas (cantidad, nombre, total_parcial)
        :param total: float con el total
        :param vueltas: float con las vueltas
        """
        # Voucher n°
        self.voucher_num_label.config(text=f"Voucher n°: {receipt_id}")
        # Fecha/hora
        self.fecha_hora_label.config(text=f"Fecha de emisión: {fecha_emision}  {hora_emision}")

        # Limpiar la tabla
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Insertar filas en la tabla, usando format_price para total parcial
        for p in productos:
            # p = (cantidad, nombre, total_parcial)
            self.tree.insert("", "end", values=(p[0], p[1], f"${format_price(p[2], decimals=0)}"))

        # Actualizamos total y vueltas, usando también format_price para tener el mismo formato
        self.total_label.config(text=f"Total: ${format_price(total, decimals=0)}")
        self.vueltas_label.config(text=f"Vueltas: ${format_price(vueltas, decimals=0)}")
