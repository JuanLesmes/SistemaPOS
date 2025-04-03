# controller/sales_view_controller.py
import tkinter as tk
from tkinter import simpledialog, messagebox
from model.sold_product import SoldProduct
from model.receipt import Receipt
import datetime

class SalesViewController:
    def __init__(self, parent_frame, main_controller, db):
        self.parent_frame = parent_frame
        self.main_controller = main_controller
        self.db = db
        self.buffer_codigo = ""  # Buffer para el código de barras
        
        # 1° Crear la vista PRIMERO
        from view.sales_view import SalesView
        self.view = SalesView(self.parent_frame, self)  # ¡Ahora existe!
        
        # 2° Configurar bindings DESPUÉS de crear la vista
        self.view.focus_set()  # Forzar foco para capturar eventos
        self.view.bind("<KeyRelease>", self.handle_barcode_input)  # Captura global
        self.sold_products = []
        self.initialize()
        
        self.view.recibe_entry.bind("<FocusIn>", self._pause_barcode_reader)
        self.view.recibe_entry.bind("<FocusOut>", self._resume_barcode_reader)

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

    def _pause_barcode_reader(self, event):
        """Pausa la lectura de códigos de barras cuando el campo Recibe tiene foco"""
        self.view.unbind("<KeyRelease>")

    def _resume_barcode_reader(self, event):
        """Reanuda la lectura cuando el campo Recibe pierde el foco"""
        self.view.bind("<KeyRelease>", self.handle_barcode_input)
        self.view.focus_set()

    def handle_barcode_input(self, event):
        if self.view.recibe_entry.focus_get() == self.view.recibe_entry:
            return
        if event.keysym == "Return":
            code = self.buffer_codigo.strip()
            self.buffer_codigo = ""  # Reiniciar buffer
            
            if not code:
                return
                
            product = self.db.get_product(code)
            if product and product.stock > 0:
                self.add_product_to_sale(product, 1)
            else:
                messagebox.showwarning("Error", "Producto no encontrado o sin stock")
        else:
            # Asegurar que solo se capturan caracteres válidos (dígitos)
            if event.char.isdigit():
                self.buffer_codigo += event.char

    def add_product_to_sale(self, product, quantity=1):
        """
        Agrega el producto como un nuevo ítem INDEPENDIENTE en la lista,
        incluso si ya existe uno igual.
        """
        # Crear nuevo ítem siempre (sin verificar duplicados)
        new_sp = SoldProduct(0, product, quantity)
        self.sold_products.append(new_sp)
        self.refresh_sales_table()

    def event_remove_product(self):
        """Elimina EXACTAMENTE el ítem seleccionado en la tabla"""
        if not self.sold_products:
            messagebox.showwarning("Error", "No hay productos en la venta")
            return

        selected_item = self.view.tree.selection()
        
        if not selected_item:
            messagebox.showwarning("Error", "Seleccione un producto de la tabla")
            return

        # Obtener el índice del ítem seleccionado en el Treeview
        selected_index = self.view.tree.index(selected_item[0])
        
        # Eliminar por posición en la lista (no por código)
        if 0 <= selected_index < len(self.sold_products):
            del self.sold_products[selected_index]
            self.refresh_sales_table()
            messagebox.showinfo("Éxito", "Ítem eliminado")
        else:
            messagebox.showwarning("Error", "Ítem no encontrado")
            
    def event_cash_payment(self):
        try:
            # 1. Validar que haya productos en la venta
            total_sale = float(self.calculate_total())
            if total_sale <= 0.0:
                raise ValueError("No hay productos en la venta")

            # 2. Obtener y validar el monto recibido
            received_str = self.view.get_received_amount().strip()
            if not received_str:
                raise ValueError("Ingrese la cantidad recibida")
            
            received = float(received_str)
            if received < total_sale:
                raise ValueError(f"Monto insuficiente. Faltan ${total_sale - received:.2f}")

            # 3. Calcular vuelto y generar recibo
            change_due = received - total_sale
            self.generate_receipt("Efectivo", total_sale, change_due)
            
            # 4. Limpiar campos después de la venta
            self.view.clear_received_amount()


        except ValueError as e:
            messagebox.showerror("Error en Pago", str(e))
        except Exception as e:
            messagebox.showerror("Error Crítico", f"Ocurrió un error inesperado: {str(e)}")

    def event_card_payment(self):
        try:
            total_sale = float(self.calculate_total())
            if total_sale <= 0.0:
                raise ValueError("No hay productos en la venta")
                
            self.generate_receipt("Tarjeta", total_sale, 0.0)
            
        except ValueError as e:
            messagebox.showerror("Error en Pago", str(e))
        except Exception as e:
            messagebox.showerror("Error Crítico", f"Ocurrió un error inesperado: {str(e)}")

    def event_transfer_payment(self):
        try:
            total_sale = float(self.calculate_total())
            if total_sale <= 0.0:
                raise ValueError("No hay productos en la venta")
                
            self.generate_receipt("Transferencia", total_sale, 0.0)
            
        except ValueError as e:
            messagebox.showerror("Error en Pago", str(e))
        except Exception as e:
            messagebox.showerror("Error Crítico", f"Ocurrió un error inesperado: {str(e)}")

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

    def process_payment(self):
        """Procesa el pago y devuelve el foco al frame principal"""
        try:
            received_str = self.view.get_received_amount().strip()
            if not received_str:
                raise ValueError("Ingrese el monto recibido")
            
            total = float(self.calculate_total())
            received = float(received_str)
            
            if received < total:
                messagebox.showerror("Error", "Monto insuficiente")
                return
                
            # Procesar pago exitoso
            self.view.clear_received_amount()
            self.view.focus_set()  # Foco de vuelta al frame
            
        except ValueError as e:
            messagebox.showerror("Error", str(e))
