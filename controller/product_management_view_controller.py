import tkinter as tk
from tkinter import messagebox
from model.product import Product

class ProductManagementViewController:
    def __init__(self, parent, main_controller, db):
        """
        parent: un Frame contenedor (ej: self.frame_product_mgmt en main_controller)
        main_controller: para volver a otras vistas, etc.
        db: instancia de DBConnection
        """
        self.parent = parent
        self.main_controller = main_controller
        self.db = db

        from view.product_management_view import ProductManagementView
        self.view = ProductManagementView(self.parent, self)
        self.view.pack(fill="both", expand=True)

        # Cargar categorías en el combo
        cats = self.db.get_categories()  # Devuelve lista de nombres
        self.view.set_categories(cats)

    # --------------------------
    # Métodos (eventos) de la vista
    # --------------------------
    def event_go_back_to_inventory(self):
        self.main_controller.show_admin_view()

    def event_search_scan(self):
        search_term = self.view.get_search_term()
        
        if not search_term:
            messagebox.showwarning("Alerta", "Ingrese un criterio de búsqueda.")
            return
        
        # Normalizar el término para búsquedas parciales
        normalized_term = search_term.strip().lower()  # <--- Añade esta línea
        
        # 1. Búsqueda exacta por código (case-sensitive)
        exact_product = self.db.get_product(search_term)  # Usar el término original
        if exact_product:
            self.fill_form_with_product(exact_product)
            return
        
        # 2. Búsqueda ampliada con término normalizado
        matched_products = self.db.search_products(normalized_term)  # <--- Usar término normalizado
            
        if not matched_products:
            messagebox.showinfo("Info", f"No se encontraron resultados para: '{search_term}'.")
            self.view.clear_search()  # Limpiar búsqueda también aquí
            return
        
        # Manejo de múltiples resultados
        if len(matched_products) > 1:
            selection = self.show_selection_dialog(matched_products)
            if selection:
                self.fill_form_with_product(selection)
        else:
            self.fill_form_with_product(matched_products[0])
        
        self.view.clear_search()  # Limpiar campo de búsqueda al final
    def event_add_stock(self):
        code = self.view.get_code()
        if not code:
            messagebox.showwarning("Alerta", "Ingrese un código de producto para agregar stock.")
            return
        
        product = self.db.get_product(code)
        if not product:
            messagebox.showinfo("Info", f"No se encontró el producto con código {code}.")
            return

        stock_str = self.view.get_stock()
        try:
            add_qty = int(stock_str)
        except ValueError:
            messagebox.showerror("Error", "La cantidad de stock a agregar debe ser un número entero.")
            return
        
        if add_qty <= 0:
            messagebox.showerror("Error", "La cantidad a agregar debe ser mayor a 0.")
            return

        self.db.update_stock(code, add_qty)
        messagebox.showinfo("Stock Actualizado", f"Se agregaron {add_qty} unidades al producto {code}.")

        updated_product = self.db.get_product(code)
        if updated_product:
            self.fill_form_with_product(updated_product)

    def event_add_product(self):
        code = self.view.get_code()
        name = self.view.get_name()
        stock_str = self.view.get_stock()
        cost_str = self.view.get_cost()
        price_str = self.view.get_price()
        category = self.view.get_category()
        desc = self.view.get_description()

        if not code or not name:
            messagebox.showerror("Error", "Código y Nombre son obligatorios.")
            return

        try:
            stock = int(stock_str) if stock_str else 0
            cost = float(cost_str) if cost_str else 0.0
            price = float(price_str) if price_str else 0.0
        except ValueError:
            messagebox.showerror("Error", "Stock, Costo y Precio deben ser numéricos.")
            return

        existing = self.db.get_product(code)
        if existing:
            messagebox.showwarning("Error", f"Ya existe un producto con código {code}.")
            return

        new_prod = Product(
            code=code,
            name=name,
            cost=cost,
            price=price,
            stock=stock,
            category=category,
            description=desc
        )
        self.db.add_product(new_prod)
        messagebox.showinfo("Éxito", f"Producto '{name}' agregado correctamente.")
        self.view.clear_fields()

    def event_modify_product(self):
        code = self.view.get_code()
        if not code:
            messagebox.showerror("Error", "Ingrese el código del producto a modificar.")
            return

        product = self.db.get_product(code)
        if not product:
            messagebox.showinfo("Info", f"No se encontró el producto con código {code}.")
            return

        name = self.view.get_name()
        stock_str = self.view.get_stock()
        cost_str = self.view.get_cost()  # Ej: "1.000" → "1000" o "1.500,25" → "1500.25"
        price_str = self.view.get_price()
        category = self.view.get_category()
        desc = self.view.get_description()

        try:
            # Convertir a enteros/floats
            stock = int(stock_str) if stock_str.strip() != "" else 0
            cost = float(cost_str) if cost_str.strip() != "" else 0.0  # "1000" → 1000.0
            price = float(price_str) if price_str.strip() != "" else 0.0
        except ValueError as e:
            messagebox.showerror("Error", f"Dato inválido: {str(e)}")
            return
        except Exception as e:
            messagebox.showerror("Error", f"Error al convertir valores: {str(e)}")
            return

        # Validación adicional de números positivos
        if stock < 0 or cost < 0 or price < 0:
            messagebox.showerror("Error", "Stock, Costo y Precio deben ser mayores o iguales a 0.")
            return

        # Actualizar en la base de datos
        self.db.update_product(name, cost, price, stock, category, desc, code)
        messagebox.showinfo("Éxito", f"Producto '{code}' modificado correctamente.")
        self.view.clear_fields()
        self.view.clear_search()  # Limpiar búsqueda al final

    def show_selection_dialog(self, products):
        dialog = tk.Toplevel(self.parent)
        dialog.title("Seleccionar Producto")
        
        # Frame principal
        main_frame = tk.Frame(dialog, padx=20, pady=10)
        main_frame.pack(fill="both", expand=True)
        
        # ListBox con scroll
        scrollbar = tk.Scrollbar(main_frame)
        scrollbar.pack(side="right", fill="y")
        
        listbox = tk.Listbox(
            main_frame, 
            width=60, 
            height=8,
            yscrollcommand=scrollbar.set,
            font=("Sans-serif", 12)
        )
        
        # Llenar con los productos
        for p in products:
            listbox.insert("end", str(p))
        
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=listbox.yview)
        
        def on_double_click(event):
            on_select() 
        
        listbox.bind("<Double-Button-1>", on_double_click) 
        
        # Botón de selección
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        selected_product = None
        
        def on_select():
            nonlocal selected_product
            selection = listbox.curselection()
            if selection:
                selected_product = products[selection[0]]
                dialog.destroy()
        
        btn_accept = tk.Button(
            btn_frame,
            text="Seleccionar",
            command=on_select,
            bg="#4CAF50",
            fg="white",
            font=("Sans-serif", 12, "bold"),
            width=15)
        btn_accept.pack(side="left", padx=10)
        
        # Hacer el diálogo modal
        dialog.transient(self.parent)
        dialog.grab_set()
        self.parent.wait_window(dialog)
        
        return selected_product

    def event_delete_product(self):
        code = self.view.get_code()
        if not code:
            messagebox.showerror("Error", "Ingrese el código del producto a eliminar.")
            return

        product = self.db.get_product(code)
        if not product:
            messagebox.showinfo("Info", f"No se encontró el producto con código {code}.")
            return

        confirm = messagebox.askyesno(
            "Confirmar",
            f"¿Está seguro de eliminar el producto '{product.name}' (código {code})? Esto también eliminará sus referencias en las ventas."
        )
        if confirm:
            # Eliminar registros en sold_products asociados al producto
            self.db.cursor.execute("DELETE FROM sold_products WHERE codeP = %s", (code,))
            self.db.conn.commit()
            # Ahora, eliminar el producto
            self.db.delete_product(code)
            messagebox.showinfo("Borrado", f"Producto {code} eliminado.")
            self.view.clear_fields()


    def event_delete_category(self):
        selected_cat = self.view.get_selected_category()
        if selected_cat == "Todas" or not selected_cat:
            messagebox.showwarning("Advertencia", "Seleccione una categoría válida para eliminar.")
            return
        
        confirm = messagebox.askyesno(
            "Confirmar eliminación permanente",
            f"¿Está seguro de eliminar definitivamente la categoría '{selected_cat}'?\n\n"
            "¡Esta acción es irreversible!\n"
            "Todos los eventos asociados a esta categoría quedarán sin clasificación.")
        if confirm:
            if self.db.delete_category(selected_cat):
                messagebox.showinfo("Éxito", f"Categoría '{selected_cat}' eliminada.")
                # Actualizar todas las vistas
                self.main_controller.refresh_all_categories()  # <--- Aquí
            else:
                messagebox.showerror("Error", "No se pudo eliminar la categoría.")
                
    # ----------------------------------------------
    # Métodos internos
    # ----------------------------------------------
    def fill_form_with_product(self, product):
        self.view.clear_search()
        self.view.set_code(product.code)
        self.view.set_name(product.name)
        self.view.set_stock(str(product.stock))
        self.view.set_cost(product.cost)
        self.view.set_price(product.price)
        self.view.set_description(product.description)
        cats = self.db.get_categories()
        self.view.set_categories(cats)
        if product.category in cats:
            idx = cats.index(product.category)
            self.view.cmb_category.current(idx)
