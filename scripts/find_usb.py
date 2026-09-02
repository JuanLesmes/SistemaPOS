"""Lista los dispositivos USB conectados con su VendorID y ProductID.

Sirve para identificar la impresora térmica y copiar sus IDs a config.json.
Ejecutar desde la raíz del proyecto: python scripts/find_usb.py
"""

import usb.core

for device in usb.core.find(find_all=True):
    print(f"VendorID: 0x{device.idVendor:04x}  ProductID: 0x{device.idProduct:04x}")
