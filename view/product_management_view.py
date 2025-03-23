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
        self.config(bg="#F0F0F0")
        self.pack(fill="both", expand=True)

        self.create_widgets()

    def create_widgets(self):
        # Paleta de colores
        turquesa   = "#00BFBF"
        gris_claro = "#F0F0F0"
        blanco     = "#FFFFFF"
        azul       = "#0000FF"
        verde      = "#28A745"
        amarillo   = "#FFD700"
        rojo       = "#FF0000"
        naranja    = "#FFA500"
        negro      = "#000000"

        # Fuentes
        font_header = ("Sans-serif", 20, "bold")
        font_label  = ("Sans-serif", 12, "bold")
        font_entry  = ("Sans-serif", 12)
        font_button = ("Sans-serif", 14, "bold")

        # ----------------------------------------------------------------
        # 1. Cabecera (fondo turquesa, título centrado)
        # ----------------------------------------------------------------
        header_frame = tk.Frame(self, bg=turquesa)
        header_frame.place(relx=0, rely=0, relwidth=1, relheight=0.15)

        lbl_title = tk.Label(
            header_frame,
            text="Gestión de Productos",
            bg=turquesa,
            fg=negro,
            font=font_header
        )
        # Lo centramos horizontal y vertical en el header
        lbl_title.place(relx=0.5, rely=0.5, anchor="center")

        # ----------------------------------------------------------------
        # 2. Zona principal (campos + botones de la derecha)
        #    Ocupa ~70% de la altura total, debajo del header
        # ----------------------------------------------------------------
        body_frame = tk.Frame(self, bg=gris_claro)
        body_frame.place(relx=0, rely=0.15, relwidth=1, relheight=0.7)

        # Fila 1: Código, Nombre
        lbl_code = tk.Label(body_frame, text="Código", bg=gris_claro, font=font_label)
        lbl_code.place(relx=0.02, rely=0.05)
        self.entry_code = tk.Entry(body_frame, font=font_entry, width=15)
        self.entry_code.place(relx=0.02, rely=0.12)

        lbl_name = tk.Label(body_frame, text="Nombre", bg=gris_claro, font=font_label)
        lbl_name.place(relx=0.25, rely=0.05)
        self.entry_name = tk.Entry(body_frame, font=font_entry, width=20)
        self.entry_name.place(relx=0.25, rely=0.12)

        # Fila 2: Stock, Costo, Precio
        lbl_stock = tk.Label(body_frame, text="Stock", bg=gris_claro, font=font_label)
        lbl_stock.place(relx=0.02, rely=0.25)
        self.entry_stock = tk.Entry(body_frame, font=font_entry, width=10)
        self.entry_stock.place(relx=0.02, rely=0.32)

        lbl_cost = tk.Label(body_frame, text="Costo", bg=gris_claro, font=font_label)
        lbl_cost.place(relx=0.25, rely=0.25)
        self.entry_cost = tk.Entry(body_frame, font=font_entry, width=10)
        self.entry_cost.place(relx=0.25, rely=0.32)

        lbl_price = tk.Label(body_frame, text="Precio", bg=gris_claro, font=font_label)
        lbl_price.place(relx=0.45, rely=0.25)
        self.entry_price = tk.Entry(body_frame, font=font_entry, width=10)
        self.entry_price.place(relx=0.45, rely=0.32)

        # Fila 3: Categoría, Descripción
        lbl_category = tk.Label(body_frame, text="Categoría", bg=gris_claro, font=font_label)
        lbl_category.place(relx=0.02, rely=0.45)
        self.cmb_category = ttk.Combobox(body_frame, values=[], state="readonly", width=15)
        self.cmb_category.place(relx=0.02, rely=0.52)

        # Nuevo botón para borrar categoría (se ubica debajo del combobox)
        self.delete_category_button = tk.Button(
            body_frame,
            text="Eliminar Categoría",
            bg=rojo,
            fg=blanco,
            font=font_button,
            command=self.controller.event_delete_category  # Llama al método en el controller
        )
        # Ajustamos la posición; por ejemplo, a relx=0.02, rely=0.60
        self.delete_category_button.place(relx=0.02, rely=0.60)

        lbl_desc = tk.Label(body_frame, text="Descripción", bg=gris_claro, font=font_label)
        lbl_desc.place(relx=0.25, rely=0.45)
        self.entry_description = tk.Entry(body_frame, font=font_entry, width=40)
        self.entry_description.place(relx=0.25, rely=0.52)

        # Botones de la derecha (buscar, stock)
        # ~20% ancho -> relx=0.75 (approx)
        btn_search_scan = tk.Button(
            body_frame,
            text="Buscar Por Scan",
            bg=azul, fg=blanco,
            font=font_button,
            command=self.controller.event_search_scan
        )
        btn_search_scan.place(relx=0.75, rely=0.05, relwidth=0.2, relheight=0.1)

        btn_search_manual = tk.Button(
            body_frame,
            text="Buscar Manual",
            bg=azul, fg=blanco,
            font=font_button,
            command=self.controller.event_search_manual
        )
        btn_search_manual.place(relx=0.75, rely=0.17, relwidth=0.2, relheight=0.1)

        btn_add_stock = tk.Button(
            body_frame,
            text="Agregar Stock",
            bg=verde, fg=blanco,
            font=font_button,
            command=self.controller.event_add_stock
        )
        btn_add_stock.place(relx=0.75, rely=0.29, relwidth=0.2, relheight=0.1)

        # Botones de Agregar/Modificar/Eliminar
        btn_add_product = tk.Button(
            body_frame,
            text="Agregar Producto",
            bg=verde, fg=blanco,
            font=font_button,
            command=self.controller.event_add_product
        )
        btn_add_product.place(relx=0.15, rely=0.7, relwidth=0.18, relheight=0.1)

        btn_modify_product = tk.Button(
            body_frame,
            text="Modificar Producto",
            bg=amarillo, fg=negro,
            font=font_button,
            command=self.controller.event_modify_product
        )
        btn_modify_product.place(relx=0.38, rely=0.7, relwidth=0.18, relheight=0.1)

        btn_delete_product = tk.Button(
            body_frame,
            text="Eliminar Producto",
            bg=rojo, fg=blanco,
            font=font_button,
            command=self.controller.event_delete_product
        )
        btn_delete_product.place(relx=0.61, rely=0.7, relwidth=0.18, relheight=0.1)

        # ----------------------------------------------------------------
        # 3. Botón "Volver a gestión de Inventario" (parte inferior)
        # ----------------------------------------------------------------
        bottom_frame = tk.Frame(self, bg=gris_claro)
        bottom_frame.place(relx=0, rely=0.85, relwidth=1, relheight=0.15)

        btn_back_inventory = tk.Button(
            bottom_frame,
            text="Volver a gestión de Inventario",
            bg=naranja, fg=negro,
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
        return self.entry_cost.get().strip()

    def set_cost(self, value):
        self.entry_cost.delete(0, "end")
        self.entry_cost.insert(0, value)

    def get_price(self):
        return self.entry_price.get().strip()

    def set_price(self, value):
        self.entry_price.delete(0, "end")
        self.entry_price.insert(0, value)

    def get_category(self):
        return self.cmb_category.get().strip()

    def set_categories(self, categories):
        self.cmb_category.config(values=categories)
        if categories:
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
        if self.cmb_category.cget("values"):
            self.cmb_category.current(0)

    # Métodos para manejar la categoría en el combobox
    def get_selected_category(self):
        return self.cmb_category.get().strip()

    def clear_new_category(self):
        self.new_category_entry.delete(0, "end")

    def get_new_category(self):
        return self.new_category_entry.get().strip()
