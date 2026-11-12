2026_11_12_12_00-(WinDbg-Triage-Walkthrough-1)

# Walkthrough 001 — WinDbg Triage: Six Investigations, Command by Command

> **For:** Timothy · **Date:** 2026-11-12
> **Type:** walkthrough. You don't type anything. You read investigations as they happen: the situation, the reasoning, the command, the output, what it means, and how it changes the next step.
> **Prerequisites:** none. Every structure, piece of code and debugger output used here is shown here. All debugger sessions are **simulated**: the command names, output formats, structure layouts and OS behavior are real, but the addresses, driver names (`vendornet`, `camvendor`, `sensorflt`, `vendori2c`, `tpfilter`) and values are invented and made consistent with each other.
> **Why this document:** you asked for scenario-driven walkthroughs: example inputs and outputs, how to interpret them, how each result changes the triage path, and how Windows itself works underneath. You said you learn best by reading worked examples.

---

## Core ideas (the answer key)

1. **Triage is a loop, not a recipe:** state a hypothesis → pick the command whose output would *distinguish* between hypotheses → read the output → update. Every command in this document is chosen because it splits the possibilities.
2. **The bug check name tells you the *category*; the parameters tell you *where to look next*.** A small faulting address (like `0x48`) means "NULL pointer plus a field offset".
3. **The top of the stack is usually the machinery that noticed, not the culprit.** Find the boundary (a trap frame, an interrupt, the bug check call) and look just below it.
4. **Context matters as much as code:** whether code ran as a DPC, a worker thread, or a system call decides what it was allowed to do. `PROCESS_NAME: System` in a DPC crash just means "whatever was running when the interrupt landed".
5. **Registers + disassembly + structure layout = which field was bad.** `.trap` restores the registers at the fault, `u`/`ub` show the instructions, and `dt` names the field at that offset.
6. **Crashes, stuck requests and hangs need different tools.** For a crash, find the faulting instruction. For a stuck request, follow the IRP to the driver holding it and the thread working on it. For a hang, ask what every CPU is doing (busy hang) or who holds what (deadlock).
7. **Waiting is visible.** `!thread` shows what a thread waits on and for how long (`Ticks`). An ownership chain that loops back on itself is a deadlock.
8. **The first dump often shows the victim. The second, with Driver Verifier, shows the culprit.** Use-after-free and races corrupt memory far from where the crash happens. Special pool and tracking turn them into immediate, attributable crashes.
9. **Architecture changes the surface, not the method.** On Arm64 vs x64, arguments, return addresses and instructions look different, but "register value + offset = address touched" works the same way.
10. **A conclusion is a 4-line triage note:** stop code in plain words, owner module (and who owns it), context/IRQL, and the next capture or fix.

---

## Table of Contents

