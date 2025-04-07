import tkinter as tk 
from tkinter import messagebox
import datetime

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
        self.main_controller.show_admin_view()

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
        """Agrupa los productos vendidos a partir de la lista de recibos."""
        aggregated = {}
        for r in receipts:
            for sp in r.sold_products:
                code = sp.get_code()
                if code in aggregated:
                    aggregated[code].quantity += sp.quantity
                    aggregated[code].calculate_total_partial()
                else:
                    # Clonar el objeto sold_product para no modificar el original
                    from model.sold_product import SoldProduct
                    new_sp = SoldProduct(0, sp.product, sp.quantity)
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