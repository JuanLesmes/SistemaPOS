# utils/printer_manager.py
from escpos.printer import Usb
import logging
import time
import os
import sys
from tkinter import messagebox
from PIL import Image

logger = logging.getLogger(__name__)

class XPrinterManager:
    def __init__(self):
        self.printer = None
        self.config = {
            'idVendor': 0x0483,       # Verificado en USBDeview
            'idProduct': 0x070b,
            'interface': 0,
            'in_ep': 0x81,
            'out_ep': 0x02,
            'timeout': 10000           # Timeout aumentado
        }

    def connect(self):
        """Conexión optimizada y compatible"""
        try:
            if not self.printer:
                self.printer = Usb(**self.config)
                self.printer._raw(b'\x1B\x40')  # Reset impresora
                logger.info("Conexión exitosa")
            return True
        except Exception as e:
            logger.error(f"Error de conexión: {str(e)}")
            messagebox.showerror(
                "Error de Hardware", 
                "1. Verifique conexión USB\n2. Encienda la impresora\n3. Reinicie el programa"
            )
            return False

    def print_receipt(self, receipt_data):
        """Versión definitiva sin errores de fuente"""
        try:
            if not self.connect():
                return False

            # Configuración compatible con todos los perfiles
            self.printer.set(
                align='center',
                font=1,
                width=1,
                height=1,
                density=8
            )
            
            # Logo (solo si existe y está optimizado)
            #logo_path = os.path.join('images', 'logo.png')
            #if os.path.exists(logo_path):
            #    self._print_logo(logo_path)

            # Encabezado
            self.printer.text("\nCIGARRERIA ANTARES\n")
            self.printer.text("Carrera 52A #134A - 31\n")
            self.printer.text("NIT: 80881386-8\n")
            self.printer.text("Tel: 350-701-6084\n")
            self.printer.text("-" * 32 + "\n")
            
            # Detalles del recibo
            self.printer.set(align='left')
            self.printer.text(f"RECIBO: {receipt_data['receipt_id']}\n")
            self.printer.text(f"FECHA: {receipt_data['date']} {receipt_data['time']}\n")
            self.printer.text("-" * 32 + "\n")
            
            # Productos
            for item in receipt_data['items']:
                self.printer.text(f"{item['qty']}x {item['name'][:29]}\n")
                self.printer.text(f"PU: ${item['price']:.2f}\n")            
                self.printer.text(f"Total: ${item['total']:.2f}\n")         
                self.printer.text("-" * 32 + "\n")
            
            # Totales
            self.printer.text("-" * 32 + "\n")
            self.printer.set(align='right', bold=True)
            self.printer.text(f"TOTAL: ${receipt_data['total']:.2f}\n")
            self.printer.set(align='right', bold=False)
            self.printer.text(f"RECIBIDO: ${receipt_data['received']:.2f}\n")
            self.printer.text(f"CAMBIO: ${receipt_data['change']:.2f}")
            
            # Corte final
            self.printer.cut()
            return True

        except Exception as e:
            logger.error(f"Error: {str(e)}", exc_info=True)
            messagebox.showerror("Error de Impresión", f"Detalle: {str(e)}")
            return False
        finally:
            self.disconnect()

    def _print_logo(self, logo_path):
        """Manejo profesional de imágenes"""
        try:
            img = Image.open(logo_path)
            img = img.convert('1')  # Convertir a blanco y negro
            img = img.resize((384, int(384 * img.height / img.width)))  # 58mm
            self.printer.image(img)
            self.printer.text("\n")
        except Exception as e:
            logger.warning(f"Error en logo: {str(e)}")

    def disconnect(self):
        """Desconexión segura"""
        if self.printer:
            try:
                self.printer.close()
                self.printer = None
            except Exception as e:
                logger.error(f"Error al cerrar: {str(e)}")

def get_resource_path(relative_path):
    """Compatibilidad con PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)