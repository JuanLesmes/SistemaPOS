# controller/sales_view_controller.py
import tkinter as tk
from tkinter import simpledialog, messagebox
from model.sold_product import SoldProduct
from model.receipt import Receipt
import datetime
import logging

from utils.printer_manager import XPrinterManager

class SalesViewController:
    def __init__(self, parent_frame, main_controller, db):
        self.parent_frame = parent_frame
        self.main_controller = main_controller
        self.db = db
        self.buffer_codigo = ""

        # 1° Creación de la vista
        from view.sales_view import SalesView
        self.view = SalesView(self.parent_frame, self)
        
        # 2° Vinculación de eventos a self.view
        self.view.bind("<KeyRelease>", self.handle_barcode_input)
        
        # Configuración del logger
        global logger
        logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)
        self.buffer_codigo = ""  
        
        # 3° Inicialización de la vista
        self.view.focus_set()  
        self.sold_products = []
        self.initialize()
        
        self.view.recibe_entry.bind("<FocusIn>", self._pause_barcode_reader)
        self.view.recibe_entry.bind("<FocusOut>", self._resume_barcode_reader)

        self.barcode_reader_active = True
        self.view.after(100, self.force_focus_restore)

        root = self.view.winfo_toplevel()


    def initialize(self):
        self.sold_products.clear()  # Vacía la lista existente
        self.view.load_table(self.sold_products)
        self.view.set_total(0.0)

    # ----------------------------------------------------------------
    # Métodos que la vista llama cuando se presionan los botones
    # ----------------------------------------------------------------
    def event_back(self):
        """Botón 'Volver al Menú'."""
        self.main_controller.show_login_view()
        self.view.master.after(100, self.activate_barcode_reader)

    def activate_barcode_reader(self):
        self.buffer_codigo = ""
        root = self.view.winfo_toplevel()
        root.bind_all("<KeyRelease>", self.handle_barcode_input)
        self.view.focus_force()

    def _pause_barcode_reader(self, event=None):
        """Pausa la lectura de códigos de barras"""
        self.barcode_reader_active = False
        root = self.view.winfo_toplevel()
        root.unbind_all("<KeyRelease>")
        logger.info("Lector PAUSADO")

    def _resume_barcode_reader(self, event=None):
        self.barcode_reader_active = True
        self.buffer_codigo = ""  # Limpiar buffer al reactivar
        root = self.view.winfo_toplevel()
        root.bind_all("<KeyRelease>", self.handle_barcode_input)
        self.view.focus_set()
        logger.info("Lector REANUDADO")

    def handle_barcode_input(self, event):
        """Maneja entrada de código de barras SOLO cuando es apropiado"""
        # Solo procesar si el lector está activo
        if not self.barcode_reader_active:
            return
            
        # Solo procesar dígitos y Enter
        if event.keysym == "Return":
            # Procesar código completo
            code = self.buffer_codigo.strip()
            self.buffer_codigo = ""
            
            if not code:
                return
                
            product = self.db.get_product(code)
            if product and product.stock > 0:
                self.add_product_to_sale(product, 1)
            else:
                messagebox.showwarning("Error", "Producto no encontrado o sin stock")
        elif event.char and event.char.isdigit():
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

            self.force_focus_restore()

    def force_focus_restore(self):
        self.view.focus_set()
        self.view.bind("<KeyRelease>", self.handle_barcode_input)
        logger.info("Foco restaurado")


    def event_cash_payment(self):
        try:
            # 1. Validar que haya productos en la venta
            total = float(self.calculate_total())
            if total <= 0.0:
                raise ValueError("No hay productos en la venta")

            # 2. Obtener y validar el monto recibido
            received_str = self.view.get_received_amount().strip()
            if not received_str:
                raise ValueError("Ingrese la cantidad recibida")
            
            received = float(received_str)
            if received < total:
                raise ValueError(f"Monto insuficiente. Faltan ${total - received:.2f}")

            # 3. Calcular vuelto y generar recibo
            change_due = received - total
            self.generate_receipt("Efectivo", total, change_due, received)
            
            # 4. Limpiar campos después de la venta
            self.view.clear_received_amount()
            self.force_focus_restore()


        except ValueError as e:
            messagebox.showerror("Error en Pago", str(e))
        except Exception as e:
            messagebox.showerror("Error Crítico", f"Ocurrió un error inesperado: {str(e)}")

    def event_card_payment(self):
        try:
            total = float(self.calculate_total())
            if total <= 0.0:
                raise ValueError("No hay productos en la venta")
                
            self.generate_receipt("Tarjeta", total, 0.0, total)
            self.force_focus_restore()
            
        except ValueError as e:
            messagebox.showerror("Error en Pago", str(e))
        except Exception as e:
            messagebox.showerror("Error Crítico", f"Ocurrió un error inesperado: {str(e)}")

    def event_transfer_payment(self):
        try:
            total = float(self.calculate_total())
            if total <= 0.0:
                raise ValueError("No hay productos en la venta")
                
            self.generate_receipt("Transferencia", total, 0.0)
            self.force_focus_restore()
            
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
    
    def generate_receipt(self, payment_method, total, change_due, received=None):
        now = datetime.datetime.now()
        receipt = Receipt(
        date=now.date(),
        time=now.time(),
        payment_method=payment_method,
        total=total
        )

        receipt.sold_products = self.sold_products.copy()  # Copia, no referencia

        receipt.id = self.db.add_receipt(receipt)
        grouped_items = {}
        for sp in self.sold_products:
            code = sp.product.code
            if code in grouped_items:
                grouped_items[code]["qty"] += sp.quantity
                grouped_items[code]["total"] += sp.quantity * sp.product.price
            else:
                grouped_items[code] = {
                    "name": sp.product.name,
                    "qty": sp.quantity,
                    "price": sp.product.price,
                    "total": sp.quantity * sp.product.price
                }

            receipt_data = {
                "receipt_id": receipt.id,
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "items": list(grouped_items.values()),
                "total": receipt.total,
                "received": received if received else receipt.total,
                "change": change_due
            }
        
        # 3. Imprimir directamente aquí
        try:
            printer = XPrinterManager()
            printer.print_receipt(receipt_data)
        except Exception as e:
            messagebox.showerror("Error Impresión", f"No se pudo imprimir: {str(e)}")
        
        # 4. Mostrar voucher (opcional, si aún lo necesitas)
        self.main_controller.show_voucher_view(receipt, change_due)
        
        # 5. Reiniciar venta
        self.initialize()

    def _handle_mouse_click(self, event):
        """Restaura el foco si el clic no es en Recibe o botones de pago."""
        widget_clickeado = self.view.winfo_containing(event.x_root, event.y_root)
        
        # Lista de widgets que NO deben interrumpir el lector
        widgets_permitidos = [
            self.view,  # Frame principal
            self.view.tree,  # Tabla de productos
            self.view.delete_btn,  # Botón eliminar
        ]
        
        # Si el clic es en un widget no permitido (ej: botones de pago), restaurar foco
        if widget_clickeado not in widgets_permitidos:
            self.force_focus_restore()

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

    def deactivate_barcode_reader(self):
        self.view.unbind("<KeyRelease>")
        root = self.view.winfo_toplevel()
        root.unbind_all("<KeyRelease>")
