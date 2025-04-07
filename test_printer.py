from escpos.printer import Usb
import usb.core

def test_impresion():
    try:
        # Configurar con IDs CORRECTOS
        printer = Usb(
            idVendor=0x0483,
            idProduct=0x070b,
            interface=0,
            in_ep=0x81,
            out_ep=0x02,
            timeout=10000
        )
        
        # Texto básico
        printer.text("\n\n--- PRUEBA ---\n")
        printer.text("Funciona con libusb-1.0.dll\n")
        printer.text("IDs: 0483:070b\n\n\n")
        printer.cut()
        
        print("✅ Verifica la impresora. ¡Debe imprimir 3 líneas!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_impresion()