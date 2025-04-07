import logging
from utils.printer_manager import XPrinterManager

logger = logging.getLogger(__name__)

class VoucherViewController:
    def __init__(self, parent, main_controller, receipt, change_due):
        self.parent = parent
        self.main_controller = main_controller
        self.receipt = receipt  # Objeto Receipt con atributo "total"
        self.change_due = change_due
        
        # Crear la vista y pasarle los datos
        from view.voucher_view import VoucherView
        self.view = VoucherView(
            self.parent, 
            controller=self, 
            receipt=receipt, 
            change_due=change_due
        )
        self.printer_manager = XPrinterManager()  # Instancia única

    def event_go_back_to_sales(self):
        """Cierra la vista y desconecta la impresora si es necesario"""
        if self.view.winfo_exists():
            self.view.destroy()
            self.printer_manager.disconnect()  # Usar la instancia existente

    def print_receipt(self):
        """Envía el recibo formateado a la impresora"""
        try:
            formatted_data = self._format_receipt()
            self.printer_manager.print_receipt(formatted_data)
        except Exception as e:
            logger.error(f"Error al imprimir: {str(e)}", exc_info=True)
            raise

    def _format_receipt(self):
        """Estandariza el formato para la impresora usando el objeto Receipt"""
        return {
            'receipt_id': self.receipt.id,
            'date': self.receipt.date.strftime("%Y-%m-%d"),
            'time': self.receipt.time.strftime("%H:%M:%S"),
            'items': [
                {
                    'qty': sp.quantity,
                    'name': sp.product.name,
                    'price': sp.product.price,
                    'total': sp.total_partial
                } for sp in self.receipt.sold_products
            ],
            'total': self.receipt.total,  # Acceso directo al atributo "total"
            'change': self.change_due
        }