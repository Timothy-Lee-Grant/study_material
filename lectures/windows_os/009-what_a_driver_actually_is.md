2026_10_22_00_30-(What-A-Driver-Actually-Is)

# Lecture 009 — What a Driver Actually Is: the .sys File, How It Loads, and How Everything Calls Everything

> **For:** Timothy · **Date:** 2026-10-22
> **Prerequisites:** 005 (IRQL, ISR/DPC/work item), 006 (device stacks, PnP, INF, signing), 008 (processes, threads, address spaces). Lecture 001 helps for the WinDbg section.
> **Why this lecture:** the earlier lectures kept saying "a kernel driver is a `.sys` file" and "the I/O manager calls the driver", and that stayed abstract. This lecture makes it concrete with one small, complete driver, `TgCounter`, built for real. You'll see what's inside the `.sys` file, which configuration makes Windows load it, what `DriverEntry` registers, and every hop a request makes from a user program's `DeviceIoControl` down to the driver's function and back. Then you'll see the same driver in KMDF, how drivers call *other* drivers, and how it all looks in WinDbg.

---

## Core ideas (the answer key)

1. **A `.sys` file is a PE executable**, the same file format as `.exe` and `.dll`, marked with the **native** subsystem. It has an entry point (`DriverEntry`) and an **import table** listing kernel functions it needs, mostly from `ntoskrnl.exe`. The kernel's exported functions *are* the driver API.
2. **A driver is loaded because configuration says so.** A **service key** in the registry (`HKLM\SYSTEM\CurrentControlSet\Services\<name>`) says what file to load and when. You create it with `sc create` for a simple, non-PnP driver, or an INF creates it for a PnP driver. Loading means: the kernel maps the image into kernel memory, resolves its imports, creates a **driver object**, and calls `DriverEntry` once.
3. **`DriverEntry` registers; it doesn't run the device.** It fills in function pointers (the dispatch table, the unload routine, or KMDF callbacks), creates device objects (or tells KMDF how to), and returns. From then on, the driver's code runs only when someone calls one of those functions.
4. **User mode reaches a driver through names and handles.** The device object has a kernel name (`\Device\TgCounter`). A **symbolic link** (`\??\TgCounter`) or a **device interface** makes it openable. `CreateFile("\\.\TgCounter")` creates a **file object** and a handle; every later call on that handle is routed to that device.
5. **Every request is an IRP built by the I/O manager.** The path is: `DeviceIoControl` → `ntdll` → **system call** → `NtDeviceIoControlFile` → the I/O manager checks access, prepares buffers, builds an IRP → calls the driver's `MajorFunction[IRP_MJ_DEVICE_CONTROL]` → the driver completes the IRP → the I/O manager copies results back → the call returns.
6. **An IOCTL code is a contract packed into 32 bits:** device type, function number, **buffering method**, and required **access**. Driver and app compile the same header. The method decides how user buffers reach the driver (copied, mapped, or raw), and raw (`METHOD_NEITHER`) is the dangerous one.
7. **Drivers call other drivers the same way:** build or forward an IRP and `IoCallDriver` the next device object (KMDF: send a request to an **I/O target**). A filter passes requests down; a function driver sends its own requests to a bus driver (hidi2c → the I2C controller).
8. **Drivers call the kernel through prefixed function families:** `Io` (I/O manager), `Ke` (scheduler, sync, IRQL), `Ex` (pool memory), `Mm` (memory mapping), `Ob` (objects), `Ps` (processes and threads), `Po` (power), `Rtl` (helpers), `Wdf` (KMDF). The kernel calls drivers back through the pointers they registered.

---

## Table of Contents

