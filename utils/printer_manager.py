from escpos.printer import Usb
import usb.core
import usb.util
import logging

# En printer_manager.py o donde manejes la impresora
import sys
import os

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

# Modificar la inicialización de la impresora
from escpos import config
cfg = config.Config()
cfg.load(get_resource_path('escpos/config.yaml'))

logger = logging.getLogger(__name__)

class XPrinterManager:
    def __init__(self):
        # Configuración para Xprinter XP-365B
        self.vendor_id = 0x0483
        self.product_id = 0x070b
        self.interface = 0
        self.in_ep = 0x81
        self.out_ep = 0x02
        
    def connect(self):
        """Intenta conectar con la impresora"""
        try:
            self.printer = Usb(
                self.vendor_id,
                self.product_id,
                interface=self.interface,
                in_ep=self.in_ep,
                out_ep=self.out_ep
            )
            # Configuración de ancho para impresoras de 58mm
            self.printer.profile.profile_data['mediaWidth'] = 58
            return True
        except Exception as e:
            logger.error(f"Error de conexión: {str(e)}")
            return False

    def print_receipt(self, receipt_data):
        """Imprime un recibo con formato mejorado"""
        if not self.connect():
            raise ConnectionError("No se pudo conectar a la impresora")
            
        try:
            # Configurar codificación para caracteres especiales
            self.printer.charcode('CP1252')
            
            # ---- ENCABEZADO ----
            self.printer.set(align='center')
            self.printer.text("\nCIGARRERIA ANTARES\n")
            self.printer.text("NIT: 80881386-8\n")
            self.printer.text("Cra 52a #134a - 31\n")
            self.printer.text("Tel: 350-701-6084\n")
            self.printer.text("-" * 32 + "\n") 
            
            # ---- INFORMACIÓN DE LA VENTA ----
            self.printer.set(align='left')
            self.printer.text(f"Fecha:  {receipt_data['date']}\n")
            self.printer.text(f"Hora:   {receipt_data['time']}\n")
            self.printer.text(f"Recibo: {receipt_data['receipt_id']}\n")
            self.printer.text("-" * 32 + "\n") 
            
            # ---- DETALLE DE PRODUCTOS ----
            for item in receipt_data['items']:
                # Asegurar que 'name' existe y tiene valor predeterminado si está vacío
                product_name = item.get('name', 'Producto sin nombre')[:24]
                product_line = f"{item['qty']}x {product_name}".ljust(32)
                self.printer.text(product_line + "\n")
                
                # Formatear precios con valores por defecto
                unit_price = item.get('price', 0.00)
                total_price = item.get('total', 0.00)
                price_line = (
                    f"PU: ${unit_price:.2f}".ljust(16) +
                    f"Total: ${total_price:.2f}".rjust(16)
                )
                self.printer.text(price_line)
            
            # ---- TOTALES ----
            self.printer.text("----------------------------------------\n")
            self.printer.set(align='right')
            self.printer.text(f"TOTAL:  ${receipt_data['total']:.2f}\n")
            self.printer.text(f"CAMBIO: ${receipt_data['change']:.2f}")
            
            # ---- ESPACIO FINAL Y CORTE ----
            try:
                # Envía el comando para abrir la caja usando solo el pin
                self.printer.cashdraw(2)
            except Exception as e:
                logger.error(f"Error abriendo caja con cashdraw: {str(e)}")
                # Fallback a comando raw
                self.printer._raw(b'\x1B\x70\x00\x19\x19')

                
            self.printer.cut()
            
        except Exception as e:
            logger.error(f"Error durante la impresión: {str(e)}")
            raise
        finally:
            if self.printer:
                self.printer.close()