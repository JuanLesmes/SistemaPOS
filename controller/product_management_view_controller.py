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

        # Cargar categorías en el combo
        cats = self.db.get_categories()  # Devuelve lista de nombres
        self.view.set_categories(cats)

    # --------------------------
    # Métodos (eventos) de la vista
    # --------------------------
    def event_go_back_to_inventory(self):
        self.main_controller.show_admin_view()

    def event_search_scan(self):
        code = self.view.get_code()
        if not code:
            messagebox.showwarning("Alerta", "Ingrese un código para escanear/buscar.")
            return
        
        product = self.db.get_product(code)
        if product:
            self.fill_form_with_product(product)
        else:
            messagebox.showinfo("Info", f"No se encontró el producto con código {code}.")

    def event_search_manual(self):
        code = self.view.get_code()
        if not code:
            messagebox.showwarning("Alerta", "Ingrese un código para buscar manualmente.")
            return

        product = self.db.get_product(code)
        if product:
            self.fill_form_with_product(product)
        else:
            messagebox.showinfo("Info", f"No se encontró el producto con código {code}.")

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
        cost_str = self.view.get_cost()
        price_str = self.view.get_price()
        category = self.view.get_category()
        desc = self.view.get_description()

        try:
            stock = int(stock_str) if stock_str else 0
            cost = float(cost_str) if cost_str else 0.0
            price = float(price_str) if price_str else 0.0
        except ValueError:
            messagebox.showerror("Error", "Stock, Costo y Precio deben ser numéricos.")
            return

        # Se realiza una única llamada para actualizar todos los campos del producto.
        self.db.update_product(name, cost, price, stock, category, desc, code)

        messagebox.showinfo("Éxito", f"Producto '{code}' modificado correctamente.")


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
            self.db.cursor.execute("DELETE FROM sold_products WHERE codeP = ?", (code,))
            self.db.conn.commit()
            # Ahora, eliminar el producto
            self.db.delete_product(code)
            messagebox.showinfo("Borrado", f"Producto {code} eliminado.")
            self.view.clear_fields()


    def event_delete_category(self):
        """
        Funcionalidad para eliminar la categoría seleccionada.
        Se obtiene la categoría del combobox y se elimina si no es "Todas".
        """
        selected_cat = self.view.get_selected_category()
        if selected_cat == "Todas" or not selected_cat:
            messagebox.showwarning("Advertencia", "Seleccione una categoría válida para eliminar.")
            return
        
        confirm = messagebox.askyesno("Confirmar eliminación", 
                                      f"¿Está seguro de eliminar la categoría '{selected_cat}'?")
        if confirm:
            # Se asume que existe el método delete_category en la BD
            result = self.db.delete_category(selected_cat)
            if result:
                messagebox.showinfo("Categoría eliminada", f"La categoría '{selected_cat}' ha sido eliminada.")
            else:
                messagebox.showerror("Error", f"No se pudo eliminar la categoría '{selected_cat}'.")
            # Actualizamos la lista de categorías en la vista
            updated_cats = self.db.get_categories()
            self.view.set_categories(updated_cats)

    # ----------------------------------------------
    # Métodos internos
    # ----------------------------------------------
    def fill_form_with_product(self, product):
        self.view.set_code(product.code)
        self.view.set_name(product.name)
        self.view.set_stock(str(product.stock))
        self.view.set_cost(str(product.cost))
        self.view.set_price(str(product.price))
        self.view.set_description(product.description)
        cats = self.db.get_categories()
        self.view.set_categories(cats)
        if product.category in cats:
            idx = cats.index(product.category)
            self.view.cmb_category.current(idx)
