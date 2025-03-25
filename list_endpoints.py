import usb.core
import usb.util
from escpos.magicencode import MagicEncode

dev = usb.core.find(idVendor=0x0483, idProduct=0x070b)
if dev is None:
    raise ValueError("Dispositivo no encontrado")

# Selecciona la primera configuración activa
cfg = dev.get_active_configuration()
for intf in cfg:
    print("Interface:", intf.bInterfaceNumber)
    for ep in intf:
        print("  Endpoint address:", hex(ep.bEndpointAddress))


print("Páginas de código disponibles:", MagicEncode().codepages.keys())