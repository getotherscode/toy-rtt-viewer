import hid

def usb_scan() -> None:
    devices = hid.enumerate()
    print(f"find {len(devices)} HID devices \n")

    for dev in devices:
        print("-" * 50)
        print(f"VID       : 0x{dev['vendor_id']:04X}")
        print(f"PID       : 0x{dev['product_id']:04X}")
        print(f"Manufacturer: {dev['manufacturer_string']}")
        print(f"Product     : {dev['product_string']}")
        print(f"Interface   : {dev['interface_number']}")
        print(f"Usage Page  : {dev['usage_page']}")
        print(f"Path        : {dev['path']}")

if __name__ == "__main__":
    usb_scan()