"""Muestra las interfaces y endpoints de la impresora configurada en config.json.

Sirve para verificar los valores in_ep y out_ep.
Ejecutar desde la raíz del proyecto: python scripts/list_endpoints.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import usb.core  # noqa: E402

from utils.config import load_settings  # noqa: E402

printer = load_settings().printer
device = usb.core.find(idVendor=printer.vendor_id, idProduct=printer.product_id)
if device is None:
    raise SystemExit(
        f"No se encontró el dispositivo 0x{printer.vendor_id:04x}:0x{printer.product_id:04x}. "
        "Revise config.json o ejecute scripts/find_usb.py."
    )

for interface in device.get_active_configuration():
    print("Interfaz:", interface.bInterfaceNumber)
    for endpoint in interface:
        print("  Endpoint:", hex(endpoint.bEndpointAddress))
