2026_11_11_00_45-(IRPs-How-An-IO-Request-Travels)

# 019 — IRPs: How an I/O Request Is Built, Where It Lives, and How It Travels Through Drivers

> **For:** Timothy · **Date:** 2026-11-11
> **Prerequisites:** none. This lecture is self-contained: every structure, every piece of code and every debugger output it uses is shown here. You don't need to have built or run anything.
> **Why this lecture:** while listening to the crash-dump audio lecture, you heard that a 0x9F's parameter four "is the blocked IRP", that `!irp` shows "which driver is holding it", and that a hang is often "a request a driver marked pending and never completed". You asked for the whole pipeline: who creates an IRP, where in memory it lives, how it gets triggered, whether it sits on a queue or is signaled by a flag, and which components touch it. You also said the debugger feels like a wall of memory addresses, and asked for a way to *see* how the pieces connect. So this lecture does two jobs: (1) the life of an IRP, and (2) how to read memory addresses in a debugger, using the IRP as the worked example.

---

## Core ideas (the answer key)

1. **An IRP (I/O Request Packet) is a block of kernel memory that describes one I/O request.** It's a data structure, not a running thing. Whoever holds a pointer to it can read it, change it, pass it on, or finish it.
2. **The I/O manager creates the IRP** when a program calls `ReadFile`, `WriteFile` or `DeviceIoControl`. The Plug and Play manager, the power manager, and drivers themselves can create IRPs too.
3. **One allocation holds a fixed header plus an array of "stack locations"**, one per driver in the device's stack. On 64-bit Windows the header is `0xD0` bytes and each stack location is `0x48` bytes. It's allocated from **nonpaged** memory, usually from a per-processor recycling list.
4. **The header says *who asked and how it ends*** (requesting thread, buffers, final status). **Each stack location says *what this one driver must do*** (operation code, parameters, which device, and an optional completion routine).
5. **Handing an IRP to a driver is a plain function call.** `IoCallDriver` moves the "current" pointer to the next stack location and calls the driver's dispatch routine through the driver's `MajorFunction` table. No queue, no flag, no scheduler is involved.
6. **A driver has exactly three choices:** complete it now (`IoCompleteRequest`), pass it down (`IoCallDriver` to the next driver), or park it and return `STATUS_PENDING` (put it on its own queue and finish later, usually from a DPC after the device interrupts).
7. **Completion runs the stack in reverse.** `IoCompleteRequest` walks the stack locations back up, calling each driver's completion routine. Then the I/O manager copies results back to the program, in the requesting thread's context (often through an APC), and frees the IRP.
8. **The only list every IRP is on is its thread's IRP list.** That's how Windows cancels a thread's outstanding I/O when the thread exits. Driver queues are optional and private to each driver.
9. **In a debugger, every address is the number of one byte.** A structure is a block starting at an address. A field is "block address + offset". A pointer field holds the address of another block. Reading memory means: get an address → lay a type over it (`dt`) → follow a pointer field → repeat.
10. **You can recognize many values on sight.** `ffff…` is kernel memory, small numbers near zero are user memory, `0` is NULL, two identical pointers in a row are usually a list with zero or one entries, and the first two bytes of many kernel objects are a type code (an IRP starts with `6`).

---

## Table of Contents

