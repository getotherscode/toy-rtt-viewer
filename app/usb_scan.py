#import hid
import usb.core
import usb.util
import usb.backend.libusb1

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
LIBUSB_DLL = ROOT_DIR / "third-party" / "libusb" / "libusb-1.0.dll"

# stop using hid device scan, wch dap-link is not support
# def usb_scan_hid() -> None:
#     devices = hid.enumerate()
#     print(f"find {len(devices)} HID devices \n")

#     for dev in devices:
#         print("-" * 50)
#         print(f"VID       : 0x{dev['vendor_id']:04X}")
#         print(f"PID       : 0x{dev['product_id']:04X}")
#         print(f"Manufacturer: {dev['manufacturer_string']}")
#         print(f"Product     : {dev['product_string']}")
#         print(f"Interface   : {dev['interface_number']}")
#         print(f"Usage Page  : {dev['usage_page']}")
#         print(f"Path        : {dev['path']}")

# need usb backend libusb-1.0
def usb_scan()-> None:
    backend = usb.backend.libusb1.get_backend(
        find_library=lambda name: str(LIBUSB_DLL)
    )

    if backend is None:
        raise RuntimeError("libusb backend initialization failed")

    devices = usb.core.find(
        find_all=True,
        backend=backend
    )
    for dev in devices:
        try:
            print(
                f"VID:PID = {dev.idVendor:04X}:{dev.idProduct:04X}",
                f"Bus = {dev.bus}",
                f"Address = {dev.address}",
            )

            for cfg in dev:
                for intf in cfg:
                    print(
                        f"Interface {intf.bInterfaceNumber}: "
                        f"Class=0x{intf.bInterfaceClass:02X}, "
                        f"Subclass=0x{intf.bInterfaceSubClass:02X}, "
                        f"Protocol=0x{intf.bInterfaceProtocol:02X}"
                    )

                    for ep in intf:
                        transfer_type = ep.bmAttributes & 0x03
                        direction = "IN" if ep.bEndpointAddress & 0x80 else "OUT"
                        print(
                            f"  {direction}: "
                            f"Address=0x{ep.bEndpointAddress:02X}, "
                            f"Type={transfer_type}, "
                            f"MaxPacketSize={ep.wMaxPacketSize}"
                        )

        except Exception as e:
            print(f"  Error: {e}")