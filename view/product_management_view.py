import tkinter as tk
from tkinter import ttk
from utils.formatters import format_price  # Si se usa para formatear precios en otros lugares

class ProductManagementView(tk.Frame):
    """
    Vista de Gestión de Productos, usando 'place' con coordenadas relativas
    para reproducir el diseño horizontal de la imagen,
    pero ocupando toda la pantalla de manera escalada.
    """
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        # Configuración de color y tamaño base
        fondo = "#9db7b1"          # Fondo general
        self.config(bg=fondo)
        self.pack(fill="both", expand=True)

        self.create_widgets()

    def create_widgets(self):
        # Paleta de colores actualizada
        header_color = "#10a2a7"    # Color de la cabecera
        fondo = "#9db7b1"           # Fondo general
        boton_principal = "#b57426"  # Botón "Volver a gestión de Inventario"
        azul       = "#0000FF"
        verde      = "#28A745"
        amarillo   = "#FFD700"
        rojo       = "#FF0000"
        negro      = "#000000"
        
        # Fuentes
        font_header = ("Sans-serif", 20, "bold")
        font_label  = ("Sans-serif", 12, "bold")
        font_entry  = ("Sans-serif", 12)
        font_button = ("Sans-serif", 14, "bold")

        # ----------------------------------------------------------------
        # 1. Cabecera (fondo header_color, título centrado)
        # ----------------------------------------------------------------
        header_frame = tk.Frame(self, bg=header_color)
        header_frame.place(relx=0, rely=0, relwidth=1, relheight=0.15)

        lbl_title = tk.Label(
            header_frame,
            text="Gestión de Productos",
            bg=header_color,
            fg=negro,
            font=font_header
        )
        lbl_title.place(relx=0.5, rely=0.5, anchor="center")

        # ----------------------------------------------------------------
        # 2. Zona principal (campos de ingreso a la izquierda)
        #    y botones en un frame vertical a la derecha.
        # ----------------------------------------------------------------
        body_frame = tk.Frame(self, bg=fondo)
        body_frame.place(relx=0, rely=0.15, relwidth=1, relheight=0.7)

        # Fila 1: Código y Nombre
        
        lbl_code = tk.Label(body_frame, text="Código", bg=fondo, font=font_label)
        lbl_code.place(relx=0.02, rely=0.05)
        self.entry_code = tk.Entry(body_frame, font=font_entry, width=25)  # Aumentado
        self.entry_code.place(relx=0.02, rely=0.12)

        lbl_name = tk.Label(body_frame, text="Nombre", bg=fondo, font=font_label)
        lbl_name.place(relx=0.25, rely=0.05)
        self.entry_name = tk.Entry(body_frame, font=font_entry, width=30)  # Aumentado
        self.entry_name.place(relx=0.25, rely=0.12)

        # Fila 2: Categoría y Descripción
        lbl_category = tk.Label(body_frame, text="Categoría", bg=fondo, font=font_label)
        lbl_category.place(relx=0.02, rely=0.25)
        self.cmb_category = ttk.Combobox(body_frame, values=[], state="readonly", width=20)  # Aumentado
        self.cmb_category.place(relx=0.02, rely=0.32)
        
        self.delete_category_button = tk.Button(
            body_frame,
            text="Eliminar Categoría",
            bg=rojo,
            fg="white",
            font=font_button,
            command=self.controller.event_delete_category
        )
        self.delete_category_button.place(relx=0.02, rely=0.40)
        
        lbl_desc = tk.Label(body_frame, text="Descripción", bg=fondo, font=font_label)
        lbl_desc.place(relx=0.25, rely=0.25)
        self.entry_description = tk.Entry(body_frame, font=font_entry, width=50)  # Aumentado
        self.entry_description.place(relx=0.25, rely=0.32)

        # Fila 3: Stock, Costo y Precio
        lbl_stock = tk.Label(body_frame, text="Stock", bg=fondo, font=font_label)
        lbl_stock.place(relx=0.02, rely=0.55)
        self.entry_stock = tk.Entry(body_frame, font=font_entry, width=15)  # Aumentado
        self.entry_stock.place(relx=0.02, rely=0.62)

        lbl_cost = tk.Label(body_frame, text="Costo", bg=fondo, font=font_label)
        lbl_cost.place(relx=0.25, rely=0.55)
        self.entry_cost = tk.Entry(body_frame, font=font_entry, width=15)  # Aumentado
        self.entry_cost.place(relx=0.25, rely=0.62)

        lbl_price = tk.Label(body_frame, text="Precio", bg=fondo, font=font_label)
        lbl_price.place(relx=0.45, rely=0.55)
        self.entry_price = tk.Entry(body_frame, font=font_entry, width=15)  # Aumentado
        self.entry_price.place(relx=0.45, rely=0.62)

        # --- Botones en el lado derecho, en un frame vertical ---
        button_frame = tk.Frame(body_frame, bg=fondo)
        button_frame.place(relx=0.75, rely=0.1, relwidth=0.2, relheight=0.8)

        # --- campo de búsqueda ---
        lbl_search = tk.Label(
            button_frame,
            text="Buscar (Código/Nombre):",
            bg=fondo,
            font=("Sans-serif", 10, "bold")
        )
        lbl_search.pack(pady=(0, 5), fill="x")

        self.entry_search = tk.Entry(
            button_frame,
            font=font_entry,
            width=20
        )
        self.entry_search.pack(pady=(0, 15), fill="x")

        # --- Botones debajo del campo de búsqueda ---
        btn_search = tk.Button(
            button_frame,
            text="Buscar",
            bg=azul, fg="white",
            font=font_button,
            command=self.controller.event_search_scan
        )
        btn_search.pack(fill="x", pady=10)

        # Botón "Agregar Producto"
        btn_add_product = tk.Button(
            button_frame,
            text="Agregar Producto",
            bg=verde,
            fg="white",
            font=font_button,
            command=self.controller.event_add_product
        )
        btn_add_product.pack(fill="x", pady=10)

        # Botón "Modificar Producto"
        btn_modify_product = tk.Button(
            button_frame,
            text="Modificar Producto",
            bg=amarillo, fg=negro,
            font=font_button,
            command=self.controller.event_modify_product
        )
        btn_modify_product.pack(fill="x", pady=10)

        # Botón "Eliminar Producto"
        btn_delete_product = tk.Button(
            button_frame,
            text="Eliminar Producto",
            bg=rojo, fg="white",
            font=font_button,
            command=self.controller.event_delete_product
        )
        btn_delete_product.pack(fill="x", pady=10)

        # ----------------------------------------------------------------
        # 3. Botón "Volver a gestión de Inventario" (parte inferior)
        # ----------------------------------------------------------------
        bottom_frame = tk.Frame(self, bg=fondo)
        bottom_frame.place(relx=0, rely=0.85, relwidth=1, relheight=0.15)

        btn_back_inventory = tk.Button(
            bottom_frame,
            text="Volver a gestión de Inventario",
            bg=boton_principal, fg=negro,
            font=("Sans-serif", 16, "bold"),
            command=self.controller.event_go_back_to_inventory
        )
        btn_back_inventory.place(relx=0.35, rely=0.2, relwidth=0.3, relheight=0.6)

    # ------------------------------------------------------
    # Métodos getters/setters
    # ------------------------------------------------------
    def get_code(self):
        return self.entry_code.get().strip()

    def set_code(self, value):
        self.entry_code.delete(0, "end")
        self.entry_code.insert(0, value)

    def get_name(self):
        return self.entry_name.get().strip()

    def set_name(self, value):
        self.entry_name.delete(0, "end")
        self.entry_name.insert(0, value)

    def get_stock(self):
        return self.entry_stock.get().strip()

    def set_stock(self, value):
        self.entry_stock.delete(0, "end")
        self.entry_stock.insert(0, value)

    def get_cost(self):
        cost_str = self.entry_cost.get().strip()
        cost_str = cost_str.replace(".", "").replace(",", ".")
        return cost_str

    def set_cost(self, value):
        formatted_cost = format_price(value, decimals=2)
        self.entry_cost.delete(0, "end")
        self.entry_cost.insert(0, formatted_cost)

    def get_price(self):
        price_str = self.entry_price.get().strip()
        price_str = price_str.replace(".", "").replace(",", ".")
        return price_str

    def set_price(self, value):
        formatted_price = format_price(value, decimals=2)
        self.entry_price.delete(0, "end")
        self.entry_price.insert(0, formatted_price)

    def get_category(self):
        return self.cmb_category.get().strip()

    def set_categories(self, categories):
        """
        Actualiza la lista de categorías en el combobox.
        """
        sorted_categories = sorted(categories, key=lambda x: x.lower())
        self.cmb_category.config(values=sorted_categories)
        if sorted_categories:
            self.cmb_category.current(0)

    def get_description(self):
        return self.entry_description.get().strip()

    def set_description(self, value):
        self.entry_description.delete(0, "end")
        self.entry_description.insert(0, value)

    def clear_fields(self):
        self.set_code("")
        self.set_name("")
        self.set_stock("")
        self.set_cost("")
        self.set_price("")
        self.set_description("")
        self.clear_search()
        if self.cmb_category.cget("values"):
            self.cmb_category.current(0)

    def get_search_term(self):
        return self.entry_search.get().strip()

    def clear_search(self):
        self.entry_search.delete(0, "end")

    # Métodos para manejar la categoría en el combobox
    def get_selected_category(self):
        return self.cmb_category.get().strip()

    def clear_new_category(self):
        self.new_category_entry.delete(0, "end")

    def get_new_category(self):
        return self.new_category_entry.get().strip()
