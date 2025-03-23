import logging
from utils.printer_manager import XPrinterManager

logger = logging.getLogger(__name__)

class VoucherViewController:
    def __init__(self, main_controller):
        self.main_controller = main_controller
        self.printer = XPrinterManager()
        
    def print_receipt(self, receipt_data):
        try:
            formatted_data = self._format_receipt(receipt_data)
            self.printer.print_receipt(formatted_data)
        except Exception as e:
            logger.error(f"Error al imprimir: {str(e)}")
            raise
    
    def _format_receipt(self, raw_data):
        """Estandariza el formato para la impresora"""
        return {
            'receipt_id': raw_data['receipt_id'],
            'date': raw_data['date'],
            'time': raw_data['time'],
            'items': [
                {
                    'qty': item[0],
                    'name': item[1],
                    'price': item[2],
                    'total': item[0] * item[2]
                } for item in raw_data['items']
            ],
            'total': raw_data['total'],
            'change': raw_data['change']
        }