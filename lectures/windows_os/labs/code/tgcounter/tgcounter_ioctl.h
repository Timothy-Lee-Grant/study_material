// tgcounter_ioctl.h - the CONTRACT shared by the driver and the user-mode app.
// Both sides compile this same header, so they agree on the numbers.
#pragma once

// Device type: 0x8000-0xFFFF are reserved for vendors (below that, Microsoft).
#define FILE_DEVICE_TGCOUNTER  0x8000u   // "u": shifting 0x8000 left 16 reaches bit 31 (sign bit of an int)

// CTL_CODE(DeviceType, Function, Method, Access) packs four fields into one 32-bit number.
// Function codes 0x800-0xFFF are for vendors.
#define IOCTL_TGCOUNTER_INCREMENT \
    CTL_CODE(FILE_DEVICE_TGCOUNTER, 0x800, METHOD_BUFFERED, FILE_ANY_ACCESS)
#define IOCTL_TGCOUNTER_GET \
    CTL_CODE(FILE_DEVICE_TGCOUNTER, 0x801, METHOD_BUFFERED, FILE_READ_ACCESS)

// Names in the kernel's object namespace.
#define TGCOUNTER_DEVICE_NAME   L"\\Device\\TgCounter"     // the device object itself
#define TGCOUNTER_LINK_NAME     L"\\??\\TgCounter"         // symbolic link user mode can open
#define TGCOUNTER_USER_PATH     L"\\\\.\\TgCounter"        // what CreateFile is given
