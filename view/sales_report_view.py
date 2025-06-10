import customtkinter as ctk
from tkinter import ttk
from tkcalendar import DateEntry
from utils.formatters import format_price
import datetime


class SalesReportView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#9db7b1")
        self.controller = controller

        # Colores
        self.fondo_general = "#9db7b1"
        self.encabezado    = "#10a2a7"
        self.boton_volver  = "#b57426"
        self.azul          = "#0000FF"
        self.rojo          = "#FF0000"
        self.blanco        = "#FFFFFF"
        self.negro         = "#000000"

        # Tamaños botones / entradas
        self.btn_cfg = {
            "corner_radius": 12,
            "height": 40,
            "width": 140,
            "font": ("Segoe UI", 14, "bold")
        }

        # Layout principal
        self.pack(fill="both", expand=True)
        self.pack_propagate(False)

        # Estilo de la tabla
        self._create_table_style()
        # Widgets
        self._create_widgets()

    def _create_table_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "SalesReport.Treeview.Heading",
            background=self.encabezado,
            foreground=self.blanco,
            font=("Segoe UI", 14, "bold")
        )
        style.configure(
            "SalesReport.Treeview",
            font=("Segoe UI", 12),
            rowheight=24,
            fieldbackground=self.blanco,
            background=self.blanco,
            foreground=self.negro,
            bordercolor="#CCCCCC",
            borderwidth=1
        )
        style.map(
            "SalesReport.Treeview",
            background=[("selected", "#A0E7E5")],
            foreground=[("selected", "black")]
        )

    def _create_widgets(self):
        # ——— 1) Encabezado —————————————
        header = ctk.CTkFrame(self, fg_color=self.encabezado, corner_radius=0, height=60)
        header.pack(side="top", fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="Reporte De Ventas",
            text_color=self.blanco,
            font=("Segoe UI", 20, "bold")
        ).place(relx=0.5, rely=0.5, anchor="center")

        # ——— 2) Contenedor principal ————————
        main = ctk.CTkFrame(self, fg_color=self.fondo_general, corner_radius=0)
        main.pack(side="top", fill="both", expand=True, padx=20, pady=10)

        # 2a) Tabla de ventas
        table_frame = ctk.CTkFrame(
            main,
            fg_color=self.blanco,
            corner_radius=8,
            border_width=1,
            border_color="#CCCCCC"
        )
        table_frame.pack(side="left", fill="both", expand=True, padx=(0,20))

        # Scrollbar integrada
        scrollbar = ctk.CTkScrollbar(table_frame)
        scrollbar.pack(side="right", fill="y", padx=(0,5), pady=5)

        # Treeview con columnas
        columns = ("datetime", "hour", "code", "name", "qty", "total", "payment")
        self.sales_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            style="SalesReport.Treeview",
            yscrollcommand=scrollbar.set
        )
        scrollbar.configure(command=self.sales_tree.yview)

        for col, w, anchor, title in [
            ("datetime", 80, "center", "Fecha"),
            ("hour",      40,  "center", "Hora"),
            ("code",      60,  "w",      "Código"),
            ("name",     180,  "w",      "Nombre"),
            ("qty",       40,  "center", "Cantidad"),
            ("total",    100,  "e",      "Total"),
            ("payment",  100, "center", "Pago"),
        ]:
            self.sales_tree.heading(col, text=title)
            self.sales_tree.column(col, width=w, anchor=anchor)

        self.sales_tree.pack(fill="both", expand=True, padx=5, pady=5)

        # placeholder inicial (una fila vacía con fecha)
        self.sales_tree.insert("", "end", values=("", "Tabla sin contenido", "", "", ""))
        
        # 2b) Panel derecho
        sidebar = ctk.CTkFrame(main, fg_color=self.fondo_general, corner_radius=0, width=260)
        sidebar.pack(side="right", fill="y")
        sidebar.pack_propagate(False)

        # Filtros de fecha
        ctk.CTkLabel(sidebar, text="Fecha Inicio", text_color=self.negro, font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(10,2), padx=10)
        self.start_date = DateEntry(sidebar, width=18, background="darkblue", foreground="white", borderwidth=2, date_pattern="yyyy-mm-dd")
        self.start_date.pack(anchor="w", padx=10)

        ctk.CTkLabel(sidebar, text="Fecha Término", text_color=self.negro, font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(10,2), padx=10)
        self.end_date = DateEntry(sidebar, width=18, background="darkblue", foreground="white", borderwidth=2, date_pattern="yyyy-mm-dd")
        self.end_date.pack(anchor="w", padx=10)

        ctk.CTkButton(
            sidebar,
            text="Buscar",
            fg_color=self.azul,
            hover_color="#3333CC",
            text_color=self.blanco,
            command=self.on_search_click,
            **self.btn_cfg
        ).pack(anchor="w", pady=15, padx=10)

        # Resumen de montos
        ctk.CTkLabel(sidebar, text="Total Recaudado", text_color=self.negro, font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(20,2), padx=10)
        self.total_amount_label = ctk.CTkLabel(sidebar, text="$0", text_color=self.negro, font=("Segoe UI", 16, "bold"))
        self.total_amount_label.pack(anchor="w", padx=10)

        self.cash_label = ctk.CTkLabel(sidebar, text="Efectivo:    $0", text_color=self.negro, font=("Segoe UI", 14))
        self.cash_label.pack(anchor="w", pady=2, padx=10)
        self.card_label = ctk.CTkLabel(sidebar, text="Tarjeta:     $0", text_color=self.negro, font=("Segoe UI", 14))
        self.card_label.pack(anchor="w", pady=2, padx=10)
        self.transfer_label = ctk.CTkLabel(sidebar, text="Transferencia: $0", text_color=self.negro, font=("Segoe UI", 14))
        self.transfer_label.pack(anchor="w", pady=2, padx=10)

        # Botón “Volver al Menú”
        ctk.CTkButton(
            sidebar,
            text="Volver al Menú",
            fg_color=self.boton_volver,
            hover_color="#c7853a",
            text_color=self.negro,
            command=self.on_back_click,
            **self.btn_cfg
        ).pack(side="bottom", pady=20, padx=10)

        # Botón “Generar Reporte”
        self.generate_report_button = ctk.CTkButton(
            sidebar,
            text="Generar Reporte",
            fg_color="#28a745",            # Verde tipo "bootstrap"
            hover_color="#218838",         # Verde oscuro al pasar el mouse
            text_color=self.blanco,
            command=self.controller.generate_report,
            **self.btn_cfg
        )
        self.generate_report_button.pack(anchor="w", pady=15, padx=10)



    

    # --------------------------------------------------------------------------
    # Métodos que el controller usa para actualizar la vista
    # --------------------------------------------------------------------------
    def load_table(self, sold_products):
        self.filtered_sold_products = sold_products
        for iid in self.sales_tree.get_children():
            self.sales_tree.delete(iid)

        if not sold_products:
            self.sales_tree.insert("", "end", values=("", "Tabla sin contenido", "", "", ""))
            return

        for sp in sold_products:
            fecha = sp.date.strftime("%Y-%m-%d") if isinstance(sp.date, datetime.date) else str(sp.date)
            self.sales_tree.insert(
                "", "end",
                values=(
                    fecha,          
                    sp.time_str,   
                    sp.get_code(),
                    sp.product.name,
                    sp.quantity,
                    f"${format_price(sp.get_total_partial(), decimals=0)}",
                    sp.payment_method
                )
            )


    def get_start_date(self):
        return self.start_date.get_date()

    def get_end_date(self):
        return self.end_date.get_date()

    def set_totals(self, total, cash, card, transfer):
        self.total_amount_label.configure(text=f"${format_price(total, decimals=2)}")
        self.cash_label.configure(text=f"Efectivo:    ${format_price(cash, decimals=2)}")
        self.card_label.configure(text=f"Tarjeta:     ${format_price(card, decimals=2)}")
        self.transfer_label.configure(text=f"Transferencia: ${format_price(transfer, decimals=2)}")

    def get_displayed_products(self):
        return self.filtered_sold_products  # O la lista que estés usando para mostrar los productos


    # --------------------------------------------------------------------------
    # Callbacks de los botones
    # --------------------------------------------------------------------------
    def on_search_click(self):
        self.controller.event_search()

    def on_back_click(self):
        self.controller.event_back()
