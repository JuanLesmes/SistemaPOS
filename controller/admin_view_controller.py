# controller/admin_view_controller.py

from tkinter import messagebox

class AdminViewController:
    def __init__(self, parent, main_controller, db):
        """
        parent: un Frame o contenedor en main_controller
        main_controller: para navegar a otras vistas
        db: instancia de DBConnection para acceder a la BD
        """
        self.parent = parent
        self.main_controller = main_controller
        self.db = db

        from view.admin_view import AdminView
        self.view = AdminView(self.parent, self)

        self.initialize()

    def initialize(self):
        # Al iniciar, mostramos todos los productos
        products = self.db.get_products()
        # Cargamos en la tabla
        self.view.load_table(products)
        # Calculamos y mostramos la valorización
        self.view.set_inventory_value(self.calculate_inventory_value(products))
        # Cargamos las categorías en el combo
        all_cats = self.db.get_categories()  # Lista de strings
        self.view.set_categories(all_cats)

    def calculate_inventory_value(self, products):
        """
        Suma de (price * stock) de todos los productos.
        """
        total = 0.0
        for p in products:
            total += p.price * p.stock
        return total

    # ------------------------
    # EVENTOS DE LA VISTA
    # ------------------------
    def event_back(self):
        """
        Vuelve al menú principal (o login_view).
        """
        self.main_controller.show_login_view()

    def event_filter(self):
        """
        Cuando se presiona "Filtrar por Categoría".
        """
        category = self.view.get_selected_category()
        if category == "Todas":
            # Mostrar todos
            products = self.db.get_products()
        else:
            # Filtrar
            products = self.db.get_products_by_category(category)
        self.view.load_table(products)
        # Recalcular valorización
        self.view.set_inventory_value(self.calculate_inventory_value(products))

    def event_add_category(self):
        """
        Cuando se presiona "Agregar Categoría" (botón verde).
        """
        new_cat = self.view.get_new_category()
        if new_cat == "":
            messagebox.showerror("Invalid Category", "No text entered! Please enter a category name.")
            return
        
        categories = self.db.get_categories()
        if new_cat in categories:
            messagebox.showwarning("Category Exists", f"This category already exists: {new_cat}")
        else:
            self.db.add_category(new_cat)
            messagebox.showinfo("Category Added", f"Category '{new_cat}' added successfully.")
            self.view.clear_new_category()
            # Actualizar combo
            updated_cats = self.db.get_categories()
            self.view.set_categories(updated_cats)

    def event_add_category(self):
        """
        Cuando se presiona "Agregar Categoría" (botón verde).
        """
        new_cat = self.view.get_new_category()
        if new_cat == "":
            messagebox.showerror("Invalid Category", "No text entered! Please enter a category name.")
            return
        
        categories = self.db.get_categories()
        if new_cat in categories:
            messagebox.showwarning("Category Exists", f"This category already exists: {new_cat}")
        else:
            self.db.add_category(new_cat)
            messagebox.showinfo("Category Added", f"Category '{new_cat}' added successfully.")
            self.view.clear_new_category()
            # Actualizar combo
            updated_cats = self.db.get_categories()
            self.view.set_categories(updated_cats)
        self.main_controller.product_mgmt_controller.view.set_categories(updated_cats)



    def event_manage_products(self):
        """
        Botón "Gestionar Producto".
        Navega a otra vista (aún por implementar) 
        o a product_management_view.
        """
        self.main_controller.show_product_management_view()
