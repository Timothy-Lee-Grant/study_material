// tgcounter_ioctl.h - the CONTRACT shared by the driver and the user-mode app.
// Phase 5 version: adds two LAB-ONLY IOCTLs that are bugs ON PURPOSE.
#pragma once

// Device type: 0x8000-0xFFFF are reserved for vendors (below that, Microsoft).
#define FILE_DEVICE_TGCOUNTER  0x8000u   // "u": shifting 0x8000 left 16 reaches bit 31 (sign bit of an int)

// Normal requests (unchanged from lecture 009).
#define IOCTL_TGCOUNTER_INCREMENT \
    CTL_CODE(FILE_DEVICE_TGCOUNTER, 0x800, METHOD_BUFFERED, FILE_ANY_ACCESS)
#define IOCTL_TGCOUNTER_GET \
    CTL_CODE(FILE_DEVICE_TGCOUNTER, 0x801, METHOD_BUFFERED, FILE_READ_ACCESS)

// LAB-ONLY bug #1 (lab 5.3): write through a NULL pointer at DISPATCH_LEVEL.
// Crashes EVERY time -> a deterministic bugcheck to analyze.
#define IOCTL_TGCOUNTER_CRASH \
    CTL_CODE(FILE_DEVICE_TGCOUNTER, 0x8FF, METHOD_BUFFERED, FILE_ANY_ACCESS)

// LAB-ONLY bug #2 (lab 5.4): read PAGED pool at DISPATCH_LEVEL.
// Usually "works" (the page happens to be in RAM). Driver Verifier makes it crash every time.
#define IOCTL_TGCOUNTER_PAGED_AT_DISPATCH \
    CTL_CODE(FILE_DEVICE_TGCOUNTER, 0x8FE, METHOD_BUFFERED, FILE_ANY_ACCESS)

// Names in the kernel's object namespace.
#define TGCOUNTER_DEVICE_NAME   L"\\Device\\TgCounter"     // the device object itself
#define TGCOUNTER_LINK_NAME     L"\\??\\TgCounter"         // symbolic link user mode can open
#define TGCOUNTER_USER_PATH     L"\\\\.\\TgCounter"        // what CreateFile is given
