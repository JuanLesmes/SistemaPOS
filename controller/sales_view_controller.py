# controller/sales_view_controller.py
import tkinter as tk
from tkinter import simpledialog, messagebox
from model.sold_product import SoldProduct
from model.receipt import Receipt
import datetime
import logging
from utils.printer_manager import XPrinterManager

logger = logging.getLogger(__name__)

class SalesViewController:
    def __init__(self, parent_frame, main_controller, db):
        self.parent_frame = parent_frame
        self.main_controller = main_controller
        self.db = db
        
        from view.sales_view import SalesView
        self.view = SalesView(self.parent_frame, self)
        self.sold_products = []
        self.initialize()

    def initialize(self):
        """Reinicia la lista de venta y refresca la tabla y total."""
        self.sold_products = []
        self.view.load_table(self.sold_products)
        self.view.set_total("0.0")
        self.view.clear_received_amount()  # Limpiar campo de monto recibido

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
        try:
            # Validación de venta vacía
            total_sale = float(self.calculate_total())
            if total_sale <= 0:
                messagebox.showerror("Error", "No hay productos en la venta.")
                return

            # Validación de campo vacío
            val_str = self.view.get_received_amount().strip()
            if not val_str:
                messagebox.showerror("Error", "Por favor ingrese la cantidad recibida.")
                return

            # Validación de formato numérico
            try:
                received = round(float(val_str), 2)
            except ValueError:
                messagebox.showerror("Error", "Formato inválido. Use números con decimales.\nEj: 15000.50")
                return

            # Validación de monto suficiente
            if received < total_sale:
                messagebox.showerror("Error", 
                    f"Monto insuficiente:\n"
                    f"Total: ${total_sale:.2f}\n"
                    f"Recibido: ${received:.2f}")
                return

            # Validación de monto negativo
            if received < 0:
                messagebox.showerror("Error", "El monto recibido no puede ser negativo.")
                return

            # Procesar pago
            change_due = round(received - total_sale, 2)
            self.generate_receipt("Cash", total_sale, change_due)

        except ValueError as ve:
            logger.error(f"Error de valor: {str(ve)}")
            messagebox.showerror("Error", f"Error en los datos numéricos: {str(ve)}")
        except Exception as e:
            logger.error(f"Error inesperado: {str(e)}", exc_info=True)
            messagebox.showerror("Error Crítico", 
                f"Ocurrió un error inesperado:\n{str(e)}\n\nRevise los logs para más detalles.")

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
        try:
            logger.info("Iniciando proceso de generación de recibo")
            
            # ======= Validación 1: Verificar productos en la venta =======
            if not self.sold_products:
                logger.error("Intento de generar recibo sin productos")
                messagebox.showerror("Error", "No se puede generar un recibo sin productos")
                return

            # ======= Validación 2: Verificar estructura de datos =======
            for sp in self.sold_products:
                if not hasattr(sp, 'product') or not hasattr(sp.product, 'name') or not hasattr(sp.product, 'price'):
                    logger.error("Estructura inválida de productos vendidos")
                    raise ValueError("Los productos no tienen la estructura esperada")

            # ======= Validación 3: Valores numéricos válidos =======
            if not isinstance(total_sale, (int, float)) or total_sale <= 0:
                logger.error(f"Total de venta inválido: {total_sale}")
                raise ValueError("El total de la venta debe ser un número positivo")

            if not isinstance(change_due, (int, float)) or change_due < 0:
                logger.error(f"Cambio inválido: {change_due}")
                raise ValueError("El cambio debe ser un número no negativo")

            # ======= 1. Crear y guardar recibo =======
            now = datetime.datetime.now()
            receipt = Receipt(
                date=now.date(),
                time=now.time(),
                payment_method=payment_method,
                total_sale=round(total_sale, 2)
            )
            receipt.sold_products = self.sold_products.copy()

            # ======= 2. Persistencia en base de datos =======
            try:
                receipt_id = self.db.add_receipt(receipt)
                if not receipt_id:
                    logger.error("Falló la inserción en la base de datos")
                    raise Exception("No se pudo obtener ID del recibo guardado")
                    
                logger.debug(f"Recibo guardado en BD con ID: {receipt_id}")
            except Exception as db_error:
                logger.error(f"Error en base de datos: {str(db_error)}")
                messagebox.showerror("Error", "Falló al guardar el recibo en el sistema")
                return

            # ======= 3. Preparar datos para impresión =======
            receipt_data = {
                "receipt_id": str(receipt_id).zfill(10),
                "date": now.strftime("%d/%m/%Y"),
                "time": now.strftime("%H:%M:%S"),
                "items": [{
                    "qty": sp.quantity,
                    "name": sp.product.name.strip() or "Producto sin nombre",
                    "price": round(float(sp.product.price), 2),
                    "total": round(float(sp.total_partial), 2)
                } for sp in self.sold_products],
                "total": round(total_sale, 2),
                "change": round(change_due, 2)
            }

            # ======= 4. Validar integridad de datos para impresión =======
            for item in receipt_data['items']:
                if any(not isinstance(v, (int, float)) for v in [item['price'], item['total']]):
                    logger.error("Datos numéricos inválidos en items")
                    raise ValueError("Valores monetarios inválidos en productos")

            # ======= 5. Imprimir recibo físico =======
            try:
                self.print_physical_receipt(receipt_data)
            except Exception as print_error:
                logger.error(f"Error de impresión: {str(print_error)}")
                messagebox.showwarning("Advertencia", 
                    "Venta completada pero falló la impresión.\n"
                    "Revise la conexión con la impresora y vuelva a intentarlo.")
                self.view.load_table(self.sold_products)
                return

            # ======= 6. Confirmación y limpieza final =======
            messagebox.showinfo("Venta Exitosa", 
                f"Venta completada exitosamente!\n"
                f"N° Recibo: {receipt_data['receipt_id']}\n"
                f"Total: ${receipt_data['total']:.2f}"
                f"\nCambio: ${receipt_data['change']:.2f}")
            
            self.initialize()

        except ValueError as ve:
            logger.error(f"Error de validación: {str(ve)}")
            messagebox.showerror("Error de Datos", f"Datos inválidos: {str(ve)}")
            self.view.load_table(self.sold_products)
        
        except Exception as e:
            logger.error(f"Error crítico: {str(e)}", exc_info=True)
            messagebox.showerror("Error Crítico", 
                "Ocurrió un error inesperado. La venta no se completó.\n"
                "Contacte al soporte técnico.")
            self.view.load_table(self.sold_products)

    def print_physical_receipt(self, receipt_data):
        """Maneja la impresión física del recibo"""
        try:
            logger.debug("Intentando imprimir recibo")
            printer = XPrinterManager()            
            if not printer.connect():
                raise ConnectionError("No se pudo conectar a la impresora")
                
            printer.print_receipt(receipt_data)
            logger.info("Recibo impreso correctamente")
                
        except Exception as e:
            logger.error(f"Error de impresión: {str(e)}")
            raise  # Relanzar excepción para manejo superior


    def clear_received_amount(self):
        """Limpia el campo de entrada del monto recibido."""
        self.recibe_entry.delete(0, tk.END)

    def get_received_amount(self):
        """Devuelve el texto del campo de monto recibido."""
        return self.recibe_entry.get()