0. [Why these six scenarios](#0-why-these-six-scenarios)
1. [How to read a WinDbg session (start here)](#1-how-to-read-a-windbg-session)
2. [Scenario 1 — A blue screen when a USB network adapter is unplugged (0xD1, Arm64)](#scenario-1)
3. [Interlude — Reading Arm64 and x64 side by side](#interlude-arm64-vs-x64)
4. [Scenario 2 — A tablet crashes going to sleep (0x9F, a stuck power IRP)](#scenario-2)
5. [Scenario 3 — The screen freezes, no blue screen (a deadlock)](#scenario-3)
6. [Scenario 4 — Freezes, then 0x133 (a DPC that never finishes, x64)](#scenario-4)
7. [Scenario 5 — Random crashes in different places (use-after-free, two dumps)](#scenario-5)
8. [Scenario 6 — 0x101: a processor went silent](#scenario-6)
9. [Patterns across all six](#9-patterns-across-all-six)
10. [Command reference, organized by question](#10-command-reference)
11. [Misconceptions](#11-misconceptions)
12. [Self-check questions](#12-self-check-questions)
13. [Sources](#13-sources)

---

## 0. Why these six scenarios

There are hundreds of bug check codes and hundreds of debugger commands. Most real investigations, though, fall into a few **shapes**, and each shape teaches a different way of thinking. I picked the scenarios to cover the shapes with the most value per hour of study, ranked roughly by how often they show up on real hardware and how much reasoning carries over to other cases:

| # | Shape | What it teaches about the debugger | What it teaches about Windows |
|---|---|---|---|
| 1 | **Bad pointer at raised IRQL** | symbols, `!analyze`, the stack, trap frames, registers, disassembly, `dt` | DPCs and their context; Plug and Play surprise removal and teardown ordering |
| 2 | **A request that never finishes** | `!irp`, `!devstack`, `!poaction`, finding the thread doing the work, `!thread`, the KMDF log | power IRPs; the order in which KMDF powers a device down |
| 3 | **Idle hang (deadlock)** | forced dumps, `!running`, `!locks`, wait chains | dispatcher objects, waits, mutexes vs resources, lock ordering |
| 4 | **Busy hang** | reading through an interrupt frame, `!dpcs`, disassembling a loop (x64) | the DPC watchdog, why a DPC must never wait for hardware |
| 5 | **Memory corruption** | `!pool`, two-dump iteration, Driver Verifier special pool, `!verifier` logs | the pool allocator, tags, cancellation races |
| 6 | **A CPU stops responding** | switching processors, recognizing "outside Windows" | processor idle states and the firmware boundary |

What I deliberately left out: user-mode debugging, kernel debugger setup, and long lists of commands. Those are easy to look up once you have the reasoning.

---

## 1. How to read a WinDbg session

### 1.1 What the debugger is looking at

WinDbg is a **reader of memory and processor state**. It can be pointed at three kinds of target:

| Target | How you get it | What you can do |
|---|---|---|
| **A dump file** (`MEMORY.DMP`, a minidump, a live dump) | the machine crashed, or someone took a snapshot | read everything that was saved; nothing moves; you can't run anything |
| **A live kernel, from another machine** (host ↔ target over KDNET) | debugger attached over a network or USB cable | freeze the target, read, set breakpoints, step, resume |
| **A live kernel, locally** (`lkd>` prompt) | WinDbg on the same machine | read memory only; no freezing, no breakpoints, can't debug a crash |

Every scenario below is a **dump file**, except Scenario 3, which starts from a dump we *force* on purpose.

### 1.2 Anatomy of a line

```
0: kd> !irp ffffc283`14a9b8a0
│  │   │    └─ argument: an address (backtick only splits it for readability)
│  │   └─ command: "!" means an extension (a plug-in that knows some structure)
│  └─ "kd" = kernel debugger
└─ the processor whose context you're currently viewing (0, 1, 2, ...)
```

Everything after the prompt line, until the next prompt, is output.

### 1.3 Number conventions

| You see | Means |
|---|---|
| `48`, `ffff…` with no prefix | **hexadecimal**: WinDbg's default |
| `0n120` | decimal 120 (the `0n` prefix) |
| `0x48`, `48h` | hexadecimal, written explicitly |
| `ffffc283`14a9b8a0` | one 64-bit hex number; the backtick is only for readability |
| `module!Function+0x5c` | 0x5c bytes past the start of `Function` inside `module` |
| `module+0x1464` | 0x1464 bytes past the start of the module: **no symbols** for it |

### 1.4 Address ranges at a glance

```
0000xxxx`xxxxxxxx  user mode (valid only inside one process)
ffff8xxx…ffffexxx  kernel dynamic memory: pool allocations, objects, stacks
fffff80x`xxxxxxxx  kernel and driver images: code and global data
00000000`000000xx  not a real address: NULL plus a small offset
```

### 1.5 The first commands of any session

```
0: kd> .symfix                    ← use Microsoft's public symbol server (+ local cache)
0: kd> .sympath+ C:\vendorsyms    ← ALSO look in this folder (e.g. symbols a vendor gave you)
0: kd> .reload                    ← reload symbols for every loaded module
0: kd> !analyze -v                ← automatic first analysis
```

And the five questions every crash dump gets, in order:

| Question | Command |
|---|---|
| What happened (category + parameters)? | `!analyze -v` |
| What code path led here? | `k` (the stack) |
| Whose code is it? | `lm`, `lmvm <module>` |
| On whose behalf was it running? | `!thread`, `!process` |
| At what priority level? | `!irql` |

The scenarios use this skeleton and then branch, depending on what each answer reveals.

---

<a id="scenario-1"></a>
## Scenario 1 — A blue screen when a USB network adapter is unplugged (0xD1, Arm64)

### The situation

An Arm64 tablet occasionally blue-screens when a USB Ethernet adapter is unplugged while traffic is flowing. It happens maybe once in twenty unplugs. A kernel dump was collected.

**Initial hypotheses** (it helps to write these down before running anything):
- (A) The adapter's driver touches something after the device is gone.
- (B) The USB stack itself mishandles the removal.
- (C) Unrelated: unplugging just happens to coincide with a crash from something else.

The first commands should tell us *whose code* faulted, which separates A and B from C.

### Step 1 — The automatic analysis

```
0: kd> !analyze -v
*******************************************************************************
*                        Bugcheck Analysis                                    *
*******************************************************************************

DRIVER_IRQL_NOT_LESS_OR_EQUAL (d1)
An attempt was made to access a pageable (or completely invalid) address at an
interrupt request level (IRQL) that is too high.  This is usually
caused by drivers using improper addresses.
If kernel debugger is available get stack backtrace.
Arguments:
Arg1: 0000000000000048, memory referenced
Arg2: 0000000000000002, IRQL
Arg3: 0000000000000000, value 0 = read operation, 1 = write operation
Arg4: fffff8063a2b1464, address which referenced memory

Debugging Details:
------------------
*** WARNING: Unable to verify timestamp for vendornet.sys

READ_ADDRESS:  0000000000000048

IRQL:  2

PROCESS_NAME:  System

TRAP_FRAME:  ffff9a81`2c4e7690 -- (.trap 0xffff9a812c4e7690)

STACK_TEXT:
ffff9a81`2c4e7410 fffff806`36a41c2c     : nt!KeBugCheckEx
ffff9a81`2c4e7420 fffff806`36a1f6b8     : nt!KiBugCheckDispatch+0x6c
ffff9a81`2c4e7460 fffff806`36a1b2d0     : nt!KiSystemFatalException+0x...
ffff9a81`2c4e7690 fffff806`3a2b1464     : nt!KiDataAbortException+0x...
ffff9a81`2c4e77a0 fffff806`368c41f0     : vendornet+0x1464
ffff9a81`2c4e7800 fffff806`368c3a4c     : nt!KiExecuteAllDpcs+0x2f0
ffff9a81`2c4e7980 fffff806`36a1e8d8     : nt!KiRetireDpcList+0x1ac
ffff9a81`2c4e7c10 00000000`00000000     : nt!KiIdleLoop+0x58

MODULE_NAME: vendornet
IMAGE_NAME:  vendornet.sys
FAILURE_BUCKET_ID:  AV_vendornet!unknown_function
```

**Reading it, line by line:**
- **`DRIVER_IRQL_NOT_LESS_OR_EQUAL (d1)`**: a driver touched memory it may not touch at its current IRQL. Either the address was invalid, or it was pageable and the IRQL was too high to bring it in.
- **`Arg1 = 0x48`**: the address touched. **No real object lives at address `0x48`.** This is almost always **a NULL pointer plus an offset**: the code read a field at offset `0x48` of a structure whose pointer was NULL. Remember this number; it comes back later.
- **`Arg2 = 2`**: IRQL 2 = **DISPATCH_LEVEL**. The scheduler can't run here, so this code may not wait and may not take page faults.
- **`Arg3 = 0`**: it was a **read**.
- **`Arg4`**: the instruction that did it, inside `vendornet.sys` (see the stack).
- **The warning and `vendornet+0x1464`**: no symbols for `vendornet.sys`, so we know *which module* but not *which function*.
- **`PROCESS_NAME: System`**: tempting to read as "the System process did it". It doesn't mean that here; Step 3 explains.
- **`FAILURE_BUCKET_ID`**: `AV` = access violation, then the module and function (unknown, because no symbols).

**What this does to our hypotheses:** the faulting instruction is in `vendornet.sys`, the adapter's own driver. (C) is now unlikely. (B) isn't excluded yet, because a USB stack bug could have handed vendornet a bad pointer, but (A) leads.

### Step 2 — Get symbols for the culprit

The vendor provided its symbol file. We add it and reload:

```
0: kd> .sympath+ C:\vendorsyms
Symbol search path is: srv*;C:\vendorsyms
0: kd> .reload /f vendornet.sys
0: kd> lmvm vendornet
Browse full module list
start             end                 module name
fffff806`3a2b0000 fffff806`3a2d6000   vendornet   (private pdb symbols)  C:\vendorsyms\vendornet.pdb
    Loaded symbol image file: vendornet.sys
    Image path: \SystemRoot\System32\drivers\vendornet.sys
    Timestamp:        Tue Mar  4 10:12:55 2025
    CompanyName:      Example Vendor Inc.
    FileVersion:      3.1.0.12
```

`(private pdb symbols)` means the full symbol file: function names, types and source lines. The `CompanyName` confirms whose driver this is. Re-running the stack:

```
0: kd> k
 # Child-SP          RetAddr               Call Site
00 ffff9a81`2c4e7410 fffff806`36a41c2c     nt!KeBugCheckEx
01 ffff9a81`2c4e7420 fffff806`36a1f6b8     nt!KiBugCheckDispatch+0x6c
02 ffff9a81`2c4e7460 fffff806`36a1b2d0     nt!KiSystemFatalException+0x...
03 ffff9a81`2c4e7690 fffff806`3a2b1464     nt!KiDataAbortException+0x...
04 ffff9a81`2c4e77a0 fffff806`368c41f0     vendornet!VnRxDpcRoutine+0x64 [vnrx.c @ 212]
05 ffff9a81`2c4e7800 fffff806`368c3a4c     nt!KiExecuteAllDpcs+0x2f0
06 ffff9a81`2c4e7980 fffff806`36a1e8d8     nt!KiRetireDpcList+0x1ac
07 ffff9a81`2c4e7c10 00000000`00000000     nt!KiIdleLoop+0x58
```

### Step 3 — Read the stack's *shape*: what context was this?

Read it **bottom to top** (oldest call first):

```
07 nt!KiIdleLoop              ← this processor had nothing to do: it was running its idle thread
06 nt!KiRetireDpcList         ← ...then it noticed DPCs queued for it
05 nt!KiExecuteAllDpcs        ← ...and started running them
04 vendornet!VnRxDpcRoutine   ← vendornet's "receive" DPC         ◄── the culprit's code
03 nt!KiDataAbortException    ← the CPU raised an exception (a data abort = bad memory access on Arm64)
02..00                        ← the kernel decided it couldn't recover and bug checked
```

> **Windows concept: a DPC has no "owner".** A **DPC** (Deferred Procedure Call) is work that an interrupt handler queues to run a bit later, at DISPATCH_LEVEL. The kernel runs queued DPCs on whatever thread happens to be current on that processor. Here it was the **idle thread**, which belongs to the System/Idle process. That's why `PROCESS_NAME: System` shows up. It tells you nothing about who *requested* the work. When you see `KiExecuteAllDpcs` or `KiRetireDpcList` below a driver frame, read the driver frame as "running as a DPC, IRQL 2, may not wait, may not page-fault", and **ignore the process name**.

So now we know the context: vendornet's receive DPC, at DISPATCH_LEVEL, read address `0x48`.

### Step 4 — Restore the registers at the moment of the fault

The frames above `VnRxDpcRoutine` are exception handling. The registers they show belong to the kernel's handler, not to the faulting instruction. The **trap frame** is where the CPU's state was saved when the exception happened. `!analyze` already gave us the command:

```
0: kd> .trap 0xffff9a812c4e7690
NOTE: The trap frame does not contain all registers.
Some register values may be zeroed or incorrect.
 x0=ffffa50c2e3f1018   x1=0000000000000000   x2=0000000000000000   x3=0000000000000000
 x4=0000000000000000   x5=0000000000000000   x6=0000000000000000   x7=0000000000000000
 x8=0000000000000000   x9=0000000000000000  x10=0000000000000000  x11=0000000000000000
x12=0000000000000000  x13=0000000000000000  x14=0000000000000000  x15=0000000000000000
x16=0000000000000000  x17=0000000000000000
 fp=ffff9a812c4e77a0   lr=fffff8063a2b1440   sp=ffff9a812c4e77a0   pc=fffff8063a2b1464
psr=60400085 -ZC- EL1
vendornet!VnRxDpcRoutine+0x64:
fffff806`3a2b1464 b9404909 ldr         w9,[x8,#0x48]
```

The debugger's view is now "as if we were stopped at the faulting instruction". Read the last two lines:

```
fffff806`3a2b1464   b9404909   ldr  w9,[x8,#0x48]
│                    │          │    │   └────────── address = (value in x8) + 0x48
│                    │          │    └────────────── destination: w9 (32-bit view of register x9)
│                    │          └─────────────────── "load register": read from memory
│                    └────────────────────────────── the 4 instruction bytes (Arm64 instructions are always 4 bytes)
└─────────────────────────────────────────────────── address of the instruction (= Arg4)
```

And `x8 = 0000000000000000`. So the address read was `0 + 0x48 = 0x48`, exactly Arg1. **The pointer in `x8` was NULL, and the code wanted the field at offset `0x48` of whatever `x8` was supposed to point to.**

Note on the warning: the trap frame doesn't save every register on Arm64 (the "callee-saved" ones like `x19`–`x28` aren't in it). So zeros in `x19`+ here don't mean "zero". The volatile registers (`x0`–`x17`) and `pc` are the trustworthy ones.

### Step 5 — Where did x8 come from? Disassemble backwards

`ub` = "unassemble backwards": show the instructions *before* an address.

```
0: kd> ub fffff806`3a2b1464 L6
vendornet!VnRxDpcRoutine+0x4c:
fffff806`3a2b144c aa0003f3 mov         x19,x0                 ; x19 = first argument
fffff806`3a2b1450 b9400668 ldr         w8,[x19,#4]            ; w8  = Adapter->State
fffff806`3a2b1454 7100091f cmp         w8,#2
fffff806`3a2b1458 540001a1 bne         vendornet!VnRxDpcRoutine+0x8c ; if State != Running, skip
fffff806`3a2b145c f9400a68 ldr         x8,[x19,#0x10]         ; x8  = Adapter->RxRing      ◄── loaded NULL
fffff806`3a2b1460 d503201f nop
```

Now the chain is visible:
1. `x19 = x0`: the first argument to the DPC routine. For a DPC, the driver passes a **context pointer** when it sets up the DPC; here it's the adapter's context structure.
2. `ldr w8,[x19,#4]`: read the field at `+0x4` (the adapter state) and compare it with 2. If it isn't 2, skip the receive work. **The check passed**, so the state *was* 2 at that instant.
3. `ldr x8,[x19,#0x10]`: read the pointer at `+0x10`. It was **NULL**.
4. `ldr w9,[x8,#0x48]`: read `+0x48` through that NULL pointer → crash.

> **Arm64 note:** since every Arm64 instruction is exactly 4 bytes, `ub` is always exact. On x64, instructions are 1 to 15 bytes long, so disassembling *backwards* is a guess and can show garbage. Section 3 covers this.

### Step 6 — Name the fields with the vendor's type information

We can look at the context structure with `dt`. Which address is it? `x0` in the trap frame was `ffffa50c2e3f1018`. That's `x0` at the fault, and `x0` was the first argument copied into `x19`. Before trusting it, check that it actually looks like the structure:

```
0: kd> dt vendornet!_VN_ADAPTER ffffa50c`2e3f1018
   +0x000 Signature        : 0x64417656  'VvAd'
   +0x004 State            : 3 ( VnAdapterRemoving )
   +0x008 Regs             : (null)
   +0x010 RxRing           : (null)
   +0x018 RxDpc            : _KDPC
   +0x058 RxLock           : 0
   +0x060 Device           : 0xffffa50c`2a1e7c30 WDFDEVICE__
   +0x068 RemoveCount      : 0n1
```

**Signature `VvAd`** matches what the vendor's code expects in this structure, so `x0` is plausible. Now the fields:
- `State` is **3 = VnAdapterRemoving**, but the code checked for `== 2` (Running) a moment earlier and the check **passed**.
- `RxRing` is **NULL**, and `Regs` too: the receive ring and the register mapping have been torn down.

So **between the state check and the `RxRing` read, another processor changed the state to Removing and freed the ring.** That's a race: two pieces of code running at the same time on different processors, with nothing ordering them.

### Step 7 — Confirm: was the device being removed at this moment?

If the race theory is right, the device should be mid-removal in the device tree. The context has `Device = 0xffffa50c2a1e7c30` (a KMDF handle). The usual way into the PnP view is `!devstack` on the device object. We'll take the device object address from the driver:

```
0: kd> !drvobj vendornet
Driver object (ffffa50c29d03e30) is for:
 \Driver\vendornet
Driver Extension List: (id , addr)
(fffff8063a2c6a10 ffffa50c29d6b2e0)
Device Object list:
ffffa50c2a1e8a10

0: kd> !devstack ffffa50c2a1e8a10
  !DevObj           !DrvObj            !DevExt           ObjectName
> ffffa50c2a1e8a10  \Driver\vendornet  ffffa50c2a1e8b60
  ffffa50c29f81060  \Driver\USBHUB3    ffffa50c29f811b0  0000004c
!DevNode ffffa50c29f3ad10 :
  DeviceInst is "USB\VID_0B95&PID_1790\00FF2A3B4C5D"
  ServiceName is "vendornet"

0: kd> !devnode ffffa50c29f3ad10
DevNode 0xffffa50c29f3ad10 for PDO 0xffffa50c29f81060
  Parent 0xffffa50c29a17b90   Sibling 0000000000   Child 0000000000
  InstancePath is "USB\VID_0B95&PID_1790\00FF2A3B4C5D"
  ServiceName is "vendornet"
  State = DeviceNodeAwaitingQueuedRemoval
  Previous State = DeviceNodeStarted
  StateHistory[..] = DeviceNodeStarted
  StateHistory[..] = DeviceNodeAwaitingQueuedRemoval
  Flags (0x...)  DNF_ENUMERATED, DNF_IDS_QUERIED, DNF_HAS_BOOT_CONFIG ...
  UserFlags (0x...)
  Problem = CM_PROB_DEVICE_NOT_THERE
```

**Reading it:**
- `!devstack`: two layers. The function driver `vendornet` (`>` marks the device object we asked about) sits on top of the **PDO** created by the USB hub driver `USBHUB3`.
- `!devnode`: `State = DeviceNodeAwaitingQueuedRemoval`, previous `Started`, problem `CM_PROB_DEVICE_NOT_THERE`. **The hardware disappeared, and Windows was in the middle of removing the device.** That confirms the timing.

> **Windows concept: surprise removal.** When a device vanishes without warning, the bus driver (here the USB hub) reports that it's gone. The PnP manager then tells the device's drivers, starting with a **surprise-removal** notification (`IRP_MN_SURPRISE_REMOVAL`). KMDF translates that into callbacks in the driver. A driver must then: (1) stop new work, (2) **wait until work already in progress finishes**, including DPCs that are already queued or running on another processor, and (3) only then free resources. Skipping step 2 creates exactly this race.

### Step 8 — The conclusion, and what the code probably looks like

Putting it together: the teardown path ran on one processor (during removal) while the receive DPC ran on another:

```
   CPU 0 (receive DPC, DISPATCH_LEVEL)          CPU 1 (removal path, PASSIVE_LEVEL)
   ────────────────────────────────────         ────────────────────────────────────
   if (Adapter->State == Running) ✓
                                                 Adapter->State = Removing;
                                                 VnFreeRxRing(Adapter);   // RxRing = NULL
   ring = Adapter->RxRing;        // NULL
   head = ring->Head;  // +0x48 → 0xD1
```

Reconstructed from the disassembly (not vendor source), the receive DPC probably looks like:

```c
VOID VnRxDpcRoutine(PKDPC Dpc, PVOID Context, PVOID Arg1, PVOID Arg2)
{
    PVN_ADAPTER Adapter = (PVN_ADAPTER)Context;     // x19
    if (Adapter->State != VnAdapterRunning)         // ldr w8,[x19,#4]; cmp w8,#2
        return;
    PVN_RX_RING ring = Adapter->RxRing;             // ldr x8,[x19,#0x10]   ← NULL
    ULONG head = ring->Head;                        // ldr w9,[x8,#0x48]    ← crash
    /* ... process received packets ... */
}
```

And the teardown path probably does:

```c
VOID VnSurpriseRemove(PVN_ADAPTER Adapter)
{
    Adapter->State = VnAdapterRemoving;
    VnFreeRxRing(Adapter);          // frees the ring and sets RxRing = NULL
    /* ... */
}
```

The fix is ordering, not a NULL check. (A NULL check would only narrow the race window, because the ring could be freed one instruction *after* the check.)

```c
VOID VnSurpriseRemove(PVN_ADAPTER Adapter)
{
    Adapter->State = VnAdapterRemoving;   // 1. stop NEW work from starting
    VnDisableDeviceInterrupts(Adapter);   // 2. no new DPCs will be queued
    KeFlushQueuedDpcs();                  // 3. wait until every queued/running DPC on every CPU has finished
    VnFreeRxRing(Adapter);                // 4. only now is it safe to free
}
```

(A KMDF driver would normally let the framework do steps 2–3, by tying the DPC to a framework interrupt object.)

### The triage note

> **0xD1, NULL+0x48 read at DISPATCH_LEVEL** in `vendornet!VnRxDpcRoutine` (Example Vendor's USB network driver, v3.1.0.12), running as a DPC. The adapter's state was `Removing` and `RxRing` was NULL; the devnode was mid surprise-removal. **Root cause:** the teardown frees the receive ring without first stopping interrupts and flushing in-flight DPCs. **Next:** send to the vendor with this dump; to confirm, an unplug loop under Driver Verifier should reproduce it far more often.

### How the path narrowed

```
"crash on unplug"
  → !analyze: vendornet faulted, NULL+0x48, IRQL 2           (rules out "unrelated")
  → symbols + k: inside a DPC                                 (context: can't wait, any CPU)
  → .trap + ub: pointer came from Adapter->RxRing             (which field)
  → dt: State=Removing, RxRing=NULL                           (what the data says)
  → !devnode: device mid-removal                              (why, and when)
  → conclusion: teardown/DPC race                             (who fixes what)
```

---

<a id="interlude-arm64-vs-x64"></a>
## Interlude — Reading Arm64 and x64 side by side

You'll meet both. The method doesn't change; the surface does.

### Registers and calling conventions

| Purpose | x64 | Arm64 |
|---|---|---|
| General registers | `rax rbx rcx rdx rsi rdi rbp rsp r8`–`r15` (64-bit) | `x0`–`x30` (64-bit) |
| 32-bit view of a register | `eax`, `ecx`, `r8d`… | `w0`–`w30` |
| Arguments 1, 2, 3, 4 | `rcx`, `rdx`, `r8`, `r9` (then the stack) | `x0`–`x7` (then the stack) |
| Return value | `rax` | `x0` |
| Kept across calls (callee-saved) | `rbx rbp rdi rsi r12`–`r15` | `x19`–`x28` |
| Stack pointer | `rsp` | `sp` |
| Frame pointer | `rbp` (optional) | `fp` = `x29` |
| Return address | **pushed onto the stack** by `call` | **put in register `lr` (= `x30`)** by `bl`; the function saves it to the stack itself |
| Instruction pointer | `rip` | `pc` |
| Instruction length | variable, 1–15 bytes | always 4 bytes |

### The same line of C, both ways

```c
ULONG head = ring->Head;     // Head is at offset 0x48 in the ring structure
```

```
x64:    mov   eax,dword ptr [rcx+48h]      ; read 4 bytes at (rcx + 0x48) into eax
Arm64:  ldr   w9,[x8,#0x48]                ; read 4 bytes at (x8 + 0x48) into w9
```

Same idea in both: **base register + constant offset = the address read**. That's why, on either architecture, a fault address like `0x48` immediately suggests "the base register was NULL, and the field is at `+0x48`".

### Notation differences

| | x64 (WinDbg) | Arm64 (WinDbg) |
|---|---|---|
| Hex constant in disassembly | `48h` | `#0x48` |
| Operand order | destination first: `mov eax, [mem]` | destination first: `ldr w9, [mem]` |
| Memory operand | `dword ptr [rcx+48h]` (size spelled out) | `[x8,#0x48]` (size implied by `w`=4 / `x`=8 bytes) |
| Store | `mov dword ptr [rcx+48h], eax` | `str w9,[x8,#0x48]` |
| Call | `call vendornet!Foo` | `bl vendornet!Foo` |
| Bad memory access exception | page fault (stack shows `nt!KiPageFault`) | data abort (stack shows an exception handler such as `nt!KiDataAbortException`) |

### What changes when you debug

- **`ub` is exact on Arm64 and a guess on x64.** Going backwards on x64, the debugger doesn't know where the previous instruction began. Use `ub` with a few extra instructions and sanity-check them, or disassemble forward from the function start with `uf` (unassemble function).
- **The return address lives in a register on Arm64** until the function saves it. In a very early crash inside a small function, `lr` may still hold the caller.
- **The trap frame contents differ.** Both save the volatile registers and the instruction pointer. Callee-saved registers may be missing or zero on Arm64; you can sometimes recover them from the next frame with `.frame /r <n>`.
- **IRQL is stored differently.** On x64 the current IRQL lives in control register `CR8`. On Arm64, Windows keeps a per-processor value and programs the interrupt controller's priority mask to match. Either way it's per processor, and `!irql` shows it.
- **Things that stay the same:** byte order (little-endian), 4 KB pages, 64-bit pointers, kernel at the top of the address space, and every structure layout in this document.

---

<a id="scenario-2"></a>
## Scenario 2 — A tablet crashes going to sleep (0x9F, a stuck power IRP)

### The situation

A tablet sometimes blue-screens about two minutes after the user presses the power button to turn off the screen (entering standby). It happens more often right after the camera app was used. A kernel dump was collected.

**Hypotheses:**
- (A) A driver never finished its power-down request.
- (B) A device's hardware hung during power-down.
- (C) A firmware or platform problem.

Since 0x9F means "a power request took too long", the key question becomes **which driver was holding it, and what was it waiting for?**

### Step 1 — The automatic analysis

```
0: kd> !analyze -v
DRIVER_POWER_STATE_FAILURE (9f)
A driver has failed to complete a power IRP within a specific time.
Arguments:
Arg1: 0000000000000003, A device object has been blocking an IRP for too long a time
Arg2: ffffc28311d4e060, Physical Device Object of the stack
Arg3: ffff8f0c3c6d7820, nt!TRIAGE_9F_POWER on Win7 and higher, otherwise the Functional Device Object of the stack
Arg4: ffffc28314a9b8a0, The blocked IRP

Debugging Details:
------------------
DRVPOWERSTATE_SUBCODE:  3
IMAGE_NAME:  ACPI.sys
MODULE_NAME: ACPI
FAILURE_BUCKET_ID:  0x9F_3_POWER_DOWN_ACPI_IMAGE_ACPI.sys

STACK_TEXT:
nt!KeBugCheckEx
nt!PopIrpWatchdogBugcheck+0x...
nt!PopIrpWatchdog+0x32
nt!KiProcessExpiredTimerList+0x...
nt!KiRetireDpcList+0x...
nt!KiIdleLoop+0x...
```

**Reading it:**
- **Arg1 = 3**: "a device object has been blocking an IRP for too long". This subcode comes with a ready-made recipe: **Arg4 is the stuck IRP, and Arg2 is the bottom device of its stack.**
- **The stack is the watchdog, not the culprit.** `PopIrpWatchdog` is a timer the power manager set when it sent the request. The timer expired, the watchdog fired in a DPC, and it bug-checked. **This stack never contains the guilty driver.** For timeout bug checks (0x9F, 0x133 with parameter 1, 0x101), the current stack is the *detector*.
- **`IMAGE_NAME: ACPI.sys` is a guess, and here a weak one.** The analyzer named the driver that owns the PDO (`ACPI.sys` created the device on this platform). That doesn't mean ACPI is holding the IRP. **Don't stop here.** Check the IRP itself.

### Step 2 — Who is holding the IRP?

```
0: kd> !irp ffffc28314a9b8a0
Irp is active with 3 stacks 2 is current (= 0xffffc28314a9b9b8)
 No Mdl: No System Buffer: Thread 00000000:  Irp stack trace.
     cmd  flg cl Device   File     Completion-Context
 [N/A(0), N/A(0)]
            0  0 00000000 00000000 00000000-00000000

			Args: 00000000 00000000 00000000 00000000
>[IRP_MJ_POWER(16), IRP_MN_SET_POWER(2)]
            0 e1 ffffc28312b70a40 00000000 fffff80632e41a20-ffffc28313c04e10 Success Error Cancel pending
	       \Driver\camvendor	nt!PopRequestCompletion
			Args: 00015400 00000001 00000004 00000002
 [N/A(0), N/A(0)]
            0  0 00000000 00000000 00000000-ffffc28313c04e10

			Args: 00000000 00000000 00000000 00000000
```

**Reading it:**
- **3 stacks, 2 is current**, and the `>` line names **`\Driver\camvendor`**: the camera driver currently owns the IRP. Not ACPI.
- `cl e1`: `0x01` = **pending returned**: camvendor returned `STATUS_PENDING` and promised to finish later. It didn't.
- `IRP_MJ_POWER / IRP_MN_SET_POWER`: a **set power state** request. The `Args` decode as: power type `1` = *device* power state, new state `4` = **D3** (off). **The power manager asked the camera to turn off.**
- `Thread 00000000`: power IRPs aren't tied to a requesting thread, because the power manager sends them on its own behalf.
- Location 1 (the bottom, ACPI's slot) shows `N/A`: the IRP never got passed down that far. Location 3 at the top is the power manager's own slot: when it built this IRP it allocated one extra location for itself and stored its completion routine, `nt!PopRequestCompletion`, in the location below (camvendor's line), so it gets called when camvendor finally completes.

**What this changes:** hypothesis (A) now names a specific driver: camvendor holds the request and never completed it. But *why* not? The IRP alone can't say. We need the code that's supposed to be working on it.

### Step 3 — The device stack and the power picture

```
0: kd> !devstack ffffc28312b70a40
  !DevObj           !DrvObj             !DevExt           ObjectName
> ffffc28312b70a40  \Driver\camvendor   ffffc28312b70b90
  ffffc28311d4e060  \Driver\ACPI        ffffc28311a52b10  00000039
!DevNode ffffc28311d1fb20 :
  DeviceInst is "ACPI\VNDR0A51\1"
  ServiceName is "camvendor"

0: kd> !poaction
PopAction: fffff80632fd3a60
  State..........: 0 - Idle
  Updates........: 0
  Action.........: None
  ...
Allocated power irps (PopIrpList - fffff80632fd2b40)
  IRP: ffffc28314a9b8a0 (set/D3,), PDO: ffffc28311d4e060, CURRENT: ffffc28312b70a40, NOTIFY: ffffc28311d1fbd0

Irp worker threads (PopIrpThreadList - fffff80632fd1f80)
  THREAD: ffffc28310f1e040 (static)
  THREAD: ffffc28310f1f080 (static)
```

**Reading it:**
- The stack is just two layers: the camera's function driver on top of the PDO that `ACPI.sys` created, because the camera is described in the platform firmware's ACPI tables (`ACPI\VNDR0A51`).
- `!poaction` lists **one outstanding power IRP in the whole system**: ours, `set/D3`, `CURRENT` = camvendor's device. Everything else finished. The system-wide state is "Idle" because this is a **device** power transition (the screen-off path) rather than a whole-system sleep.

> **Windows concept: who sends device power IRPs, and why a timeout exists.** On a tablet, turning the screen off starts **Modern Standby**: the system stays on, but every device is asked to move to a low-power state. For each device, the **power policy owner** (usually the function driver, here camvendor via KMDF) has the power manager send an `IRP_MN_SET_POWER` for D3. The request goes down the stack, each driver turns its part off, and the IRP comes back up. The power manager can't tell whether a slow driver is just slow or truly stuck. So it arms a **watchdog timer** for each power IRP, and if the IRP isn't back in time, it bug checks with 0x9F. The 0x9F is a symptom: *someone didn't come back*.

### Step 4 — Find the thread doing the work

camvendor is a **KMDF** driver. KMDF doesn't do power transitions inside the dispatch routine. It runs a power state machine that calls the driver's callbacks, usually on a system worker thread. So somewhere there should be a thread executing camvendor's power-down callback. `!stacks` searches all thread stacks for a string:

```
0: kd> !stacks 2 camvendor
Proc.Thread  .Thread  Ticks   ThreadState Blocker
                            [ffffc28310e6f080 System]
   4.000214  ffffc28313b2a040 0001e0a Blocked    nt!KiSwapContext+0x76
                                        nt!KiSwapThread+0x500
                                        nt!KiCommitThreadWait+0x14f
                                        nt!KeWaitForSingleObject+0x233
                                        camvendor!CamWaitForStreamStopAck+0x5a
                                        camvendor!CamEvtDeviceD0Exit+0x8e
                                        Wdf01000!FxPnpDeviceD0Exit::InvokeClient+0x...
                                        Wdf01000!FxPkgPnp::PowerGotoDxIoStopped+0x...
                                        Wdf01000!FxPkgPnp::PowerEnterNewState+0x...
                                        Wdf01000!FxPkgPnp::PowerProcessEventInner+0x...
                                        Wdf01000!FxPkgPnp::_PowerProcessEventInner+0x...
                                        Wdf01000!FxEventQueue::EventQueueWorker+0x...
                                        nt!IopProcessWorkItem+0x...
                                        nt!ExpWorkerThread+0x...
                                        nt!PspSystemThreadStartup+0x...
                                        nt!KiStartSystemThread+0x...

Threads Processed: 1342
```

**Found it.** Read bottom to top: a system **worker thread** (`ExpWorkerThread`) ran a work item for KMDF's power state machine (`FxPkgPnp::Power...`). The state machine called the driver's **`CamEvtDeviceD0Exit`** callback ("leave the working state D0"). That callback called `CamWaitForStreamStopAck`, which is **waiting** (`KeWaitForSingleObject`), and the thread is `Blocked`.

> **Windows concept: blocking vs. busy.** `KiSwapContext` at the top of a stack means the thread **gave up the processor** and is waiting for an object to be signaled. It isn't using any CPU. A waiting thread holds the request it's working on, so the power IRP can't move until this wait ends.

### Step 5 — What exactly is it waiting for, and for how long?

```
0: kd> !thread ffffc28313b2a040
THREAD ffffc28313b2a040  Cid 0004.0214  Teb: 0000000000000000 Win32Thread: 0000000000000000 WAIT: (Executive) KernelMode Non-Alertable
    ffffc28313c05238  NotificationEvent
Not impersonating
Owning Process            ffffc28310e6f080       Image:         System
Attached Process          N/A            Image:         N/A
Wait Start TickCount      18310          Ticks: 7690 (0:00:02:00.156)
Context Switch Count      2214           IdealProcessor: 1
UserTime                  00:00:00.000
KernelTime                00:00:00.015
Win32 Start Address nt!ExpWorkerThread (0xfffff806328a5c10)
Stack Init ffff8f0c3c7b7c90 Current ffff8f0c3c7b7270
...
```

**Reading it:**
- `WAIT: (Executive) KernelMode Non-Alertable`: a kernel-mode wait that nothing except the object itself can end. "Executive" is the generic wait reason drivers get from `KeWaitForSingleObject`.
- The object waited on: **`ffffc28313c05238 NotificationEvent`**, a kernel event.
- **`Ticks: 7690 (0:00:02:00.156)`**: it has been waiting **2 minutes and 0.156 seconds**. The clock tick here is 15.625 ms, and 7690 × 15.625 ms = 120.156 s. That matches the symptom: crash "about two minutes after".
- `KernelTime 0.015 s`: it barely ran at all. It isn't doing work; it's waiting.

Which event is that? Look at the driver's device context (the KMDF context area for this device):

```
0: kd> dt camvendor!_CAM_DEVICE_CONTEXT ffffc28313c05200
   +0x000 Signature        : 0x6d614376  'vCam'
   +0x008 Regs             : 0xffff8501`0b7a0000 CAM_REGS
   +0x010 Interrupt        : 0x00003d7c`eb3fa6e8 WDFINTERRUPT__
   +0x018 StreamActive     : 0n1
   +0x020 StreamFlags      : 0x3
   +0x038 StreamStopAck    : _KEVENT        ← at 0xffffc28313c05238 (0x...5200 + 0x38): the event being waited on
   +0x050 LastIsrStatus    : 0x00000004
   +0x054 IsrCount         : 0n18744
```

`StreamStopAck` sits at context `+0x38` = `ffffc28313c05238`, the exact address in the wait. So the driver is waiting for **"the camera firmware acknowledged that streaming stopped"**. Who signals that event? Searching the driver for code that sets it, using the symbols:

```
0: kd> x camvendor!*Dpc*
fffff806`3b412c80 camvendor!CamEvtInterruptDpc (struct WDFINTERRUPT__ *, struct WDFOBJECT__ *)
```

The vendor's source (or the disassembly) for that DPC looks like this:

```c
VOID CamEvtInterruptDpc(WDFINTERRUPT Interrupt, WDFOBJECT AssociatedObject)
{
    PCAM_DEVICE_CONTEXT ctx = CamGetContext(WdfInterruptGetDevice(Interrupt));
    ULONG status = ctx->LastIsrStatus;
    if (status & CAM_IRQ_STREAM_STOPPED) {
        ctx->StreamActive = 0;
        KeSetEvent(&ctx->StreamStopAck, IO_NO_INCREMENT, FALSE);   // the ONLY place it's signaled
    }
    /* ... frame-done handling ... */
}
```

**The event can only be signaled by the interrupt path.** So: did the stop interrupt ever arrive?

### Step 6 — The KMDF log: what did the framework do, in order?

KMDF keeps an in-memory log for each driver (the In-Flight Recorder, IFR). The `wdfkd` extension can dump it:

```
0: kd> !wdfkd.wdflogdump camvendor
Trace searchpath is:
Trace format prefix is: %7!u!: %!FUNC! -
...
2187: FxPkgPnp::PowerPolicyEnterNewState - WDFDEVICE 0x00003D7CED48F9B8 !devobj 0xFFFFC28312B70A40 entering power policy state WdfDevStatePwrPolStartingDecideS0Wake from ...
2191: FxPkgPnp::PowerEnterNewState - WDFDEVICE 0x00003D7CED48F9B8 !devobj 0xFFFFC28312B70A40 entering Power State WdfDevStatePowerGotoDx from WdfDevStatePowerD0
2192: FxIoQueue::StopProcessingForPower - stopping queue 0x00003D7CEB3F7A28
2193: FxPkgPnp::NotifyResourceObjectsDx - WDFINTERRUPT 0x00003D7CEB3FA6E8 disconnecting: EvtInterruptDisable called
2194: FxInterrupt::Disconnect - WDFINTERRUPT 0x00003D7CEB3FA6E8 IRQ 0x5f disconnected
2195: FxPkgPnp::PowerEnterNewState - ... entering Power State WdfDevStatePowerGotoDxIoStopped
2196: FxPnpDeviceD0Exit::InvokeClient - calling EvtDeviceD0Exit, target state WdfPowerDeviceD3
```

**There it is, in order:**
1. The device starts moving from D0 (on) to Dx (off).
2. The I/O queue stops.
3. **The interrupt is disabled and disconnected** (entries 2193–2194).
4. **Only then** is `EvtDeviceD0Exit` called (entry 2196).

> **Windows concept: KMDF's power-down order.** When a KMDF device leaves D0, the framework calls the driver's callbacks in a fixed order. Simplified: stop the I/O queues → `EvtDeviceD0ExitPreInterruptsDisabled` → **disable and disconnect interrupts** (`EvtInterruptDisable`) → **`EvtDeviceD0Exit`**. So by the time `EvtDeviceD0Exit` runs, the driver's interrupt is already disconnected. **No ISR and no interrupt DPC will run for this device again until it powers back up.**

### Step 7 — Conclusion

`CamEvtDeviceD0Exit` sends "stop streaming" to the camera firmware and then waits for the firmware's "stopped" acknowledgment, which can only arrive through an interrupt. But the interrupt was disconnected *before* `EvtDeviceD0Exit` was called. The wait can never end. The power IRP never completes. Two minutes later, the watchdog fires 0x9F.

Why only "sometimes, especially after using the camera"? `StreamActive = 1`: the wait only happens if a stream was still active at power-down. If the camera app had already stopped streaming, the callback skips the wait.

```c
// What the driver does (reconstructed):
NTSTATUS CamEvtDeviceD0Exit(WDFDEVICE Device, WDF_POWER_DEVICE_STATE TargetState)
{
    PCAM_DEVICE_CONTEXT ctx = CamGetContext(Device);
    if (ctx->StreamActive) {
        CamSendStopStream(ctx);                        // ask firmware to stop
        CamWaitForStreamStopAck(ctx);                  // KeWaitForSingleObject(&ctx->StreamStopAck, ..., NULL) ← no timeout!
    }
    CamPowerOffSensor(ctx);
    return STATUS_SUCCESS;
}

// The fix: do the interrupt-dependent handshake BEFORE interrupts are disabled, with a timeout.
NTSTATUS CamEvtDeviceD0ExitPreInterruptsDisabled(WDFDEVICE Device, WDF_POWER_DEVICE_STATE TargetState)
{
    PCAM_DEVICE_CONTEXT ctx = CamGetContext(Device);
    if (ctx->StreamActive) {
        LARGE_INTEGER timeout; timeout.QuadPart = -10LL * 1000 * 500;   // 500 ms, relative
        CamSendStopStream(ctx);
        if (KeWaitForSingleObject(&ctx->StreamStopAck, Executive, KernelMode, FALSE, &timeout) == STATUS_TIMEOUT)
            CamForceStopStream(ctx);                   // fall back: reset the stream engine directly
    }
    return STATUS_SUCCESS;
}
```

### The triage note

> **0x9F subcode 3: a D3 power IRP was held for about 2 minutes** by `camvendor.sys` (camera function driver, KMDF). Its `EvtDeviceD0Exit` waits with no timeout on `StreamStopAck`, an event that is only signaled from the interrupt DPC, but KMDF disconnects the interrupt before calling `EvtDeviceD0Exit`. It only triggers if a stream is still active at power-down. **Fix:** move the stop handshake into `EvtDeviceD0ExitPreInterruptsDisabled` and add a timeout plus a forced-stop fallback. `!analyze`'s `ACPI.sys` attribution is a red herring (the PDO owner).

### How the path narrowed

```
"crash ~2 min after screen-off"
  → !analyze: 0x9F/3; stack = watchdog (detector, not culprit); IMAGE_NAME guess = ACPI
  → !irp Arg4: current location = camvendor, pending                 (who holds it)
  → !devstack / !poaction: the only outstanding power IRP, set D3     (what transition)
  → !stacks camvendor: worker thread in EvtDeviceD0Exit, waiting      (where the work stopped)
  → !thread: waiting on an event for 2:00                              (on what, how long)
  → dt context + code: event only set by the interrupt DPC            (who should wake it)
  → wdflogdump: interrupt disconnected before D0Exit                   (why it never will)
```

---

<a id="scenario-3"></a>
## Scenario 3 — The screen freezes, no blue screen (a deadlock)

### The situation

A tablet occasionally **freezes completely** when the user rotates it while a sensor-heavy app is opening. No blue screen, no dump: the screen just stops updating, and touch does nothing. Users hold the power button until it turns off.

**The first problem:** there's no evidence. A frozen machine writes nothing by itself, and holding the power button throws away all of memory. So the first step is a **collection plan**, not a command:

1. Configure the test devices so that holding the power button produces a dump: set the registry value `PowerButtonBugcheck = 1` under `HKLM\SYSTEM\CurrentControlSet\Control\Power`. Holding the button for about 7 seconds then triggers bug check **0x1C8 (MANUALLY_INITIATED_POWER_BUTTON_HOLD)** and writes a dump, as long as the button is released before the firmware's hard reset at about 10 seconds.
2. Reproduce, then hold the button for 7 seconds when the screen freezes.

A day later, a dump arrives.

**Hypotheses for a freeze:**
- (A) **Busy hang**: one or more CPUs are stuck in a loop at high IRQL, so nothing else can run.
- (B) **Idle hang / deadlock**: CPUs are idle, but the threads that matter are all waiting on each other.
- (C) A device stopped working and the UI is waiting on it.

**`!running` splits A from B and C in one command.** That's why it's the first move for any hang.

### Step 1 — The analysis: expect nothing useful

```
0: kd> !analyze -v
MANUALLY_INITIATED_POWER_BUTTON_HOLD (1c8)
The system was configured to initiate a bugcheck when the user holds the power button for a specified length of time.
This is a diagnostic bugcheck used to capture a dump when the system is about to be hard reset with a long power button hold.
Arguments:
Arg1: 0000000000001b58, Time in milliseconds the power button was held down.
Arg2: ffff8f0c3be41730, Pointer to nt!_POP_POWER_BUTTON_TRIAGE_BLOCK
...
FAILURE_BUCKET_ID:  0x1C8_MANUALLY_INITIATED_POWER_BUTTON_HOLD
```

`0x1b58` = 7000 ms. This bug check was **requested by a person**, so the "crash" location is meaningless: it's wherever the button-press handling happened to run. `!analyze` has no culprit to find. **From here on we investigate the state of the whole system.**

### Step 2 — What is every processor doing?

```
0: kd> !running -ti

System Processors:  (00000000000000ff)
  Idle Processors:  (00000000000000fe)

       Prcbs             Current         (pri) Next            (pri) Idle
  0    fffff80630d6d180  ffffc2831061a080 (12)                       fffff80630e7e440  ................
 # Child-SP          RetAddr               Call Site
00 ffff8f0c`3be41580 fffff806`3299f3c8     nt!KeBugCheckEx
01 ffff8f0c`3be41590 fffff806`32a1b0dc     nt!PopPowerButtonBugcheck+0x...
 ...

  1    ffff8f0c3a3c2180  ffff8f0c3a3cd2c0 ( 0)                       ffff8f0c3a3cd2c0  ................
 # Child-SP          RetAddr               Call Site
00 ffff8f0c`3a3e7c00 fffff806`32a1e8d8     nt!PpmIdleExecuteTransition+0x...
01 ffff8f0c`3a3e7c60 00000000`00000000     nt!KiIdleLoop+0x...

  2 … 7: (same: idle thread, in the idle loop)
```

**Reading it:**
- `Idle Processors: fe`: in binary `11111110`. **Processors 1–7 are idle.** Processor 0 is running only because it's handling the button-press bug check.
- Every idle CPU shows its idle thread in `KiIdleLoop`, with nothing to do.

**What this changes:** hypothesis (A), a busy hang, is **ruled out**. Nobody is spinning. The machine looks frozen because the threads that should update the screen and handle touch are **waiting**, and whatever they wait for never arrives. This is (B) or (C). We now need to find **who is waiting on what**.

### Step 3 — Are kernel locks involved?

A good next command for an idle hang is `!locks`, which lists every **executive resource** (`ERESOURCE`, a kernel reader/writer lock) that has an owner and waiters:

```
0: kd> !locks
**** DUMP OF ALL RESOURCE OBJECTS ****
KD: Scanning for held locks....

Resource @ sensorflt!g_ConfigLock (0xfffff8063c5a3140)    Exclusively owned
    Contention Count = 41
    NumberOfExclusiveWaiters = 1
    NumberOfSharedWaiters = 9
     Threads: ffffc283135d5080-01<*>
     Threads Waiting On Exclusive Access:
              ffffc283135e2080
     Threads Waiting On Shared Access:
              ffffc28312f10080  ffffc28313012080  ffffc2831389e080  ffffc28313a4f040
              ffffc28313aa1080  ffffc28313b17080  ffffc28313c90080  ffffc28313f08080
              ffffc28314011080

3624 total locks, 1 locks currently held
```

**Reading it:**
- **One** lock is held in the entire system: `sensorflt!g_ConfigLock`, a resource in a sensor **filter** driver (`sensorflt.sys`).
- It's **exclusively owned** by thread `…135d5080` (`<*>` marks the owner; `-01` is the recursion count).
- One thread (`…135e2080`) wants it exclusively, and **nine** threads want it shared. Those nine are why the whole UI froze: they include the threads that process sensor data, and everything else waits behind them.
- `Contention Count = 41`: threads have blocked on this lock 41 times since boot. It's busy, but that's normal for a hot lock.

> **Windows concept: two kinds of kernel locks you'll meet in hangs.**
> - **ERESOURCE (executive resource):** a reader/writer lock: many readers (shared) or one writer (exclusive). Acquired with `ExAcquireResourceExclusiveLite` / `ExAcquireResourceSharedLite`, at PASSIVE or APC level. `!locks` lists them with owners and waiters.
> - **KMUTEX (kernel mutex, a "mutant" in debugger output):** a single-owner lock that is a **dispatcher object**, so you wait for it with `KeWaitForSingleObject`. It records its owning thread. `!thread` on a waiter shows `Mutant - owning thread <addr>`.
> Both are *waitable*: a thread that can't get one goes to sleep (gives up the CPU). That's why deadlocks on them produce **idle** hangs. Spin locks are different: a waiter spins at DISPATCH_LEVEL, which produces a **busy** hang.

### Step 4 — The owner: what is *it* waiting for?

The owner holds the lock. If it were running, it would eventually release it. So: why isn't it?

```
0: kd> !thread ffffc283135d5080
THREAD ffffc283135d5080  Cid 0004.1a8c  Teb: 0000000000000000 Win32Thread: 0000000000000000 WAIT: (Executive) KernelMode Non-Alertable
    ffffc2831298c0e0  Mutant - owning thread ffffc283135e2080
Owning Process            ffffc28310e6f080       Image:         System
Wait Start TickCount      402771         Ticks: 11520 (0:00:03:00.000)
 # Child-SP          RetAddr               Call Site
00 ffff8f0c`3d2a7270 fffff806`32893a40     nt!KiSwapContext+0x76
01 ffff8f0c`3d2a73b0 fffff806`328928ff     nt!KiSwapThread+0x500
02 ffff8f0c`3d2a7460 fffff806`32891d23     nt!KiCommitThreadWait+0x14f
03 ffff8f0c`3d2a7500 fffff806`3c5a1b44     nt!KeWaitForSingleObject+0x233
04 ffff8f0c`3d2a75f0 fffff806`3c5a1e10     sensorflt!SfAcquireBus+0x24
05 ffff8f0c`3d2a7630 fffff806`3c5a2470     sensorflt!SfApplyOrientation+0x80
06 ffff8f0c`3d2a7680 fffff806`328a5d01     sensorflt!SfOrientationWorkItem+0x40
07 ffff8f0c`3d2a76d0 fffff806`328a5c10     nt!IopProcessWorkItem+0x...
08 ffff8f0c`3d2a7720 fffff806`3299c247     nt!ExpWorkerThread+0x...
09 ffff8f0c`3d2a77b0 fffff806`32a12a64     nt!PspSystemThreadStartup+0x...
0a ffff8f0c`3d2a7800 00000000`00000000     nt!KiStartSystemThread+0x...
```

**Reading it:**
- Thread A (`…135d5080`) is a **worker thread** running `sensorflt!SfOrientationWorkItem` (the rotation handling). It **owns `g_ConfigLock`** (from `!locks`).
- It's now waiting in `SfAcquireBus` for a **Mutant (KMUTEX)** at `…298c0e0`, **owned by thread `ffffc283135e2080`**.
- It has been waiting **3 minutes** (`Ticks: 11520` × 15.625 ms = 180 s).

Look back at `!locks`: **`ffffc283135e2080` is the thread waiting for exclusive access to `g_ConfigLock`.** We already have a suspicion. One more look:

### Step 5 — Close the loop

```
0: kd> !thread ffffc283135e2080
THREAD ffffc283135e2080  Cid 1f44.21b0  Teb: 0000008e1a3c6000 Win32Thread: ffffc28313f0c0e0 WAIT: (WrResource) KernelMode Non-Alertable
    ffffc283135e2398  SynchronizationEvent
IRP List:
    ffffc28314c0e7a0: (0006,0118) Flags: 00060070  Mdl: 00000000
Owning Process            ffffc28313210080       Image:         SensorApp.exe
Wait Start TickCount      402770         Ticks: 11521 (0:00:03:00.015)
 # Child-SP          RetAddr               Call Site
00 ffff8f0c`3e1c6f40 fffff806`32893a40     nt!KiSwapContext+0x76
01 ffff8f0c`3e1c7080 fffff806`328928ff     nt!KiSwapThread+0x500
02 ffff8f0c`3e1c7130 fffff806`32891d23     nt!KiCommitThreadWait+0x14f
03 ffff8f0c`3e1c71d0 fffff806`328d0f12     nt!ExpWaitForResource+0x...
04 ffff8f0c`3e1c7280 fffff806`3c5a2d50     nt!ExAcquireResourceExclusiveLite+0x...
05 ffff8f0c`3e1c7310 fffff806`3c5a3010     sensorflt!SfUpdateCalibration+0x60
06 ffff8f0c`3e1c7360 fffff806`3c5a0a28     sensorflt!SfDispatchDeviceControl+0xd0
07 ffff8f0c`3e1c73b0 fffff806`32881a35     nt!IofCallDriver+0x55
08 ffff8f0c`3e1c73f0 fffff806`32c7c1e2     nt!IopSynchronousServiceTail+0x...
09 ffff8f0c`3e1c7490 fffff806`32c7b5a6     nt!IopXxxControlFile+0x...
0a ffff8f0c`3e1c75d0 fffff806`32a12505     nt!NtDeviceIoControlFile+0x56
0b ffff8f0c`3e1c7640 00007ffc`a2b4f4d4     nt!KiSystemServiceCopyEnd+0x25
0c 0000008e`1a7ff6a8 00007ffc`9f9a6e3b     ntdll!NtDeviceIoControlFile+0x14
0d 0000008e`1a7ff6b0 00007ff7`1c2a31b9     KERNELBASE!DeviceIoControl+0x6b
0e 0000008e`1a7ff720 00000000`00000000     SensorApp+0x31b9
```

**Reading it:**
- Thread B (`…135e2080`) belongs to **`SensorApp.exe`**. Bottom to top: the app called `DeviceIoControl` (frames 0e–0c, user mode). That became a system call (0b), the I/O manager built an IRP (you can see it in the `IRP List`) and called the driver (07). sensorflt's `SfUpdateCalibration` is now waiting (`WrResource`) to **acquire `g_ConfigLock` exclusively** (frame 04).
- Earlier in that same IOCTL path, B **acquired the bus mutex**: `!thread A` said the mutex's owner is B.

**The cycle:**

```
         holds g_ConfigLock (ERESOURCE, exclusive)
   ┌─────────────── Thread A ◄───────────────────────┐
   │      (rotation work item: SfApplyOrientation)  │
   │                                                │ waits for g_ConfigLock (exclusive)
   │ waits for BusMutex (KMUTEX)                     │
   ▼                                                │
   Thread B ─────────────────────────────────────────┘
   (SensorApp IOCTL: SfUpdateCalibration)
         holds BusMutex

   + 9 more threads waiting (shared) on g_ConfigLock behind them → the UI stops updating
```

**Each thread holds the lock the other one needs.** Neither can continue, so neither will ever release. That's a **deadlock**, specifically a **lock-order inversion**:

| Path | Takes first | Then tries |
|---|---|---|
| Rotation work item (A) | `g_ConfigLock` | `BusMutex` |
| Calibration IOCTL (B) | `BusMutex` | `g_ConfigLock` |

If they run at almost the same time, as when the user rotates the device while the app is opening, each gets its first lock and blocks on its second.

### Step 6 — Conclusion and fix

```c
// Rotation path (simplified):
VOID SfApplyOrientation(PSF_CONTEXT ctx, ULONG orientation) {
    ExAcquireResourceExclusiveLite(&g_ConfigLock, TRUE);   // 1st: ConfigLock
    ctx->Orientation = orientation;
    SfAcquireBus(ctx);                                      // 2nd: BusMutex   ← waits on B
    SfWriteSensorAxisMap(ctx);
    SfReleaseBus(ctx);
    ExReleaseResourceLite(&g_ConfigLock);
}

// Calibration IOCTL path (simplified):
NTSTATUS SfCalibrate(PSF_CONTEXT ctx, PCAL_DATA cal) {
    SfAcquireBus(ctx);                                      // 1st: BusMutex
    SfReadSensorTrim(ctx, cal);
    SfUpdateCalibration(ctx, cal);                          //   → acquires ConfigLock  ← waits on A
    SfReleaseBus(ctx);
    return STATUS_SUCCESS;
}
```

**The fix:** choose one global order (for example, always `g_ConfigLock` before `BusMutex`) and follow it everywhere. Or restructure so that no path holds one of these locks while acquiring the other. Driver Verifier has a **deadlock detection** option that tracks lock acquisition order and reports an inversion the first time *both orders are ever used*, even if they never actually collide. That turns a once-a-week freeze into a deterministic report.

### The triage note

> **Hang (forced 0x1C8 dump), idle: all CPUs idle.** Deadlock in `sensorflt.sys` (sensor filter driver): the rotation work item holds `g_ConfigLock` (ERESOURCE) and waits for the bus KMUTEX; SensorApp's calibration IOCTL holds the bus KMUTEX and waits for `g_ConfigLock` exclusive; 9 more threads are blocked shared behind them. Both waits are 3 minutes old. **Root cause:** lock-order inversion. **Next:** fix the ordering; confirm with Driver Verifier deadlock detection on sensorflt.

### How the path narrowed

```
"freezes, no dump"
  → collection plan: PowerButtonBugcheck → 0x1C8 dump        (get evidence without losing memory)
  → !analyze: nothing to find (requested crash)              (expected)
  → !running -ti: all CPUs idle                              (not busy: waiting)
  → !locks: one ERESOURCE held, 10 waiters                   (a starting thread)
  → !thread owner: waits on KMUTEX owned by B                (follow the chain)
  → !thread B: waits on the ERESOURCE owned by A             (chain closes: cycle)
  → conclusion: lock-order inversion                         (fix: one order)
```

---

<a id="scenario-4"></a>
## Scenario 4 — Freezes, then 0x133 (a DPC that never finishes, x64)

### The situation

An **x64** laptop freezes for several seconds and then blue-screens with `DPC_WATCHDOG_VIOLATION (0x133)`. It started after a touchpad firmware update. This time we get a crash dump automatically: the freeze converts itself into a crash.

**Hypotheses:**
- (A) One driver's DPC or ISR runs far too long (a loop).
- (B) Many DPCs together keep the CPU at DISPATCH_LEVEL too long (a storm).
- (C) Interrupts arrive so fast that the CPU never gets back to normal work.

0x133's **first parameter separates A from B**, so it's the first thing to read.

### Step 1 — The analysis

```
0: kd> !analyze -v
DPC_WATCHDOG_VIOLATION (133)
The DPC watchdog detected a prolonged run time at an IRQL of DISPATCH_LEVEL
or above.
Arguments:
Arg1: 0000000000000000, A single DPC or ISR exceeded its time allotment. The offending
	component can usually be identified with a stack trace.
Arg2: 0000000000000501, The DPC time count (in ticks).
Arg3: 0000000000000500, The DPC time allotment (in ticks).
Arg4: fffff80314ffb320, cast to nt!DPC_WATCHDOG_GLOBAL_TRIAGE_BLOCK, which contains
	additional information regarding this single DPC timeout

STACK_TEXT:
 # Child-SP          RetAddr               Call Site
00 fffff803`1a8d5c88 fffff803`14838f2d     nt!KeBugCheckEx
01 fffff803`1a8d5c90 fffff803`14837b11     nt!KeAccumulateTicks+0x1ed
02 fffff803`1a8d5cf0 fffff803`14836c3a     nt!KiUpdateRunTime+0x61
03 fffff803`1a8d5d50 fffff803`1483aa5e     nt!KeClockInterruptNotify+0x...
04 fffff803`1a8d5e40 fffff803`1483a0c2     nt!HalpTimerClockInterrupt+0x...
05 fffff803`1a8d5e70 fffff803`149e0f7a     nt!KiCallInterruptServiceRoutine+0x...
06 fffff803`1a8d5eb0 fffff803`149e14e7     nt!KiInterruptSubDispatchNoLockNoEtw+0xfa
07 fffff803`1a8c3a60 fffff803`1489c2d1     nt!KiInterruptDispatchNoLockNoEtw+0x37
08 fffff803`1a8c3bf0 fffff803`1f612a63     nt!KeStallExecutionProcessor+0x91
09 fffff803`1a8c3c20 fffff803`1f612b21     vendori2c!I2cWaitForTxEmpty+0x23
0a fffff803`1a8c3c60 fffff803`1484d1f5     vendori2c!I2cDpcForIsr+0x91
0b fffff803`1a8c3cb0 fffff803`1484c43a     nt!KiExecuteAllDpcs+0x2f5
0c fffff803`1a8c3e20 fffff803`149e30d5     nt!KiRetireDpcList+0x1ba
0d fffff803`1a8c4060 00000000`00000000     nt!KiIdleLoop+0x55

IMAGE_NAME:  vendori2c.sys
FAILURE_BUCKET_ID:  0x133_DPC_vendori2c!I2cWaitForTxEmpty
```

**Reading the parameters:**
- **Arg1 = 0: a *single* DPC or ISR exceeded its allotment.** Hypothesis (A). For subcode 0, the offending code is usually still on the stack, because it was running when the watchdog checked.
- Arg2/Arg3: `0x501` ticks used against an allotment of `0x500`. It went just over the limit, which is how a watchdog check always looks: it fires on the first check past the line. 0x500 = 1280 clock ticks; at 15.625 ms per tick, that's about 20 seconds. The user's "freezes for several seconds" was actually about 20.

**Reading the stack: find the boundary.** This stack has two parts:

```
00–06   nt!KeBugCheckEx ... nt!HalpTimerClockInterrupt ... KiInterruptSubDispatch
        └─ the CLOCK INTERRUPT: it arrived, counted ticks, noticed the limit, bug checked   ← the detector
07      nt!KiInterruptDispatchNoLockNoEtw        ← the boundary: "an interrupt arrived here"
08      nt!KeStallExecutionProcessor             ← a kernel helper the driver called (a busy-wait for N microseconds)
09–0a   vendori2c!I2cWaitForTxEmpty  ← vendori2c!I2cDpcForIsr                          ← what was INTERRUPTED: the culprit
0b–0d   nt!KiExecuteAllDpcs ← KiRetireDpcList ← KiIdleLoop                            ← it was a DPC
```

> **Windows concept: how the DPC watchdog works.** Each processor receives a **clock interrupt** periodically. The clock interrupt has a higher IRQL than DISPATCH_LEVEL, so it can interrupt a running DPC. Each time it runs, it charges the elapsed tick to whatever the processor was doing (`KeAccumulateTicks`). If the processor has been inside the **same DPC** for longer than the allotment, it bug checks right there, inside the clock interrupt. So the clock interrupt frames are on top, and the guilty DPC is **just below the interrupt boundary**.

### Step 2 — What is that DPC doing for 20 seconds? Disassemble the function

On x64, `ub` (backwards) can mis-decode, so use **`uf`** (unassemble the whole function, from its start):

```
0: kd> uf vendori2c!I2cWaitForTxEmpty
vendori2c!I2cWaitForTxEmpty:
fffff803`1f612a40 48895c2408      mov     qword ptr [rsp+8],rbx
fffff803`1f612a45 57              push    rdi
fffff803`1f612a46 4883ec20        sub     rsp,20h
fffff803`1f612a4a 488bd9          mov     rbx,rcx                         ; rbx = 1st argument (controller context)
fffff803`1f612a4d 488b7b10        mov     rdi,qword ptr [rbx+10h]         ; rdi = ctx->Regs (mapped device registers)

vendori2c!I2cWaitForTxEmpty+0x11:                                         ; ── loop top ──
fffff803`1f612a51 8b4714          mov     eax,dword ptr [rdi+14h]         ; eax = read STATUS register (Regs + 0x14)
fffff803`1f612a54 a802            test    al,2                            ; bit 1 = TX_EMPTY?
fffff803`1f612a56 7512            jne     vendori2c!I2cWaitForTxEmpty+0x2a ; if set → done
fffff803`1f612a58 b90a000000      mov     ecx,0Ah                         ; ecx = 10
fffff803`1f612a5d ff15e5450000    call    qword ptr [vendori2c!_imp_KeStallExecutionProcessor] ; busy-wait 10 µs
fffff803`1f612a63 0f1f440000      nop     dword ptr [rax+rax]
fffff803`1f612a68 ebe7            jmp     vendori2c!I2cWaitForTxEmpty+0x11 ; back to loop top  ← NO EXIT except bit 1
                                                                            ; (+0x23 = ...a63 is the return address from the
                                                                            ;  stall call: the stack's frame 09 pointed here)
vendori2c!I2cWaitForTxEmpty+0x2a:
fffff803`1f612a6a 488b5c2430      mov     rbx,qword ptr [rsp+30h]
fffff803`1f612a6f 4883c420        add     rsp,20h
fffff803`1f612a73 5f              pop     rdi
fffff803`1f612a74 c3              ret
```

Translated back into C:

```c
static VOID I2cWaitForTxEmpty(PI2C_CONTROLLER ctx)
{
    volatile PI2C_REGS regs = ctx->Regs;            // mov rdi,[rbx+10h]
    while ((READ_REGISTER_ULONG(&regs->Status) & I2C_STATUS_TX_EMPTY) == 0) {   // mov eax,[rdi+14h]; test al,2
        KeStallExecutionProcessor(10);              // spin 10 microseconds, without yielding
    }                                               // jmp back: no timeout, no retry limit
}
```

**This is an unbounded polling loop at DISPATCH_LEVEL.** It reads a hardware status register until "transmit empty" goes high, spinning 10 µs between reads. If the bit never sets, it loops forever, and nothing else can run on that CPU at or below DISPATCH_LEVEL: no threads, no other DPCs.

### Step 3 — Why didn't the bit ever set? Look at the controller state

The controller context gives us the mapped register block:

```
0: kd> .frame /r 9                ← switch to frame 09 (I2cWaitForTxEmpty) and recover its registers
09 fffff803`1a8c3c20 fffff803`1f612b21     vendori2c!I2cWaitForTxEmpty+0x23
rax=0000000000000019 rbx=ffffd0812c71a200 rcx=000000000000000a ... rdi=ffffd0812c6f0000 ...

0: kd> dt vendori2c!_I2C_CONTROLLER @rbx
   +0x000 Signature        : 0x43633249 'I2cC'
   +0x010 Regs             : 0xffffd081`2c6f0000 _I2C_REGS
   +0x018 TargetAddress    : 0x2c
   +0x020 BytesPending     : 4
   +0x028 LastError        : 0
   +0x030 TransferCount    : 0n981441

0: kd> dt vendori2c!_I2C_REGS 0xffffd081`2c6f0000
   +0x000 Control          : 0x00000003
   +0x004 TargetAddr       : 0x0000002c
   +0x008 TxFifo           : 0
   +0x00c RxFifo           : 0
   +0x010 IntStatus        : 0x00000040
   +0x014 Status           : 0x00000019
   +0x018 IntMask          : 0x0000004f
```

(Here `@rbx` means "the value of register rbx". `.frame /r 9` made the debugger show registers as they were in frame 09; `rbx` holds the controller context (the function's first instruction after the prologue copied `rcx` into it), and `rdi` holds `Regs`, matching the `dt`. Note `rax = 0x19`: the last status value the loop read. In a dump, reading device registers shows what the dump captured, if the platform saved that memory. On a live machine, **reading device registers in the debugger can have side effects**: some status registers clear when read. Be careful with `dd` on device memory.)

`Status = 0x19` = binary `0001 1001`: bit 1 (`TX_EMPTY`, value `0x2`) is **0**. The controller's datasheet (the vendor's register documentation) would say, for example, that bit 0 = busy, bit 3 = bus held, and bit 4 = arbitration lost. The bus is stuck: the device at address `0x2c` (the touchpad controller, after its firmware update) is holding the bus line, so the transmit FIFO can never drain.

### Step 4 — Was it only this DPC? (Checking hypotheses B and C)

```
0: kd> !dpcs
CPU Type      KDPC       Function
 0: Normal  : 0xffffd0812c71a2c0 0xfffff8031f612ab0 vendori2c!I2cDpcForIsr     (running)
 0: Normal  : 0xfffff80314e1d840 0xfffff8031489a6c0 nt!PpmCheckPeriodicStart
 0: Normal  : 0xffffd0812a4b7110 0xfffff80321c0a3d0 ndis!ndisInterruptDpc
 0: Normal  : 0xffffd0812b0f3d58 0xfffff80322b41150 USBXHCI!Interrupter_DpcForIsr
```

One DPC running, three **queued behind it** on the same CPU, waiting their turn. Those victims are why networking and USB froze along with everything else. There's no storm of repeated DPCs (B), and the stack shows no ISR storm (C). **Hypothesis A is confirmed.**

### Step 5 — Conclusion

Two problems, owned by two different parties:
1. **Driver bug (vendori2c, the I2C controller driver):** it polls hardware **without a timeout at DISPATCH_LEVEL**. Even if the hardware misbehaves, a driver must never spin unbounded in a DPC. It should give up after a bounded time (microseconds to a millisecond, not seconds), report an error, and recover, for example by resetting the controller or scheduling a bus-recovery sequence from a PASSIVE_LEVEL work item.
2. **Hardware/firmware trigger:** after the update, the touchpad at address `0x2c` holds the bus. That goes to the touchpad firmware owners, with the register snapshot.

```c
// Bounded version: never wait unbounded at DISPATCH_LEVEL.
static NTSTATUS I2cWaitForTxEmpty(PI2C_CONTROLLER ctx)
{
    for (ULONG i = 0; i < 50; i++) {                // at most ~500 µs
        if (READ_REGISTER_ULONG(&ctx->Regs->Status) & I2C_STATUS_TX_EMPTY)
            return STATUS_SUCCESS;
        KeStallExecutionProcessor(10);
    }
    ctx->LastError = STATUS_IO_TIMEOUT;
    WdfWorkItemEnqueue(ctx->BusRecoveryWorkItem);   // recovery runs at PASSIVE_LEVEL, where waiting is allowed
    return STATUS_IO_TIMEOUT;
}
```

### The triage note

> **0x133 subcode 0: a single DPC ran ~20 s** (0x501 of 0x500 ticks) in `vendori2c!I2cWaitForTxEmpty`, called from its DPC `I2cDpcForIsr`. It polls `Status` bit 1 (TX_EMPTY) with `KeStallExecutionProcessor(10)` and no exit; the status register shows TX_EMPTY clear and bus-held bits set, with target `0x2c` (touchpad) pending 4 bytes. **Two owners:** vendori2c must bound the wait and recover at PASSIVE_LEVEL; the touchpad firmware must not hold the bus. Three other DPCs (ndis, USB, power) were starved behind it.

---

<a id="scenario-5"></a>
## Scenario 5 — Random crashes in different places (use-after-free, two dumps)

### The situation

A laptop crashes every few days with **different bug checks in different modules**: one `0x50` in a touch driver, one `0x3B` in a USB driver, one `0x139` in the kernel. Users say it happens "while using the touchpad". Different stop codes in different places usually mean one thing: **something is corrupting memory**, and whoever touches the damaged memory next takes the blame.

**Hypotheses:**
- (A) A driver writes to memory it no longer owns (use-after-free or overflow), damaging other drivers' data.
- (B) Faulty RAM.
- (C) Three unrelated bugs.

(B) can be checked with a memory test, and (C) is statistically unlikely with "while using the touchpad" in common. Let's look at the clearest dump, the 0x50.

### Step 1 — The first dump

```
0: kd> !analyze -v
PAGE_FAULT_IN_NONPAGED_AREA (50)
Invalid system memory was referenced.  This cannot be protected by try-except.
Typically the address is just plain bad or it is pointing at freed memory.
Arguments:
Arg1: ffffb40f7a3c2fd8, memory referenced.
Arg2: 0000000000000000, X64: bit 0 set if the fault was due to a not-present PTE.
	bit 1 is set if the fault was due to a write, clear if a read.
	bit 3 is set if the processor decided the fault was due to a corrupted PTE.
	bit 4 is set if the fault was due to attempted execute of a no-execute PTE.
	- ARM64: bit 1 is set if the fault was due to a write, clear if a read.
	bit 3 is set if the fault was due to attempted execute of a no-execute PTE.
Arg3: fffff8034a71b2e6, If non-zero, the instruction address which referenced the bad memory
	address.
Arg4: 0000000000000002, (reserved)

STACK_TEXT:
nt!KeBugCheckEx
nt!MiSystemFault+0x...
nt!MmAccessFault+0x...
nt!KiPageFault+0x...
hidclass!HidpDistributeInterruptReport+0x46
hidclass!HidpInterruptReadComplete+0x...
nt!IopfCompleteRequest+0x...
Wdf01000!FxRequest::CompleteInternal+0x...
tpfilter!TpCompleteReport+0x72
tpfilter!TpEvtInterruptDpc+0x1b0
nt!KiExecuteAllDpcs+0x...
...

IMAGE_NAME:  hidclass.sys
FAILURE_BUCKET_ID:  AV_R_INVALID_hidclass!HidpDistributeInterruptReport
```

**Reading it:**
- **0x50**: an invalid kernel address was touched. Not NULL+offset this time: `ffffb40f`7a3c2fd8` looks like a perfectly normal **pool** address. A real-looking address that's invalid is a strong sign the memory **used to be** valid and was freed.
- **Arg2** (the help text shows how its meaning differs between x64 and Arm64): `0` = a read.
- `!analyze` blames **`hidclass.sys`**, Microsoft's HID class driver. But look at the stack: `hidclass` is completing a report that **`tpfilter`** (a vendor touchpad filter) handed to it through a request completion. hidclass may simply be **the victim**: it received a request whose buffer pointed at freed memory.

### Step 2 — What's at that address?

```
0: kd> !pool ffffb40f7a3c2fd8
Pool page ffffb40f7a3c2fd8 region is Nonpaged pool
 ffffb40f7a3c2000 size:   60 previous size:    0  (Allocated)  Irp
 ffffb40f7a3c2060 size:  130 previous size:    0  (Allocated)  Irp
 ...
*ffffb40f7a3c2fc0 size:   40 previous size:    0  (Free)      *TpRp
		Owning component : Unknown (update pooltag.txt)
```

**Reading it:**
- The faulting address is inside a pool block at `…2fc0`, which is **`(Free)`**.
- Its **pool tag** was `TpRp`. A tag is a 4-character label the allocating driver chooses; `Tp…` suggests **tpfilter**, "Rp" probably "report". The block was freed, but someone still read it.

> **Windows concept: pool and pool tags.** Kernel components get dynamic memory from **pool**, the kernel's heap: `ExAllocatePool2(flags, size, tag)`. Nonpaged pool never leaves RAM; paged pool can. Every allocation carries the caller's **tag**, which survives in the block header even after it's freed. That's how `!pool` can tell you who *last* owned a freed block. Freed blocks go back into the allocator's free lists and get reused, sometimes within microseconds, by **anyone**. A driver that keeps using a freed block either reads garbage (as here) or **corrupts whoever got the memory next**, which explains the other crashes in other modules.

**What this changes:** strong support for (A) against (B). Faulty RAM doesn't free blocks with consistent tags. The suspect is tpfilter, with a use-after-free of its own "report" buffer. But this dump can only show **who used the memory after it was freed**, not **who freed it too early, or when**. The evidence of that has already been overwritten. We need a better dump.

### Step 3 — Change the experiment: Driver Verifier with special pool

The next capture is a **configuration change**, not a command. On the test machine:

```
verifier /standard /driver tpfilter.sys
```

(then reboot; the standard checks include **special pool** and **pool tracking**). Under special pool, each of tpfilter's allocations is placed so that its end touches an **inaccessible page**, and when it's freed, the **whole page is made inaccessible** for a while instead of being reused. So:
- a read or write past the end faults **immediately**, at the guilty instruction;
- any use after free faults **immediately**, at the guilty instruction, with a dedicated bug check.

Two days later, a new dump:

### Step 4 — The second dump

```
0: kd> !analyze -v
DRIVER_PAGE_FAULT_IN_FREED_SPECIAL_POOL (d5)
Memory was referenced after it was freed.
This cannot be protected by try-except.
When possible, the guilty driver's name (Unicode string) is printed on
the bugcheck screen and saved in KiBugCheckDriver.
Arguments:
Arg1: ffffa60c1e9b7fc0, memory referenced
Arg2: 0000000000000000, value 0 = read operation, 1 = write operation
Arg3: fffff8034a7a1f84, if non-zero, the address which referenced memory.
Arg4: 0000000000000000, (reserved)

STACK_TEXT:
nt!KeBugCheckEx
nt!MiSystemFault+0x...
nt!MmAccessFault+0x...
nt!KiPageFault+0x...
tpfilter!TpCompleteReport+0x44
tpfilter!TpEvtInterruptDpc+0x1b0
nt!KiExecuteAllDpcs+0x...
...

IMAGE_NAME:  tpfilter.sys
FAILURE_BUCKET_ID:  AV_VRF_R_tpfilter!TpCompleteReport
```

**Now the crash is in tpfilter itself**, at the first touch of the freed memory: `TpCompleteReport+0x44` reads the freed block before passing it on. `0xD5` says it outright: memory referenced **after it was freed**. `VRF` in the bucket means Verifier was active. The victim is gone from the story.

### Step 5 — Who freed it, and from where?

With Verifier's pool tracking on, the `!verifier` extension can show the recent allocate/free history of an address (flag `0x80`):

```
0: kd> !verifier 0x80 ffffa60c1e9b7fc0

Log of recent kernel pool Allocate and Free operations:

There are up to 0x10000 entries in the log.

Parsing 0x0000000000010000 log entries, searching for address 0xffffa60c1e9b7fc0.

======================================================================
Pool block ffffa60c1e9b7fc0, Size 0000000000000040, Thread ffffc6812a0bc080
fffff803153b3a1d nt!VfFreePoolNotification+0x...
fffff80315181c4d nt!ExFreePoolWithTag+0x...
fffff8034a7a2210 tpfilter!TpFreeReport+0x20
fffff8034a7a2390 tpfilter!TpEvtRequestCancel+0x50          ◄── freed by the CANCEL routine
fffff8031520e8f1 Wdf01000!FxRequest::...Cancel...+0x...
fffff803150b7a1c nt!IoCancelIrp+0x...
fffff8031552c0a1 nt!IopCancelIrpsInThreadList+0x...
fffff803155c1e0b nt!PspExitThread+0x...
======================================================================
Pool block ffffa60c1e9b7fc0, Size 0000000000000040, Thread ffffc6812a8e1080
fffff803153b3b2a nt!VfAllocPoolNotification+0x...
fffff80315182b13 nt!ExAllocatePool2+0x...
fffff8034a7a21b0 tpfilter!TpAllocReport+0x20
fffff8034a7a1d40 tpfilter!TpEvtIoRead+0x60                  ◄── allocated when a read request arrived
fffff8031521d0aa Wdf01000!FxIoQueue::DispatchEvents+0x...
...
```

**Reading it (newest entry first):**
- **Allocated** in `TpEvtIoRead`: when an application's read request (waiting for the next touch report) arrived, tpfilter allocated a report buffer for it.
- **Freed** in `TpEvtRequestCancel`. Look at the frames below it: `PspExitThread → IopCancelIrpsInThreadList → IoCancelIrp`. **The thread that issued the read exited** (for example, an app closed), so Windows cancelled its outstanding IRPs (the thread's IRP list), and tpfilter's cancel routine freed the buffer.
- **Then used** in `TpEvtInterruptDpc → TpCompleteReport`: a touch interrupt arrived, and the DPC tried to fill and complete the **same** request with its now-freed buffer.

> **Windows concept: cancellation is a race by nature.** When a thread exits, the kernel cancels every IRP in that thread's IRP list. The cancel callback can run on one CPU at the same time as the driver's DPC is completing the same request on another CPU. Exactly one of them may complete the request and free its resources. Drivers must arbitrate who owns the request. KMDF provides that: `WdfRequestUnmarkCancelable` fails with `STATUS_CANCELLED` if cancellation already won. A driver that ignores that return value, or frees shared resources inside the cancel routine without coordinating, has a use-after-free.

### Step 6 — Conclusion

```
 CPU 1 (thread exit → cancel)                 CPU 0 (touch interrupt → DPC)
 ───────────────────────────────              ─────────────────────────────────────
 TpEvtRequestCancel(request):                 TpEvtInterruptDpc:
                                                req = ctx->PendingRead;   // still set
   TpFreeReport(ctx->PendingReport);  // FREE
   WdfRequestComplete(request, CANCELLED);
                                                TpCompleteReport(req, ctx->PendingReport)
                                                  → reads freed report → 0xD5 (with Verifier)
                                                  → without Verifier: memory may already be someone
                                                    else's; corrupted data flows into hidclass and others
```

```c
// The fix pattern in KMDF: arbitrate ownership before touching the request's resources.
VOID TpEvtInterruptDpc(WDFINTERRUPT Interrupt, WDFOBJECT Device)
{
    PTP_CONTEXT ctx = TpGetContext(Device);
    WDFREQUEST req = TpTakePendingRead(ctx);        // atomically take it (under a lock), or NULL
    if (req == NULL) return;
    if (WdfRequestUnmarkCancelable(req) == STATUS_CANCELLED) {
        return;                                     // cancel routine owns it now: don't touch it
    }
    TpFillAndComplete(req, ctx);                    // we own it: safe to use and free its report
}
// ...and the cancel routine must take the request via the same TpTakePendingRead, so only one side ever does.
```

### The triage note

> **Memory corruption** (various 0x50/0x3B/0x139). The first dump's 0x50 read a freed `TpRp` pool block via hidclass (a victim). With **Driver Verifier special pool on tpfilter.sys**, the next crash was **0xD5** in `tpfilter!TpCompleteReport`. Verifier's log shows the block was **freed by `TpEvtRequestCancel` during thread exit** and then used by the interrupt DPC: a cancel-vs-completion race. **Fix:** arbitrate request ownership (`WdfRequestUnmarkCancelable` result) and free the report only by the side that owns the request. Other crash signatures are likely downstream corruption; recheck after the fix.

### How the path narrowed (across two dumps)

```
"different crashes, various modules"
  → pattern suggests corruption, not three bugs
  → dump 1: 0x50 at a normal-looking pool address; !pool: Free, tag TpRp    (who OWNED it)
  → the first dump can't show who freed it → change the experiment
  → Verifier special pool on tpfilter → dump 2: 0xD5 in tpfilter            (who USED it, immediately)
  → !verifier 0x80: freed in the cancel routine during thread exit          (who FREED it, and why)
  → conclusion: cancel/complete race                                         (fix: ownership)
```

---

<a id="scenario-6"></a>
## Scenario 6 — 0x101: a processor went silent

### The situation

An Arm64 development board hangs and then crashes with `CLOCK_WATCHDOG_TIMEOUT (0x101)`, rarely, after hours idle on the desktop. It's the shortest scenario, because it ends at a boundary the debugger can't see past, and recognizing that boundary is the lesson.

### Step 1 — The analysis

```
0: kd> !analyze -v
CLOCK_WATCHDOG_TIMEOUT (101)
An expected clock interrupt was not received on a secondary processor in an
MP system within the allocated interval. This indicates that the specified
processor is hung and not processing interrupts.
Arguments:
Arg1: 0000000000000030, Clock interrupt time out interval in nominal clock ticks.
Arg2: 0000000000000000, 0.
Arg3: ffff8f0c3a5c0180, The PRCB address of the hung processor.
Arg4: 0000000000000003, The index of the hung processor.

STACK_TEXT:
nt!KeBugCheckEx
nt!KeAccumulateTicks+0x...
nt!KeClockInterruptNotify+0x...
...
nt!KiIdleLoop+0x...
```

**Reading it:**
- **Arg4 = 3: processor 3 is the one that hung.** The current stack is on processor 0, the one that **noticed**. As in Scenarios 2 and 4, the visible stack is the detector.
- Arg1: processor 3 missed clock interrupts for `0x30` = 48 ticks.

> **Windows concept: why one CPU can tell another is dead.** Processors regularly confirm they're alive by handling their clock interrupt. Another processor checks this. If one processor stops responding for too long (not even taking interrupts), the system can't trust it, for example to answer a request to flush caches or to stop. The watchdog bug checks to capture what it can.

### Step 2 — Switch to the hung processor

```
0: kd> ~3
3: kd> k
 # Child-SP          RetAddr               Call Site
00 ffff8f0c`3a5e7b90 fffff806`32a1e8d8     nt!PpmIdleExecuteTransition+0x...
01 ffff8f0c`3a5e7c60 00000000`00000000     nt!KiIdleLoop+0x58

3: kd> .frame /r 0
00 ffff8f0c`3a5e7b90 fffff806`32a1e8d8     nt!PpmIdleExecuteTransition+0x...
 x0=0000000000000004  x1=0000000040000000  ...
 pc=fffff8063292b10c ...
```

**Reading it:**
- `~3` switches the debugger's view to processor 3. The **prompt changes to `3: kd>`** to remind you.
- Processor 3's last saved state: it was in its **idle loop**, inside `PpmIdleExecuteTransition`, the kernel's processor power management code entering an **idle state**.
- The last instruction is the hand-off point to platform firmware: on Arm64, deep CPU idle states are entered through a standard **firmware call** (PSCI, the Power State Coordination Interface), passing which state to enter (`x1` holds a value that identifies the state). **After that call, the CPU is executing firmware or is powered down, which is outside Windows and outside anything the dump captured.**

> **Windows concept: processor idle states.** When a CPU has nothing to run, Windows doesn't just spin. It asks the platform to put the CPU into a low-power idle state, from light (stop the clock) to deep (power the core off and restore it later). The kernel picks a state and calls the platform. Waking requires an interrupt to arrive *and* the firmware/hardware to bring the core back. If that wake-up path fails, the CPU never returns to Windows, and the watchdog reports 0x101.

### Step 3 — Where the debugger's view ends

There's no driver to blame and no Windows code running on processor 3. The dump stops at the firmware boundary. The right conclusion:

> **0x101: processor 3 stopped responding while entering a deep idle state** (last kernel frame `PpmIdleExecuteTransition`, about to call the platform firmware to enter the idle state). No Windows code was running on it. **Likely owner:** platform firmware / power management for that idle state (or silicon). **Next capture:** firmware logs from the platform; as a diagnostic experiment, disable the deepest idle state (via the platform's power settings) and see whether the hang disappears. If it does, that's strong evidence for the idle-state path.

The lesson: **sometimes the right triage result is "the evidence leaves Windows here; hand it to these owners, with this proof."**

---

## 9. Patterns across all six

### The stack: "detector" vs "culprit"

| Scenario | What's at the top of the current stack | Where the culprit actually is |
|---|---|---|
| 1 (0xD1) | exception handling + bug check | the frame just below the trap: `VnRxDpcRoutine` |
| 2 (0x9F) | the power watchdog timer DPC | a **different thread**, found with `!stacks` |
| 3 (hang) | the button-press handler | **two other threads**, found with `!locks` + `!thread` |
| 4 (0x133) | the clock interrupt | **below the interrupt boundary** on the same stack |
| 5 (0x50 → 0xD5) | an innocent driver (dump 1) | revealed by **a second dump** with Verifier |
| 6 (0x101) | processor 0's clock check | **another processor** (`~3`), and then outside Windows |

**General rule:** first decide *what kind of thing noticed the problem* (an exception, a watchdog, a person, Verifier), then look **away** from that, toward the code that caused it.

### The first command for each shape

| Shape | First command after `!analyze -v` | Why |
|---|---|---|
| Bad pointer / exception | `.trap` (or `.cxr` for 0x7E/0x3B), then `u`/`ub` | registers + instruction = which pointer, which field |
| Stuck request (0x9F, I/O hang) | `!irp` on the IRP | who holds it |
| Hang (forced dump) | `!running -ti` | busy (CPU stuck) vs idle (waiting) |
| Idle hang | `!locks`, then `!thread` on owners | follow the wait chain until it loops |
| DPC watchdog (0x133) | read Arg1, then `k` below the interrupt frame | single overrun vs cumulative |
| Corruption | `!pool` on the bad address | free or allocated, and whose tag |
| Processor timeout (0x101) | `~<Arg4>` then `k` | the hung CPU, not the noticing one |

### Context labels to attach to every frame you care about

| Stack below the driver frame contains | Context | IRQL | May it wait? |
|---|---|---|---|
| `KiSystemServiceCopyEnd` / user frames | system call on a program's thread | PASSIVE (unless raised) | yes |
| `ExpWorkerThread` / `IopProcessWorkItem` | system worker thread (work item) | PASSIVE | yes |
| `KiExecuteAllDpcs` / `KiRetireDpcList` | DPC (any thread, any process) | DISPATCH | **no** |
| `KiInterruptDispatch…` | interrupt service routine | device IRQL (DIRQL) | **no** |

### The triage note template

```
<stop code / symptom> — <plain-language meaning, with the key parameter>
in <module>!<function> (<who owns that module>), running as <context> at <IRQL>.
Evidence: <the 2–3 facts that prove it>.
Next: <fix, or the next capture that would confirm it>.
```

---

## 10. Command reference

Organized by the question you're trying to answer. Every command here appeared in a scenario above.

| Question | Command | Seen in |
|---|---|---|
| Set up symbols | `.symfix`, `.sympath+ <dir>`, `.reload /f <module>`, `!sym noisy` | §1, S1 |
| What happened? | `!analyze -v` | all |
| What path led here? | `k` (stack), `kb`/`kn`/`kv` variants | all |
| Whose module, which version? | `lm`, `lmvm <module>` | S1 |
| Registers at the fault | `.trap <addr>`, `.cxr <addr>` (exceptions), `r`, `.frame /r <n>` | S1, S6 |
| Instructions | `u <addr>`, `ub <addr>`, `uf <function>` | S1, S4 |
| Interpret memory as a type | `dt <module>!<type> <addr>` | S1, S2, S4 |
| Raw memory | `dq`, `dd`, `db` | — |
| Find symbols by pattern | `x <module>!<pattern>` | S2 |
| Driver / device / stack / tree | `!drvobj`, `!devobj`, `!devstack`, `!devnode` | S1, S2 |
| A request | `!irp <addr>` | S2 |
| Power state | `!poaction` | S2 |
| One thread | `!thread <addr>` | S2, S3 |
| Search all stacks | `!stacks 2 <string>` | S2 |
| KMDF driver log | `!wdfkd.wdflogdump <driver>` | S2 |
| Every CPU | `!running -ti` | S3 |
| Locks | `!locks` | S3 |
| Queued DPCs | `!dpcs` | S4 |
| Pool block / tag | `!pool <addr>` | S5 |
| Verifier history | `!verifier 0x80 <addr>` | S5 |
| Switch processor | `~<n>` | S6 |
| IRQL | `!irql` | §1 |

---

## 11. Misconceptions

| You might think | Reality | Seen in |
|---|---|---|
| `IMAGE_NAME` / "Probably caused by" is the answer. | It's a rule-based guess. It named ACPI in S2 and hidclass in S5, and both were wrong. | S2, S5 |
| The top of the stack is the culprit. | For exceptions it's the handler; for watchdogs it's the detector; for forced dumps it's irrelevant. | all |
| `PROCESS_NAME: System` means a system process caused it. | In a DPC it's whatever thread was interrupted, often the idle thread. | S1 |
| A NULL check fixes a NULL crash. | If the pointer is freed by another CPU, the check only shrinks the window. Fix the ordering. | S1 |
| A freeze with no dump can't be debugged. | Force a dump (power button, keyboard, NMI) and investigate the whole system's state. | S3 |
| Waiting threads use CPU. | Blocked threads are off the CPU (`KiSwapContext` on top). An idle hang has idle CPUs. | S3 |
| A deadlock needs a bug in one place. | It needs **two** paths that take the same locks in opposite orders. Each path alone looks fine. | S3 |
| Polling a register in a DPC is fine if the hardware is "always fast". | Hardware can stop responding. Unbounded waits at DISPATCH_LEVEL become 0x133 and starve every other DPC on that CPU. | S4 |
| The module that crashed is the module with the bug. | With corruption, the crasher is often the victim. Verifier moves the crash to the culprit. | S5 |
| The debugger can see everything. | It sees what Windows saved. Firmware, powered-off cores and device internals are outside the dump. | S6 |
| Arm64 debugging needs a different method. | Same method; different registers, instruction syntax and argument registers. | interlude |

---

## 12. Self-check questions

**1.** A 0xD1 shows `Arg1 = 0000000000000020`. Before running any other command, what does that number most likely mean?

<details><summary>Answer</summary>
The code read or wrote the field at offset `0x20` of a structure through a NULL pointer: NULL + 0x20. No object lives at address `0x20`. The next step is `.trap` and `ub` to find which register held NULL and where it was loaded from.
</details>

**2.** In Scenario 1, why did we ignore `PROCESS_NAME: System`?

<details><summary>Answer</summary>
The faulting code ran as a DPC (`KiExecuteAllDpcs` below it). DPCs run on whatever thread is current on that processor. Here it was the idle thread, so the process name says nothing about who requested the work.
</details>

**3.** Arm64 trap frame: `x8=0`, instruction `ldr w9,[x8,#0x48]`. Write the x64 equivalent and say what's identical about the reasoning.

<details><summary>Answer</summary>
Something like `mov r9d,dword ptr [rax+48h]`. In both, the address read = base register + 0x48. With the base at 0, the faulting address is 0x48: a NULL pointer to a structure whose field is at +0x48.
</details>

**4.** In Scenario 2, the analyzer said `IMAGE_NAME: ACPI.sys`. What single command showed it was wrong, and what in its output proved it?

<details><summary>Answer</summary>
`!irp <Arg4>`. The current stack location (`>`) belonged to `\Driver\camvendor` with Control `e1` (pending returned). ACPI's location (the bottom) had never been reached.
</details>

**5.** `!thread` shows `Ticks: 3840`. About how long has the thread been waiting, assuming the usual 15.625 ms tick?

<details><summary>Answer</summary>
3840 × 15.625 ms = 60,000 ms = 60 seconds.
</details>

**6.** A forced dump shows `Idle Processors: (fe)` on an 8-CPU machine. Busy hang or idle hang, and what's your next command?

<details><summary>Answer</summary>
`fe` = CPUs 1–7 idle. CPU 0 is only handling the forced bug check. It's an idle hang (deadlock or stuck wait). Next: `!locks`, and/or `!stacks 2 <suspect driver>`, then `!thread` on owners and waiters to follow the chain.
</details>

**7.** Describe the deadlock in Scenario 3 as a table of "holds / wants", and state the general fix.

<details><summary>Answer</summary>
A (rotation work item): holds `g_ConfigLock`, wants `BusMutex`. B (calibration IOCTL): holds `BusMutex`, wants `g_ConfigLock`. Fix: one global lock order used by every path, or never hold one lock while acquiring the other. Verifier's deadlock detection can catch the inversion even without a collision.
</details>

**8.** In Scenario 4's stack, which frame is "the boundary", and why are the frames above it not the culprit?

<details><summary>Answer</summary>
`nt!KiInterruptDispatchNoLockNoEtw` (frame 07): an interrupt arrived there. The frames above are the clock interrupt that counted ticks and noticed the overrun. The frames below it (`nt!KeStallExecutionProcessor`, called by `vendori2c!I2cWaitForTxEmpty` ← `I2cDpcForIsr`) are the DPC that was running when the clock interrupt arrived. `KeStallExecutionProcessor` is Microsoft's code, but it's only there because vendori2c called it in a loop; the first non-Microsoft frame is the lead.
</details>

**9.** Why did Scenario 4 use `uf` rather than `ub`?

<details><summary>Answer</summary>
On x64, instructions are variable-length, so disassembling backwards can start mid-instruction and show garbage. `uf` disassembles the function forward from its known start. (On Arm64, with fixed 4-byte instructions, `ub` is exact.)
</details>

**10.** In Scenario 5, why couldn't the first dump identify the bug, and what did Verifier's special pool change?

<details><summary>Answer</summary>
The first dump caught a **later** user of freed memory (hidclass, receiving a buffer from tpfilter). The free had happened earlier, and the memory may already have been reused. Special pool keeps freed pages inaccessible, so the **first** touch after the free crashes immediately (0xD5) in the guilty driver. Pool tracking (`!verifier 0x80`) shows the allocation and free stacks.
</details>

**11.** What sequence of kernel events led to the freed buffer in Scenario 5?

<details><summary>Answer</summary>
An application thread issued a read (tpfilter allocated a report buffer in `TpEvtIoRead`). The thread exited, so `PspExitThread` cancelled the IRPs on its list (`IopCancelIrpsInThreadList` → `IoCancelIrp`). tpfilter's cancel routine freed the buffer while the interrupt DPC on another CPU was about to complete the same request with it.
</details>

**12.** For 0x101, which parameter do you use, what command follows, and when is "outside Windows" a valid conclusion?

<details><summary>Answer</summary>
Arg4 (the index of the hung processor) → `~<n>` then `k` (and `.frame /r`). "Outside Windows" is valid when the hung CPU's last Windows state shows it handing off to firmware or hardware (for example, entering an idle state) and no Windows code was running there. Then hand off to the platform owners with that evidence, plus an experiment (disable that idle state).
</details>

---

## 13. Sources

All checked 2026-11-12. Debugger sessions in this document are simulated (see the header); the facts below are what they're built on.

- Microsoft Learn, bug check reference: 0xD1 DRIVER_IRQL_NOT_LESS_OR_EQUAL, 0x9F DRIVER_POWER_STATE_FAILURE (subcode 3: Arg2 PDO, Arg4 blocked IRP), 0x133 DPC_WATCHDOG_VIOLATION (Arg1 0 = single DPC/ISR, with time count vs allotment; Arg1 1 = cumulative), 0x101 CLOCK_WATCHDOG_TIMEOUT (Arg4 = hung processor index), 0x50 PAGE_FAULT_IN_NONPAGED_AREA (Arg2 meaning differs between x64 and Arm64), 0xD5 DRIVER_PAGE_FAULT_IN_FREED_SPECIAL_POOL, 0x1C8 MANUALLY_INITIATED_POWER_BUTTON_HOLD.
- Microsoft Learn, "Forcing a System Crash with the Power Button" (PowerButtonBugcheck registry value; hold 7 s, release before the 10 s firmware reset).
- Microsoft Learn, debugger command references: `!analyze`, `.trap`, `.cxr`, `.frame`, `u`/`ub`/`uf`, `dt`, `x`, `lm`, `!irp`, `!devstack`, `!devnode`, `!drvobj`, `!poaction`, `!thread`, `!stacks`, `!running`, `!locks`, `!dpcs`, `!pool`, `!verifier`, `~` (switch processor), and `!wdfkd.wdflogdump` (KMDF In-Flight Recorder).
- Microsoft Learn, KMDF "A device leaves the working (D0) state" callback sequence: I/O queues stopped → `EvtDeviceD0ExitPreInterruptsDisabled` → `EvtInterruptDisable` → `EvtDeviceD0Exit`.
- Microsoft Learn, Driver Verifier: Special Pool, Pool Tracking, Deadlock Detection, Force IRQL checking; `WdfRequestUnmarkCancelable` returning `STATUS_CANCELLED`; `KeFlushQueuedDpcs`.
- Microsoft Learn / Arm documentation: Arm64 calling convention (x0–x7 arguments, x19–x28 callee-saved, x29 frame pointer, x30 link register), x64 calling convention (rcx, rdx, r8, r9); PSCI as the firmware interface for CPU idle/power states on Arm.
- The 0x133 example values (0x501 of 0x500 ticks) follow the example in Microsoft's 0x133 documentation; the 15.625 ms clock tick is Windows' default timer resolution.
