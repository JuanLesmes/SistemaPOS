import customtkinter as ctk
from tkinter import ttk
from utils.formatters import format_price

ctk.deactivate_automatic_dpi_awareness()

class VoucherView(ctk.CTkToplevel):
    def __init__(self, parent, controller, receipt, change_due):
        super().__init__(parent)
        self.controller = controller
        self.receipt = receipt
        self.change_due = change_due
        self.original_parent = parent
        self._pending_after_ids = []
        self.attributes('-topmost', True)

        # Configuración de colores
        self.franja_color = "#10a2a7"
        self.titulo_color = "#FFFFFF"
        self.fondo_tabla = "#F8F9F9"

        # Fuerza la opacidad del padre original
        try:
            self.original_parent.attributes("-alpha", 1.0)
        except Exception:
            pass

        self.title("Recibo de Venta")
        self.geometry("720x640+100+100")
        self.minsize(700, 620)
        
        self._create_tree_style()
        self._create_widgets()
        self.load_receipt_data_from_objects()

        self.lift()
        self.focus_force()

    def destroy(self):
        for after_id in self._pending_after_ids:
            self.after_cancel(after_id)
        
        try:
            self.original_parent.lift()
            self.original_parent.focus_force()
        except Exception:
            pass
        
        super().destroy()

    def _create_tree_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Voucher.Treeview.Heading",
                        background=self.franja_color,
                        foreground=self.titulo_color,
                        font=("Segoe UI", 12, "bold"),
                        padding=5)
        style.configure("Voucher.Treeview",
                        font=("Segoe UI", 12),
                        rowheight=28,
                        fieldbackground=self.fondo_tabla,
                        background=self.fondo_tabla,
                        foreground="black",
                        bordercolor="#CCCCCC",
                        borderwidth=1)
        style.map("Voucher.Treeview",
                  background=[("selected", "#A0E7E5")],
                  foreground=[("selected", "black")])

    def _create_widgets(self):
        fondo = "#E0E0E0"
        verde = "#28A745"
        negro = "#000000"

        self.configure(fg_color=fondo)

        header_frame = ctk.CTkFrame(self, fg_color=fondo, corner_radius=0)
        header_frame.pack(side="top", fill="x", padx=20, pady=(20, 0))

        franja_decorativa = ctk.CTkFrame(
            self, 
            height=4, 
            fg_color=self.franja_color,
            corner_radius=0
        )
        franja_decorativa.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(header_frame,
                     text="CIGARRERÍA ANTARES",
                     font=("Segoe UI", 18, "bold"),
                     text_color=negro,
                     fg_color=fondo).pack(anchor="w")

        ctk.CTkLabel(header_frame,
                     text="NIT: 80881386-8 | Tel: 350-701-6084",
                     font=("Segoe UI", 12),
                     text_color=negro,
                     fg_color=fondo).pack(anchor="w", pady=(5, 0))

        data_frame = ctk.CTkFrame(self, fg_color=fondo, corner_radius=0)
        data_frame.pack(side="top", fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(data_frame,
                     text=f"Recibo N°: {str(self.receipt.id).zfill(10)}",
                     font=("Segoe UI", 14, "bold"),
                     text_color=negro,
                     fg_color=fondo).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(data_frame,
                     text=f"Fecha: {self.receipt.date.strftime('%d/%m/%Y')}",
                     font=("Segoe UI", 12),
                     text_color=negro,
                     fg_color=fondo).grid(row=1, column=0, sticky="w", pady=(5, 0))

        ctk.CTkLabel(data_frame,
                     text=f"Hora: {self.receipt.time.strftime('%H:%M')}",
                     font=("Segoe UI", 12),
                     text_color=negro,
                     fg_color=fondo).grid(row=2, column=0, sticky="w")

        table_frame = ctk.CTkFrame(
            self, 
            fg_color="white", 
            corner_radius=10, 
            border_color="#CCCCCC", 
            border_width=1
        )
        table_frame.pack(side="top", fill="both", expand=True, padx=20, pady=10)

        columns = ("cantidad", "nombre", "precio_unitario", "total_parcial")
        self.tree = ttk.Treeview(
            table_frame, 
            columns=columns, 
            show="headings", 
            style="Voucher.Treeview"
        )

        self.tree.heading("cantidad", text="CANTIDAD")
        self.tree.heading("nombre", text="PRODUCTO")
        self.tree.heading("precio_unitario", text="PRECIO UNITARIO")
        self.tree.heading("total_parcial", text="TOTAL PARCIAL")

        self.tree.column("cantidad", width=80, anchor="center")
        self.tree.column("nombre", width=250, anchor="w")
        self.tree.column("precio_unitario", width=150, anchor="e")
        self.tree.column("total_parcial", width=150, anchor="e")

        scrollbar = ctk.CTkScrollbar(table_frame)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.configure(command=self.tree.yview)

        self.tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)

        totales_frame = ctk.CTkFrame(self, fg_color=fondo)
        totales_frame.pack(side="top", fill="x", padx=20, pady=10)

        self.lbl_total = ctk.CTkLabel(
            totales_frame,
            text="TOTAL COMPRA: $0",
            font=("Segoe UI", 14, "bold"),
            text_color=negro,
            fg_color=fondo
        )
        self.lbl_total.pack(anchor="e")

        self.lbl_recibido = ctk.CTkLabel(
            totales_frame,
            text="RECIBIDO: $0",
            font=("Segoe UI", 12),
            text_color=negro,
            fg_color=fondo
        )
        self.lbl_recibido.pack(anchor="e")

        self.lbl_vueltas = ctk.CTkLabel(
            totales_frame,
            text="VUELTAS: $0",
            font=("Segoe UI", 12),
            text_color=negro,
            fg_color=fondo
        )
        self.lbl_vueltas.pack(anchor="e")

        btn_frame = ctk.CTkFrame(self, fg_color=fondo)
        btn_frame.pack(side="bottom", fill="x", padx=20, pady=(0, 15))

        ctk.CTkButton(
            btn_frame,
            text="Volver a Ventas",
            fg_color="#28A745",
            hover_color="#218838",
            text_color="white",
            font=("Segoe UI", 12, "bold"),
            corner_radius=10,
            width=180,
            height=40,
            command=self.close_view
        ).pack(side="left", anchor="w")

    def close_view(self):
        self.destroy()

    def load_receipt_data_from_objects(self):
        productos = [
            (
                sp.quantity,
                sp.product.name,
                format_price(sp.product.price),
                format_price(sp.total_partial)
            )
            for sp in self.receipt.sold_products
        ]

        total_compra = self.receipt.total
        recibido = total_compra + self.change_due

        self.lbl_total.configure(text=f"TOTAL COMPRA: {format_price(total_compra)}")
        self.lbl_recibido.configure(text=f"RECIBIDO: {format_price(recibido)}")
        self.lbl_vueltas.configure(text=f"VUELTAS: {format_price(self.change_due)}")

        for item in self.tree.get_children():
            self.tree.delete(item)

        for producto in productos:
            self.tree.insert("", "end", values=producto)