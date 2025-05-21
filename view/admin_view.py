# view/admin_view.py

import customtkinter as ctk
from tkinter import ttk
from utils.formatters import format_price


class AdminView(ctk.CTkFrame):
    """
    Vista para el Control de Inventario, usando CustomTkinter.
    Tiene:
      - Cabecera con título y botón "Volver al Menú".
      - Sidebar izquierdo con combobox categorías, filtro, campo "nueva categoría",
        y botones redondeados para filtrar, agregar categoría, gestionar producto.
      - Tabla de productos (ttk.Treeview) con estilo personalizado.
      - Etiqueta con valorización total del inventario.
    """
    def __init__(self, parent, controller):
        super().__init__(parent)

        # Modo de apariencia y fondo principal
        ctk.set_appearance_mode("light")
        self.configure(width=800, height=600, fg_color="#9db7b1")
        self.controller = controller

        self.pack_propagate(False)
        self.pack(fill="both", expand=True)

        # Crear estilos para tabla y botones
        self.create_table_styles()

        # Crear widgets
        self.create_widgets()

    def create_table_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        # Estilo para el Treeview
        style.configure(
            "Inventory.Treeview.Heading",
            background="#2C7A7B",
            foreground="white",
            font=("Sans-serif", 14, "bold")
        )
        style.configure(
            "Inventory.Treeview",
            font=("Sans-serif", 12),
            rowheight=28,
            fieldbackground="#F5F5F5",
            background="#F5F5F5",
            foreground="black",
            bordercolor="#CCCCCC",
            borderwidth=1
        )
        style.map(
            "Inventory.Treeview",
            background=[("selected", "#A0E7E5")],
            foreground=[("selected", "black")]
        )

        # Estilo para botones redondeados
        style.configure(
            "RoundedButton.TButton",
            font=("Sans-serif", 14, "bold"),
            padding=6,
            borderwidth=0
        )
        style.map(
            "RoundedButton.TButton",
            background=[("!active", "#E0E0E0"), ("active", "#d0d0d0")],
            foreground=[("!active", "black"), ("active", "black")]
        )

    def create_widgets(self):
        # Fuentes
        font_header = ("Segoe UI", 20, "bold")
        font_button = ("Segoe UI", 14, "bold")
        font_label  = ("Segoe UI", 14, "bold")
        font_table  = ("Segoe UI", 12)

        # ------------------------
        # Cabecera
        # ------------------------
        header_frame = ctk.CTkFrame(self, fg_color="#10a2a7", corner_radius=0)
        header_frame.pack(side="top", fill="x", ipady=15)
        header_frame.configure(height=70)

        title_label = ctk.CTkLabel(
            header_frame,
            text="Control de Inventario",
            text_color="black",
            font=font_header
        )
        title_label.pack(side="left", padx=20)

        back_button = ctk.CTkButton(
            header_frame,
            text="Volver al Menú",
            fg_color="#b57426",
            hover_color="#c7853a",
            text_color="#113949",
            font=font_button,
            corner_radius=10,
            command=self.controller.event_back
        )
        back_button.pack(side="right", padx=20)

        # ------------------------
        # Cuerpo principal
        # ------------------------
        main_frame = ctk.CTkFrame(self, fg_color="#9db7b1", corner_radius=0)
        main_frame.pack(side="top", fill="both", expand=True, padx=10, pady=10)

        # Sidebar izquierdo
        sidebar_frame = ctk.CTkFrame(main_frame, fg_color="#9db7b1", corner_radius=0, width=200)
        sidebar_frame.pack(side="left", fill="y", padx=(0,10))
        sidebar_frame.pack_propagate(False)

        boton_style = {
            "font": ("Sans-serif", 16, "bold"),
            "corner_radius": 20,
            "height": 40
        }

        # Categoría
        ctk.CTkLabel(sidebar_frame, text="Categoría:", text_color="black", font=font_label).pack(anchor="w", pady=(10,5))
        self.category_combobox = ttk.Combobox(sidebar_frame, values=["Todas"], state="readonly", width=15)
        self.category_combobox.current(0)
        self.category_combobox.pack(pady=(0,10))

        # Botón Filtrar por Categoría (azul, redondeado)
        filter_button = ctk.CTkButton(
            sidebar_frame,
            text="Filtrar por Categoría",
            fg_color="#0000FF",
            hover_color="#3333CC",
            text_color="white",
            command=self.controller.event_filter,
            **boton_style
        )
        filter_button.pack(fill="x", pady=5)

        # Etiqueta y entrada de Nueva Categoría (justo debajo de Filtrar)
        ctk.CTkLabel(
            sidebar_frame,
            text="Nueva Categoría:",
            text_color="black",
            font=font_label
        ).pack(anchor="w", pady=(10,5))
        self.new_category_entry = ctk.CTkEntry(
            sidebar_frame,
            width=180,
            font=("Sans-serif", 12),
            corner_radius=8
        )
        self.new_category_entry.pack(fill="x", pady=(0,10))

        # Botón Agregar Categoría (verde, redondeado)
        add_cat_btn = ctk.CTkButton(
            sidebar_frame,
            text="Agregar Categoría",
            fg_color="#28A745",
            hover_color="#218838",
            text_color="white",
            command=self.controller.event_add_category,
            **boton_style
        )
        add_cat_btn.pack(fill="x", pady=5)

        # Botón Gestionar Producto (amarillo, redondeado)
        manage_btn = ctk.CTkButton(
            sidebar_frame,
            text="Gestionar Producto",
            fg_color="#FFD700",
            hover_color="#E6C200",
            text_color="black",
            command=self.controller.event_manage_products,
            **boton_style
        )
        manage_btn.pack(fill="x", pady=5)

        # Valorización
        ctk.CTkLabel(sidebar_frame, text="Valorización Inventario", text_color="black", font=font_label).pack(anchor="w", pady=(20,5))
        self.valuation_amount_label = ctk.CTkLabel(
            sidebar_frame,
            text="$0",
            text_color="black",
            font=("Sans-serif", 16, "bold"),
            justify="center"
        )
        self.valuation_amount_label.pack(pady=(0, 10), anchor="center", fill="x")


        # ------------------------
        # Área de contenido (tabla)
        # ------------------------
        content_frame = ctk.CTkFrame(main_frame, fg_color="#9db7b1", corner_radius=0)
        content_frame.pack(side="right", fill="both", expand=True)

        ctk.CTkLabel(
            content_frame,
            text="Productos en Inventario",
            text_color="black",
            font=("Sans-serif", 16, "bold")
        ).pack(anchor="w", pady=(10,5))

        table_frame = ctk.CTkFrame(content_frame, fg_color="white", corner_radius=8)
        table_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Treeview
        columns = ("code","name","stock","cost","price","category","description")
        self.inventory_tree = ttk.Treeview(table_frame, columns=columns, show="headings", style="Inventory.Treeview")
        for col, width, anchor, heading in [
            ("code", 100, "w", "Código"),
            ("name", 150, "w", "Nombre"),
            ("stock",  60, "center", "Stock"),
            ("cost",   80, "e", "Costo"),
            ("price",  80, "e", "Precio"),
            ("category",120,"w","Categoría"),
            ("description",200,"w","Descripción"),
        ]:
            self.inventory_tree.heading(col, text=heading)
            self.inventory_tree.column(col, width=width, anchor=anchor)

        self.inventory_tree.pack(side="left", fill="both", expand=True)

        # Scrollbar vertical
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.inventory_tree.yview)
        self.inventory_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # Mensaje cuando está vacía
        self.inventory_tree.insert("", "end", values=("", "Tabla sin contenido", "", "", "", "", ""))

    # --------------------------------------------------------------------------
    # Métodos que el controller puede usar para actualizar la vista
    # --------------------------------------------------------------------------
    def load_table(self, products):
        # Limpia rows
        for item in self.inventory_tree.get_children():
            self.inventory_tree.delete(item)
        # Inserta nuevos
        if not products:
            self.inventory_tree.insert("", "end", values=("", "Tabla sin contenido", "", "", "", "", ""))
        else:
            for p in products:
                self.inventory_tree.insert(
                    "", "end",
                    values=(
                        p.code, p.name, p.stock,
                        f"{p.cost:.2f}", f"{p.price:.2f}",
                        p.category, p.description
                    )
                )

    def set_inventory_value(self, value):
        """
        Actualiza la etiqueta con la valorización total del inventario,
        formateada con puntos de miles y coma decimal.
        """
        text = format_price(value)
        self.valuation_amount_label.configure(text=f"${text}")

    def set_categories(self, categories):
        if "Todas" not in categories:
            categories = ["Todas"] + categories
        self.category_combobox["values"] = categories
        self.category_combobox.current(0)

    def get_selected_category(self):
        return self.category_combobox.get()

    def get_new_category(self):
        return self.new_category_entry.get().strip()

    def clear_new_category(self):
        self.new_category_entry.delete(0, "end")
