from escpos.printer import Usb
import usb.core
import usb.util
import logging

logger = logging.getLogger(__name__)

class XPrinterManager:
    def __init__(self):
        # Configuración para Xprinter común (ajustar según modelo)
        self.vendor_id = 0x0483    # Ej: Xprinter XP-365B
        self.product_id = 0x070b
        self.interface = 0         # Generalmente 0
        self.in_ep = 0x81          # Endpoint de entrada
        self.out_ep = 0x2         # Endpoint de salida
        
    def connect(self):
        try:
            self.printer = Usb(
                self.vendor_id,
                self.product_id,
                interface=self.interface,
                in_ep=self.in_ep,
                out_ep=self.out_ep
            )
            self.printer.profile.profile_data['mediaWidth'] = 58  # 58mm ≈ 6cm
            return True
        except usb.core.USBError as e:
            logger.error(f"Error USB: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error general: {str(e)}")
            return False

    def print_receipt(self, receipt_data):
        if not self.connect():
            raise ConnectionError("No se pudo conectar a la impresora")
            
        try:
            # Configurar página de códigos para caracteres en español
            self.printer.charcode('PC858')
            
            # Encabezado
            self.printer.set(
                align='center', 
                text_type='B', 
                width=2, 
                height=2
            )
            self.printer.text("\nTIENDA MENGUANTE\n")
            self.printer.text("----------------\n")
            
            # Cuerpo del recibo
            self.printer.set(align='left')
            self.printer.text(f"Fecha: {receipt_data['date']} {receipt_data['time']}\n")
            self.printer.text(f"Recibo: {receipt_data['receipt_id']}\n")
            self.printer.text("----------------\n")
            
            # Productos
            for item in receipt_data['items']:
                self.printer.text(f"{item['qty']}x {item['name'].ljust(20)[:20]}\n")
                self.printer.text(
                    f"P.U: ${item['price']:.2f}".ljust(15) + 
                    f"Total: ${item['total']:.2f}\n"
                )
            
            # Totales
            self.printer.text("----------------\n")
            self.printer.set(align='right')
            self.printer.text(f"TOTAL: ${receipt_data['total']:.2f}\n")
            self.printer.text(f"Cambio: ${receipt_data['change']:.2f}\n")
            
            # Comandos especiales
            self.printer.text("\n")  # Espacio antes de cortar
            self.printer.cashdraw(2)  # Apertura de caja (pin 2)
            self.printer.cut()
            
        except Exception as e:
            logger.error(f"Error durante la impresión: {str(e)}")
            raise
        finally:
            if self.printer:
                self.printer.close()