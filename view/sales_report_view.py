import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry  # Para mostrar un calendario desplegable
from utils.formatters import format_price  # Importa la función para formatear precios

class SalesReportView(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        # Colores
        self.fondo_general = "#9db7b1"
        self.encabezado = "#10a2a7"
        self.boton_volver = "#b57426"
        self.azul = "#0000FF"
        self.rojo = "#FF0000"
        self.blanco = "#FFFFFF"
        self.negro = "#000000"
        
        # Configura el tamaño base de la ventana y el color de fondo
        self.config(width=800, height=600, bg=self.fondo_general)
        self.pack_propagate(False)
        self.pack(fill="both", expand=True)
        
        # Crea el estilo para la tabla
        self.create_table_styles()
        
        # Construye la interfaz
        self.create_widgets()
    
    def create_widgets(self):
        # Fuentes
        font_header   = ("Sans-serif", 20, "bold")  # Título principal
        font_label    = ("Sans-serif", 14, "bold")
        font_button   = ("Sans-serif", 14, "bold")
        font_summary  = ("Sans-serif", 14)
        
        # ----------------------------------------------------------------
        # 1. Encabezado: Título "Reporte De Ventas" sobre fondo encabezado
        # ----------------------------------------------------------------
        header_frame = tk.Frame(self, bg=self.encabezado, height=60)
        header_frame.pack(side="top", fill="x")
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(
            header_frame,
            text="Reporte De Ventas",
            bg=self.encabezado,
            fg=self.negro,
            font=font_header
        )
        title_label.place(relx=0.5, rely=0.5, anchor="center")
        
        # ----------------------------------------------------------------
        # 2. Cuerpo principal: Tabla de ventas (izquierda) y panel derecho
        # ----------------------------------------------------------------
        body_frame = tk.Frame(self, bg=self.fondo_general)
        body_frame.pack(side="top", fill="both", expand=True)
        
        # Sección Izquierda: Tabla de ventas
        table_frame = tk.Frame(body_frame, bg=self.blanco, bd=1, relief="solid")
        table_frame.pack(side="left", fill="both", expand=True, padx=20, pady=20)
        
        columns = ("code", "name", "qty", "total")
        self.sales_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            style="SalesReport.Treeview"
        )
        self.sales_tree.heading("code", text="Código")
        self.sales_tree.heading("name", text="Nombre")
        self.sales_tree.heading("qty", text="Cantidad")
        self.sales_tree.heading("total", text="Total")
        
        self.sales_tree.column("code", width=80)
        self.sales_tree.column("name", width=160)
        self.sales_tree.column("qty", width=80, anchor="center")
        self.sales_tree.column("total", width=80, anchor="e")
        self.sales_tree.pack(side="left", fill="both", expand=True)
        
        # Scrollbar vertical para la tabla
        scrollbar_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.sales_tree.yview)
        self.sales_tree.configure(yscroll=scrollbar_y.set)
        scrollbar_y.pack(side="right", fill="y")
        
        # Mensaje predeterminado cuando la tabla está vacía
        self.sales_tree.insert("", "end", values=("", "Tabla sin contenido", "", ""))
        
        # Sección Derecha: Filtros de fecha, resumen de montos y botones
        right_frame = tk.Frame(body_frame, bg=self.fondo_general, width=250)
        right_frame.pack(side="right", fill="y", padx=20, pady=20)
        right_frame.pack_propagate(False)
        
        # 2.1 Filtros de fecha
        filters_frame = tk.Frame(right_frame, bg=self.fondo_general)
        filters_frame.pack(side="top", fill="x")
        
        start_label = tk.Label(filters_frame, text="Fecha Inicio", bg=self.fondo_general, fg=self.negro, font=font_label)
        start_label.pack(anchor="w", pady=(0,5))
        self.start_date = DateEntry(filters_frame, width=15, background="darkblue",
                                    foreground="white", borderwidth=2, date_pattern="yyyy-mm-dd")
        self.start_date.pack(anchor="w", pady=(0,10))
        
        end_label = tk.Label(filters_frame, text="Fecha Término", bg=self.fondo_general, fg=self.negro, font=font_label)
        end_label.pack(anchor="w", pady=(0,5))
        self.end_date = DateEntry(filters_frame, width=15, background="darkblue",
                                  foreground="white", borderwidth=2, date_pattern="yyyy-mm-dd")
        self.end_date.pack(anchor="w", pady=(0,10))
        
        search_button = tk.Button(
            filters_frame,
            text="Buscar",
            bg=self.azul,
            fg=self.blanco,
            font=font_button,
            bd=0,
            cursor="hand2",
            command=self.on_search_click
        )
        search_button.config(width=12, height=1)
        search_button.pack(anchor="w", pady=(10,10))
        
        # 2.2 Resumen de montos
        summary_frame = tk.Frame(right_frame, bg=self.fondo_general)
        summary_frame.pack(side="top", fill="x", pady=(20, 0))
        
        total_label = tk.Label(summary_frame, text="Total Recaudado", bg=self.fondo_general, font=("Sans-serif", 16, "bold"))
        total_label.pack(anchor="w", pady=(0,0))
        self.total_amount_label = tk.Label(summary_frame, text="$0", bg=self.fondo_general, font=("Sans-serif", 16, "bold"))
        self.total_amount_label.pack(anchor="w", pady=5)
        
        self.cash_label = tk.Label(summary_frame, text="Efectivo        $0", bg=self.fondo_general, font=font_summary)
        self.cash_label.pack(anchor="w", pady=5)
        self.card_label = tk.Label(summary_frame, text="Tarjeta         $0", bg=self.fondo_general, font=font_summary)
        self.card_label.pack(anchor="w", pady=5)
        self.transfer_label = tk.Label(summary_frame, text="Transferencia  $0", bg=self.fondo_general, font=font_summary)
        self.transfer_label.pack(anchor="w", pady=5)
        
        # 2.3 Botón "Volver al Menú"
        back_button = tk.Button(
            right_frame,
            text="Volver al Menú",
            bg=self.boton_volver,
            fg=self.negro,
            font=("Sans-serif", 16, "bold"),
            bd=0,
            cursor="hand2",
            command=self.on_back_click
        )
        back_button.config(width=14, height=2)
        back_button.pack(side="bottom", pady=20)
    
    def create_table_styles(self):
        """Define el estilo personalizado para la tabla."""
        style = ttk.Style()
        style.theme_use("clam")
        
        # Cabecera de la tabla
        style.configure(
            "SalesReport.Treeview.Heading",
            background=self.encabezado,
            foreground=self.negro,
            font=("Sans-serif", 14, "bold")
        )
        # Contenido de la tabla
        style.configure(
            "SalesReport.Treeview",
            font=("Sans-serif", 12),
            rowheight=25,
            bordercolor="#D3D3D3",
            borderwidth=1
        )
        # Color de la fila seleccionada
        style.map(
            "SalesReport.Treeview",
            background=[("selected", self.fondo_general)]
        )
    
    # Métodos para obtener la fecha seleccionada
    def get_start_date(self):
        return self.start_date.get_date()
    
    def get_end_date(self):
        return self.end_date.get_date()
    
    # Método para cargar la tabla con los productos vendidos
    def load_table(self, sold_products):
        # Elimina registros anteriores
        for item in self.sales_tree.get_children():
            self.sales_tree.delete(item)
        
        # Si la lista está vacía, muestra un mensaje
        if not sold_products:
            self.sales_tree.insert("", "end", values=("", "Tabla sin contenido", "", ""))
            return
        
        # Inserta cada producto vendido en la tabla, formateando el total con separador de miles
        for sp in sold_products:
            self.sales_tree.insert(
                "",
                "end",
                values=(
                    sp.get_code(),
                    sp.product.name,
                    sp.quantity,
                    f"${format_price(sp.get_total_partial(), decimals=0)}"
                )
            )
    
    # Método para actualizar los totales en el resumen
    def set_totals(self, total, cash, card, transfer):
        self.total_amount_label.config(text=f"${format_price(total, decimals=2)}")
        self.cash_label.config(text=f"Efectivo        ${format_price(cash, decimals=2)}")
        self.card_label.config(text=f"Tarjeta         ${format_price(card, decimals=2)}")
        self.transfer_label.config(text=f"Transferencia  ${format_price(transfer, decimals=2)}")
    
    # Eventos de los botones
    def on_search_click(self):
        """Al hacer clic en 'Buscar', se llama al controlador para procesar la búsqueda."""
        self.controller.event_search()
    
    def on_back_click(self):
        """Al hacer clic en 'Volver al Menú', se llama al controlador para regresar a la vista principal."""
        self.controller.event_back()