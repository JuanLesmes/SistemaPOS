# view/admin_view.py

import tkinter as tk
from tkinter import ttk

class AdminView(tk.Frame):
    """
    Vista para el Control de Inventario.
    Tiene:
      - Cabecera con título y botón "Volver al Menú".
      - Sidebar izquierdo con combobox categorías, filtro, campo "nueva categoría", 
        y botones para filtrar, agregar categoría, gestionar producto.
      - Tabla de productos (Treeview).
      - Etiqueta con valorización total del inventario.
    """
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        # Ajustes principales de la ventana
        self.config(width=800, height=600)
        self.pack_propagate(False)
        self.pack(fill="both", expand=True)
        
        # Crear estilos para la tabla
        self.create_table_styles()
        
        # Crear la interfaz (widgets)
        self.create_widgets()

    def create_widgets(self):
        self.color_turquesa = "#00BFBF"
        self.color_naranja  = "#FFA500"
        self.color_gris     = "#F0F0F0"
        self.color_blanco   = "#FFFFFF"
        self.color_azul     = "#0000FF"
        self.color_verde    = "#28A745"
        self.color_amarillo = "#FFD700"
        self.color_borde    = "#D3D3D3"
        
        self.font_header  = ("Sans-serif", 20, "bold")
        self.font_button  = ("Sans-serif", 14, "bold")
        self.font_label   = ("Sans-serif", 14, "bold")
        self.font_table   = ("Sans-serif", 14)
        
        # ----------------------------------------------------------------
        # Cabecera
        # ----------------------------------------------------------------
        header_height = 60
        header_frame = tk.Frame(self, bg=self.color_turquesa, height=header_height)
        header_frame.pack(side="top", fill="x")
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(
            header_frame,
            text="Control de Inventario",
            bg=self.color_turquesa,
            fg="#FFFFFF",
            font=self.font_header
        )
        title_label.pack(side="left", padx=20)
        
        back_button = tk.Button(
            header_frame,
            text="Volver al Menú",
            bg=self.color_naranja,
            fg="#000000",
            font=self.font_button,
            bd=0,
            cursor="hand2",
            command=self.controller.event_back  # Llamamos al método en el controller
        )
        back_button.config(width=12, height=1)
        back_button.pack(side="right", padx=20, pady=10)
        
        # ----------------------------------------------------------------
        # Cuerpo Principal (sidebar + tabla)
        # ----------------------------------------------------------------
        main_frame = tk.Frame(self, bg=self.color_gris)
        main_frame.pack(side="top", fill="both", expand=True)
        
        # Sidebar
        sidebar_width = int(800 * 0.25)
        sidebar_frame = tk.Frame(main_frame, bg=self.color_gris, width=sidebar_width)
        sidebar_frame.pack(side="left", fill="y", padx=20, pady=20)
        sidebar_frame.pack_propagate(False)
        
        # Etiqueta "Categoría:"
        category_label = tk.Label(sidebar_frame, text="Categoría:", bg=self.color_gris, font=self.font_label)
        category_label.pack(anchor="w", pady=5)
        
        # Combobox para categorías
        self.category_combobox = ttk.Combobox(sidebar_frame, values=["Todas"], state="readonly")
        self.category_combobox.current(0)
        self.category_combobox.config(width=15)
        self.category_combobox.pack(pady=5)
        
        # Botón Filtrar por Categoría
        self.filter_button = tk.Button(
            sidebar_frame,
            text="Filtrar por Categoría",
            bg=self.color_azul,
            fg=self.color_blanco,
            font=self.font_button,
            bd=0,
            cursor="hand2",
            command=self.controller.event_filter  # Llamamos al método del controller
        )
        self.filter_button.config(width=18, height=2)
        self.filter_button.pack(pady=5)
        
        # Campo de búsqueda (para nueva categoría)
        # Se usará como "nuevo nombre de categoría"
        self.new_category_entry = tk.Entry(sidebar_frame, width=20, font=("Sans-serif", 12))
        self.new_category_entry.pack(pady=5)
        
        # Botón Agregar Categoría
        self.add_category_button = tk.Button(
            sidebar_frame,
            text="Agregar Categoría",
            bg=self.color_verde,
            fg=self.color_blanco,
            font=self.font_button,
            bd=0,
            cursor="hand2",
            command=self.controller.event_add_category  # controller
        )
        self.add_category_button.config(width=18, height=2)
        self.add_category_button.pack(pady=5)
        
        # Botón Gestionar Producto
        self.manage_product_button = tk.Button(
            sidebar_frame,
            text="Gestionar Producto",
            bg=self.color_amarillo,
            fg="#000000",
            font=self.font_button,
            bd=0,
            cursor="hand2",
            command=self.controller.event_manage_products
        )
        self.manage_product_button.config(width=18, height=2)
        self.manage_product_button.pack(pady=5)
        
        # Valorización Inventario
        valuation_label_title = tk.Label(
            sidebar_frame,
            text="Valorización Inventario",
            bg=self.color_gris,
            font=self.font_label
        )
        valuation_label_title.pack(pady=(20, 0))
        
        self.valuation_amount_label = tk.Label(
            sidebar_frame,
            text="$0",
            bg=self.color_gris,
            font=("Sans-serif", 16, "bold")
        )
        self.valuation_amount_label.pack(pady=5)
        
        # Contenido: Tabla
        content_frame = tk.Frame(main_frame, bg=self.color_blanco)
        content_frame.pack(side="right", fill="both", expand=True, padx=20, pady=20)
        
        products_label = tk.Label(
            content_frame,
            text="Productos en Inventario",
            bg=self.color_blanco,
            fg="#000000",
            font=("Sans-serif", 16, "bold"),
            anchor="w"
        )
        products_label.pack(fill="x", pady=5)
        
        table_frame = tk.Frame(content_frame, bg=self.color_blanco, bd=1, relief="solid")
        table_frame.pack(fill="both", expand=True)
        
        columns = ("code", "name", "stock", "cost", "price", "category", "description")
        self.inventory_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            style="Inventory.Treeview"
        )
        self.inventory_tree.heading("code", text="Código Producto")
        self.inventory_tree.heading("name", text="Nombre Producto")
        self.inventory_tree.heading("stock", text="Stock")
        self.inventory_tree.heading("cost", text="Costo")
        self.inventory_tree.heading("price", text="Precio")
        self.inventory_tree.heading("category", text="Categoría")
        self.inventory_tree.heading("description", text="Descripción")
        
        # Ajuste de columnas
        self.inventory_tree.column("code", width=100, anchor="w")
        self.inventory_tree.column("name", width=150, anchor="w")
        self.inventory_tree.column("stock", width=60, anchor="center")
        self.inventory_tree.column("cost", width=80, anchor="e")
        self.inventory_tree.column("price", width=80, anchor="e")
        self.inventory_tree.column("category", width=120, anchor="w")
        self.inventory_tree.column("description", width=200, anchor="w")
        
        self.inventory_tree.pack(side="left", fill="both", expand=True)
        
        # Scrollbar
        scrollbar_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.inventory_tree.yview)
        self.inventory_tree.configure(yscroll=scrollbar_y.set)
        scrollbar_y.pack(side="right", fill="y")
        
        # Mensaje por defecto si está vacía
        self.inventory_tree.insert("", "end", values=("", "Tabla sin contenido", "", "", "", "", ""))
    
    def create_table_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        
        style.configure(
            "Inventory.Treeview.Heading",
            background="#00BFBF",
            foreground="#FFFFFF",
            font=("Sans-serif", 14, "bold")
        )
        style.configure(
            "Inventory.Treeview",
            font=("Sans-serif", 12),
            rowheight=25,
            bordercolor="#D3D3D3",
            borderwidth=1
        )
        style.map("Inventory.Treeview", background=[("selected", "#00BFBF")])
    
    # --------------------------------------------------------------------------
    # Métodos que el controller puede usar para actualizar la vista
    # --------------------------------------------------------------------------
    def load_table(self, products):
        """
        Recibe una lista de objetos Product y los muestra en el Treeview.
        Cada Product tiene: code, name, cost, price, stock, category, description
        """
        # Limpiar tabla
        for item in self.inventory_tree.get_children():
            self.inventory_tree.delete(item)
        
        if not products:
            self.inventory_tree.insert("", "end", values=("", "Tabla sin contenido", "", "", "", "", ""))
        else:
            for p in products:
                # p es un objeto Product (según tu modelo)
                code = p.code
                name = p.name
                stock = p.stock
                cost = f"{p.cost:.2f}"
                price = f"{p.price:.2f}"
                category = p.category
                desc = p.description
                self.inventory_tree.insert("", "end", values=(code, name, stock, cost, price, category, desc))
    
    def set_inventory_value(self, value):
        """
        Actualiza la etiqueta con la valorización total del inventario.
        """
        self.valuation_amount_label.config(text=f"${value:.2f}")
    
    def set_categories(self, categories):
        """
        Actualiza la lista de categorías en el combobox. 
        categories es una lista de strings.
        """
        # Ponemos "Todas" (o "All") al inicio
        combo_values = ["Todas"] + categories
        self.category_combobox.config(values=combo_values)
        self.category_combobox.current(0)
    
    def get_selected_category(self):
        """
        Retorna la categoría seleccionada en el combobox.
        """
        return self.category_combobox.get()
    
    def get_new_category(self):
        """
        Retorna el texto escrito en la Entry para nueva categoría.
        """
        return self.new_category_entry.get().strip()
    
    def clear_new_category(self):
        """
        Limpia la Entry luego de agregar la categoría.
        """
        self.new_category_entry.delete(0, "end")
