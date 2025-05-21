import tkinter as tk 
from tkinter import messagebox, filedialog
import datetime
from model.sold_product import SoldProduct
from openpyxl import Workbook
import os

class SalesReportViewController:
    def __init__(self, parent, main_controller, db):
        self.parent = parent
        self.main_controller = main_controller
        self.db = db
        from view.sales_report_view import SalesReportView
        self.view = SalesReportView(self.parent, self)
        self.initialize()

    def initialize(self):
        # Inicia la vista con la tabla vacía y totales en 0
        self.view.load_table([])  
        self.view.set_totals(0.0, 0.0, 0.0, 0.0)

    def event_back(self):
        self.main_controller.show_login_view()

    def event_search(self):
        # Recupera las fechas seleccionadas en la vista
        start_date = self.view.get_start_date()
        end_date = self.view.get_end_date()
        if start_date is None or end_date is None:
            messagebox.showerror("No Dates", "Please select start and end dates.")
            return
        
        # Obtiene los recibos desde la base de datos en el rango indicado
        receipts = self.db.get_receipts_in_range(start_date, end_date)
        
        # Agrupa los productos vendidos de los recibos
        sold_products = self.aggregate_sold_products(receipts)
        # Actualiza la tabla de la vista
        self.view.load_table(sold_products)
        
        # Calcula los totales según el método de pago
        rec_total, cash, card, transfer = self.calculate_totals(receipts)
        # Actualiza los totales en la vista
        self.view.set_totals(rec_total, cash, card, transfer)

    def aggregate_sold_products(self, receipts):
        aggregated = {}
        for r in receipts:
            for sp in r.sold_products:
                code = sp.get_code()
                if code in aggregated:
                    agg_sp = aggregated[code]
                    agg_sp.quantity += sp.quantity
                    agg_sp.calculate_total_partial()
                else:
                    # constructor de SoldProduct: (id, product, quantity)
                    new_sp = SoldProduct(0, sp.product, sp.quantity)
                    # Copiamos fecha y hora desde el recibo
                    new_sp.date = r.date    # aquí va el atributo date de Receipt
                    new_sp.time = r.time    # y el atributo time de Receipt
                    aggregated[code] = new_sp
        return list(aggregated.values())

    
    def get_receipts_by_date_range(self, start_date, end_date):
        # Ejemplo de filtrado
        all_receipts = self.model.get_all_receipts()
        filtered = [r for r in all_receipts if start_date <= r.sale_date <= end_date]
        return filtered

    def calculate_totals(self, receipts):
        total = 0.0
        cash = 0.0
        card = 0.0
        transfer = 0.0

        for r in receipts:
            total += r.total
            # Usar las mismas cadenas que al generar el recibo
            if r.payment_method == "Efectivo":  # <--- Antes era "Cash"
                cash += r.total
            elif r.payment_method == "Tarjeta":  # <--- Antes era "Card"
                card += r.total
            elif r.payment_method == "Transferencia":  # <--- Antes era "Transfer"
                transfer += r.total

        return total, cash, card, transfer
    
    def generate_report(self):
        sold_products = self.view.get_displayed_products()  # Este método lo definiremos en la vista
        if not sold_products:
            messagebox.showinfo("Sin datos", "No hay productos vendidos para exportar.")
            return

        wb = Workbook()
        ws = wb.active
        ws.title = "Reporte de Ventas"

        # Encabezados
        headers = ["Nombre", "Cantidad", "Precio unitario", "Subtotal", "Fecha", "Hora"]
        ws.append(headers)

        # Datos
        for sp in sold_products:
            fecha = sp.date.strftime("%Y-%m-%d") if hasattr(sp.date, "strftime") else str(sp.date)
            hora = sp.time.strftime("%H:%M") if hasattr(sp.time, "strftime") else str(sp.time)
            ws.append([
                sp.product.name,
                sp.quantity,
                sp.product.price,
                sp.get_total_partial(),
                sp.date.strftime("%Y-%m-%d")
            ])

        # Selección de ruta
        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile=f"reporte_ventas_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )

        if filename:
            try:
                wb.save(filename)
                messagebox.showinfo("Éxito", f"Reporte guardado en:\n{filename}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar el archivo:\n{e}")