// tgcounter.c - Phase 5 lab version of the TgCounter WDM driver (lecture 009).
// Same as before, plus two DELIBERATE bugs reachable through lab-only IOCTLs:
//   IOCTL_TGCOUNTER_CRASH              NULL write at DISPATCH_LEVEL  (always crashes)
//   IOCTL_TGCOUNTER_PAGED_AT_DISPATCH  paged-pool read under a spin lock (crashes reliably only under Driver Verifier)
// Never ship code like this. It exists so you can practice lectures 001-004 on your own bug.
#include <ntddk.h>
#include "tgcounter_ioctl.h"

typedef struct _TG_EXTENSION {          // per-device state, lives in nonpaged memory
    LONG Counter;
} TG_EXTENSION, *PTG_EXTENSION;

// A small PAGED allocation, made in DriverEntry. Touching it at DISPATCH_LEVEL is the bug in lab 5.4.
static PLONG g_PagedValue = NULL;
#define TG_POOL_TAG 'gTgT'              // shows as "TgTg" in pool tools (bytes are stored reversed)

// A spin lock. Acquiring it raises the CPU to DISPATCH_LEVEL (lecture 005 §6), and it's a real
// call into the kernel, which Driver Verifier intercepts (that's what triggers "Force IRQL checking").
static KSPIN_LOCK g_Lock;

static NTSTATUS CompleteIrp(PIRP Irp, NTSTATUS status, ULONG_PTR bytesReturned)
{
    Irp->IoStatus.Status = status;
    Irp->IoStatus.Information = bytesReturned;
    IoCompleteRequest(Irp, IO_NO_INCREMENT);
    return status;
}

static NTSTATUS TgDispatchCreateClose(PDEVICE_OBJECT DeviceObject, PIRP Irp)
{
    UNREFERENCED_PARAMETER(DeviceObject);
    return CompleteIrp(Irp, STATUS_SUCCESS, 0);
}

static NTSTATUS TgDispatchDeviceControl(PDEVICE_OBJECT DeviceObject, PIRP Irp)
{
    PTG_EXTENSION ext = (PTG_EXTENSION)DeviceObject->DeviceExtension;
    PIO_STACK_LOCATION stack = IoGetCurrentIrpStackLocation(Irp);
    ULONG code   = stack->Parameters.DeviceIoControl.IoControlCode;
    ULONG outLen = stack->Parameters.DeviceIoControl.OutputBufferLength;
    PVOID buffer = Irp->AssociatedIrp.SystemBuffer;
    KIRQL oldIrql;
    LONG value;

    if (outLen < sizeof(LONG))
        return CompleteIrp(Irp, STATUS_BUFFER_TOO_SMALL, 0);

    switch (code) {
    case IOCTL_TGCOUNTER_INCREMENT:
        value = InterlockedIncrement(&ext->Counter);
        break;

    case IOCTL_TGCOUNTER_GET:
        value = ext->Counter;
        break;

    case IOCTL_TGCOUNTER_CRASH: {
        // BUG ON PURPOSE (lab 5.3). Raise to DISPATCH_LEVEL, like a DPC or a spin-lock holder,
        // then write through a NULL pointer. The page-fault handler can't help at this IRQL.
        volatile LONG *bad = NULL;
        DbgPrint("TgCounter: CRASH requested, raising to DISPATCH_LEVEL and writing to NULL\n");
        KeRaiseIrql(DISPATCH_LEVEL, &oldIrql);
        *bad = 0x5A5A;                      // <- the faulting instruction
        KeLowerIrql(oldIrql);               // never reached
        value = 0;
        break;
    }

    case IOCTL_TGCOUNTER_PAGED_AT_DISPATCH:
        // BUG ON PURPOSE (lab 5.4). g_PagedValue is in PAGED pool. Reading it while holding a spin lock
        // (so at DISPATCH_LEVEL) is illegal, but it only crashes if the page happens to be out of RAM
        // at that moment. Driver Verifier's "Force IRQL checking" pushes pageable memory out when the
        // driver takes a spin lock, so under Verifier it crashes every time.
        if (g_PagedValue == NULL)
            return CompleteIrp(Irp, STATUS_INSUFFICIENT_RESOURCES, 0);
        KeAcquireSpinLock(&g_Lock, &oldIrql);   // now at DISPATCH_LEVEL (holding a spin lock)
        value = *g_PagedValue;                  // <- illegal at DISPATCH_LEVEL
        KeReleaseSpinLock(&g_Lock, oldIrql);
        break;

    default:
        return CompleteIrp(Irp, STATUS_INVALID_DEVICE_REQUEST, 0);
    }

    *(LONG *)buffer = value;
    return CompleteIrp(Irp, STATUS_SUCCESS, sizeof(LONG));
}

static VOID TgUnload(PDRIVER_OBJECT DriverObject)
{
    UNICODE_STRING link;
    RtlInitUnicodeString(&link, TGCOUNTER_LINK_NAME);
    IoDeleteSymbolicLink(&link);
    IoDeleteDevice(DriverObject->DeviceObject);
    if (g_PagedValue != NULL) {
        ExFreePoolWithTag(g_PagedValue, TG_POOL_TAG);
        g_PagedValue = NULL;
    }
    DbgPrint("TgCounter: unloaded\n");
}

NTSTATUS DriverEntry(PDRIVER_OBJECT DriverObject, PUNICODE_STRING RegistryPath)
{
    UNICODE_STRING devName, linkName;
    PDEVICE_OBJECT device;
    NTSTATUS status;

    RtlInitUnicodeString(&devName, TGCOUNTER_DEVICE_NAME);
    RtlInitUnicodeString(&linkName, TGCOUNTER_LINK_NAME);
    KeInitializeSpinLock(&g_Lock);

    // The paged allocation for lab 5.4 (ExAllocatePool2 zero-fills it; then store 42).
    g_PagedValue = (PLONG)ExAllocatePool2(POOL_FLAG_PAGED, sizeof(LONG), TG_POOL_TAG);
    if (g_PagedValue != NULL)
        *g_PagedValue = 42;

    status = IoCreateDevice(DriverObject, sizeof(TG_EXTENSION), &devName,
                            FILE_DEVICE_TGCOUNTER, FILE_DEVICE_SECURE_OPEN,
                            FALSE, &device);
    if (!NT_SUCCESS(status)) goto fail;
    ((PTG_EXTENSION)device->DeviceExtension)->Counter = 0;

    status = IoCreateSymbolicLink(&linkName, &devName);
    if (!NT_SUCCESS(status)) { IoDeleteDevice(device); goto fail; }

    DriverObject->MajorFunction[IRP_MJ_CREATE]         = TgDispatchCreateClose;
    DriverObject->MajorFunction[IRP_MJ_CLOSE]          = TgDispatchCreateClose;
    DriverObject->MajorFunction[IRP_MJ_DEVICE_CONTROL] = TgDispatchDeviceControl;
    DriverObject->DriverUnload                         = TgUnload;

    DbgPrint("TgCounter: loaded (phase 5 build) from %wZ\n", RegistryPath);
    return STATUS_SUCCESS;

fail:
    if (g_PagedValue != NULL) { ExFreePoolWithTag(g_PagedValue, TG_POOL_TAG); g_PagedValue = NULL; }
    return status;
}
