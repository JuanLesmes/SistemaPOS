# controller/sales_view_controller.py
import tkinter as tk
from tkinter import simpledialog, messagebox
from model.sold_product import SoldProduct
from model.receipt import Receipt
import datetime

class SalesViewController:
    def __init__(self, parent_frame, main_controller, db):
        """
        parent_frame: el Frame en el que se dibujará toda la vista de ventas.
        main_controller: para navegar a otras vistas (show_login_view, etc.).
        db: instancia de DBConnection para acceder a la BD.
        """
        self.parent_frame = parent_frame
        self.main_controller = main_controller
        self.db = db
        
        # Importa la vista aquí para evitar import circular
        from view.sales_view import SalesView
        # Creamos la vista pasándole el frame y "self" (este controller)
        self.view = SalesView(self.parent_frame, self)

        # Lista interna de productos vendidos
        self.sold_products = []
        
        self.initialize()

    def initialize(self):
        """Reinicia la lista de venta y refresca la tabla y total."""
        self.sold_products = []
        self.view.load_table(self.sold_products)
        self.view.set_total("0.0")

    # ----------------------------------------------------------------
    # Métodos que la vista llama cuando se presionan los botones
    # ----------------------------------------------------------------
    def event_back(self):
        """Botón 'Volver al Menú'."""
        self.main_controller.show_login_view()

    def event_add_product(self):
        """Botón 'Agregar Producto' que toma los datos de los Entry de la vista."""
        # Obtiene los datos de los campos de la vista
        code = self.view.product_code_entry.get().strip()
        qty_str = self.view.product_qty_entry.get().strip()
        
        if code == "" or qty_str == "":
            messagebox.showwarning("Error", "Debes ingresar el código y la cantidad.")
            return

        product = self.db.get_product(code)
        if product is None:
            messagebox.showwarning("Error", "Producto no encontrado.")
            return

        try:
            qty = int(qty_str)
            if qty <= 0:
                messagebox.showwarning("Error", "La cantidad debe ser mayor a 0.")
                return
        except ValueError:
            messagebox.showerror("Error", "La cantidad debe ser un número entero.")
            return

        if qty > product.stock:
            messagebox.showwarning("Error", f"No hay suficiente stock. Disponible: {product.stock}")
            return

        # Verifica si el producto ya está en la lista de sold_products
        for sp in self.sold_products:
            if sp.get_code() == product.code:
                new_qty = sp.quantity + qty
                if new_qty > product.stock:
                    messagebox.showwarning("Error", f"No hay suficiente stock. Disponible: {product.stock}")
                    return
                sp.quantity = new_qty
                sp.calculate_total_partial()
                self.refresh_sales_table()
                # Limpia los campos de entrada
                self.view.product_code_entry.delete(0, tk.END)
                self.view.product_qty_entry.delete(0, tk.END)
                return

        # Si es un producto nuevo en la venta
        sp = SoldProduct(0, product, qty)
        self.sold_products.append(sp)
        self.refresh_sales_table()

        # Limpia los campos de entrada después de agregar
        self.view.product_code_entry.delete(0, tk.END)
        self.view.product_qty_entry.delete(0, tk.END)

    def event_remove_product(self):
        """Botón 'Eliminar Producto'."""
        code = simpledialog.askstring("Eliminar Producto", "Ingrese código del producto a eliminar:")
        if code is None or code.strip() == "":
            return

        removed = False
        for i, sp in enumerate(self.sold_products):
            if sp.get_code() == code.strip():
                self.sold_products.pop(i)
                removed = True
                break

        if removed:
            self.refresh_sales_table()
        else:
            messagebox.showwarning("Error", "Producto no se encuentra en la lista de venta.")

    def event_cash_payment(self):
        """Botón 'Pago con Efectivo'."""
        total_sale = float(self.calculate_total())
        if total_sale == 0.0:
            messagebox.showerror("Error", "No hay productos en la venta.")
            return
        
        val_str = self.view.get_received_amount().strip()
        if val_str == "":
            messagebox.showerror("Error", "Por favor ingrese la cantidad recibida.")
            return
        
        try:
            received = float(val_str)
            if received < total_sale:
                messagebox.showerror("Error", "El valor recibido no cubre el total de la venta.")
                return
            change_due = received - total_sale
            self.generate_receipt("Cash", total_sale, change_due)
        except ValueError:
            messagebox.showerror("Error", "Valor recibido inválido.")

    def event_card_payment(self):
        """Botón 'Pago con Tarjeta'."""
        total_sale = float(self.calculate_total())
        if total_sale == 0.0:
            messagebox.showerror("Error", "No hay productos en la venta.")
            return
        self.generate_receipt("Card", total_sale, 0.0)

    def event_transfer_payment(self):
        """Botón 'Transferencia'."""
        total_sale = float(self.calculate_total())
        if total_sale == 0.0:
            messagebox.showerror("Error", "No hay productos en la venta.")
            return
        self.generate_receipt("Transfer", total_sale, 0.0)

    # ----------------------------------------------------------------
    # Métodos de apoyo
    # ----------------------------------------------------------------
    def refresh_sales_table(self):
        self.view.load_table(self.sold_products)
        self.view.set_total(self.calculate_total())

    def calculate_total(self):
        total = 0.0
        for sp in self.sold_products:
            total += sp.total_partial
        return f"{total:.2f}"

    def generate_receipt(self, payment_method, total_sale, change_due):
        now = datetime.datetime.now()
        receipt = Receipt(
            date=now.date(),
            time=now.time(),
            payment_method=payment_method,
            total_sale=total_sale
        )
        receipt.sold_products = self.sold_products
        self.db.add_receipt(receipt)

        # Cuando la venta está lista, mostramos el Recibo
        self.main_controller.show_voucher_view(receipt, change_due)

        # Limpia la venta actual
        self.initialize()