0. [Direct answers to your questions](#0-direct-answers-to-your-questions)
1. [How to read memory addresses (the skill under everything else)](#1-how-to-read-memory-addresses)
2. [The structures involved, and how they point to each other](#2-the-structures-involved-and-how-they-point-to-each-other)
3. [The shape of an IRP in memory](#3-the-shape-of-an-irp-in-memory)
4. [The full trip: one DeviceIoControl call, step by step](#4-the-full-trip-one-deviceiocontrol-call-step-by-step)
5. [The same trip seen in WinDbg, byte by byte](#5-the-same-trip-seen-in-windbg-byte-by-byte)
6. [Queues, lists and flags: what "pending" actually means](#6-queues-lists-and-flags)
7. [The asynchronous version: a real device with an interrupt](#7-the-asynchronous-version-a-real-device-with-an-interrupt)
8. [Stacks of drivers: passing down and completing back up](#8-stacks-of-drivers-passing-down-and-completing-back-up)
9. [Where IRPs show up when things go wrong](#9-where-irps-show-up-when-things-go-wrong)
10. [Misconceptions](#10-misconceptions)
11. [Self-check questions](#11-self-check-questions)
12. [Sources](#12-sources)

---

## 0. Direct answers to your questions

| Your question | Short answer | Where it's explained |
|---|---|---|
| **Who creates it?** | For a program's request, the **I/O manager** (part of the kernel) inside the system call. The PnP manager creates `IRP_MJ_PNP` IRPs, the power manager creates `IRP_MJ_POWER` IRPs, and drivers can build their own with `IoAllocateIrp` to send requests to other drivers. | §4 step 3, §8 |
| **Where in memory does it live?** | In **kernel, nonpaged** memory: an address that starts with `ffff…`. It's one allocation: a `0xD0`-byte header followed by `0x48` bytes per stack location. Small IRPs come from a per-processor recycling list (a "lookaside list"); bigger ones come straight from nonpaged pool with the tag `Irp `. | §3 |
| **How does it get triggered?** | Nothing "triggers" it in the sense of a signal. The I/O manager fills it in and then **calls** the driver's function directly, on the same thread that made the system call, passing the IRP's address as an argument. | §4 steps 4–5 |
| **Is it put on a queue, or is there a flag?** | Both exist, but neither is how it's *delivered*. It's always linked into the **requesting thread's IRP list** (for cancellation). A driver *may* put it on its **own** queue when it can't finish right away; it then marks it pending (a bit in the stack location) and returns `STATUS_PENDING`. Flags in the IRP describe it (buffered or not, read or write, pending returned, cancelled); they don't wake anyone up. | §6 |
| **Which components touch it?** | The program (indirectly), ntdll (the system call), the I/O manager (build, dispatch, final copy-back), the object manager (handle → file object), each driver in the device stack, the interrupt and DPC machinery (async completion), the APC machinery (delivering the result to the right thread), and the memory manager (if the request uses locked user pages). | §4, §7 |
| **How do I use the debugger with all these addresses?** | Treat every address as "the start of some block". Ask what type the block is, lay that type over it with `dt`, read the pointer fields, and follow them. §1 gives the method; §5 does it on a real-shaped IRP. | §1, §5 |

---

## 1. How to read memory addresses

This section is the foundation. Once you can do this, `!irp`, `!devstack` and the raw dumps in the rest of the lecture stop looking like noise.

### 1.1 What an address stands for

Memory is a very long row of bytes. Each byte has a number, its **address**. An address is just that: the number of one byte.

```
address:   ...  1000  1001  1002  1003  1004  1005  1006  1007  ...
byte:      ...   06    00    18    01    00    00    00    00   ...
```

Everything else is built from this one idea:

| Term | What it stands for |
|---|---|
| **Address** | The number of one byte. |
| **Block** (an allocation, an object, a structure) | A run of consecutive bytes. We refer to it by the address of its **first** byte. |
| **Field** | A fixed-size piece of a block, found at **block address + offset**. The offset is fixed by the type. |
| **Pointer** (a field of pointer type) | A field whose value is **the address of another block**. 8 bytes on 64-bit Windows. |
| **Type** (like `nt!_IRP`) | A layout: which field sits at which offset, and how big each is. It's a template, not data. |

So when you see `Irp->IoStatus.Status`, the compiler turns it into: take the value of `Irp` (an address), add the offset of `IoStatus.Status` (`0x30`), and read 4 bytes there. The debugger does the same thing in reverse when it shows you a structure.

### 1.2 How WinDbg writes a 64-bit address

A 64-bit address is 16 hex digits. WinDbg puts a backtick in the middle so you can read it: `ffffb10e`4c2f7a20` is the number `0xffffb10e4c2f7a20`. The backtick is only for display. You can type addresses with or without it.

### 1.3 Telling what kind of address you're looking at

Windows splits the 64-bit address space into a **user half** (low addresses) and a **kernel half** (high addresses). On both x64 and Arm64 only 48 bits are actually used, so a valid address either starts with lots of zeros (user) or lots of `f`s (kernel).

```
0x00000000`00000000 ─┐
                     │  user space: each process has its OWN copy of this half
   0000004f`a3cff7c4 │  ← e.g. a local variable on a program's stack
   00007ff7`12340000 │  ← e.g. a program's .exe code
0x00007fff`ffffffff ─┘
        (huge unused gap: addresses here are invalid)
0xffff8000`00000000 ─┐
   ffffb10e`4c2f7a20 │  ← kernel dynamic memory: pool allocations (IRPs, device objects…)
   fffff800`67600000 │  ← kernel and driver images (code), e.g. ntoskrnl
0xffffffff`ffffffff ─┘  kernel space: ONE copy, shared by every process
```

A decoder ring for values you'll see in dumps:

| You see | It's probably |
|---|---|
| `00000000`00000000` | NULL, or a zero count/flag |
| a small number like `00000000`00000070` | a count, a length, a set of flags, or an enum |
| `0000xxxx`xxxxxxxx` (top part small, at most `00007fff…`) | a **user-mode** pointer (only meaningful in the right process) |
| `ffffXXXX`xxxxxxxx` (`ffff8…` to `ffffe…`) | a **kernel pointer** to dynamically allocated memory (pool) |
| `fffff80x`xxxxxxxx` | a pointer **into code** or static data of the kernel or a driver; `ln` will name it |
| a value close to the block's own address | a **self-reference**: a pointer to another part of the same block |
| the same pointer twice in a row | a `LIST_ENTRY` (a two-pointer list link, §1.6) for a list with **zero or one** entries |

These address ranges come from how Windows lays out memory today. KASLR (address randomization) changes the exact numbers on every boot; the ranges stay roughly the same.

### 1.4 Little-endian: why bytes look backwards

Both x64 and Arm64 (as Windows runs it) store multi-byte numbers **least significant byte first**. The 8-byte number `0x0000000001180006` sits in memory as:

```
offset:   +0  +1  +2  +3  +4  +5  +6  +7
byte:     06  00  18  01  00  00  00  00
          └─┬──┘  └─┬──┘
      Type = 0x0006  Size = 0x0118     (two 2-byte fields, each stored low byte first)
```

That's why `db` (show bytes) and `dq` (show 8-byte numbers) display the same memory differently. Use `dq` for pointers and `dt` for structures. Use `db` only for raw byte data (buffers, strings).

### 1.5 The debugger commands, by the question they answer

| Question | Command | What it does |
|---|---|---|
| What raw values are at this address? | `dq <addr>` / `dd <addr>` / `db <addr>` | Show memory as 8-byte, 4-byte or 1-byte values. No interpretation. |
| What does this block mean as type T? | `dt nt!_IRP <addr>` | Lays the type's template over the bytes and prints each field with its offset. |
| …and just one nested part? | `dt nt!_IRP <addr> Tail.Overlay.` | The trailing dot expands that sub-structure. |
| Same thing, C-style | `dx ((nt!_IRP*)0x<addr>)->Tail.Overlay.Thread` | Evaluates a C-like expression, follows pointers for you. |
| What code is at this address? | `ln <addr>` | "List nearest symbol": names the function an address is in. |
| What allocation contains this address? | `!pool <addr>` | Shows the pool block, its size and its 4-letter **tag** (who allocated it). |
| What object is this? | `!object <addr>` | For named kernel objects (devices, files…). |
| Do arithmetic | `? <expr>` | e.g. `? ffffb10e`4c2f7a20 + 0xd0` |
| Summarize an IRP / device / driver / thread | `!irp`, `!devobj`, `!devstack`, `!drvobj`, `!thread` | Pre-built "readers" that know the layouts and follow the pointers for you. |

The **method** is always the same loop:

```
 start from something with a NAME (a driver, a process, a parameter of a bug check)
        │
        ▼
 get its ADDRESS ──► lay the TYPE over it (dt) ──► read a POINTER field
        ▲                                                │
        └──────────────── follow that pointer ◄──────────┘
```

The `!` extensions are this loop pre-packaged. `!irp` is just someone else running `dt nt!_IRP`, following the stack locations and the device pointers, and printing a summary. When an extension's output confuses you, you can always fall back to `dt` on the same address and see the raw fields.

### 1.6 One more building block: LIST_ENTRY

The kernel links things into lists using a tiny two-pointer structure:

```c
typedef struct _LIST_ENTRY {
    struct _LIST_ENTRY *Flink;   // +0x0  "forward link": next entry
    struct _LIST_ENTRY *Blink;   // +0x8  "backward link": previous entry
} LIST_ENTRY;
```

The list **head** is a `LIST_ENTRY` inside the owner (for example inside a thread). Each **member** has a `LIST_ENTRY` embedded inside it. The links point at the embedded `LIST_ENTRY`, **not** at the start of the member. So to get from a link back to the member, you subtract the offset of the embedded field. In code that's the `CONTAINING_RECORD` macro. In the debugger it's `dt nt!_IRP <link address> - 0x20`, if the link field is at offset `0x20`.

```
         thread (owner)                      IRP (member)
   ┌────────────────────────┐        ┌───────────────────────────┐
   │ ...                    │        │ +0x00 Type, Size ...       │
   │ IrpList  Flink ────────┼───────►│ +0x20 ThreadListEntry.Flink ┼──┐
   │          Blink ────────┼───────►│ +0x28 ThreadListEntry.Blink ┼──┤
   │ ...  ▲                 │        │ ...                        │  │
   └──────┼─────────────────┘        └───────────────────────────┘  │
          └──────────────────────────────────────────────────────────┘
   One IRP on the list: both of the head's links point to the IRP's links,
   and both of the IRP's links point back to the head. (Empty list: the
   head points to ITSELF, twice.)
```

That's why "the same pointer twice in a row" is such a useful pattern to recognize.

---

## 2. The structures involved, and how they point to each other

An I/O request touches six kinds of block. Here is each one: what it's for, who creates it, and the fields that matter for following an IRP. The offsets are for **64-bit Windows 11 24H2** (your VM's build, 26100), taken from the kernel's public symbols. Arm64 and x64 use the same layouts for these structures because pointers are 8 bytes on both, but Microsoft can change internal layouts between builds. On any machine, `dt nt!_IRP` gives the real offsets for that build.

### 2.1 DRIVER_OBJECT: one per loaded driver

Created by the I/O manager when it loads the driver's `.sys` file, just before it calls the driver's `DriverEntry`. The driver fills in its function table.

```c
// Simplified: only the fields we use. Offsets are 64-bit Windows 11 24H2.
typedef struct _DRIVER_OBJECT {
    CSHORT          Type;            // +0x000  = 4 (IO_TYPE_DRIVER)
    CSHORT          Size;            // +0x002
    PDEVICE_OBJECT  DeviceObject;    // +0x008  first device this driver created (a linked list via NextDevice)
    ULONG           Flags;           // +0x010
    PVOID           DriverStart;     // +0x018  where the .sys image is loaded (fffff80x`…)
    ULONG           DriverSize;      // +0x020
    /* ... */
    UNICODE_STRING  DriverName;      // +0x038  e.g. "\Driver\TgCounter"
    /* ... */
    PDRIVER_UNLOAD  DriverUnload;    // +0x068
    PDRIVER_DISPATCH MajorFunction[28]; // +0x070  one function pointer per kind of request
} DRIVER_OBJECT;                     // total 0x150 bytes
```

`MajorFunction` is the table the I/O manager calls through. Index `0x0E` is `IRP_MJ_DEVICE_CONTROL`, so the pointer for device-control requests sits at `+0x070 + 0x0E × 8 = +0x0E0`. The index values you'll meet most:

| Index | Name | Sent when |
|---|---|---|
| `0x00` | `IRP_MJ_CREATE` | a program opens the device (`CreateFile`) |
| `0x02` | `IRP_MJ_CLOSE` | the last handle and reference are gone |
| `0x03` | `IRP_MJ_READ` | `ReadFile` |
| `0x04` | `IRP_MJ_WRITE` | `WriteFile` |
| `0x0E` | `IRP_MJ_DEVICE_CONTROL` | `DeviceIoControl` |
| `0x0F` | `IRP_MJ_INTERNAL_DEVICE_CONTROL` | driver-to-driver control requests |
| `0x12` | `IRP_MJ_CLEANUP` | the last **handle** is closed |
| `0x16` | `IRP_MJ_POWER` | power manager: sleep, wake, device power states |
| `0x1B` | `IRP_MJ_PNP` | PnP manager: start, stop, remove, query relations |

Here's how a real driver fills in the table, from TgCounter's `DriverEntry`:

```c
DriverObject->MajorFunction[IRP_MJ_CREATE]         = TgDispatchCreateClose;
DriverObject->MajorFunction[IRP_MJ_CLOSE]          = TgDispatchCreateClose;
DriverObject->MajorFunction[IRP_MJ_DEVICE_CONTROL] = TgDispatchDeviceControl;
DriverObject->DriverUnload                         = TgUnload;
```

Every entry the driver doesn't fill in points to a kernel default that fails the request with "invalid device request".

### 2.2 DEVICE_OBJECT: one per device a driver serves

A **device object** is the thing requests are aimed at. A driver creates it with `IoCreateDevice`. One driver can have many (one per physical device, plus control devices).

```c
typedef struct _DEVICE_OBJECT {
    CSHORT          Type;            // +0x000  = 3 (IO_TYPE_DEVICE)
    USHORT          Size;            // +0x002
    LONG            ReferenceCount;  // +0x004
    PDRIVER_OBJECT  DriverObject;    // +0x008  which driver handles requests sent here
    PDEVICE_OBJECT  NextDevice;      // +0x010  next device created by the SAME driver
    PDEVICE_OBJECT  AttachedDevice;  // +0x018  the device stacked ON TOP of this one (NULL if top)
    PIRP            CurrentIrp;      // +0x020  only used by old "StartIo"-style drivers
    /* ... */
    ULONG           Flags;           // +0x030
    ULONG           Characteristics; // +0x034
    /* ... */
    PVOID           DeviceExtension; // +0x040  the driver's own private per-device data
    DEVICE_TYPE     DeviceType;      // +0x048  e.g. 0x8000 for TgCounter
    CCHAR           StackSize;       // +0x04c  how many stack locations an IRP sent HERE needs
    /* ... */
} DEVICE_OBJECT;                     // total 0x150 bytes, extension follows
```

Two fields matter most for IRPs:
- **`DriverObject`**: how the I/O manager finds the function to call.
- **`StackSize`**: how many stack locations to allocate. It's 1 for a device with nothing below it. Each time a driver attaches a device on top of another, the new device's `StackSize` becomes the lower one's plus one.

The **device extension** is memory the driver asked for in `IoCreateDevice` (TgCounter asked for `sizeof(TG_EXTENSION)`, 4 bytes for the counter). It's allocated together with the device object, and `DeviceExtension` points to it.

### 2.3 FILE_OBJECT: one per open

When a program calls `CreateFile` on a device, the I/O manager creates a **file object** to represent *that open*. Even for a device that isn't a file, it's still called a file object. The program gets a **handle**, which is an index into its process's handle table, and the handle table entry points to the file object.

```c
typedef struct _FILE_OBJECT {
    CSHORT          Type;            // +0x000  = 5 (IO_TYPE_FILE)
    CSHORT          Size;            // +0x002
    PDEVICE_OBJECT  DeviceObject;    // +0x008  the device this open refers to
    /* ... */
    PVOID           FsContext;       // +0x018  driver's per-open data (optional)
    PVOID           FsContext2;      // +0x020
    /* ... */
    ULONG           Flags;           // +0x050  e.g. FO_SYNCHRONOUS_IO if opened without OVERLAPPED
    UNICODE_STRING  FileName;        // +0x058
    /* ... */
    KEVENT          Event;           // +0x098  signaled when synchronous I/O on this open finishes
    /* ... */
} FILE_OBJECT;                       // total 0xd8 bytes
```

The chain from a program's handle to a driver is:
**handle → handle table entry → FILE_OBJECT → `DeviceObject` → `DriverObject` → `MajorFunction[...]`**.

### 2.4 ETHREAD: the thread that asked

The kernel's thread object. For IRPs, it matters for two reasons: the IRP records which thread it belongs to (`Tail.Overlay.Thread`), and the thread keeps a **list of its outstanding IRPs** (`IrpList`). Its exact offset varies by build, so let `!thread` find it for you.

### 2.5 IRP header and IO_STACK_LOCATION: the request itself

These are the subject of §3. For now, the one-line versions:
- **IRP header**: who asked (thread, requestor mode), where the data goes (system buffer, user buffer), how it ends (status, bytes transferred), and bookkeeping (stack count, current location, cancel state).
- **IO_STACK_LOCATION**: for **one** driver: what to do (major/minor function), the parameters (lengths, IOCTL code, offset), which device and file object, and an optional completion routine for that driver.

### 2.6 The map: how they all point to each other

This is the picture to keep. Arrows are pointer fields; the label on each arrow is the field that holds the address.

```
 USER MODE (tgclient.exe)                                 KERNEL MODE
 ─────────────────────────                                ──────────────────────────────────────────────────────────
  HANDLE h  ──(index into process handle table)──────►  FILE_OBJECT  (one per CreateFile)
  LONG value  (output buffer, on the program's stack)        │ +0x008 DeviceObject
     ▲                                                       ▼
     │                                                 DEVICE_OBJECT  \Device\TgCounter
     │                                                   │ +0x008 DriverObject      +0x040 DeviceExtension ─► TG_EXTENSION { Counter }
     │                                                   ▼                          +0x04c StackSize = 1
     │                                                 DRIVER_OBJECT  \Driver\TgCounter
     │                                                   │ +0x0e0 MajorFunction[0x0E]
     │                                                   ▼
     │                                                 TgDispatchDeviceControl   (code inside TgCounter.sys, fffff80x`…)
     │
     │                 ┌──────────────────────── IRP (one allocation, nonpaged) ───────────────────────────┐
     │                 │ HEADER (0xD0 bytes)                                                              │
     │ +0x070 UserBuffer  ◄──── where the result is copied back to, at the very end                      │
     └─────────────────┤ +0x018 AssociatedIrp.SystemBuffer ─────────► kernel copy of the data (4 bytes)   │
                       │ +0x020 ThreadListEntry ◄──────────────────► ETHREAD.IrpList  (thread's IRP list) │
                       │ +0x098 Tail.Overlay.Thread ──────────────────► ETHREAD (the thread that asked)    │
                       │ +0x0b8 Tail.Overlay.CurrentStackLocation ──┐                                     │
                       │ +0x0c0 Tail.Overlay.OriginalFileObject ────┼──► FILE_OBJECT                      │
                       ├────────────────────────────────────────────┼─────────────────────────────────────┤
                       │ STACK LOCATION 1 (0x48 bytes)  ◄────────────┘                                     │
                       │   +0x00 MajorFunction = 0x0E                                                     │
                       │   +0x08..0x18 OutputBufferLength, InputBufferLength, IoControlCode               │
                       │   +0x28 DeviceObject ──────────────────────► DEVICE_OBJECT                        │
                       │   +0x30 FileObject   ──────────────────────► FILE_OBJECT                          │
                       │   +0x38 CompletionRoutine (NULL here)                                            │
                       └──────────────────────────────────────────────────────────────────────────────────┘
```

Notice the IRP doesn't point to a driver. It points to a **device** (in each stack location), and the device points to its driver. The request is aimed at devices; drivers are whoever serves them.

---

## 3. The shape of an IRP in memory

### 3.1 One allocation, two parts

An IRP for a device whose `StackSize` is N is a single block of `0xD0 + N × 0x48` bytes:

```
 IRP address ─►┌──────────────────────────────┐  +0x000
               │  IRP header                  │
               │  (0xD0 = 208 bytes)          │
               ├──────────────────────────────┤  +0x0D0   stack location 1  ← the LOWEST driver uses this one
               │  IO_STACK_LOCATION (0x48)    │
               ├──────────────────────────────┤  +0x118   stack location 2
               │  IO_STACK_LOCATION (0x48)    │
               ├──────────────────────────────┤  +0x160   stack location 3  ← the TOP driver uses this one
               │  IO_STACK_LOCATION (0x48)    │
               └──────────────────────────────┘  +0x1A8   end  (for N = 3: Size field = 0x1A8)
```

The header's `Size` field holds the total, and `StackCount` holds N. For TgCounter, N = 1, so its IRPs are `0xD0 + 0x48 = 0x118` bytes. You'll see that `0x118` in the raw dump in §5.

**Why one allocation?** The I/O manager knows N up front (it reads `StackSize` from the target device), so it can allocate everything at once and no driver ever has to allocate memory just to pass a request along. Allocating while passing a request down would be slow and could fail.

### 3.2 The header, field by field

```c
// The IRP header, 64-bit Windows 11 24H2. Simplified: unions trimmed to the members we use.
typedef struct _IRP {
    CSHORT   Type;                    // +0x000  = 6 (IO_TYPE_IRP). A signature: "this block is an IRP".
    USHORT   Size;                    // +0x002  total bytes: 0xD0 + StackCount * 0x48
    /* +0x004..0x007: small internal bookkeeping */
    PMDL     MdlAddress;              // +0x008  describes locked user pages (Direct I/O); NULL for buffered
    ULONG    Flags;                   // +0x010  IRP_BUFFERED_IO, IRP_INPUT_OPERATION, ... (see §6.3)
    union {
        PVOID SystemBuffer;           // +0x018  kernel copy of the data (Buffered I/O)
        struct _IRP *MasterIrp;       //         (or: parent IRP, for split requests)
    } AssociatedIrp;
    LIST_ENTRY ThreadListEntry;       // +0x020  link in the requesting thread's IrpList
    IO_STATUS_BLOCK IoStatus;         // +0x030  the RESULT: .Status (+0x30), .Information (+0x38, bytes moved)
    KPROCESSOR_MODE RequestorMode;    // +0x040  0 = KernelMode, 1 = UserMode: can buffer pointers be trusted?
    BOOLEAN  PendingReturned;         // +0x041  some driver returned STATUS_PENDING (set during completion)
    CHAR     StackCount;              // +0x042  N
    CHAR     CurrentLocation;         // +0x043  index of the current stack location (counts DOWN from N to 1)
    BOOLEAN  Cancel;                  // +0x044  someone asked to cancel this IRP
    KIRQL    CancelIrql;              // +0x045
    CCHAR    ApcEnvironment;          // +0x046
    UCHAR    AllocationFlags;         // +0x047  how it was allocated (lookaside or pool)
    PIO_STATUS_BLOCK UserIosb;        // +0x048  where to copy IoStatus in the CALLER's memory
    PKEVENT  UserEvent;               // +0x050  event to signal when done (if the caller gave one)
    /* +0x058..0x067: Overlay (user APC routine/context for async callers) */
    PDRIVER_CANCEL CancelRoutine;     // +0x068  set by a driver that parks the IRP and can cancel it
    PVOID    UserBuffer;              // +0x070  the CALLER's output buffer address (user-mode address)
    union {                           // +0x078  "Tail": reused for different jobs at different times
        struct {
            PVOID DriverContext[4];   // +0x078  scratch space for the driver that currently owns the IRP
            PETHREAD Thread;          // +0x098  the requesting thread
            PCHAR AuxiliaryBuffer;    // +0x0a0
            LIST_ENTRY ListEntry;     // +0x0a8  free for the CURRENT OWNER to queue the IRP on its own list
            PIO_STACK_LOCATION CurrentStackLocation; // +0x0b8  pointer to the current stack location
            PFILE_OBJECT OriginalFileObject;         // +0x0c0
        } Overlay;
        KAPC Apc;                     // +0x078  after completion, this same memory becomes an APC object (§4 step 9)
    } Tail;
} IRP;                                // header total: 0xD0 bytes
```

Read the fields in four groups and it stops being a wall:

| Group | Fields | Question it answers |
|---|---|---|
| **Identity** | `Type`, `Size`, `StackCount` | Is this an IRP, and how big is it? |
| **Where's the data?** | `AssociatedIrp.SystemBuffer`, `MdlAddress`, `UserBuffer` | Which buffer holds the bytes, and where do results go? |
| **Who's on it now?** | `CurrentLocation`, `Tail.Overlay.CurrentStackLocation`, `Tail.Overlay.ListEntry`, `CancelRoutine` | Which driver owns it, and is it parked on someone's queue? |
| **How does it end?** | `IoStatus`, `PendingReturned`, `Cancel`, `UserIosb`, `UserEvent`, `Tail.Overlay.Thread` | What was the result, and who gets told? |

### 3.3 The stack location, field by field

```c
// One per driver in the stack. 0x48 bytes on 64-bit.
typedef struct _IO_STACK_LOCATION {
    UCHAR MajorFunction;             // +0x00  IRP_MJ_xxx: which MajorFunction[] entry to call
    UCHAR MinorFunction;             // +0x01  sub-operation (used by PnP, power, WMI)
    UCHAR Flags;                     // +0x02
    UCHAR Control;                   // +0x03  SL_PENDING_RETURNED, SL_INVOKE_ON_SUCCESS/ERROR/CANCEL
    union {                          // +0x08  Parameters: 0x20 bytes, meaning depends on MajorFunction
        struct {                     //        ...for IRP_MJ_DEVICE_CONTROL:
            ULONG OutputBufferLength;//   +0x08
            ULONG InputBufferLength; //   +0x10
            ULONG IoControlCode;     //   +0x18  the IOCTL code, e.g. 0x80002000
            PVOID Type3InputBuffer;  //   +0x20
        } DeviceIoControl;
        struct {                     //        ...for IRP_MJ_READ:
            ULONG Length;            //   +0x08
            ULONG Key;               //   +0x10
            LARGE_INTEGER ByteOffset;//   +0x18
        } Read;
        /* ... one member per kind of request ... */
    } Parameters;
    PDEVICE_OBJECT DeviceObject;     // +0x28  the device this location is aimed at
    PFILE_OBJECT   FileObject;       // +0x30
    PIO_COMPLETION_ROUTINE CompletionRoutine; // +0x38  set by the driver ABOVE, called on the way back up
    PVOID          Context;          // +0x40  argument for that completion routine
} IO_STACK_LOCATION;
```

One subtle point is worth stating outright: **the completion routine stored in location *k* belongs to the driver *above* location *k***. A driver that wants to be told when the lower drivers are done writes its routine into the **next** location (the one below its own) before passing the IRP down. §8 shows this in code.

### 3.4 "Current" counts downward, and the top driver uses the *last* location

When the IRP is allocated, nobody owns a stack location yet. The I/O manager sets:
- `CurrentLocation = N + 1` (one past the last valid index), and
- `Tail.Overlay.CurrentStackLocation` = the address **just past** the end of the block.

Each `IoCallDriver` moves both **down by one** (index − 1, pointer − `0x48`) before calling the driver. So the first driver called, the top of the stack, gets location N, which is the **highest address**. The bottom driver gets location 1, right after the header.

```
 N = 3              index   address           who uses it
                    ─────   ──────────────    ───────────────────────────────
 (after alloc)        4     IRP + 0x1A8       nobody (one past the end)
 1st IoCallDriver ►   3     IRP + 0x160       top driver   (e.g. a filter)
 2nd IoCallDriver ►   2     IRP + 0x118       middle driver (the function driver)
 3rd IoCallDriver ►   1     IRP + 0x0D0       bottom driver (the bus driver)
 a 4th call would make it 0 → the kernel bug checks: 0x35 NO_MORE_IRP_STACK_LOCATIONS
```

Two consequences you'll see in the debugger:
- `!irp` lists stack locations **from 1 upward**, so the **top** driver appears **last** in its output, and the current one is marked with `>`.
- `IoGetNextIrpStackLocation(Irp)` is simply `CurrentStackLocation − 1`: the location *below* yours in the stack, at a *lower* address.

### 3.5 Where the block comes from

- **Nonpaged memory, always.** IRPs are touched during completion, which often runs at DISPATCH_LEVEL inside a DPC. Code at DISPATCH_LEVEL can't take a page fault, so the IRP must never be paged out.
- **Usually from a per-processor lookaside list.** IRPs are allocated and freed constantly. So each processor keeps a small cache of recently freed IRPs of common sizes (one list for single-location IRPs, another for IRPs with a few locations). Allocating is mostly "pop one off this CPU's list", and freeing is "push it back". If the list is empty or the IRP is too big, the kernel falls back to nonpaged pool.
- **Pool tag `Irp `** (with a trailing space). Running `!pool` on an IRP address shows that tag, which helps you confirm a random address really is an IRP.
- **`IoAllocateIrp(StackSize, ChargeQuota)`** is the public function. The I/O manager uses it (or an internal equivalent) for user requests. Drivers use it when they build their own IRPs.

---

## 4. The full trip: one DeviceIoControl call, step by step

We'll follow one request all the way: a small program asks a driver to increment a counter and return the new value. The driver is TgCounter. All of the code it needs is shown here.

### 4.0 The code on both ends

**The contract** (shared header):

```c
#define FILE_DEVICE_TGCOUNTER  0x8000u
#define IOCTL_TGCOUNTER_INCREMENT \
    CTL_CODE(FILE_DEVICE_TGCOUNTER, 0x800, METHOD_BUFFERED, FILE_ANY_ACCESS)
```

`CTL_CODE` packs four values into one 32-bit number. Here's what each bit range stands for:

```
 IOCTL_TGCOUNTER_INCREMENT = 0x80002000

 bits:  31 ........ 16 | 15 .. 14 | 13 ........... 2 | 1 .. 0
        device type    | access   | function         | method
        0x8000         | 0 (any)  | 0x800            | 0 (METHOD_BUFFERED)

 0x8000 << 16 = 0x80000000
 0      << 14 = 0x00000000
 0x800  << 2  = 0x00002000
 0      << 0  = 0x00000000
                ──────────
                0x80002000
```

The **method** bits matter for IRPs: `METHOD_BUFFERED` tells the I/O manager to copy data through a kernel buffer (the `SystemBuffer`). §4 step 3 shows what that means in memory.

**The program** (user mode):

```c
HANDLE h = CreateFileW(L"\\\\.\\TgCounter", GENERIC_READ | GENERIC_WRITE, 0, NULL,
                       OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);   // no OVERLAPPED flag → synchronous
LONG  value = 0;
DWORD bytes = 0;
DeviceIoControl(h, IOCTL_TGCOUNTER_INCREMENT,
                NULL, 0,                  // no input
                &value, sizeof(value),    // 4-byte output buffer
                &bytes, NULL);            // NULL OVERLAPPED → wait until done
```

**The driver's dispatch routine** (kernel mode; only the INCREMENT path shown):

```c
typedef struct _TG_EXTENSION { LONG Counter; } TG_EXTENSION, *PTG_EXTENSION;

static NTSTATUS CompleteIrp(PIRP Irp, NTSTATUS status, ULONG_PTR bytesReturned)
{
    Irp->IoStatus.Status = status;            // header +0x30
    Irp->IoStatus.Information = bytesReturned; // header +0x38
    IoCompleteRequest(Irp, IO_NO_INCREMENT);  // hand it back: see step 7
    return status;
}

static NTSTATUS TgDispatchDeviceControl(PDEVICE_OBJECT DeviceObject, PIRP Irp)
{
    PTG_EXTENSION ext = (PTG_EXTENSION)DeviceObject->DeviceExtension;
    PIO_STACK_LOCATION stack = IoGetCurrentIrpStackLocation(Irp);   // = Irp->Tail.Overlay.CurrentStackLocation
    ULONG code   = stack->Parameters.DeviceIoControl.IoControlCode; // stack location +0x18
    ULONG outLen = stack->Parameters.DeviceIoControl.OutputBufferLength; // +0x08
    PVOID buffer = Irp->AssociatedIrp.SystemBuffer;                 // header +0x18
    LONG value;

    if (outLen < sizeof(LONG))
        return CompleteIrp(Irp, STATUS_BUFFER_TOO_SMALL, 0);

    switch (code) {
    case IOCTL_TGCOUNTER_INCREMENT:
        value = InterlockedIncrement(&ext->Counter);
        break;
    /* ... other codes ... */
    default:
        return CompleteIrp(Irp, STATUS_INVALID_DEVICE_REQUEST, 0);
    }

    *(LONG *)buffer = value;                          // write into the KERNEL buffer, not the program's
    return CompleteIrp(Irp, STATUS_SUCCESS, sizeof(LONG));
}
```

Look at what the driver reads: the IOCTL code and lengths come from **its stack location**, the data buffer comes from the **header**, and its private state comes from the **device extension**. It never touches the program's `value` variable directly.

### 4.1 The timeline

Here is the whole trip on one page. Every step runs **on the program's own thread**. No other thread is involved in this synchronous case.

```
 step  layer                    what happens                                         IRQL      may wait?
 ────  ───────────────────────  ───────────────────────────────────────────────────  ────────  ─────────
  1    tgclient.exe (user)      DeviceIoControl(h, 0x80002000, ..., &value, 4, ...)  PASSIVE   yes
  2    ntdll → syscall          NtDeviceIoControlFile: CPU switches to kernel mode   PASSIVE   yes
  3    I/O manager              handle → FILE_OBJECT → DEVICE_OBJECT; allocate IRP;  PASSIVE   yes
                                allocate SystemBuffer; fill header + stack loc;
                                link IRP into thread's IrpList
  4    I/O manager              IoCallDriver(device, irp)                             PASSIVE   yes
  5    IoCallDriver             current location 2 → 1; look up MajorFunction[0x0E];  PASSIVE   yes
                                CALL TgDispatchDeviceControl(device, irp)
  6    TgCounter                read IOCTL code; increment; write 4 bytes into        PASSIVE   yes
                                SystemBuffer; set IoStatus
  7    IoCompleteRequest        walk stack locations upward (no completion routines)  PASSIVE   yes
  8    TgCounter returns        STATUS_SUCCESS back up through IoCallDriver           PASSIVE   yes
  9    I/O manager              final work: copy SystemBuffer → user's &value;        PASSIVE   yes
                                write IoStatus → user's IO_STATUS_BLOCK; unlink
                                from thread; free buffer and IRP
 10    syscall return           back to user mode; DeviceIoControl returns TRUE,      PASSIVE   yes
                                bytes = 4, value = new count
```

Now each step in detail, with what changes in memory.

### Step 1–2: the program calls, the CPU enters the kernel

`DeviceIoControl` is a library function in kernel32/KernelBase. It calls `NtDeviceIoControlFile` in `ntdll.dll`, which executes the system-call instruction (`syscall` on x64, `svc` on Arm64). The CPU switches to kernel mode and jumps into the kernel's system call dispatcher, which calls the kernel's `NtDeviceIoControlFile`. It's **still the same thread**. The thread now runs kernel code on its kernel stack.

The arguments that arrive are all **user-mode addresses and values**: the handle, the IOCTL code, `NULL`/0 for input, the address of `value` (something like `0000004f`a3cff7c4`), the length 4, and the address of an I/O status block that KernelBase keeps on its own stack.

### Step 3: the I/O manager builds the IRP

This is where the IRP is born. Here is a **simplified sketch** of what the kernel does (illustrative pseudocode, not Microsoft's source):

```c
// Sketch of the kernel's NtDeviceIoControlFile for a METHOD_BUFFERED IOCTL. Error handling omitted.
NTSTATUS NtDeviceIoControlFile(HANDLE h, ..., PIO_STATUS_BLOCK UserIosb,
                               ULONG code, PVOID inBuf, ULONG inLen, PVOID outBuf, ULONG outLen)
{
    // (a) handle → file object (object manager checks the handle and access rights)
    PFILE_OBJECT file;
    ObReferenceObjectByHandle(h, /*access*/..., IoFileObjectType, UserMode, &file, NULL);

    // (b) which device? The TOP of the stack the file's device belongs to.
    PDEVICE_OBJECT dev = IoGetRelatedDeviceObject(file);

    // (c) allocate: header + dev->StackSize stack locations, nonpaged
    PIRP irp = IoAllocateIrp(dev->StackSize, FALSE);

    // (d) fill the header: who asked, and how it ends
    irp->RequestorMode               = UserMode;              // pointers came from user mode: don't trust them
    irp->UserIosb                    = UserIosb;              // where to report the result
    irp->UserBuffer                  = outBuf;                // where the output finally goes
    irp->Tail.Overlay.Thread         = PsGetCurrentThread();
    irp->Tail.Overlay.OriginalFileObject = file;

    // (e) METHOD_BUFFERED: one kernel buffer, big enough for input and output
    ULONG bufLen = max(inLen, outLen);                        // max(0, 4) = 4
    irp->AssociatedIrp.SystemBuffer = ExAllocatePool2(POOL_FLAG_NON_PAGED, bufLen, 'IoSB' /*illustrative*/);
    if (inLen) RtlCopyMemory(irp->AssociatedIrp.SystemBuffer, inBuf, inLen);   // probe + copy IN now
    irp->Flags = IRP_BUFFERED_IO | IRP_DEALLOCATE_BUFFER | (outLen ? IRP_INPUT_OPERATION : 0);

    // (f) fill the FIRST driver's stack location (the one IoCallDriver is about to make current)
    PIO_STACK_LOCATION sl = IoGetNextIrpStackLocation(irp);
    sl->MajorFunction = IRP_MJ_DEVICE_CONTROL;                 // 0x0E
    sl->Parameters.DeviceIoControl.IoControlCode     = code;   // 0x80002000
    sl->Parameters.DeviceIoControl.InputBufferLength  = inLen; // 0
    sl->Parameters.DeviceIoControl.OutputBufferLength = outLen;// 4
    sl->FileObject = file;

    // (g) link into this thread's IRP list (so the thread can cancel it if it exits)
    InsertHeadList(&PsGetCurrentThread()->IrpList, &irp->ThreadListEntry);

    // (h) hand it to the driver (step 4)
    NTSTATUS st = IoCallDriver(dev, irp);
    /* ... step 9: wait if pending, then finish ... */
}
```

The important design choice is in (e): **buffered I/O**. The driver must never touch the program's memory directly. That memory belongs to one process, could be freed by another thread at any moment, and could be paged out. So the I/O manager:
- allocates a **kernel** buffer (`SystemBuffer`) in nonpaged pool,
- copies any **input** into it now, while it's running in the caller's process, where the user addresses are valid,
- and later copies the **output** back out, also in the caller's process (step 9).

The driver only ever sees the kernel buffer. That's why TgCounter writes `*(LONG *)buffer = value;` and not into the user's `value`.

**Memory snapshot after step 3.** These addresses are illustrative but internally consistent, and §5 uses the same ones:

| Block | Address | Key contents |
|---|---|---|
| IRP | `ffffb10e`4c2f7a20` | `Type=6`, `Size=0x118`, `StackCount=1`, `CurrentLocation=2` (one past the end), `SystemBuffer=ffffb10e`4a1c3e70`, `UserBuffer=0000004f`a3cff7c4`, `Thread=ffffb10e`4d0e5080` |
| stack location 1 | `ffffb10e`4c2f7af0` (IRP + 0xD0) | `MajorFunction=0x0E`, `OutputBufferLength=4`, `InputBufferLength=0`, `IoControlCode=0x80002000`, `FileObject=ffffb10e`4c90a7b0` |
| SystemBuffer | `ffffb10e`4a1c3e70` | 4 bytes, not yet written |
| program's `value` | `0000004f`a3cff7c4` | still 0 |

### Step 4–5: IoCallDriver, which is "just a function call"

This is the step that answers "how does it get triggered?". Here's a **simplified sketch** of `IoCallDriver` (illustrative, but this is essentially all it does):

```c
NTSTATUS IoCallDriver(PDEVICE_OBJECT DeviceObject, PIRP Irp)
{
    // move "current" one location down
    Irp->CurrentLocation--;
    if (Irp->CurrentLocation <= 0)
        KeBugCheckEx(NO_MORE_IRP_STACK_LOCATIONS, (ULONG_PTR)Irp, 0, 0, 0);   // bug check 0x35
    PIO_STACK_LOCATION sl = --Irp->Tail.Overlay.CurrentStackLocation;

    sl->DeviceObject = DeviceObject;           // record which device this location is aimed at

    // look up the driver's function for this kind of request, and CALL it
    PDRIVER_OBJECT drv = DeviceObject->DriverObject;
    return drv->MajorFunction[sl->MajorFunction](DeviceObject, Irp);
}
```

No queue. No flag. No wakeup. The thread that made the system call is now executing TgCounter's code, one function call deeper. If you broke into the debugger right now, the call stack of the program's thread would look like this, most recent at the top:

```
 # Call Site
 00 TgCounter!TgDispatchDeviceControl+0x40      ← the driver
 01 nt!IofCallDriver+0x...                      ← IoCallDriver
 02 nt!IopXxxControlFile+0x...                  ← I/O manager building + sending the IRP
 03 nt!NtDeviceIoControlFile+0x...
 04 nt!KiSystemServiceCopyEnd+0x...             ← system call entry (name differs on Arm64)
 05 ntdll!NtDeviceIoControlFile+0x...           ← user mode below this line
 06 KERNELBASE!DeviceIoControl+0x...
 07 tgclient!SendIoctl+0x...
 08 tgclient!main+0x...
```

Read it bottom to top and it is exactly steps 1 to 5.

### Step 6: the driver does the work

TgCounter reads its stack location, increments the counter in its device extension (say from 2 to 3), writes `3` into the 4-byte `SystemBuffer`, and fills in the result:

| Field | Before | After |
|---|---|---|
| `TG_EXTENSION.Counter` (device extension) | 2 | 3 |
| `*SystemBuffer` (`ffffb10e`4a1c3e70`) | ? | `03 00 00 00` |
| `IoStatus.Status` (IRP + 0x30) | 0 | 0 (`STATUS_SUCCESS`) |
| `IoStatus.Information` (IRP + 0x38) | 0 | 4 (bytes to copy back) |

`IoStatus.Information` matters: it tells the I/O manager **how many bytes** of the system buffer to copy back to the program in step 9. If a driver forgets to set it, the program gets 0 bytes even though the driver wrote the data.

### Step 7: IoCompleteRequest, which runs the stack in reverse

`IoCompleteRequest` declares "this request is finished". It doesn't free anything yet. Here's a **simplified sketch** (illustrative):

```c
VOID IoCompleteRequest(PIRP Irp, CCHAR PriorityBoost)
{
    // 1. Walk UP the stack, starting at the current location.
    for (PIO_STACK_LOCATION sl = IoGetCurrentIrpStackLocation(Irp);
         Irp->CurrentLocation <= Irp->StackCount;
         sl++, Irp->CurrentLocation++)
    {
        Irp->PendingReturned = (sl->Control & SL_PENDING_RETURNED) != 0;

        // The routine in THIS location was installed by the driver ABOVE.
        if (sl->CompletionRoutine && /* SL_INVOKE_ON_SUCCESS / ERROR / CANCEL bits match */ ...) {
            NTSTATUS r = sl->CompletionRoutine(/*device of the driver above*/, Irp, sl->Context);
            if (r == STATUS_MORE_PROCESSING_REQUIRED)
                return;                         // that driver took the IRP back: STOP here
        }
    }

    // 2. Every driver has seen it. Hand it to the I/O manager's final processing (step 9).
    //    If the requesting thread is waiting synchronously in the I/O manager, that can happen
    //    right there. Otherwise, queue a special kernel APC to Irp->Tail.Overlay.Thread.
    IopCompleteRequestForThread(Irp, PriorityBoost);   // name illustrative
}
```

TgCounter's IRP has one stack location and no completion routines, so the loop does almost nothing here. §8 shows the case where it matters.

### Step 8: the return value travels back

`IoCompleteRequest` returns to `CompleteIrp`, which returns `STATUS_SUCCESS` from `TgDispatchDeviceControl`, which `IoCallDriver` returns to the I/O manager. **Two things travel back separately:**
- the **return value of the dispatch routine** (`STATUS_SUCCESS` or `STATUS_PENDING`), which tells the caller "is it done *yet*?";
- **`Irp->IoStatus`**, which holds the *actual result* of the request.

For a request completed synchronously, they match. For a pending request, the return value is `STATUS_PENDING` and the real result arrives later in `IoStatus`.

### Step 9: the final processing, back in the right process

Now the results have to reach the program. That means writing to **user-mode addresses** (`value` and the I/O status block), and user addresses are only valid **inside the right process**. Completion can happen on any thread in any process (in §7 it happens inside a DPC). So the I/O manager's final step must run **in the requesting thread**. When it isn't already on that thread, it gets there with a **special kernel APC** (Asynchronous Procedure Call: a function queued to run on one particular thread). The kernel reuses the IRP's own `Tail` memory (from `+0x78`) as the APC object, because the overlay fields aren't needed anymore.

Running in the requesting thread, the final processing:

1. copies `IoStatus.Information` bytes (4) from `SystemBuffer` to `UserBuffer` (the program's `value`), because `IRP_INPUT_OPERATION` is set,
2. writes `IoStatus` to `UserIosb` (the caller's status block), which is how `bytes` becomes 4,
3. frees the `SystemBuffer` (because `IRP_DEALLOCATE_BUFFER` is set),
4. sets the event the caller waits on (for this synchronous open, the file object's event),
5. removes the IRP from the thread's `IrpList`,
6. frees the IRP back to the lookaside list,
7. drops the reference on the file object.

In TgCounter's synchronous case, the requesting thread is still inside the I/O manager when the driver completes the IRP. For some request types the I/O manager uses that: it marks the IRP "defer completion" (flag `0x800`, §6.3) and, if the driver didn't return pending, does this final work itself on the way out, with no APC and no wait. Otherwise it goes through the APC. Either way, the work runs in the requesting thread. Which path a given request takes is an internal detail you don't need to memorize.

### Step 10: back to the program

`NtDeviceIoControlFile` returns `STATUS_SUCCESS`, the CPU returns to user mode, and `DeviceIoControl` returns `TRUE` with `bytes = 4` and `value = 3`.

The IRP existed for a few microseconds. That's typical, and it's why you almost never "see" an IRP in a debugger unless (a) you stop the machine mid-request with a breakpoint, or (b) something is stuck and the IRP has been sitting there.

---

## 5. The same trip seen in WinDbg, byte by byte

This section shows what you'd see if you stopped the machine at the start of `TgDispatchDeviceControl` (step 6) with a kernel debugger attached from another machine. Local kernel debugging (the `lkd>` prompt) can't do this, because it can't freeze the machine it runs on.

> **About these listings:** the **layouts and offsets are real** (64-bit Windows 11 24H2 public symbols). The **addresses and the exact formatting are illustrative**: built to be consistent with each other, not copied from a live session. On a real machine, every address will differ on every boot.

### 5.1 Start from a name: the driver

```
kd> !drvobj TgCounter 2
Driver object (ffffb10e`4b2f5e30) is for:
 \Driver\TgCounter

DriverEntry:   fffff800`8a3c5010  TgCounter!GsDriverEntry
DriverStartIo: 00000000
DriverUnload:  fffff800`8a3c1300  TgCounter!TgUnload

Dispatch routines:
[00] IRP_MJ_CREATE              fffff800`8a3c1000  TgCounter!TgDispatchCreateClose
[01] IRP_MJ_CREATE_NAMED_PIPE   fffff800`67a2c1d0  nt!IopInvalidDeviceRequest
[02] IRP_MJ_CLOSE               fffff800`8a3c1000  TgCounter!TgDispatchCreateClose
 ...
[0e] IRP_MJ_DEVICE_CONTROL      fffff800`8a3c1040  TgCounter!TgDispatchDeviceControl
 ...
```

Read it with the method from §1:
- `ffffb10e`4b2f5e30` is a **pool** address: the DRIVER_OBJECT block.
- `fffff800`8a3c…` addresses are **code inside TgCounter.sys**, and the debugger names them using TgCounter's symbols.
- `fffff800`67a2…` is **code inside the kernel** (`nt`): the default "invalid request" handler for every entry TgCounter didn't fill in.

You can check the table by hand. `MajorFunction` starts at `+0x070`, so entry `0x0E` is at `+0x070 + 0x0E*8 = +0x0E0`:

```
kd> dq ffffb10e`4b2f5e30+0xe0 L1
ffffb10e`4b2f5f10  fffff800`8a3c1040
kd> ln fffff800`8a3c1040
(fffff800`8a3c1040)   TgCounter!TgDispatchDeviceControl   |  (fffff800`8a3c1200)   TgCounter!TgUnload
Exact matches:
    TgCounter!TgDispatchDeviceControl (struct _DEVICE_OBJECT *, struct _IRP *)
```

That is exactly the lookup `IoCallDriver` does in step 5: read 8 bytes at `driver + 0x70 + 8 × major`, and jump there.

### 5.2 Get the IRP's address from the call itself

At the breakpoint, the dispatch routine has just been called with two arguments: `(DeviceObject, Irp)`. The calling convention puts the first two arguments in registers:

| CPU | 1st argument (`DeviceObject`) | 2nd argument (`Irp`) |
|---|---|---|
| Arm64 (your VM) | `x0` | `x1` |
| x64 | `rcx` | `rdx` |

```
kd> r x0, x1
x0=ffffb10e4b6a1d30 x1=ffffb10e4c2f7a20
```

`x0` is the device object and `x1` is the IRP. Both start with `ffff`, so both are kernel pool blocks.

### 5.3 The summary view: !irp

```
kd> !irp ffffb10e`4c2f7a20
Irp is active with 1 stacks 1 is current (= 0xffffb10e4c2f7af0)
 No Mdl: System buffer=ffffb10e4a1c3e70: Thread ffffb10e4d0e5080:  Irp stack trace.
     cmd  flg cl Device   File     Completion-Context
>[IRP_MJ_DEVICE_CONTROL(e), N/A(0)]
            0  0 ffffb10e4b6a1d30 ffffb10e4c90a7b0 00000000-00000000
	       \Driver\TgCounter
			Args: 00000004 00000000 80002000 00000000
```

Every item here is a field you now know:

| `!irp` shows | Comes from |
|---|---|
| `1 stacks 1 is current` | `StackCount` (+0x42) and `CurrentLocation` (+0x43) |
| `(= 0xffffb10e4c2f7af0)` | `Tail.Overlay.CurrentStackLocation` (+0xb8) = IRP + 0xD0 |
| `No Mdl` | `MdlAddress` (+0x08) is NULL: not Direct I/O |
| `System buffer=ffffb10e4a1c3e70` | `AssociatedIrp.SystemBuffer` (+0x18) |
| `Thread ffffb10e4d0e5080` | `Tail.Overlay.Thread` (+0x98) |
| `>` | marks the current stack location |
| `[IRP_MJ_DEVICE_CONTROL(e), N/A(0)]` | stack location `MajorFunction` / `MinorFunction` |
| `flg cl` | stack location `Flags` / `Control` (Control would show `1` if pending had been returned) |
| `Device`, `File` | stack location `DeviceObject` (+0x28), `FileObject` (+0x30) |
| `Completion-Context` | stack location `CompletionRoutine` (+0x38) – `Context` (+0x40) |
| `\Driver\TgCounter` | `DeviceObject → DriverObject → DriverName`, followed for you |
| `Args: 00000004 00000000 80002000 00000000` | the 4 parameter slots: output length 4, input length 0, IOCTL `0x80002000`, Type3InputBuffer |

### 5.4 The structured view: dt

```
kd> dt nt!_IRP ffffb10e`4c2f7a20
   +0x000 Type             : 0n6
   +0x002 Size             : 0x118
   +0x008 MdlAddress       : (null)
   +0x010 Flags            : 0x70
   +0x018 AssociatedIrp    : <unnamed-tag>
   +0x020 ThreadListEntry  : _LIST_ENTRY [ 0xffffb10e`4d0e5650 - 0xffffb10e`4d0e5650 ]
   +0x030 IoStatus         : _IO_STATUS_BLOCK
   +0x040 RequestorMode    : 1 ''
   +0x041 PendingReturned  : 0 ''
   +0x042 StackCount       : 1 ''
   +0x043 CurrentLocation  : 1 ''
   +0x044 Cancel           : 0 ''
   +0x045 CancelIrql       : 0 ''
   +0x046 ApcEnvironment   : 0 ''
   +0x047 AllocationFlags  : 0x6 ''
   +0x048 UserIosb         : 0x0000004f`a3cff6e0 _IO_STATUS_BLOCK
   +0x050 UserEvent        : (null)
   +0x058 Overlay          : <unnamed-tag>
   +0x068 CancelRoutine    : (null)
   +0x070 UserBuffer       : 0x0000004f`a3cff7c4 Void
   +0x078 Tail             : <unnamed-tag>
```

What it tells you, by group:
- **Identity:** `Type` 6 = IRP. `Size` `0x118` = `0xD0 + 1 × 0x48`, so one stack location, which matches `StackCount` 1.
- **Data:** `MdlAddress` NULL and `Flags` `0x70` mean buffered I/O with an output direction (decoded in §6.3). `UserBuffer` and `UserIosb` start with `0000004f`: **user-mode** addresses in tgclient's memory.
- **Owner:** `CurrentLocation` 1: TgCounter's location is current.
- **Thread list:** `ThreadListEntry` has the **same pointer twice**. That's a one-entry list (§1.6): this is the only IRP the thread has outstanding, and `ffffb10e`4d0e5650` is the list head inside the thread object.
- **RequestorMode** 1 = UserMode: the request came from a program, so any pointers in it must be treated as untrusted.

Expand the nested parts with a trailing dot:

```
kd> dt nt!_IRP ffffb10e`4c2f7a20 AssociatedIrp. IoStatus. Tail.Overlay.
   +0x018 AssociatedIrp  :
      +0x000 MasterIrp      : 0xffffb10e`4a1c3e70 _IRP
      +0x000 IrpCount       : 0n1243364976
      +0x000 SystemBuffer   : 0xffffb10e`4a1c3e70 Void
   +0x030 IoStatus       :
      +0x000 Status         : 0n0
      +0x008 Information    : 0
   +0x078 Tail           :
      +0x000 Overlay        :
         +0x000 DriverContext  : [4] (null)
         +0x020 Thread         : 0xffffb10e`4d0e5080 _ETHREAD
         +0x028 AuxiliaryBuffer: (null)
         +0x030 ListEntry      : _LIST_ENTRY [ 0x00000000`00000000 - 0x00000000`00000000 ]
         +0x040 CurrentStackLocation : 0xffffb10e`4c2f7af0 _IO_STACK_LOCATION
         +0x048 OriginalFileObject : 0xffffb10e`4c90a7b0 _FILE_OBJECT
```

Two lessons hide in here:
- `AssociatedIrp` is a **union**: three names for the same 8 bytes. `dt` shows all three interpretations. Only one makes sense for this IRP (`SystemBuffer`, since the flags say buffered I/O). `IrpCount 0n1243364976` is the low 4 of those bytes read as a number, which is meaningless here. **When `dt` shows a union, the other fields tell you which member is real.**
- Inside `Tail`, offsets restart from 0 (`+0x020 Thread`), because they're relative to `Tail`, which itself sits at `+0x78`. So `Thread` is at `0x78 + 0x20 = 0x98` from the IRP's start.

### 5.5 The raw view: dq, annotated

This is the "wall of numbers" view. Here is the same IRP, all `0x118` bytes, with each value labeled:

```
kd> dq ffffb10e`4c2f7a20 L23
                    +0 / +8 within each line
ffffb10e`4c2f7a20  00000000`01180006 00000000`00000000   +00 Type=6 Size=0x118 | +08 MdlAddress=NULL
ffffb10e`4c2f7a30  00000000`00000070 ffffb10e`4a1c3e70   +10 Flags=0x70        | +18 SystemBuffer
ffffb10e`4c2f7a40  ffffb10e`4d0e5650 ffffb10e`4d0e5650   +20 ThreadListEntry.Flink | +28 .Blink   (same twice: 1-entry list)
ffffb10e`4c2f7a50  00000000`00000000 00000000`00000000   +30 IoStatus.Status=0 | +38 IoStatus.Information=0
ffffb10e`4c2f7a60  06000000`01010001 0000004f`a3cff6e0   +40 8 one-byte fields (below) | +48 UserIosb (user addr)
ffffb10e`4c2f7a70  00000000`00000000 00000000`00000000   +50 UserEvent=NULL | +58 Overlay
ffffb10e`4c2f7a80  00000000`00000000 00000000`00000000   +60 Overlay       | +68 CancelRoutine=NULL
ffffb10e`4c2f7a90  0000004f`a3cff7c4 00000000`00000000   +70 UserBuffer (user addr) | +78 DriverContext[0]
ffffb10e`4c2f7aa0  00000000`00000000 00000000`00000000   +80 DriverContext[1] | +88 DriverContext[2]
ffffb10e`4c2f7ab0  00000000`00000000 ffffb10e`4d0e5080   +90 DriverContext[3] | +98 Thread
ffffb10e`4c2f7ac0  00000000`00000000 00000000`00000000   +a0 AuxiliaryBuffer | +a8 ListEntry.Flink
ffffb10e`4c2f7ad0  00000000`00000000 ffffb10e`4c2f7af0   +b0 ListEntry.Blink | +b8 CurrentStackLocation (points INSIDE this block)
ffffb10e`4c2f7ae0  ffffb10e`4c90a7b0 00000000`00000000   +c0 OriginalFileObject | +c8 (internal)
──────────── end of header (0xD0), start of stack location 1 ────────────
ffffb10e`4c2f7af0  00000000`0000000e 00000000`00000004   SL+00 Major=0x0E Minor=0 Flags=0 Control=0 | SL+08 OutputBufferLength=4
ffffb10e`4c2f7b00  00000000`00000000 00000000`80002000   SL+10 InputBufferLength=0 | SL+18 IoControlCode=0x80002000
ffffb10e`4c2f7b10  00000000`00000000 ffffb10e`4b6a1d30   SL+20 Type3InputBuffer=0 | SL+28 DeviceObject
ffffb10e`4c2f7b20  ffffb10e`4c90a7b0 00000000`00000000   SL+30 FileObject | SL+38 CompletionRoutine=NULL
ffffb10e`4c2f7b30  00000000`00000000                     SL+40 Context=NULL
```

The line at `+0x40` packs eight one-byte fields into one 8-byte value. Read them **from the right** (little-endian, §1.4):

```
 06000000`01010001
 ││          ││││└┴─ +40 RequestorMode   = 01 (UserMode)
 ││          ││└┴─── +41 PendingReturned = 00
 ││          └┴───── +42 StackCount      = 01
 ││     (01 at +43)  +43 CurrentLocation = 01
 ││   00 00 00       +44 Cancel, +45 CancelIrql, +46 ApcEnvironment = 0
 └┴───────────────── +47 AllocationFlags = 06 (internal: how it was allocated)
```

Applying the decoder ring from §1.3 to this dump without any symbols:
- The first 2 bytes are `0006`: **an IRP**.
- Values starting with `ffffb10e` are **pointers to other kernel blocks** (system buffer, thread, file object, device object).
- Values starting with `0000004f` are **pointers into the program's memory**.
- `ffffb10e`4c2f7af0` is **inside this same block** (IRP + 0xD0): the current-location pointer.
- `0x80002000` looks like an **IOCTL code** (top bit set, device type 0x8000).

With practice, you start reading raw memory like this before reaching for `dt`.

### 5.6 Follow the pointers outward

From the IRP, every arrow in the §2.6 map can be followed:

```
kd> dt nt!_IO_STACK_LOCATION ffffb10e`4c2f7af0
   +0x000 MajorFunction    : 0xe ''
   +0x001 MinorFunction    : 0 ''
   +0x002 Flags            : 0 ''
   +0x003 Control          : 0 ''
   +0x008 Parameters       : <unnamed-tag>
   +0x028 DeviceObject     : 0xffffb10e`4b6a1d30 _DEVICE_OBJECT
   +0x030 FileObject       : 0xffffb10e`4c90a7b0 _FILE_OBJECT
   +0x038 CompletionRoutine : (null)
   +0x040 Context          : (null)

kd> dt nt!_DEVICE_OBJECT ffffb10e`4b6a1d30 Type DriverObject AttachedDevice DeviceExtension DeviceType StackSize
   +0x000 Type             : 0n3
   +0x008 DriverObject     : 0xffffb10e`4b2f5e30 _DRIVER_OBJECT     ← same address !drvobj showed
   +0x018 AttachedDevice   : (null)                                  ← nothing stacked on top
   +0x040 DeviceExtension  : 0xffffb10e`4b6a1e80 Void               ← right after the device object
   +0x048 DeviceType       : 0x8000
   +0x04c StackSize        : 1 ''

kd> dd ffffb10e`4b6a1e80 L1                    ← TgCounter's TG_EXTENSION: { LONG Counter; }
ffffb10e`4b6a1e80  00000002                     ← counter is 2 (this call will make it 3)

kd> !pool ffffb10e`4c2f7a20
Pool page ffffb10e4c2f7a20 region is Nonpaged pool
*ffffb10e4c2f7a10 size:  130 previous size:    0  (Allocated) *Irp
		Pooltag Irp  : Io, IRP packets
```

The `!pool` result confirms three things: the IRP is in **nonpaged** pool, its tag is **`Irp `**, and the pool block (`0x130`) is slightly bigger than the IRP (`0x118`) because of the pool's own small header in front of it.

And from the thread side:

```
kd> !thread ffffb10e`4d0e5080
THREAD ffffb10e4d0e5080  Cid 1a2c.0f30  Teb: 0000004fa3d8e000 Win32Thread: 0000000000000000 RUNNING on processor 1
IRP List:
    ffffb10e4c2f7a20: (0006,0118) Flags: 00000070  Mdl: 00000000
Owning Process            ffffb10e4cf1a080       Image:         tgclient.exe
...
```

`!thread` walks the thread's `IrpList` for you and prints each IRP with `(Type, Size)`, which is the `(0006, 0118)` you decoded by hand at offset 0.

### 5.7 The whole picture with real-shaped numbers

```
   tgclient.exe  (user space, process-private)
   ┌───────────────────────────────────────────┐
   │ 0000004f`a3cff6e0  IO_STATUS_BLOCK        │◄─────────────────────────── IRP +0x48 UserIosb
   │ 0000004f`a3cff7c4  LONG value             │◄─────────────────────────── IRP +0x70 UserBuffer
   └───────────────────────────────────────────┘
   kernel space (shared)
   ┌───────────────────────────────────────────┐
   │ ffffb10e`4d0e5080  ETHREAD (tgclient)     │◄─────────────────────────── IRP +0x98 Thread
   │   ...  +IrpList  ffffb10e`4d0e5650 ───────┼──► IRP +0x20 (and back)
   └───────────────────────────────────────────┘
   ┌───────────────────────────────────────────┐
   │ ffffb10e`4c2f7a20  IRP  (0x118 bytes)     │
   │   +0x18 SystemBuffer ─────────────────────┼──► ffffb10e`4a1c3e70  [4 bytes: result goes here first]
   │   +0xb8 CurrentStackLocation ──┐          │
   │   +0xc0 OriginalFileObject ────┼──────────┼──► ffffb10e`4c90a7b0  FILE_OBJECT ── +0x08 ──┐
   │ ffffb10e`4c2f7af0 stack loc 1 ◄┘          │                                             │
   │   +0x28 DeviceObject ─────────────────────┼──► ffffb10e`4b6a1d30  DEVICE_OBJECT ◄───────┘
   └───────────────────────────────────────────┘        │ +0x08 DriverObject   +0x40 DeviceExtension
                                                         ▼                        ▼
                                          ffffb10e`4b2f5e30 DRIVER_OBJECT   ffffb10e`4b6a1e80 { Counter = 2 }
                                                  │ +0xe0 MajorFunction[0x0E]
                                                  ▼
                                          fffff800`8a3c1040  TgCounter!TgDispatchDeviceControl  (code)
```

---

## 6. Queues, lists and flags

### 6.1 The one list every IRP is on: the thread's IrpList

When the I/O manager builds an IRP for a thread, it links it into that thread's `IrpList` (step 3g). It isn't a work queue. Nobody "takes work" from it. It exists so the kernel can answer the question **"what I/O does this thread have outstanding?"**:
- When a thread exits, or calls `CancelIo`, the kernel walks this list and asks each IRP's current owner to cancel it.
- `!thread` shows it in the debugger, which is often how you spot a thread stuck waiting on I/O.

(IRPs that a driver builds for itself with `IoAllocateIrp` are **not** tied to a thread. That driver must free them itself, usually in its completion routine.)

### 6.2 Driver queues: optional, private, and only when the driver can't finish now

If a driver can finish immediately, as TgCounter does, the IRP never sits on any queue. A driver queues an IRP only when it **has to wait**: for hardware, for an earlier request to finish, or for a resource. The rules for "parking" an IRP:

```c
// Inside a dispatch routine that can't finish right away (WDM style)
IoMarkIrpPending(Irp);                          // sets SL_PENDING_RETURNED (0x01) in MY stack location's Control
InsertTailList(&ext->PendingQueue,              // my own queue, in my device extension
               &Irp->Tail.Overlay.ListEntry);   // IRP +0xa8: the link field the owner may use
StartHardwareIfIdle(ext);
return STATUS_PENDING;                          // tells IoCallDriver's caller: "not done yet"
```

Three rules come with this, and breaking any of them is a classic bug:
1. **Mark pending before returning `STATUS_PENDING`**, and never return `STATUS_PENDING` without marking it. The two must agree.
2. **After you've queued it, it may already be gone.** Another processor could dequeue and complete it before your `return` runs. Don't touch the IRP after making it reachable by someone else.
3. **A parked IRP must be cancellable.** The driver must be able to give it back if the thread exits. That's what `CancelRoutine` (IRP + 0x68) is for. In practice, drivers use the kernel's **cancel-safe queue** helpers (`IoCsqInsertIrp` and friends) or, much more commonly today, let KMDF manage the queue (§7.3).

Where IRPs can be parked:

| Queue | Who owns it | Link used |
|---|---|---|
| A driver's own `LIST_ENTRY` queue | the driver (in its device extension) | `Tail.Overlay.ListEntry` (+0xa8) |
| A cancel-safe queue (`IO_CSQ`) | the driver, with kernel helpers handling cancellation | same field, managed for you |
| A KMDF `WDFQUEUE` | the framework, on the driver's behalf | framework's own request object, wrapping the IRP |
| The device's `DeviceQueue` / `CurrentIrp` | old "StartIo"-model drivers | `Tail.Overlay.DeviceQueueEntry` |

### 6.3 The flags: descriptions, not signals

No flag in an IRP causes anything to run. Flags **describe** the request so that whoever handles it next knows how to treat it.

**IRP header `Flags` (+0x10)**, the bits you'll see most:

| Bit | Name | Meaning |
|---|---|---|
| `0x00000004` | `IRP_SYNCHRONOUS_API` | the caller is waiting synchronously |
| `0x00000010` | `IRP_BUFFERED_IO` | `SystemBuffer` is in use |
| `0x00000020` | `IRP_DEALLOCATE_BUFFER` | free `SystemBuffer` during final processing |
| `0x00000040` | `IRP_INPUT_OPERATION` | data flows **into** the caller (copy `SystemBuffer` → `UserBuffer` at the end) |
| `0x00000100` | `IRP_READ_OPERATION` | a read |
| `0x00000200` | `IRP_WRITE_OPERATION` | a write |
| `0x00000800` | `IRP_DEFER_IO_COMPLETION` | the I/O manager will finish this itself on the way out if the driver completes it synchronously (§4 step 9) |

TgCounter's `0x70` = `0x40 + 0x20 + 0x10` = "copy back to the caller, then free the system buffer, which is in use". On a real system you may see extra bits too. Decode any value by splitting it into these powers of two.

**Stack location `Control` (+0x03):**

| Bit | Name | Meaning |
|---|---|---|
| `0x01` | `SL_PENDING_RETURNED` | the driver at this location returned `STATUS_PENDING` |
| `0x20` | `SL_INVOKE_ON_CANCEL` | call this location's completion routine if the IRP was cancelled |
| `0x40` | `SL_INVOKE_ON_SUCCESS` | …if it succeeded |
| `0x80` | `SL_INVOKE_ON_ERROR` | …if it failed |

**Other header state:** `PendingReturned` (+0x41) is set during completion as each level is unwound, `Cancel` (+0x44) is set when someone requested cancellation, and `CancelRoutine` (+0x68) is non-NULL while a driver has the IRP parked in a cancellable state.

### 6.4 So what does "pending" actually mean?

"Pending" means: **the dispatch routine returned before the request finished, and some later code path promises to call `IoCompleteRequest` on it.** It's a promise, recorded in two places (the `SL_PENDING_RETURNED` bit and the `STATUS_PENDING` return value). Whatever code path keeps the promise (usually a DPC after a hardware interrupt) runs later, on whatever processor and thread the interrupt lands on.

That's why a "hang waiting for an IRP" looks the way it does in a dump: the requesting thread is waiting, the IRP sits at one driver's stack location marked pending, and nothing in the system is going to complete it.

---

## 7. The asynchronous version: a real device with an interrupt

TgCounter finishes instantly because it has no hardware. Most real drivers can't: they have to start the device and wait for it. Here is the same pipeline for a read from a device that delivers data by interrupt, such as a sensor or serial device.

### 7.1 The timeline, with IRQL and "may it wait?" at every stage

```
 time ─►
 ┌─ program's thread ─────────────────────────────────────────────────┐                ┌─ program's thread again ───────┐
 │ 1 ReadFile → syscall                       PASSIVE  may wait       │                │ 9 APC runs in this thread:     │
 │ 2 I/O manager builds IRP                   PASSIVE  may wait       │                │   copy SystemBuffer → user buf │
 │ 3 IoCallDriver → driver's dispatch         PASSIVE  may wait       │                │   write IoStatus, set event,   │
 │ 4 driver: mark pending, queue IRP,         PASSIVE  may wait       │                │   free IRP     PASSIVE (APC)   │
 │   start the hardware, return PENDING                               │                │ 10 Wait returns; ReadFile      │
 │ 5 I/O manager: thread WAITS on an event    PASSIVE  waiting...     │                │    returns to the program      │
 └────────────────────────────────────────────────────────────────────┘                └────────────────────────────────┘
                     ... device works ...                                                          ▲
 ┌─ whatever was running on CPU 2 when the interrupt arrived ─────────────────────────────┐       │
 │ 6 ISR: read/clear device status, mask the source, queue a DPC  DIRQL    may NOT wait    │       │
 │ 7 DPC: dequeue the IRP, copy data into SystemBuffer,           DISPATCH may NOT wait    │       │
 │   set IoStatus, IoCompleteRequest → completion routines run    DISPATCH may NOT wait    │       │
 │ 8 I/O manager: queue special kernel APC to the IRP's Thread    DISPATCH may NOT wait    ├───────┘
 └─────────────────────────────────────────────────────────────────────────────────────────┘
```

Three facts this picture makes concrete:
- **Steps 6–8 run on someone else's thread** (whatever happened to be running on that CPU) in **someone else's process**. The program's user addresses aren't valid there. That's the whole reason for the `SystemBuffer` and the APC in step 9.
- **Steps 6–8 run at DISPATCH_LEVEL or above**, so nothing there may wait. The IRP, the system buffer, and every queue they touch must be in nonpaged memory. The DPC must not block on anything. If it needs to do something that waits (for example, a slow bus transaction), it must hand that off to a work item running at PASSIVE_LEVEL. A DPC that spins waiting for hardware is how you get bug check 0x133.
- **The IRP is the only thing that connects the two halves.** The dispatch routine and the DPC never call each other. The dispatch routine leaves the IRP on a queue, and the DPC finds it there later.

### 7.2 The code (WDM style), dispatch half and completion half

```c
// ---- Dispatch half: runs on the PROGRAM's thread, PASSIVE_LEVEL ----
NTSTATUS MyDispatchRead(PDEVICE_OBJECT DeviceObject, PIRP Irp)
{
    PMY_EXT ext = DeviceObject->DeviceExtension;
    KIRQL old;

    IoMarkIrpPending(Irp);                              // promise: someone will complete this later
    KeAcquireSpinLock(&ext->QueueLock, &old);           // → DISPATCH_LEVEL (the DPC also touches the queue)
    InsertTailList(&ext->ReadQueue, &Irp->Tail.Overlay.ListEntry);
    KeReleaseSpinLock(&ext->QueueLock, old);            // → back to PASSIVE_LEVEL

    WRITE_REGISTER_ULONG(&ext->Regs->Control, START_READ);   // kick the hardware
    return STATUS_PENDING;                              // DON'T touch Irp after this point
}

// ---- Interrupt half: ISR at DIRQL, keep it tiny ----
BOOLEAN MyIsr(PKINTERRUPT Interrupt, PVOID Context)
{
    PMY_EXT ext = Context;
    ULONG status = READ_REGISTER_ULONG(&ext->Regs->Status);
    if (!(status & DATA_READY)) return FALSE;           // not our device
    WRITE_REGISTER_ULONG(&ext->Regs->IntMask, 0);       // mask the source so it stops interrupting
    IoRequestDpc(ext->DeviceObject, NULL, NULL);        // finish the work at DISPATCH_LEVEL
    return TRUE;
}

// ---- Completion half: DPC at DISPATCH_LEVEL, on whatever thread was interrupted ----
VOID MyDpc(PKDPC Dpc, PDEVICE_OBJECT DeviceObject, PIRP Unused, PVOID Context)
{
    PMY_EXT ext = DeviceObject->DeviceExtension;
    PLIST_ENTRY link;
    PIRP irp;

    KeAcquireSpinLockAtDpcLevel(&ext->QueueLock);
    link = RemoveHeadList(&ext->ReadQueue);
    KeReleaseSpinLockFromDpcLevel(&ext->QueueLock);
    irp = CONTAINING_RECORD(link, IRP, Tail.Overlay.ListEntry);   // link address − 0xa8 = IRP address

    ULONG n = CopyFromDeviceFifo(ext, irp->AssociatedIrp.SystemBuffer,
                                 IoGetCurrentIrpStackLocation(irp)->Parameters.Read.Length);
    irp->IoStatus.Status = STATUS_SUCCESS;
    irp->IoStatus.Information = n;
    IoCompleteRequest(irp, IO_NO_INCREMENT);            // from here, the I/O manager takes over (step 8)

    WRITE_REGISTER_ULONG(&ext->Regs->IntMask, DATA_READY);   // unmask only after the data is drained
}
```

(Simplified to show the IRP's path: a real driver would also handle cancellation, an empty queue, and errors.)

Look at the `CONTAINING_RECORD` line. The queue holds links to the IRP's `Tail.Overlay.ListEntry` field at `+0xa8`, so the DPC subtracts `0xa8` to get back to the IRP's start. That's the §1.6 idea in real code.

### 7.3 The same thing in KMDF

Most new drivers use KMDF (the Kernel-Mode Driver Framework), which hides the IRP behind a **request object** and manages the queue and cancellation for you. The IRP is still there underneath. KMDF registers its own functions in the `MajorFunction` table (so `!drvobj` on a KMDF driver shows dispatch entries inside `Wdf01000.sys`, not the driver), wraps each incoming IRP in a `WDFREQUEST`, puts it on a `WDFQUEUE`, and calls your callback:

```c
// The framework calls this with a WDFREQUEST; the IRP is inside it.
VOID MyEvtIoRead(WDFQUEUE Queue, WDFREQUEST Request, size_t Length)
{
    // Park it in a manual queue until the hardware has data (framework handles cancellation).
    WdfRequestForwardToIoQueue(Request, GetDevCtx(WdfIoQueueGetDevice(Queue))->PendingReads);
    StartHardware(...);
}

// Later, from the DPC (EvtInterruptDpc), at DISPATCH_LEVEL:
//   WdfIoQueueRetrieveNextRequest(pendingReads, &request);
//   ...copy data into the buffer from WdfRequestRetrieveOutputBuffer(request, ...)...
//   WdfRequestCompleteWithInformation(request, STATUS_SUCCESS, n);   // → IoCompleteRequest underneath
//
// If you ever need the raw IRP: PIRP irp = WdfRequestWdmGetIrp(request);
```

The pipeline doesn't change: build, call down, park, complete back up, deliver in the requester's thread. KMDF only changes who writes the bookkeeping code.

---

## 8. Stacks of drivers: passing down and completing back up

Real devices are served by a **stack** of drivers. A typical one, top to bottom:

```
   upper filter driver     (optional: adds or modifies behavior)
   function driver (FDO)   (knows how to operate THIS device)
   lower filter (optional)
   bus driver (PDO)        (owns the bus the device sits on: USB, PCI, the SoC's I2C/SPI…)
```

Each layer is a DEVICE_OBJECT, linked bottom-to-top by `AttachedDevice`. The I/O manager always sends a new IRP to the **top** of the stack, and that top device's `StackSize` (3 here) decides how many stack locations to allocate.

### 8.1 Passing an IRP down, with an optional "tell me when it's done"

```c
// In the FILTER's dispatch routine (top driver), WDM style:
NTSTATUS FilterDispatchRead(PDEVICE_OBJECT DeviceObject, PIRP Irp)
{
    PFILTER_EXT ext = DeviceObject->DeviceExtension;

    // 1. Give the next driver the same parameters I received:
    //    copies MY stack location into the one BELOW (lower address), minus my completion routine.
    IoCopyCurrentIrpStackLocationToNext(Irp);

    // 2. Ask to be called back on the way up. This writes my routine into the NEXT
    //    location's CompletionRoutine/Context fields, because completion walks upward.
    IoSetCompletionRoutine(Irp, FilterReadDone, ext, TRUE, TRUE, TRUE);

    // 3. Send it to the device directly below mine.
    return IoCallDriver(ext->LowerDevice, Irp);         // current location moves down by one
}

NTSTATUS FilterReadDone(PDEVICE_OBJECT DeviceObject, PIRP Irp, PVOID Context)
{
    if (Irp->PendingReturned)
        IoMarkIrpPending(Irp);          // propagate the "pending" mark up to MY location (classic rule)
    // inspect or adjust Irp->IoStatus / the data here...
    return STATUS_CONTINUE_COMPLETION;  // let completion keep walking up
                                        // (STATUS_MORE_PROCESSING_REQUIRED would stop it and keep the IRP)
}
```

A driver that doesn't need a callback uses `IoSkipCurrentIrpStackLocation(Irp)` instead of steps 1–2. That moves the current location back up by one, so the lower driver **reuses** this driver's location. It's slightly cheaper.

### 8.2 What the three stack locations look like when the IRP is stuck at the bottom

Suppose the bus driver at the bottom has the IRP pending, waiting for hardware. `!irp` would show:

```
kd> !irp ffffb10e`51a0c010
Irp is active with 3 stacks 1 is current (= 0xffffb10e51a0c0e0)
 Mdl=ffffb10e52b17000: No System Buffer: Thread ffffb10e4f2d9080:  Irp stack trace.
     cmd  flg cl Device   File     Completion-Context
>[IRP_MJ_READ(3), N/A(0)]
            0  1 ffffb10e4e771060 00000000 00000000-00000000    pending
	       \Driver\BusDriverX
			Args: 00000040 00000000 00000000 00000000
 [IRP_MJ_READ(3), N/A(0)]
            0 e1 ffffb10e4e7728a0 00000000 fffff8009c4d1a20-ffffb10e4e7729f0
	       \Driver\VendorFunc	Success Error Cancel pending
			Args: 00000040 00000000 00000000 00000000
 [IRP_MJ_READ(3), N/A(0)]
            0 e1 ffffb10e4e7743d0 ffffb10e50c8f9b0 fffff8009c5e2010-ffffb10e4e774520
	       \Driver\VendorFilter	Success Error Cancel pending
			Args: 00000040 00000000 00000000 00000000
```

(Illustrative, with made-up driver names. The shape is the point.) How to read it:
- **3 stacks, 1 is current**: the IRP has gone all the way down to the **bottom** location, and `>` marks it. It sits at `IRP + 0xD0`, the lowest address, listed **first**.
- The **top** driver (`VendorFilter`) is listed **last**, at location 3 (`IRP + 0x160`).
- `cl` (Control) `1` = `SL_PENDING_RETURNED` at the bottom: the bus driver returned `STATUS_PENDING`. `e1` = `0x80 + 0x40 + 0x20 + 0x01`: invoke on error, success and cancel, plus pending returned (propagated up).
- **Completion-Context** in location 2 is `fffff8009c4d1a20-…`: a completion routine **installed by the driver above** (`VendorFilter`'s `FilterReadDone`, in `fffff800…` code). `ln` would name it.
- `Mdl=…: No System Buffer`: this read uses **Direct I/O**. The user's pages are locked in memory and described by an MDL, instead of being copied through a system buffer.

When the bus driver finally calls `IoCompleteRequest`, completion walks upward: location 1 has no routine; location 2's routine (the filter's) runs; location 3 has none; then the I/O manager's final processing runs.

```
                    going DOWN (IoCallDriver)            coming UP (IoCompleteRequest)
                    ─────────────────────────            ───────────────────────────────
 loc 3  IRP+0x160   VendorFilter dispatch ─┐            ┌► (no routine here) ─► I/O manager final processing
 loc 2  IRP+0x118   VendorFunc dispatch  ◄─┘─┐          │  FilterReadDone  ◄── stored in loc 2 by VendorFilter
 loc 1  IRP+0x0D0   BusDriverX dispatch  ◄───┘          │  (no routine here)
                    → returns PENDING                   │
                    ... interrupt, DPC ...  ────────────┘  IoCompleteRequest(irp) in BusDriverX's DPC
```

---

## 9. Where IRPs show up when things go wrong

Now the audio lecture's references make concrete sense:

| Situation | What you see | First moves |
|---|---|---|
| **0x9F DRIVER_POWER_STATE_FAILURE, parameter 1 = 3** | A power IRP (`IRP_MJ_POWER`) wasn't completed in time. Parameter 4 is that IRP's address. Parameter 2 is the device at the bottom of the stack. | `!irp <P4>`: which location is current, and which driver is it? Is it marked pending? Then `!devstack <P2>` for the whole stack, and `!poaction` for the overall transition. |
| **A thread hung in I/O** | `!thread` shows the thread waiting, with an `IRP List:` entry. | `!irp` on that IRP: which driver holds it? If it's pending at a driver, why hasn't that driver's DPC or work item completed it? |
| **"Where are all the stuck IRPs?"** | No starting point | `!irpfind` scans nonpaged pool for blocks tagged `Irp ` and lists them. It's slow, but it finds IRPs nobody points to anymore. |
| **0x44 MULTIPLE_IRP_COMPLETE_REQUESTS** | A driver called `IoCompleteRequest` twice on the same IRP. | The stack shows the second completion. The first completion already freed the IRP, so the second call is touching memory that may already belong to someone else. |
| **Random corruption, 0x50 or 0xD1 inside the I/O manager** | Often a driver touched an IRP **after** completing it, or after returning `STATUS_PENDING` while another CPU completed it. | Enable Driver Verifier's I/O verification on the suspect driver. It checks IRP handling rules and catches these at the moment they happen. |
| **0x35 NO_MORE_IRP_STACK_LOCATIONS** | A driver passed an IRP down without enough locations, usually after attaching to a stack without updating its own `StackSize`. | `!irp` on parameter 1: compare `StackCount` with how deep the stack really is. |

The common pattern: **every one of these questions is "where is this block, and which driver's stack location is current?"** That's exactly what §1 to §5 prepare you to answer.

---

## 10. Misconceptions

| You might think | Reality | Why it matters |
|---|---|---|
| An IRP is a process or thread that runs. | It's a **data structure**. Code runs *on* it: the I/O manager, then each driver, on whatever thread calls them. | In a dump, you look *at* an IRP to see where it's stuck; you don't look for it "running". |
| The I/O manager puts the IRP on a queue and the driver picks it up. | `IoCallDriver` **directly calls** the driver's function, on the requesting thread. Queuing happens only if the driver chooses to park it. | Explains why the dispatch routine runs at PASSIVE_LEVEL in the caller's context, and why the call stack shows the program's frames below the driver. |
| There's one stack location, and it's overwritten as the IRP goes down. | There's **one per driver**, allocated together, and each keeps its parameters and completion routine. | Completion routines work only because each layer's location survives until completion walks back up. |
| The top driver uses the first stack location. | The top driver uses the **last** one (highest address). "Current" counts **down** as the IRP descends. | In `!irp`, the top driver is printed **last**; the `>` marks where the IRP is now. |
| The driver writes results straight into the program's buffer. | For buffered I/O, it writes into the **kernel** `SystemBuffer`. The I/O manager copies to the program's buffer at the end, **in the program's thread**. | User addresses are only valid in the right process, and completion often runs in a DPC on an unrelated thread. |
| The I/O manager "takes the data from the buffer" during the request. | The **driver** fills the buffer and sets `IoStatus.Information`. The I/O manager only copies back that many bytes, **after** the driver completes the request. | If `Information` is wrong, the program gets the wrong amount of data even though the driver wrote it correctly. |
| `STATUS_PENDING` is the result. | It's a promise that the real result will arrive later in `IoStatus`. | A pending IRP that nobody completes is a hang with no crash and no error. |
| After `IoCompleteRequest`, I can still read the IRP. | It may already be freed and reused. | Classic cause of 0x44 and of random corruption. |
| Memory addresses in the debugger are random numbers. | Each is the address of a block's first byte, or a field inside one. Their ranges tell you user vs kernel vs code, and the first bytes of many blocks tell you their type. | It turns "a wall of numbers" into "a set of blocks with arrows between them". |

---

## 11. Self-check questions

**1.** A program calls `DeviceIoControl` on a device whose stack has a filter on top of a function driver on top of a bus driver. How many bytes does the IRP allocation take on 64-bit Windows, and which stack location (by offset from the IRP's start) will the filter driver use?

<details><summary>Answer</summary>

`StackSize` of the top device = 3, so `0xD0 + 3 × 0x48 = 0xD0 + 0xD8 = 0x1A8` bytes. The filter is called first, so it gets location 3: `0xD0 + 2 × 0x48 = 0x160` from the start (the highest address). The bus driver gets location 1 at `+0xD0`.
</details>

**2.** "How does the driver find out there's a new request?" Answer in one sentence, then name the two fields `IoCallDriver` reads to find the function.

<details><summary>Answer</summary>

It's called: `IoCallDriver` directly calls the driver's dispatch routine with the device and IRP pointers, on the requesting thread. It reads `DeviceObject->DriverObject` (+0x08) and then `DriverObject->MajorFunction[stackLocation->MajorFunction]` (+0x70 + 8 × major).
</details>

**3.** You see this in a raw dump: `ffffb10e`4c2f7a40  ffffb10e`4d0e5650 ffffb10e`4d0e5650`. The block starts at `ffffb10e`4c2f7a20`. What field is this, and what does the repeated value tell you?

<details><summary>Answer</summary>

Offset `0x20` from the block start: `ThreadListEntry` (Flink, Blink). The same pointer twice means a one-entry list: this is the thread's only outstanding IRP, and `ffffb10e`4d0e5650` is the list head inside the thread object.
</details>

**4.** Why does buffered I/O copy the data twice (user → system buffer → user) instead of letting the driver use the program's buffer directly? Give two reasons.

<details><summary>Answer</summary>

(1) The program's buffer is a **user-mode address**, valid only in that process. Completion can run in a DPC on a different thread in a different process, where that address means something else or nothing. (2) User memory can be **paged out or freed** by another thread at any moment. A driver touching it at DISPATCH_LEVEL could fault (0xD1), and trusting user pointers is a security hole. The kernel buffer is nonpaged, private, and owned by the I/O manager.
</details>

**5.** A dispatch routine does `InsertTailList(&q, &Irp->Tail.Overlay.ListEntry); return STATUS_PENDING;` but forgets `IoMarkIrpPending`. What rule did it break, and what can go wrong?

<details><summary>Answer</summary>

Returning `STATUS_PENDING` requires the `SL_PENDING_RETURNED` mark in the driver's stack location. Without it, the I/O manager and the drivers above can disagree about whether the request finished synchronously. The final processing can then run in the wrong way, for example the caller waits forever, or the completion work is done twice. Driver Verifier's I/O checks flag this.
</details>

**6.** In the async timeline, why must the final copy-back run through an APC to the requesting thread, rather than inside the DPC that calls `IoCompleteRequest`?

<details><summary>Answer</summary>

The DPC runs on whatever thread was interrupted, in whatever process that thread belongs to, at DISPATCH_LEVEL. The program's buffer and I/O status block are user addresses in the **requesting** process, and they may also be pageable. The APC runs in the requesting thread, in the right process and at a level where page faults can be handled.
</details>

**7.** `dt nt!_IRP` shows `AssociatedIrp` with `MasterIrp`, `IrpCount` and `SystemBuffer` all at `+0x000`, with different-looking values. Which one is real, and how do you decide?

<details><summary>Answer</summary>

They're a union: the same 8 bytes with three interpretations. Use the other fields to decide. If `Flags` includes `IRP_BUFFERED_IO` (0x10), it's `SystemBuffer`. For an associated (child) IRP of a split request, it's `MasterIrp`. For the master of such a split, it's `IrpCount`.
</details>

**8.** You're handed bug check 0x9F with parameter 1 = 3 and parameter 4 = an address. What's your first command, and which two things in its output do you look at first?

<details><summary>Answer</summary>

`!irp <parameter 4>`. Look at which stack location is current (the `>` line), and the driver named on that line. Then check whether that location shows "pending" (Control bit 1). That driver is holding the power IRP.
</details>

**9.** In `!irp` output, a stack location's Completion-Context column shows a routine address. Which driver installed that routine: the one on that line, or a different one?

<details><summary>Answer</summary>

The driver **above** it (the next location up, listed below it in `!irp`'s output). `IoSetCompletionRoutine` writes into the *next lower* location, because completion walks upward and calls each location's routine once the drivers below are done.
</details>

**10.** Decode IRP header `Flags = 0x00000070` and `IOCTL = 0x80006004`.

<details><summary>Answer</summary>

`0x70` = `0x40` (input operation: copy back to the caller) + `0x20` (deallocate the system buffer) + `0x10` (buffered I/O). `0x80006004`: device type = top 16 bits = `0x8000`; access = bits 15–14 = `0x6004 >> 14` = 1 (`FILE_READ_ACCESS`); function = bits 13–2 = `(0x6004 >> 2) & 0xFFF` = `0x801`; method = low 2 bits = 0 (`METHOD_BUFFERED`). That's TgCounter's `IOCTL_TGCOUNTER_GET`.
</details>

**11.** Starting from a raw IRP address and no extension commands, how would you find the name of the driver whose dispatch routine is handling it? List the hops with offsets.

<details><summary>Answer</summary>

IRP `+0xb8` → current stack location; that location `+0x28` → DEVICE_OBJECT; device `+0x08` → DRIVER_OBJECT; driver `+0x38` → `DriverName` (a UNICODE_STRING; `dt nt!_UNICODE_STRING` or `dS` prints it). Optionally, driver `+0x70 + 8 × MajorFunction` → the routine's address, and `ln` names it.
</details>

---

## 12. Sources

All checked 2026-11-11.

- Vergilius Project, Windows 11 24H2 x64 structure layouts: `_IRP` (0xD0 bytes; MdlAddress 0x8, Flags 0x10, AssociatedIrp 0x18, ThreadListEntry 0x20, IoStatus 0x30, …, Tail 0x78 with Thread 0x98, ListEntry 0xa8, CurrentStackLocation 0xb8, OriginalFileObject 0xc0), `_IO_STACK_LOCATION` (0x48 bytes), `_DEVICE_OBJECT`, `_DRIVER_OBJECT` (MajorFunction at 0x70, 28 entries), `_FILE_OBJECT`. vergiliusproject.com/kernels/x64/windows-11/24h2/
- Microsoft Learn: IoAllocateIrp (allocated from nonpaged system space; IRPs a driver allocates aren't associated with a thread and must be freed by that driver).
- Geoff Chappell, "PP_NPAGED_LOOKASIDE_NUMBER" and lookaside list studies: per-processor lookaside lists for IRPs (per-processor first, then shared, then pool).
- ReactOS `ntoskrnl/io/iomgr/irp.c` (a clean-room reimplementation, used here only as a readable model of the algorithm: lookaside choice by stack size, `IRP_ALLOCATED_FIXED_SIZE`, `TAG_IRP`).
- SSD Secure Disclosure advisory on ksthunk.sys: decompiled `IopfCompleteRequest` showing the special kernel APC initialized at IRP + 120 (0x78, i.e. over `Tail`) and queued to `Tail.Overlay.Thread`, and the user IO_STATUS_BLOCK copy.
- Microsoft Learn (WDK): IoCallDriver, IoCompleteRequest, IoMarkIrpPending, IoSetCompletionRoutine, IoCopyCurrentIrpStackLocationToNext / IoSkipCurrentIrpStackLocation, CTL_CODE / buffer descriptions for I/O control codes, `!irp`, `!drvobj`, `!thread`, `!irpfind`, `!pool`, `dt`, `dx` debugger references; Bug Check 0x9F, 0x44, 0x35.
- Debugger listings in §5 and §8 are illustrative: layouts and offsets are real for this build; addresses, driver names in §8, and minor formatting are constructed to be consistent, not captured from a live session.
