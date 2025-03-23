from escpos.printer import Usb
import time

VENDOR_ID = 0x0483
PRODUCT_ID = 0x070b

test_data = { 
    # ... (tus datos actuales)
}

try:
    printer = Usb(VENDOR_ID, PRODUCT_ID, interface=0, in_ep=0x81, out_ep=0x02)
    
    # ... (tu código de impresión actual)

    # Opciones para apertura de caja (prueba una por una)
    opciones = [
        (b'\x1B\x70\x00', "Activación pin 2 (estándar)"),          # 00 = pin 2
        (b'\x1B\x70\x01', "Activación pin 5"),                    # 01 = pin 5
        (b'\x1B\x70\x00\x19\xFF', "Pin 2 con tiempos específicos"),  # 25ms ON, 255ms OFF
        (b'\x1B\x70\x00\x64\x64', "Pin 2 con 100ms ON/OFF"),      # 100ms ON, 100ms OFF
        (b'\x1B\x70\x02', "Doble pulso en pin 2")                 # Algunos modelos
    ]

    for codigo, descripcion in opciones:
        try:
            print(f"\nProbando: {descripcion}")
            printer._raw(codigo)
            time.sleep(2)  # Espera para ver si se activa
        except Exception as e:
            print(f"Error con {descripcion}: {str(e)}")

    # Alternativa usando el método cashdraw integrado
    try:
        printer.cashdraw(2)  # Prueba con pin 2
        print("Probando método cashdraw() con pin 2")
        time.sleep(2)
    except Exception as e:
        print(f"Error con cashdraw(): {str(e)}")

    printer.cut()

except Exception as e:
    print("Error general:", e)