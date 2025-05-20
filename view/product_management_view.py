import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from utils.formatters import format_price  # Si se usa para formatear precios en otros lugares

ctk.set_appearance_mode("light")   # light / dark
ctk.set_default_color_theme("blue")  # blue / dark-blue / green

class ProductManagementView(tk.Frame):
    """
    Vista de Gestión de Productos, usando 'place' con coordenadas relativas
    para reproducir el diseño horizontal de la imagen,
    pero ocupando toda la pantalla de manera escalada.
    """
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
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
        font_header = ("Segoe UI", 20, "bold")
        font_label  = ("Segoe UI", 15, "bold")
        font_entry  = ("Segoe UI", 15)
        font_button = ("Segoe UI", 15, "bold")

        # Cabecera
        header_frame = ctk.CTkFrame(self, fg_color=header_color, corner_radius=0)
        header_frame.place(relx=0, rely=0, relwidth=1, relheight=0.15)
        ctk.CTkLabel(header_frame, text="Gestión de Productos", fg_color=header_color, text_color="black", font=font_header).pack(expand=True)

        # Zona principal
        body_frame = ctk.CTkFrame(self, fg_color="#9db7b1", corner_radius=0)
        body_frame.place(relx=0, rely=0.15, relwidth=1, relheight=0.7)

        # Usamos grid en body_frame
        # Configuramos columnas para que las etiquetas estén alineadas y las entradas también
        for col in range(4):
            body_frame.grid_columnconfigure(col, weight=1, uniform="col")

       # Cabecera
        header_frame = ctk.CTkFrame(self, fg_color=header_color, corner_radius=0)
        header_frame.place(relx=0, rely=0, relwidth=1, relheight=0.15)
        ctk.CTkLabel(
            header_frame,
            text="Gestión de Productos",
            fg_color=header_color,
            text_color="black",
            font=font_header
        ).place(relx=0.5, rely=0.5, anchor="center")

        # Zona principal
        body_frame = ctk.CTkFrame(self, fg_color="#9db7b1", corner_radius=0)
        body_frame.place(relx=0, rely=0.15, relwidth=1, relheight=0.7)

        row_gap = 0.17
        offset_label = 0.05
        offset_entry = 0.10

        # Fila 0 - Código y Nombre
        row = 0
        ctk.CTkLabel(body_frame, text="Código", text_color="black", font=font_label).place(relx=0.02, rely=row * row_gap + offset_label)
        self.entry_code = ctk.CTkEntry(body_frame, width=200, height=30, corner_radius=15, font=font_entry)
        self.entry_code.place(relx=0.02, rely=row * row_gap + offset_entry)

        ctk.CTkLabel(body_frame, text="Nombre", text_color="black", font=font_label).place(relx=0.17, rely=row * row_gap + offset_label)
        self.entry_name = ctk.CTkEntry(body_frame, width=250, height=30, corner_radius=15, font=font_entry)
        self.entry_name.place(relx=0.17, rely=row * row_gap + offset_entry)

        # Fila 1 - Descripción
        row = 1
        ctk.CTkLabel(body_frame, text="Descripción", text_color="black", font=font_label).place(relx=0.02, rely=row * row_gap + offset_label)
        self.entry_description = ctk.CTkTextbox(body_frame, width=500, height=50, corner_radius=15, font=font_entry)
        self.entry_description.place(relx=0.02, rely=row * row_gap + offset_entry)

        # Fila 2 - Categoría y Stock
        row = 2
        ctk.CTkLabel(body_frame, text="Categoría", text_color="black", font=font_label).place(relx=0.02, rely=row * row_gap + offset_label)
        self.cmb_category = ttk.Combobox(body_frame, values=[], state="readonly", width=20)
        self.cmb_category.place(relx=0.02, rely=row * row_gap + offset_entry)

        # Botón justo debajo del combobox (agregamos +0.07 de separación vertical)
        ctk.CTkButton(
            body_frame, text="Eliminar Categoría", corner_radius=15,
            fg_color="#FF0000", font=font_button,
            command=self.controller.event_delete_category
        ).place(relx=0.02, rely=row * row_gap + offset_entry + 0.07)

        ctk.CTkLabel(body_frame, text="Stock", text_color="black", font=font_label).place(relx=0.22, rely=row * row_gap + offset_label)
        self.entry_stock = ctk.CTkEntry(body_frame, width=150, height=30, corner_radius=15, font=font_entry)
        self.entry_stock.place(relx=0.22, rely=row * row_gap + offset_entry)

        # Fila 3 - Costo, Ganancia %, Precio
        row = 3
        ctk.CTkLabel(body_frame, text="Costo", text_color="black", font=font_label).place(relx=0.02, rely=row * row_gap + offset_label)
        self.entry_cost = ctk.CTkEntry(body_frame, width=150, height=30, corner_radius=15, font=font_entry)
        self.entry_cost.place(relx=0.02, rely=row * row_gap + offset_entry)
        self.entry_cost.bind("<FocusOut>", lambda e: self._on_gain_selected())

        ctk.CTkLabel(body_frame, text="Ganancia %", text_color="black", font=font_label).place(relx=0.14, rely=row * row_gap + offset_label)
        self.cmb_gain = ttk.Combobox(body_frame, values=["10", "20", "30", "40", "50", "100", "200"], state="readonly", width=10)
        self.cmb_gain.current(0)
        self.cmb_gain.place(relx=0.14, rely=row * row_gap + offset_entry)
        self.cmb_gain.bind("<<ComboboxSelected>>", lambda e: self._on_gain_selected())

        ctk.CTkLabel(body_frame, text="Precio", text_color="black", font=font_label).place(relx=0.22, rely=row * row_gap + offset_label)
        self.entry_price = ctk.CTkEntry(body_frame, width=150, height=30, corner_radius=15, font=font_entry, state="readonly")
        self.entry_price.place(relx=0.22, rely=row * row_gap + offset_entry)



        # Botones y búsqueda
        btn_frame = ctk.CTkFrame(body_frame, fg_color="#9db7b1", corner_radius=0)
        btn_frame.place(relx=0.5, rely=0.05, relwidth=0.25, relheight=0.9, anchor="n")

        ctk.CTkLabel(
            btn_frame, text="Ingrese Nombre o código del producto:",
            font=font_label, text_color="black"
        ).pack(pady=(10,5))

        self.entry_search = ctk.CTkEntry(
            btn_frame, width=200, height=30,
            corner_radius=15, font=font_entry
        )
        self.entry_search.pack(pady=(10,5))
        ctk.CTkButton(
            btn_frame, text="Buscar", text_color="black", corner_radius=15,
            fg_color="#0000FF", font=font_button,
            command=self.controller.event_search_scan,
            height=40
        ).pack(fill="x", pady=5)
        ctk.CTkButton(
            btn_frame, text="Agregar Producto", text_color="black", corner_radius=15,
            fg_color="#28A745", font=font_button,
            command=self.controller.event_add_product,
            height=40
        ).pack(fill="x", pady=5)
        ctk.CTkButton(
            btn_frame, text="Modificar Producto", text_color="black", corner_radius=15,
            fg_color="#FFD700", font=font_button,
            command=self.controller.event_modify_product,
            height=40
        ).pack(fill="x", pady=5)
        ctk.CTkButton(
            btn_frame, text="Eliminar Producto", text_color="black", corner_radius=15,
            fg_color="#FF0000", font=font_button,
            command=self.controller.event_delete_product,
            height=40
        ).pack(fill="x", pady=5)

        # Contenedor visual para resultados de búsqueda (por ahora solo estético)
        results_frame = ctk.CTkFrame(body_frame, fg_color="#ffffff", corner_radius=10, border_width=2, border_color="#cccccc")
        results_frame.place(relx=0.65, rely=0.05, relwidth=0.33, relheight=0.9)


        ctk.CTkLabel(
            results_frame,
            text="Resultados de Búsqueda",
            font=font_label,
            text_color="black"
        ).pack(pady=(10, 5))

        # Placeholder visual simulado
        for i in range(5):  # Simulamos 5 resultados como ejemplo
            ctk.CTkLabel(
                results_frame,
                text=f"Producto {i+1}",
                font=font_entry,
                text_color="#333333",
                anchor="w"
            ).pack(fill="x", padx=10, pady=2)


        # Botón volver
        ctk.CTkButton(
            self, text="Volver a gestión de Inventario", text_color="black", corner_radius=15,
            fg_color=boton_principal, font=font_button,
            command=self.controller.event_go_back_to_inventory
        ).place(relx=0.35, rely=0.85, relwidth=0.3, relheight=0.1)

        # Cálculo inicial
        self._on_gain_selected()

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
        self.entry_price.configure(state="normal")
        self.entry_price.delete(0, "end")
        self.entry_price.insert(0, formatted_price)
        self.entry_price.configure(state="readonly")

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

    def _on_gain_selected(self):
        # Leer costo actual
        cost_str = self.entry_cost.get().strip().replace(".", "").replace(",", ".")
        try:
            cost = float(cost_str) if cost_str else 0.0
        except ValueError:
            return

        # Leer % de ganancia
        gain_pct = float(self.cmb_gain.get())

        # Precio = costo * (1 + ganancia/100)
        price = cost * (1 + gain_pct / 100)

        # Mostrarlo con formato
        self.set_price(price)