- [0. The whole picture, in one diagram](#0-the-whole-picture-in-one-diagram)
- [1. The example: TgCounter](#1-the-example-tgcounter)
- [2. Inside the .sys file](#2-inside-the-sys-file)
- [3. Configuration: what makes Windows load it](#3-configuration-what-makes-windows-load-it)
- [4. Loading, and DriverEntry](#4-loading-and-driverentry)
- [5. The complete driver](#5-the-complete-driver)
- [6. The contract: IOCTL codes and buffering methods](#6-the-contract-ioctl-codes-and-buffering-methods)
- [7. The user-mode side](#7-the-user-mode-side)
- [8. One call, every hop](#8-one-call-every-hop)
- [9. The same driver in KMDF, as a PnP device](#9-the-same-driver-in-kmdf-as-a-pnp-device)
- [10. Drivers calling drivers](#10-drivers-calling-drivers)
- [11. Drivers calling the kernel, and the kernel calling drivers](#11-drivers-calling-the-kernel-and-the-kernel-calling-drivers)
- [12. Seeing all of it in WinDbg](#12-seeing-all-of-it-in-windbg)
- [13. Lab: load it for real](#13-lab-load-it-for-real)
- [14. The Linux equivalent, briefly](#14-the-linux-equivalent-briefly)
- [15. Misconceptions](#15-misconceptions)
- [16. Saying it precisely](#16-saying-it-precisely)
- [17. Self-check](#17-self-check)
- [Sources](#sources)

---

## 0. The whole picture, in one diagram 🟢

Every arrow is one of the four channels from earlier lectures: a function call, a system call, an I/O request, or a hardware access. Each box names its actor.

```
USER MODE (the app's process)
  tgclient.exe ──calls──► KERNEL32 / KERNELBASE  DeviceIoControl()
                               │ calls
                               ▼
                          ntdll.dll  NtDeviceIoControlFile()   ← thin stub: puts a number in a register
                               │ SYSTEM CALL instruction (privilege: user → kernel)
═══════════════════════════════╪════════════════════════════════════════════════════════════
KERNEL MODE (one shared address space)
                               ▼
                          nt!KiSystemCall64 → nt!NtDeviceIoControlFile     ← system service
                               │ handle → FILE_OBJECT → DEVICE_OBJECT (via the object manager)
                               ▼
                          I/O manager: check access bits, copy input to a system buffer,
                                       allocate an IRP, fill this driver's stack location
                               │ IoCallDriver(device, irp)
                               │   = device->DriverObject->MajorFunction[IRP_MJ_DEVICE_CONTROL](device, irp)
                               ▼
                          TgCounter.sys  TgDispatchDeviceControl()          ← YOUR code
                               │ (a real device driver would now touch registers, or call
                               │  IoCallDriver on a lower driver: the bus driver, an I2C controller)
                               │ IoCompleteRequest(irp)
                               ▼
                          I/O manager: copy output back to the app's buffer, set status
                               │ return from system call (privilege: kernel → user)
═══════════════════════════════╪════════════════════════════════════════════════════════════
                               ▼
  tgclient.exe ◄── DeviceIoControl returns TRUE, value filled in
```

Keep this picture in mind. Every section below zooms into one part of it.

---

## 1. The example: TgCounter 🟢

`TgCounter` is the smallest driver that still shows every interaction. It has no hardware. It owns one device object holding a counter, and it answers three requests:

| User-mode call | Becomes this IRP | Driver does |
|---|---|---|
| `CreateFile(L"\\\\.\\TgCounter", …)` | `IRP_MJ_CREATE` | Says yes |
| `DeviceIoControl(h, IOCTL_TGCOUNTER_INCREMENT, …)` | `IRP_MJ_DEVICE_CONTROL` | Adds 1 to the counter, returns the new value |
| `DeviceIoControl(h, IOCTL_TGCOUNTER_GET, …)` | `IRP_MJ_DEVICE_CONTROL` | Returns the counter |
| `CloseHandle(h)` | `IRP_MJ_CLOSE` | Says yes |

Files, in `lectures/windows_internals/code/tgcounter/`:

| File | Role |
|---|---|
| `tgcounter_ioctl.h` | The **contract**: IOCTL codes and names, shared by both sides |
| `tgcounter.c` | The **driver** (classic WDM style, so every mechanism is visible) |
| `tgclient.c` | The **user-mode program** |

Real check: both were compiled for this lecture with MinGW-w64 (`-Wall -Wextra`, no warnings), producing an 8.5 KB `TgCounter.sys` and `tgclient.exe`. The driver wasn't loaded into a real Windows kernel here: that needs a Windows test machine (§13). The outputs in §2 and §7 are real; WinDbg outputs in §12 are illustrative. For production you'd build with Visual Studio and the WDK (Windows Driver Kit), and usually write KMDF (§9). The WDM version is here because it hides nothing.

---

## 2. Inside the .sys file 🟢

### 2.1 It's a PE executable

Windows executables, DLLs and drivers all use one file format: **PE** (Portable Executable). Here's what `objdump` reports about the `TgCounter.sys` built for this lecture (real output):

```
TgCounter.sys:     file format pei-x86-64
architecture: i386:x86-64
start address 0x0000000140001130

AddressOfEntryPoint   0000000000001130
ImageBase             0000000140000000
Subsystem             00000001  (NT native)
DllCharacteristics    HIGH_ENTROPY_VA  DYNAMIC_BASE  NX_COMPAT
```

What each line stands for:
- **`pei-x86-64`**: a PE image for 64-bit x86. An Arm64 laptop needs an Arm64 build of the same driver (the INF's `NTarm64` section from 006).
- **Entry point `0x1130`**: the offset of `DriverEntry`. When the kernel loads the image, this is the function it calls.
- **Subsystem: NT native**: "this doesn't run under the Windows (Win32) subsystem". `.exe` files say *Windows GUI* or *Windows console*; drivers say *native*. It's one of the things that makes a PE file a driver.
- **`DYNAMIC_BASE`**: the image can be loaded at any address (kernel ASLR), so it carries relocation information.

### 2.2 Sections

```
  .text    code: DriverEntry, the dispatch routines
  .rdata   read-only data: the device name strings
  .pdata / .xdata   unwind tables, so stacks can be walked (that's how WinDbg's k works on x64)
  .edata   export table
  .idata   IMPORT table: which kernel functions this driver needs
```

Drivers built with the WDK commonly also have a **`PAGE`** section (pageable code, 005 §8) and an **`INIT`** section (code used only in `DriverEntry`, discarded afterwards to save memory).

### 2.3 The import table: the driver API, made visible

This is the single most clarifying thing to look at. The real import table of `TgCounter.sys`:

```
DLL Name: ntoskrnl.exe
    DbgPrint
    IoCreateDevice
    IoCreateSymbolicLink
    IoDeleteDevice
    IoDeleteSymbolicLink
    IofCompleteRequest
    RtlInitUnicodeString
```

What this tells you:
- **A driver links against the kernel the way an app links against a DLL.** `ntoskrnl.exe` (the kernel image) *exports* thousands of functions; the driver *imports* the ones it uses. At load time the kernel fills in their addresses.
- **Every interaction with the kernel is one of these calls.** "The driver communicates with the I/O manager" means, concretely, "it calls `IoCreateDevice`, `IoCompleteRequest`…".
- **`IofCompleteRequest`, not `IoCompleteRequest`:** the name in the source is a macro wrapping the real exported function. Imports show what really happens.
- **`InterlockedIncrement` is missing**: it compiled to a single atomic CPU instruction, so it needs no import.

Compare the user-mode client's imports (also real):

```
DLL Name: KERNEL32.dll
    CloseHandle
    CreateFileW
    DeviceIoControl
```

Same mechanism, different library: apps import from user-mode system DLLs; drivers import from the kernel. A **KMDF** driver additionally depends on the framework, loaded for it through the framework loader (`WDFLDR.SYS`) and the framework library (`Wdf01000.sys`).

Try it on Windows: `dumpbin /imports C:\Windows\System32\drivers\hidi2c.sys` (from a Visual Studio command prompt) shows a real Microsoft driver's dependencies.

---

## 3. Configuration: what makes Windows load it 🟢

A `.sys` file on disk does nothing. Windows loads a driver because **configuration** names it. There are two routes, and both end in the same registry structure.

### 3.1 The service key: the configuration every driver has

Every driver has a key under `HKLM\SYSTEM\CurrentControlSet\Services\`. For TgCounter it would look like this (shown as a `.reg` export):

```
[HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\TgCounter]
"Type"=dword:00000001          ; 1 = kernel-mode driver (2 = file system driver, 0x10 = user-mode service)
"Start"=dword:00000003         ; 0 boot, 1 system, 2 automatic, 3 demand (on request), 4 disabled
"ErrorControl"=dword:00000001  ; how bad a load failure is: 1 = log it and continue
"ImagePath"=expand_sz:"\??\C:\drivers\TgCounter.sys"   ; which file to load
"DisplayName"="TgCounter"
```

What each value stands for:
- **`Type`**: what kind of service this is. The same `Services` key holds Windows services (user-mode programs) and drivers; `Type` tells them apart.
- **`Start`**: *when* to load it. Boot-start drivers (0) are loaded by the boot loader itself, e.g. storage drivers needed to read the disk. System-start (1) load during kernel initialization. Demand (3) load when asked: for PnP drivers, PnP asks when a matching device appears.
- **`ImagePath`**: where the `.sys` is. PnP drivers from the driver store point into `DriverStore\FileRepository\…`.
- PnP drivers often also have a **`Parameters`** subkey (driver settings read in `DriverEntry`). KMDF drivers get a `Parameters\Wdf` subkey recording the framework version they need.

The `RegistryPath` argument that `DriverEntry` receives is the path to this exact key. That's how a driver finds its own configuration.

### 3.2 Route A: a non-PnP driver, created by hand

TgCounter isn't tied to hardware, so it can be loaded as a **legacy (non-PnP) driver**. One command creates the service key above:

```
sc create TgCounter type= kernel start= demand binPath= C:\drivers\TgCounter.sys
sc start TgCounter          ← load it now: DriverEntry runs
sc stop TgCounter           ← unload: the Unload routine runs
sc delete TgCounter         ← remove the service key
```

(`sc` requires the space *after* each `=`.) `sc` talks to the **Service Control Manager** (`services.exe`), which writes the key and, on `sc start`, asks the kernel to load the driver (the `NtLoadDriver` system service).

### 3.3 Route B: a PnP driver, created by an INF

A hardware driver is installed with an INF (006 §7). Its `AddService` directive creates the **same** service key. Additionally, the PnP manager records the device itself under `HKLM\SYSTEM\CurrentControlSet\Enum\<bus>\<device id>\<instance>`, with a value `Service = TgCounter` that links the device to its driver. That's how PnP knows which driver to load when the device appears. §9 shows the INF for a PnP version of TgCounter.

| | Non-PnP (route A) | PnP (route B) |
|---|---|---|
| Created by | `sc create` (or code calling the Service Control Manager) | INF install (`pnputil`, Windows Update, `devcon`) |
| Loaded when | Someone runs `sc start` (or at boot, if `Start` says so) | A matching device appears; PnP loads the driver and calls `AddDevice` |
| Device objects created | By the driver itself, in `DriverEntry` | Per device, in `AddDevice` (KMDF: `EvtDriverDeviceAdd`) |
| Typical use | Software-only drivers, tools | All hardware |

---

## 4. Loading, and DriverEntry 🟢

### 4.1 What "loading a driver" does, numbered

1. **Something asks:** the Service Control Manager (`sc start`), or the PnP manager (a device appeared), or the boot loader (boot-start drivers).
2. **The kernel checks the signature** (code integrity, 006 §9). Unsigned or wrongly signed → refused, and the load fails.
3. **The memory manager maps the image** into kernel address space (system space, shared by every process), applies relocations, and **resolves imports**: each entry in the import table gets the real address of the kernel function.
4. **The I/O manager creates a driver object** (`DRIVER_OBJECT`) and a kernel name for it, `\Driver\TgCounter`.
5. **It calls `DriverEntry(DriverObject, RegistryPath)`** once, at PASSIVE_LEVEL, on a system thread.
6. If `DriverEntry` returns success, the driver stays loaded. If it returns an error, the kernel unloads the image.

There's no `main()` loop, no process and no thread of its own. After step 6 the driver is a set of functions sitting in kernel memory, waiting to be called.

### 4.2 What DriverEntry registers

For TgCounter (WDM style), `DriverEntry` does four things:

1. **Creates a device object**: `IoCreateDevice(..., L"\\Device\\TgCounter", ...)`. This is the thing requests are *sent to*. It gets space for the driver's per-device data (the **device extension**: here, the counter).
2. **Creates a symbolic link** `\??\TgCounter` → `\Device\TgCounter`, so user mode can open it by name (§7).
3. **Fills in the dispatch table**: `DriverObject->MajorFunction[]` is an array of function pointers, one per request type (`IRP_MJ_CREATE`, `IRP_MJ_CLOSE`, `IRP_MJ_READ`, `IRP_MJ_WRITE`, `IRP_MJ_DEVICE_CONTROL`, `IRP_MJ_PNP`, `IRP_MJ_POWER`, … about 28 in total). Entries the driver doesn't fill in point to a default that rejects the request.
4. **Sets `DriverUnload`**, the function to call when the driver is stopped.

That table is the real meaning of "the I/O manager calls the driver": for a device-control request, the I/O manager literally calls `DriverObject->MajorFunction[IRP_MJ_DEVICE_CONTROL](DeviceObject, Irp)`.

---

## 5. The complete driver 🟢

`tgcounter_ioctl.h`, the contract:

```c
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
```

The `u` on `0x8000u` came from a real compiler warning while building this lecture. `CTL_CODE` shifts the device type left 16 bits, and `0x8000 << 16` lands in bit 31, the sign bit of a signed `int`, so comparisons against the driver's `ULONG` became signed-vs-unsigned. Making the type unsigned fixes it.

`tgcounter.c`, the driver:

```c
// tgcounter.c - a minimal, legacy (non-PnP) WDM kernel driver.
// It creates one device object with a counter, and handles three requests:
//   IRP_MJ_CREATE / IRP_MJ_CLOSE    (CreateFile / CloseHandle from user mode)
//   IRP_MJ_DEVICE_CONTROL           (DeviceIoControl: INCREMENT and GET)
#include <ntddk.h>
#include "tgcounter_ioctl.h"

typedef struct _TG_EXTENSION {          // per-device state, lives in nonpaged memory
    LONG Counter;
} TG_EXTENSION, *PTG_EXTENSION;

// Finish an IRP: record the result and hand it back to the I/O manager.
static NTSTATUS CompleteIrp(PIRP Irp, NTSTATUS status, ULONG_PTR bytesReturned)
{
    Irp->IoStatus.Status = status;
    Irp->IoStatus.Information = bytesReturned;   // how many output bytes are valid
    IoCompleteRequest(Irp, IO_NO_INCREMENT);
    return status;
}

// Called by the I/O manager for IRP_MJ_CREATE and IRP_MJ_CLOSE.
static NTSTATUS TgDispatchCreateClose(PDEVICE_OBJECT DeviceObject, PIRP Irp)
{
    UNREFERENCED_PARAMETER(DeviceObject);
    return CompleteIrp(Irp, STATUS_SUCCESS, 0);  // nothing to set up: just say yes
}

// Called by the I/O manager for IRP_MJ_DEVICE_CONTROL (user mode called DeviceIoControl).
static NTSTATUS TgDispatchDeviceControl(PDEVICE_OBJECT DeviceObject, PIRP Irp)
{
    PTG_EXTENSION ext = (PTG_EXTENSION)DeviceObject->DeviceExtension;
    PIO_STACK_LOCATION stack = IoGetCurrentIrpStackLocation(Irp);   // THIS driver's slot
    ULONG code   = stack->Parameters.DeviceIoControl.IoControlCode;
    ULONG outLen = stack->Parameters.DeviceIoControl.OutputBufferLength;
    PVOID buffer = Irp->AssociatedIrp.SystemBuffer;  // METHOD_BUFFERED: a kernel copy

    if (code != IOCTL_TGCOUNTER_INCREMENT && code != IOCTL_TGCOUNTER_GET)
        return CompleteIrp(Irp, STATUS_INVALID_DEVICE_REQUEST, 0);
    if (outLen < sizeof(LONG))
        return CompleteIrp(Irp, STATUS_BUFFER_TOO_SMALL, 0);

    LONG value = (code == IOCTL_TGCOUNTER_INCREMENT)
                     ? InterlockedIncrement(&ext->Counter)   // safe if two callers race
                     : ext->Counter;
    *(LONG *)buffer = value;                                 // I/O manager copies it out
    return CompleteIrp(Irp, STATUS_SUCCESS, sizeof(LONG));
}

// Called when the driver is stopped (sc stop). Undo everything DriverEntry did.
static VOID TgUnload(PDRIVER_OBJECT DriverObject)
{
    UNICODE_STRING link;
    RtlInitUnicodeString(&link, TGCOUNTER_LINK_NAME);
    IoDeleteSymbolicLink(&link);
    IoDeleteDevice(DriverObject->DeviceObject);
    DbgPrint("TgCounter: unloaded\n");
}

// The entry point. The I/O manager calls this ONCE, right after loading the .sys file.
NTSTATUS DriverEntry(PDRIVER_OBJECT DriverObject, PUNICODE_STRING RegistryPath)
{
    UNICODE_STRING devName, linkName;
    PDEVICE_OBJECT device;
    NTSTATUS status;

    RtlInitUnicodeString(&devName, TGCOUNTER_DEVICE_NAME);
    RtlInitUnicodeString(&linkName, TGCOUNTER_LINK_NAME);

    // 1. Create the device object: the thing requests are sent TO.
    status = IoCreateDevice(DriverObject, sizeof(TG_EXTENSION), &devName,
                            FILE_DEVICE_TGCOUNTER, FILE_DEVICE_SECURE_OPEN,
                            FALSE, &device);
    if (!NT_SUCCESS(status)) return status;
    ((PTG_EXTENSION)device->DeviceExtension)->Counter = 0;

    // 2. Give user mode a name it can open: \??\TgCounter -> \Device\TgCounter.
    status = IoCreateSymbolicLink(&linkName, &devName);
    if (!NT_SUCCESS(status)) { IoDeleteDevice(device); return status; }

    // 3. Fill in the dispatch table: "for this kind of request, call this function".
    DriverObject->MajorFunction[IRP_MJ_CREATE]         = TgDispatchCreateClose;
    DriverObject->MajorFunction[IRP_MJ_CLOSE]          = TgDispatchCreateClose;
    DriverObject->MajorFunction[IRP_MJ_DEVICE_CONTROL] = TgDispatchDeviceControl;
    DriverObject->DriverUnload                         = TgUnload;

    DbgPrint("TgCounter: loaded from %wZ\n", RegistryPath);
    return STATUS_SUCCESS;
}
```

**Questions to ask of every line** (connecting earlier lectures):
- *What IRQL does each function run at?* All of them at PASSIVE_LEVEL here. `DriverEntry` and `Unload` always are. The dispatch routines run on the **calling app's thread**, in the app's process context, because the app's thread made the system call (008 §1.2).
- *Where does the counter live?* In the device extension, allocated by `IoCreateDevice` from **nonpaged** memory, so it'd be safe even at DISPATCH_LEVEL (005 §8).
- *Why `InterlockedIncrement`?* Two apps (two threads) can be in the dispatch routine at once, on two CPUs. A plain `Counter++` could lose an update.
- *Who frees the IRP?* Not the driver. `IoCompleteRequest` hands it back to the I/O manager, which copies results and frees it.

**Production note** (⚫ for now): this device can be opened by any user, because `IoCreateDevice` applies a default security descriptor. A real driver uses `IoCreateDeviceSecure` with an SDDL string (for example, only SYSTEM and Administrators), or KMDF's equivalent. Driver devices that any user can open, combined with weak input checking, are a common class of security vulnerability.

---

## 6. The contract: IOCTL codes and buffering methods 🟢

### 6.1 What's inside an IOCTL code

`CTL_CODE(DeviceType, Function, Method, Access)` packs four fields into 32 bits:

```
 bits 31..16   bits 15..14   bits 13..2       bits 1..0
 DeviceType  |   Access    |   Function     |  Method
```

The two codes from the header, decoded (values printed by the real client program and checked by hand):

| Code | Value | Device type | Access | Function | Method |
|---|---|---|---|---|---|
| `IOCTL_TGCOUNTER_INCREMENT` | `0x80002000` | `0x8000` | 0 = `FILE_ANY_ACCESS` | `0x800` | 0 = `METHOD_BUFFERED` |
| `IOCTL_TGCOUNTER_GET` | `0x80006004` | `0x8000` | 1 = `FILE_READ_ACCESS` | `0x801` | 0 = `METHOD_BUFFERED` |

What each field is *for*:
- **Access**: the I/O manager checks it **before the driver is called**. `IOCTL_TGCOUNTER_GET` requires that the handle was opened with read access; otherwise the call fails with access denied and the driver never sees it. It's free security, enforced by the kernel.
- **Method**: tells the I/O manager how to deliver the caller's buffers (§6.2).
- **DeviceType + Function**: make the code unique. Microsoft's own codes use device types below `0x8000` and function numbers below `0x800`.

### 6.2 The four buffering methods

| Method | How the driver sees the caller's buffers | Safety |
|---|---|---|
| **`METHOD_BUFFERED`** | The I/O manager allocates a kernel buffer (`Irp->AssociatedIrp.SystemBuffer`), copies the input in, and after completion copies the output back to the app | Safest; the driver never touches user memory. Best for small data |
| **`METHOD_IN_DIRECT` / `METHOD_OUT_DIRECT`** | The output buffer is locked in physical memory and described by an **MDL** (memory descriptor list) the driver maps into kernel space; no copy | For large transfers (DMA, big reads) |
| **`METHOD_NEITHER`** | The driver gets the **raw user-mode pointers** | Dangerous: the driver must validate and access them carefully, only in the caller's context, at PASSIVE_LEVEL, inside exception handling. Mishandled, it causes crashes (0x50 subtype 0xF from 002) and security holes |

TgCounter uses `METHOD_BUFFERED`: the four bytes it writes go into a kernel buffer, and the I/O manager copies them to the app's `value` variable.

---

## 7. The user-mode side 🟢

`tgclient.c`:

```c
// tgclient.c - user-mode program that talks to the TgCounter driver.
#include <windows.h>
#include <winioctl.h>      // CTL_CODE, METHOD_BUFFERED, FILE_ANY_ACCESS ...
#include <stdio.h>
#include "tgcounter_ioctl.h"

int main(void)
{
    printf("IOCTL_TGCOUNTER_INCREMENT = 0x%08lX\n", (unsigned long)IOCTL_TGCOUNTER_INCREMENT);
    printf("IOCTL_TGCOUNTER_GET       = 0x%08lX\n", (unsigned long)IOCTL_TGCOUNTER_GET);

    // 1. Open the device by its symbolic link. This becomes IRP_MJ_CREATE in the driver.
    HANDLE h = CreateFileW(TGCOUNTER_USER_PATH, GENERIC_READ | GENERIC_WRITE, 0, NULL,
                           OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (h == INVALID_HANDLE_VALUE) {
        printf("CreateFile failed, GetLastError=%lu (2 = no such name: is the driver loaded?)\n",
               GetLastError());
        return 1;
    }

    // 2. Send requests. Each DeviceIoControl becomes one IRP_MJ_DEVICE_CONTROL.
    for (int i = 0; i < 3; i++) {
        LONG value = 0; DWORD bytes = 0;
        if (!DeviceIoControl(h, IOCTL_TGCOUNTER_INCREMENT, NULL, 0,
                             &value, sizeof(value), &bytes, NULL)) {
            printf("DeviceIoControl failed, GetLastError=%lu\n", GetLastError());
            break;
        }
        printf("INCREMENT -> %ld (%lu bytes returned)\n", value, bytes);
    }

    // 3. Close. This becomes IRP_MJ_CLOSE (after the last handle to the file object closes).
    CloseHandle(h);
    return 0;
}
```

**Real output** of this program, run under Wine on Linux, where no driver exists:

```
IOCTL_TGCOUNTER_INCREMENT = 0x80002000
IOCTL_TGCOUNTER_GET       = 0x80006004
CreateFile failed, GetLastError=2 (2 = no such name: is the driver loaded?)
```

That failure is instructive in itself: error 2 (`ERROR_FILE_NOT_FOUND`) is exactly what you'd see on Windows if the driver isn't loaded, because the name `\??\TgCounter` doesn't exist in the object namespace. With the driver loaded (§13) you'd expect:

```
INCREMENT -> 1 (4 bytes returned)
INCREMENT -> 2 (4 bytes returned)
INCREMENT -> 3 (4 bytes returned)
```

(That's the expected output, not one captured here.)

### 7.1 How a name becomes a device 🟢

`"\\\\.\\TgCounter"` in C is the string `\\.\TgCounter`. The steps:
1. Win32 (KERNEL32/KERNELBASE) converts the `\\.\` prefix to the NT path `\??\TgCounter`.
2. `\??` is the **DOS devices directory** in the kernel's object namespace: the same namespace that holds named sections and mutexes (008 §5). It's where `C:` lives, too: drive letters are symbolic links in that directory.
3. The object manager finds the **symbolic link** `TgCounter` there, which points to `\Device\TgCounter`.
4. It reaches the **device object** and asks the I/O manager to open it. The I/O manager creates a **file object** (`FILE_OBJECT`, the kernel's record of "one open instance of this device"), sends `IRP_MJ_CREATE` to the driver, and if the driver succeeds, puts a **handle** to the file object into the app's handle table.

From then on, the handle is the app's "connection": every `DeviceIoControl(h, …)` is looked up handle → file object → device object → driver.

---

## 8. One call, every hop 🟢

`DeviceIoControl(h, IOCTL_TGCOUNTER_INCREMENT, NULL, 0, &value, 4, &bytes, NULL)`, traced. The actor is named at every step:

1. **tgclient.exe** calls `DeviceIoControl` in **KERNELBASE.dll** (user mode).
2. KERNELBASE calls `NtDeviceIoControlFile` in **ntdll.dll**: a few instructions that put the *system service number* in a register and execute the **system call instruction** (`syscall` on x64).
3. **The CPU** switches privilege, user → kernel (008 §2.3), switches to the thread's **kernel stack**, and jumps to the kernel's system-call entry, `nt!KiSystemCall64`. Same thread, now in kernel mode, at PASSIVE_LEVEL.
4. The kernel's dispatcher uses the service number to call **`nt!NtDeviceIoControlFile`**.
5. **The object manager** turns the handle into the file object, checking that the handle is valid for this process.
6. **The I/O manager**:
   1. finds the target device object (the top of the device's stack);
   2. checks the IOCTL's **access bits** against the handle's granted access;
   3. because of `METHOD_BUFFERED`, allocates a nonpaged **system buffer** big enough for input and output, and copies the input in (none here);
   4. **allocates an IRP**, sets the major function `IRP_MJ_DEVICE_CONTROL`, and fills the current stack location with the code and buffer lengths;
   5. calls **`IoCallDriver(device, irp)`**, which calls `device->DriverObject->MajorFunction[IRP_MJ_DEVICE_CONTROL]`.
7. **TgCounter's `TgDispatchDeviceControl`** runs on the same app thread. It reads the code from its stack location, increments the counter, writes 4 bytes into the system buffer, sets `IoStatus`, and calls `IoCompleteRequest`.
8. **The I/O manager** completion: copies `IoStatus.Information` bytes (4) from the system buffer to the app's `value`, writes the status, and frees the system buffer and the IRP.
9. `NtDeviceIoControlFile` returns, then **the CPU** returns from the system call, kernel → user.
10. ntdll converts the status to a Win32 result; KERNELBASE returns `TRUE`, with `bytes = 4`.

**Pause and predict:** a real hardware driver can't always answer immediately. Its dispatch routine might start a hardware operation and return `STATUS_PENDING` without completing the IRP. Who completes it later, from where, and what happens to the app's thread in the meantime?

<details><summary>Answer</summary>The driver keeps the IRP and returns STATUS_PENDING. The app's thread, in a synchronous call, waits inside the I/O manager on the file object's event (Waiting state, no CPU used: 008 §6). Later, when the hardware interrupts, the driver's ISR → DPC calls IoCompleteRequest from DISPATCH_LEVEL, on whatever thread was interrupted (005). The I/O manager then finishes the completion (the copy into the app's buffer happens in the requesting thread's context) and wakes the waiting thread. That's how one request crosses from the app's thread to an interrupt and back.</details>

---

## 9. The same driver in KMDF, as a PnP device 🔵

### 9.1 What changes

KMDF (005, 006) replaces the raw dispatch table with **objects and callbacks**, and handles PnP, power and IRP bookkeeping for you. A sketch of the same counter (not compiled here: KMDF headers come with the WDK):

```c
#include <ntddk.h>
#include <wdf.h>
#include <initguid.h>
#include "tgcounter_ioctl.h"

// A device interface GUID: how user mode will find this device instead of a fixed name.
DEFINE_GUID(GUID_DEVINTERFACE_TGCOUNTER,
    0x6b4a5e2a, 0x3c1d, 0x4f7e, 0x9a, 0x11, 0x2f, 0x5c, 0x8d, 0x7e, 0x41, 0x90);  // made up

typedef struct _TG_CONTEXT { LONG Counter; } TG_CONTEXT;
WDF_DECLARE_CONTEXT_TYPE_WITH_NAME(TG_CONTEXT, TgGetContext)   // generates TgGetContext()

EVT_WDF_DRIVER_DEVICE_ADD       TgEvtDeviceAdd;
EVT_WDF_IO_QUEUE_IO_DEVICE_CONTROL TgEvtIoDeviceControl;

NTSTATUS DriverEntry(PDRIVER_OBJECT DriverObject, PUNICODE_STRING RegistryPath)
{
    WDF_DRIVER_CONFIG config;
    WDF_DRIVER_CONFIG_INIT(&config, TgEvtDeviceAdd);      // "call this when a device appears"
    return WdfDriverCreate(DriverObject, RegistryPath, WDF_NO_OBJECT_ATTRIBUTES,
                           &config, WDF_NO_HANDLE);
}

// PnP found a device for us (here: the root-enumerated Root\TgCounter).
NTSTATUS TgEvtDeviceAdd(WDFDRIVER Driver, PWDFDEVICE_INIT DeviceInit)
{
    UNREFERENCED_PARAMETER(Driver);
    WDF_OBJECT_ATTRIBUTES attrs;
    WDF_IO_QUEUE_CONFIG queueConfig;
    WDFDEVICE device;
    NTSTATUS status;

    WDF_OBJECT_ATTRIBUTES_INIT_CONTEXT_TYPE(&attrs, TG_CONTEXT);  // device extension, typed
    status = WdfDeviceCreate(&DeviceInit, &attrs, &device);       // FDO, attached to the stack
    if (!NT_SUCCESS(status)) return status;
    TgGetContext(device)->Counter = 0;

    status = WdfDeviceCreateDeviceInterface(device, &GUID_DEVINTERFACE_TGCOUNTER, NULL);
    if (!NT_SUCCESS(status)) return status;

    // One queue; KMDF delivers device-control requests to our callback, one at a time.
    WDF_IO_QUEUE_CONFIG_INIT_DEFAULT_QUEUE(&queueConfig, WdfIoQueueDispatchSequential);
    queueConfig.EvtIoDeviceControl = TgEvtIoDeviceControl;
    return WdfIoQueueCreate(device, &queueConfig, WDF_NO_OBJECT_ATTRIBUTES, WDF_NO_HANDLE);
}

VOID TgEvtIoDeviceControl(WDFQUEUE Queue, WDFREQUEST Request,
                          size_t OutputBufferLength, size_t InputBufferLength, ULONG IoControlCode)
{
    UNREFERENCED_PARAMETER(OutputBufferLength); UNREFERENCED_PARAMETER(InputBufferLength);
    TG_CONTEXT *ctx = TgGetContext(WdfIoQueueGetDevice(Queue));
    LONG *out;

    if (IoControlCode != IOCTL_TGCOUNTER_INCREMENT && IoControlCode != IOCTL_TGCOUNTER_GET) {
        WdfRequestComplete(Request, STATUS_INVALID_DEVICE_REQUEST);
        return;
    }
    NTSTATUS status = WdfRequestRetrieveOutputBuffer(Request, sizeof(LONG), (PVOID *)&out, NULL);
    if (!NT_SUCCESS(status)) { WdfRequestComplete(Request, status); return; }

    *out = (IoControlCode == IOCTL_TGCOUNTER_INCREMENT) ? InterlockedIncrement(&ctx->Counter)
                                                        : ctx->Counter;
    WdfRequestCompleteWithInformation(Request, STATUS_SUCCESS, sizeof(LONG));
}
```

### 9.2 WDM vs KMDF, side by side

| Concept | WDM TgCounter | KMDF TgCounter |
|---|---|---|
| Entry | `DriverEntry` fills `MajorFunction[]` | `DriverEntry` → `WdfDriverCreate` with an `EvtDeviceAdd` callback |
| Device object | `IoCreateDevice` in `DriverEntry` | `WdfDeviceCreate` in `EvtDeviceAdd`, once per device PnP finds |
| Per-device data | Device extension, cast by hand | Typed context (`TgGetContext`) |
| How user mode finds it | Symbolic link with a fixed name | **Device interface** (a GUID) |
| Request delivery | Raw IRP to the dispatch routine | `WDFREQUEST` from a **queue** to `EvtIoDeviceControl` |
| Buffers | `Irp->AssociatedIrp.SystemBuffer` | `WdfRequestRetrieveOutputBuffer` (checks the length for you) |
| Completion | `IoCompleteRequest` | `WdfRequestCompleteWithInformation` |
| PnP and power IRPs | Must be written by hand (hundreds of lines in a real WDM driver) | Handled by the framework; you get callbacks (`D0Entry`…) |

Under the hood, KMDF's own `DriverEntry` code fills the real `MajorFunction[]` table with **framework** functions that turn IRPs into `WDFREQUEST`s and route them to your queues. Same mechanism, one layer added.

### 9.3 Device interfaces: how user mode finds a PnP device

A fixed name like `\??\TgCounter` breaks when there are two devices. A PnP driver instead registers a **device interface**: a GUID meaning "devices that speak the TgCounter protocol". Windows creates a unique symbolic link per device instance, and user mode **enumerates** them:

```c
// user mode, sketch (cfgmgr32): get the list of present TgCounter devices
CM_Get_Device_Interface_List(&GUID_DEVINTERFACE_TGCOUNTER, NULL, buffer, len,
                             CM_GET_DEVICE_INTERFACE_LIST_PRESENT);
// buffer now holds paths like \\?\ROOT#SYSTEM#0000#{6b4a5e2a-...}  → pass one to CreateFile
```

That `\\?\ROOT#…#{guid}` path is the per-instance symbolic link. HID devices, serial ports and other device classes are all found this way.

### 9.4 The INF for the PnP version

A software-only PnP device is **root-enumerated**: there's no physical bus, so the PnP manager's own "root" bus driver creates its PDO. The INF matches a made-up hardware ID `Root\TgCounter`:

```ini
[Version]
Signature   = "$WINDOWS NT$"
Class       = System
ClassGuid   = {4d36e97d-e325-11ce-bfc1-08002be10318}   ; the "System devices" class
Provider    = %Provider%
CatalogFile = TgCounter.cat
DriverVer   = 10/22/2026,1.0.0.0
PnpLockdown = 1

[Manufacturer]
%Provider% = Models, NTamd64.10.0...16299, NTarm64.10.0...16299

[Models.NTamd64.10.0...16299]
%DeviceDesc% = TgCounter_Install, Root\TgCounter
[Models.NTarm64.10.0...16299]
%DeviceDesc% = TgCounter_Install, Root\TgCounter

[TgCounter_Install.NT]
CopyFiles = TgCounter_Files
[TgCounter_Files]
TgCounter.sys
[DestinationDirs]
DefaultDestDir = 13
[SourceDisksNames]
1 = %DiskName%
[SourceDisksFiles]
TgCounter.sys = 1

[TgCounter_Install.NT.Services]
AddService = TgCounter, 0x00000002, TgCounter_Service    ; creates the service key from §3.1

[TgCounter_Service]
ServiceType   = 1
StartType     = 3
ErrorControl  = 1
ServiceBinary = %13%\TgCounter.sys

[TgCounter_Install.NT.Wdf]
KmdfService = TgCounter, TgCounter_WdfSect
[TgCounter_WdfSect]
KmdfLibraryVersion = $KMDFVERSION$

[Strings]
Provider   = "Example"
DeviceDesc = "TgCounter Example Device"
DiskName   = "TgCounter Install Disk"
```

A root-enumerated device doesn't appear by itself, because there's no hardware to discover. A tool must **create** the devnode. With the WDK's `devcon`:

```
devcon install TgCounter.inf Root\TgCounter
```

This creates a devnode under the root bus with hardware ID `Root\TgCounter`, installs the INF on it, and PnP then loads the driver and calls `TgEvtDeviceAdd`. Device Manager shows it under *System devices*.

Map the configuration files to the mechanism:

| File / key | Produces | Read by |
|---|---|---|
| `TgCounter.inf` | The service key; the device's link to the service; the KMDF version requirement | Windows setup / PnP at install time |
| `TgCounter.cat` | Signed hashes of the package's files | Code integrity at install and load |
| `Services\TgCounter` registry key | Load instructions (`Type`, `Start`, `ImagePath`) | Service Control Manager / PnP / the kernel loader |
| `Enum\ROOT\…\0000` registry key | The devnode's identity, hardware ID, `Service` value | PnP manager |
| `TgCounter.sys` | The code | The kernel loader |
| `tgcounter_ioctl.h` | The IOCTL contract | Compilers on both sides; never Windows |

---

## 10. Drivers calling drivers 🟢

Everything the app did to reach TgCounter, a driver can do to reach another driver. There are three patterns.

### 10.1 Passing a request down (filters, and any upper layer)

A filter that doesn't care about a request hands the *same* IRP to the driver below it (WDM):

```c
NTSTATUS FilterPassThrough(PDEVICE_OBJECT DeviceObject, PIRP Irp)
{
    PFILTER_EXT ext = (PFILTER_EXT)DeviceObject->DeviceExtension;
    IoSkipCurrentIrpStackLocation(Irp);          // "the next driver can reuse my stack slot"
    return IoCallDriver(ext->LowerDevice, Irp);  // call the next driver's MajorFunction
}
```

`ext->LowerDevice` was saved in `AddDevice`, when the filter attached itself to the stack (`IoAttachDeviceToDeviceStack` returns the device below). This is how an IRP walks down a device stack (006 §4): each layer calls `IoCallDriver` on the next.

### 10.2 Sending your own request to another driver

A driver can build a brand-new IRP for a different device: for example, to ask another driver for information. In WDM:

```c
// sketch: synchronously send an IOCTL to another driver's device
KEVENT done; IO_STATUS_BLOCK iosb; PIRP irp;
KeInitializeEvent(&done, NotificationEvent, FALSE);
irp = IoBuildDeviceIoControlRequest(SOME_IOCTL, targetDevice,
                                    inBuf, inLen, outBuf, outLen,
                                    FALSE, &done, &iosb);        // the I/O manager builds the IRP
NTSTATUS status = IoCallDriver(targetDevice, irp);
if (status == STATUS_PENDING) {                                  // the other driver will finish later
    KeWaitForSingleObject(&done, Executive, KernelMode, FALSE, NULL);  // PASSIVE_LEVEL only!
    status = iosb.Status;
}
```

Note the wait: this is only legal at PASSIVE_LEVEL (005 §8). Sending a synchronous request from a DPC is a classic bug.

### 10.3 The KMDF way: I/O targets, and the touch driver's real case

KMDF wraps "a driver I send requests to" as an **I/O target** (`WDFIOTARGET`). This is exactly how a HID-over-I2C driver reaches the I2C controller (006 §5). Here's the pattern for an SPB (I2C/SPI) peripheral driver, sketched:

```c
// In EvtDevicePrepareHardware: PnP handed us resources, including an I2C "connection ID".
// 1. Turn the connection ID into a path the Resource Hub understands.
DECLARE_UNICODE_STRING_SIZE(path, RESOURCE_HUB_PATH_SIZE);
RESOURCE_HUB_CREATE_PATH_FROM_ID(&path, connIdLowPart, connIdHighPart);

// 2. Open it as an I/O target. Behind the scenes, this opens the I2C controller's device stack.
WDF_IO_TARGET_OPEN_PARAMS openParams;
WDF_IO_TARGET_OPEN_PARAMS_INIT_OPEN_BY_NAME(&openParams, &path, GENERIC_READ | GENERIC_WRITE);
WdfIoTargetCreate(device, WDF_NO_OBJECT_ATTRIBUTES, &ctx->SpbTarget);
WdfIoTargetOpen(ctx->SpbTarget, &openParams);

// Later, at PASSIVE_LEVEL (e.g. in a passive-level ISR or a work item):
// 3. Read 30 bytes from the device: becomes an IRP_MJ_READ to the I2C controller's driver.
WDF_MEMORY_DESCRIPTOR mem;
WDF_MEMORY_DESCRIPTOR_INIT_BUFFER(&mem, report, 30);
WdfIoTargetSendReadSynchronously(ctx->SpbTarget, NULL, &mem, NULL, NULL, &bytesRead);
```

This is the concrete form of "hidi2c sends a read request to the I2C controller driver": the touch driver's thread calls a framework function → the framework builds an IRP → `IoCallDriver` into the I2C controller's stack → the controller driver programs its registers → the transfer finishes (interrupts) → the IRP completes → the call returns with the bytes. (The real SPB interface also supports multi-step transfers through an IOCTL called `IOCTL_SPB_EXECUTE_SEQUENCE`. Treat the details as ⚫ until you write an SPB driver.)

---

## 11. Drivers calling the kernel, and the kernel calling drivers 🟢

### 11.1 Calling down: the kernel's function families

The kernel's exports are grouped by **prefix**, one per component. Knowing the prefixes makes any driver's import table readable at a glance:

| Prefix | Component | Examples |
|---|---|---|
| `Io` | I/O manager: devices, IRPs, interrupts | `IoCreateDevice`, `IoCallDriver`, `IoCompleteRequest`, `IoConnectInterruptEx` |
| `Ke` | Kernel core: scheduling, synchronization, DPCs, IRQL | `KeWaitForSingleObject`, `KeAcquireSpinLock`, `KeInsertQueueDpc`, `KeRaiseIrql` |
| `Ex` | Executive support: pool memory, locks, work items | `ExAllocatePool2`, `ExFreePoolWithTag`, `ExAcquireResourceExclusiveLite` |
| `Mm` | Memory manager | `MmMapIoSpaceEx` (map device registers), `MmGetSystemAddressForMdlSafe` |
| `Ob` | Object manager | `ObReferenceObject`, `ObDereferenceObject` |
| `Ps` | Processes and threads | `PsCreateSystemThread`, `PsSetCreateProcessNotifyRoutineEx` |
| `Po` | Power manager | `PoRequestPowerIrp`, `PoSetPowerState` |
| `Rtl` | Run-time library (helpers) | `RtlInitUnicodeString`, `RtlCopyMemory` |
| `Zw` / `Nt` | System services callable from kernel code | `ZwCreateFile`, `ZwQueryValueKey` (read the registry) |
| `Hal` / `READ_REGISTER_*` | Hardware access | `READ_REGISTER_ULONG` (MMIO), `HalGetBusData` (old) |
| `Wdf` | KMDF (through the framework loader) | `WdfDeviceCreate`, `WdfRequestComplete`, `WdfIoTargetOpen` |

So, for example, "a driver maps its device registers" means it calls `MmMapIoSpaceEx` with the physical address PnP gave it, and gets a kernel virtual address back. That's the answer to your earlier question about register pointers under an OS (003 recall, 10-18).

### 11.2 Calling up: the kernel calls drivers through registered pointers

The kernel calls into a driver **only** through function pointers the driver handed over:

| The driver registered… | With… | The kernel calls it when… |
|---|---|---|
| Dispatch routines | `MajorFunction[]` (WDM) or queues (KMDF) | An IRP arrives |
| `AddDevice` / `EvtDriverDeviceAdd` | The driver object / `WdfDriverCreate` | PnP finds a device for it |
| ISR, DPC | `IoConnectInterruptEx`, `KeInitializeDpc` / `WdfInterruptCreate` | Its interrupt fires / the DPC queue drains |
| Completion routine | `IoSetCompletionRoutine` | An IRP it sent down finishes |
| Notify callbacks | `PsSetCreateProcessNotifyRoutineEx`, registry callbacks (`CmRegisterCallbackEx`) | A process starts or exits, or a registry operation happens (how security products observe the system) |
| Unload | `DriverUnload` | The driver is stopped |

That's the complete answer to "how does the kernel run driver code?": **it stores pointers, and calls them when the matching event happens.** Lecture 005's ISR, DPC and work item are just three more rows in this table.

---

## 12. Seeing all of it in WinDbg 🔵

With TgCounter loaded on a test VM (§13) and a debugger attached (or local kernel debugging for the read-only commands). Outputs are illustrative shapes.

| Command | What it proves |
|---|---|
| `lm m TgCounter` | The `.sys` is mapped into kernel space (start and end address) |
| `!drvobj TgCounter 2` | The driver object and its **dispatch table**: `IRP_MJ_CREATE → TgCounter+0x…`, `IRP_MJ_DEVICE_CONTROL → TgCounter+0x…`, everything else → `nt!IopInvalidDeviceRequest` |
| `!devobj \Device\TgCounter` | The device object, its type, its extension |
| `!object \GLOBAL??\TgCounter` | The symbolic link and its target `\Device\TgCounter` |
| `bp TgCounter!TgDispatchDeviceControl`, then run `tgclient.exe`, then `k` | The whole call path of §8, as a real stack |

The stack at that breakpoint would look like this (illustrative, newest on top):

```
TgCounter!TgDispatchDeviceControl
nt!IofCallDriver
nt!IopSynchronousServiceTail
nt!IopXxxControlFile
nt!NtDeviceIoControlFile
nt!KiSystemServiceCopyEnd           ← the system-call boundary
ntdll!NtDeviceIoControlFile          ← user mode from here down
KERNELBASE!DeviceIoControl
KERNEL32!DeviceIoControlImplementation
tgclient!main
```

Read it bottom-up (001 §4.2) and you're reading §8's numbered steps.

---

## 13. Lab: load it for real

On a **Windows VM** with Secure Boot **off** (test signing requires it):

1. **Build** with Visual Studio + WDK: create an *Empty WDM Driver* project, add `tgcounter.c` and the header, and build x64 (or ARM64 for an Arm VM). Build `tgclient.c` as a console app. (MinGW also builds it, as done for this lecture, but the WDK is the supported toolchain.)
2. **Enable test signing:** `bcdedit /set testsigning on`, then reboot (a "Test Mode" watermark appears).
3. **Test-sign the driver:**
   - create a code-signing certificate in PowerShell: `New-SelfSignedCertificate -Type CodeSigningCert -Subject "CN=TgTest" -CertStoreLocation Cert:\CurrentUser\My`;
   - sign: `signtool sign /fd sha256 /a /s My /n TgTest TgCounter.sys`;
   - follow Microsoft's test-signing documentation for trusting the test certificate on the machine.
4. **See its messages:** `DbgPrint` output is filtered by default. Attach WinDbg, or run Sysinternals DebugView with *Capture Kernel* and set the debug print filter as its documentation describes.
5. **Load:**
   ```
   copy TgCounter.sys C:\drivers\
   sc create TgCounter type= kernel start= demand binPath= C:\drivers\TgCounter.sys
   sc start TgCounter
   ```
   Expect `TgCounter: loaded from \REGISTRY\MACHINE\SYSTEM\ControlSet001\Services\TgCounter` in the debug output.
6. **Run** `tgclient.exe`: expect INCREMENT → 1, 2, 3. Run it again: 4, 5, 6. The counter lives in the driver, not in the app.
7. **Explore:** `regedit` → `HKLM\SYSTEM\CurrentControlSet\Services\TgCounter` (§3.1). Sysinternals WinObj → `\Device\TgCounter` and `\GLOBAL??\TgCounter` (§7.1).
8. **Unload and clean up:** `sc stop TgCounter` ("unloaded" message), `sc delete TgCounter`.

**Predict before step 6:** what does `tgclient.exe` print if you run it *before* `sc start`? (You already know from §7: error 2.)

---

## 14. The Linux equivalent, briefly 🔵

| Concept | Windows | Linux |
|---|---|---|
| Driver file | `.sys`, PE format, native subsystem | `.ko` kernel module, ELF format |
| Entry / exit | `DriverEntry` / `DriverUnload` | `module_init(fn)` / `module_exit(fn)` |
| Imports | From `ntoskrnl.exe` (`Io…`, `Ke…`) | Exported kernel symbols (`EXPORT_SYMBOL`), checked by `modpost` |
| Load configuration | Service key; `sc create` / INF | `insmod` / `modprobe`; auto-load by device ID through `modules.alias` |
| Dispatch table | `MajorFunction[]` | `struct file_operations` (`.open`, `.read`, `.unlocked_ioctl`, …) |
| User-visible name | Symbolic link / device interface | Device node in `/dev` (e.g. `misc_register` creates `/dev/tgcounter`) |
| Control codes | `CTL_CODE(type, function, method, access)` | `_IO`, `_IOR`, `_IOW`, `_IOWR(type, nr, datatype)` |
| Copying user buffers | I/O manager (`METHOD_BUFFERED`) or the driver (`NEITHER`) | The driver calls `copy_from_user` / `copy_to_user` explicitly |
| Debug print | `DbgPrint` → debugger / DebugView | `printk` → `dmesg` |

The shape is the same on both: a module of functions, an entry point that registers a table of handlers, a name user space can open, and numeric control codes for custom operations. The biggest difference is that Linux always makes the driver copy user buffers itself.

---

## 15. Misconceptions

| You might think | Reality | Why it matters |
|---|---|---|
| A `.sys` file is a special, opaque kind of binary | It's a PE file like any `.exe`/`.dll`, with the native subsystem and imports from the kernel | You can inspect it with ordinary tools (`dumpbin`, `objdump`) |
| A driver runs continuously, like a program with a main loop | `DriverEntry` registers callbacks and returns; afterwards code runs only when called | "What is the driver doing?" = "who called which of its functions?" |
| The I/O manager "talks to" drivers in some abstract way | It calls the driver's function pointer: `MajorFunction[IRP_MJ_…](device, irp)` | Concrete, debuggable with a breakpoint |
| Apps call drivers directly | Apps make a system call; the I/O manager validates, builds an IRP and calls the driver | Access checks and buffering happen before the driver runs |
| Each request gets its own thread | Dispatch runs on the caller's thread; completion may run on an interrupted thread (DPC) | Matters for IRQL rules and for what memory is reachable |
| Drivers talk to each other through shared memory | They send IRPs (`IoCallDriver`, I/O targets) down or across stacks | The `>` in `!irp` shows exactly where a request is |
| The IOCTL access bits are just documentation | The I/O manager enforces them before calling the driver | Free security; get them right |
| `METHOD_NEITHER` is just faster | It hands the driver raw user pointers: the riskiest choice | Prefer BUFFERED / DIRECT unless you really need it |

---

## 16. Saying it precisely

- "A `.sys` file is a PE image with the native subsystem. Its import table lists kernel exports like `IoCreateDevice` and `IofCompleteRequest`. The kernel maps it, resolves those imports, creates a driver object and calls `DriverEntry` once."
- "What loads it is configuration: a service key under `Services` with `Type`, `Start` and `ImagePath`, created by `sc create` for a legacy driver or by an INF's `AddService` for a PnP driver."
- "`DriverEntry` only registers: the dispatch table, an unload routine, a device object and a symbolic link, or in KMDF an `EvtDeviceAdd` callback, a typed context, a device interface and a queue."
- "`DeviceIoControl` goes through ntdll's system call to `NtDeviceIoControlFile`. The I/O manager resolves the handle to the file object and device, checks the IOCTL's access bits, buffers per the method, builds an IRP and calls the driver's `IRP_MJ_DEVICE_CONTROL` routine. When the driver completes the IRP, the I/O manager copies the output back."
- "Drivers reach other drivers the same way: forward the IRP with `IoCallDriver`, or in KMDF send requests to an I/O target. That's how an HID-over-I2C driver reads its device through the I2C controller's stack."

---

## 17. Self-check

1. What file format is a `.sys`, and what marks it as a driver rather than an app?
<details><summary>Answer</summary>PE (Portable Executable), the same as .exe/.dll. Its subsystem is "native", its entry point is DriverEntry, and it imports from ntoskrnl.exe (and HAL, the KMDF loader…) instead of user-mode DLLs.</details>

2. TgCounter's import table lists `IofCompleteRequest`, not `IoCompleteRequest`, and no `InterlockedIncrement`. Why?
<details><summary>Answer</summary><code>IoCompleteRequest</code> is a macro around the exported <code>IofCompleteRequest</code>. <code>InterlockedIncrement</code> compiles to an atomic CPU instruction (an intrinsic), so nothing is imported.</details>

3. Name the registry values that tell Windows how to load a driver, and what each means.
<details><summary>Answer</summary>Under Services\&lt;name&gt;: Type (1 = kernel driver), Start (0 boot … 3 demand, 4 disabled), ErrorControl (how serious a load failure is), ImagePath (the file).</details>

4. List the loading steps from `sc start` to a running driver.
<details><summary>Answer</summary>The SCM asks the kernel (NtLoadDriver) → code integrity checks the signature → the image is mapped into kernel space, relocated, imports resolved → a driver object is created → DriverEntry(DriverObject, RegistryPath) is called once at PASSIVE_LEVEL → success keeps it loaded.</details>

5. What does `DriverObject->MajorFunction[IRP_MJ_DEVICE_CONTROL] = TgDispatchDeviceControl;` mean in practice?
<details><summary>Answer</summary>When an IRP with major function DEVICE_CONTROL is sent to one of this driver's device objects, IoCallDriver will literally call TgDispatchDeviceControl(device, irp).</details>

6. Trace how `CreateFile("\\\\.\\TgCounter")` reaches the driver.
<details><summary>Answer</summary><code>\\.\</code> → NT path <code>\??\TgCounter</code> → the object manager follows the symbolic link to <code>\Device\TgCounter</code> → the I/O manager creates a FILE_OBJECT and sends IRP_MJ_CREATE to the driver → on success, a handle to the file object goes into the process's handle table.</details>

7. Decode `0x80006004`.
<details><summary>Answer</summary>Device type 0x8000, access 1 (FILE_READ_ACCESS), function 0x801, method 0 (METHOD_BUFFERED): IOCTL_TGCOUNTER_GET.</details>

8. Who checks an IOCTL's access bits, and when?
<details><summary>Answer</summary>The I/O manager, in NtDeviceIoControlFile, before the driver is called, against the access the handle was opened with.</details>

9. Compare METHOD_BUFFERED and METHOD_NEITHER.
<details><summary>Answer</summary>BUFFERED: the I/O manager copies input into a kernel system buffer and copies the output back, so the driver never touches user memory. NEITHER: the driver receives raw user pointers and must validate and access them safely itself, which is risky.</details>

10. On which thread does TgDispatchDeviceControl run, and at what IRQL?
<details><summary>Answer</summary>On the calling application's thread (now in kernel mode, after the system call), in its process context, at PASSIVE_LEVEL.</details>

11. A dispatch routine returns STATUS_PENDING. Who completes the IRP later, and what is the app's thread doing meanwhile?
<details><summary>Answer</summary>The driver completes it later, typically from its DPC after the hardware interrupts. The app's thread waits (in the I/O manager, synchronous I/O) without using CPU, and is woken at completion.</details>

12. Give three differences between the WDM and KMDF versions.
<details><summary>Answer</summary>Any three of: the MajorFunction table vs queues and callbacks; the device created in DriverEntry vs in EvtDeviceAdd per PnP device; the device extension vs a typed context; a fixed symbolic link vs a device interface GUID; raw IRPs vs WDFREQUEST; IoCompleteRequest vs WdfRequestCompleteWithInformation; hand-written PnP/power vs framework-handled.</details>

13. How does a filter driver pass a request it doesn't care about to the next driver?
<details><summary>Answer</summary><code>IoSkipCurrentIrpStackLocation(Irp); return IoCallDriver(lowerDevice, Irp);</code>, where lowerDevice was saved from IoAttachDeviceToDeviceStack in AddDevice.</details>

14. In KMDF, how does an I2C peripheral driver send a read to the I2C controller?
<details><summary>Answer</summary>It turns its connection-ID resource into a Resource Hub path (RESOURCE_HUB_CREATE_PATH_FROM_ID), opens a WDFIOTARGET on it, and sends requests (e.g. WdfIoTargetSendReadSynchronously). The framework builds IRPs and IoCallDrivers them into the controller's stack.</details>

15. Match prefixes to components: Io, Ke, Ex, Mm, Ps, Po.
<details><summary>Answer</summary>Io = I/O manager; Ke = kernel core (scheduling, sync, DPCs, IRQL); Ex = executive support (pool, locks, work items); Mm = memory manager; Ps = processes and threads; Po = power manager.</details>

16. Complete the sentence: "The kernel runs driver code only…"
<details><summary>Answer</summary>…by calling function pointers the driver registered (dispatch routines, AddDevice, ISR/DPC, completion routines, notify callbacks, Unload) when the matching event happens.</details>

---

## Sources

Checked 2026-10-22.

- Microsoft Learn: Writing a DriverEntry routine; DRIVER_OBJECT (`MajorFunction`, `DriverUnload`); IRP major function codes; `IoCreateDevice`, `IoCreateSymbolicLink`, `IoCompleteRequest`, `IoCallDriver`, `IoSkipCurrentIrpStackLocation`, `IoBuildDeviceIoControlRequest`.
- Microsoft Learn: Defining I/O control codes (`CTL_CODE` layout; vendor ranges for device types and function codes); Buffer descriptions for I/O control codes (`METHOD_BUFFERED`, `METHOD_IN_DIRECT` / `METHOD_OUT_DIRECT`, `METHOD_NEITHER`).
- Microsoft Learn: Introduction to MS-DOS device names (`\??`, `\GLOBAL??`, symbolic links); Device interface classes; `CM_Get_Device_Interface_List`.
- Microsoft Learn: KMDF (`WdfDriverCreate`, `WdfDeviceCreate`, `WdfDeviceCreateDeviceInterface`, `WdfIoQueueCreate`, `EvtIoDeviceControl`, `WdfRequestRetrieveOutputBuffer`, `WdfRequestCompleteWithInformation`; I/O targets, `WdfIoTargetOpen`, `WdfIoTargetSendReadSynchronously`); SPB peripheral drivers and connection IDs (`RESOURCE_HUB_CREATE_PATH_FROM_ID`); the KMDF Echo sample as a root-enumerated reference; DevCon `install`.
- Microsoft Learn: `sc create` syntax; service registry entries (`Type`, `Start`, `ErrorControl`, `ImagePath`); test signing (`bcdedit /set testsigning on`, `signtool`); `IoCreateDeviceSecure` and SDDL for device objects.
- *Windows Internals, 7th ed., Part 1*: system service dispatching, the I/O system, driver loading.

**What was actually run for this lecture (2026-10-22):** `tgcounter.c` compiled and linked into a native-subsystem PE `TgCounter.sys` with MinGW-w64 GCC against the MinGW DDK headers (`-Wall -Wextra`, no warnings after the `0x8000u` fix); `objdump` produced the header, section and import listings in §2. `tgclient.c` compiled the same way and ran under Wine 9.0, producing the §7 output (the IOCTL values and the expected "not loaded" failure). **Not run:** loading the driver into a Windows kernel (needs a test-signed Windows VM, §13), the KMDF version (needs the WDK), the INF and `devcon` steps, and the WinDbg outputs in §12, which are illustrative.
