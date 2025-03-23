import usb.core

devices = usb.core.find(find_all=True)
for dev in devices:
    print(f"VendorID: 0x{dev.idVendor:04x}, ProductID: 0x{dev.idProduct:04x}")