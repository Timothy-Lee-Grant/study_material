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
