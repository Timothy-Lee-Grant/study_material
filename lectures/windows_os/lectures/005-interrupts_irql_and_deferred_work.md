2026_10_21_23_00-(Interrupts-IRQL-And-Deferred-Work)

# Lecture 005 — Interrupt Handling in Code: IRQL, the ISR → DPC → Work Item Chain, and Why Paging Is Forbidden at DISPATCH_LEVEL

> **For:** Timothy · **Date:** 2026-10-21
> **Prerequisites:** `lectures/firmware/003-from_bare_metal_to_an_os.md` §4–7 (flags, edge/level, controllers, IRQL basics, passive-level ISRs, pageable memory). This lecture goes one level deeper: **into the code**, and into the exact rules.
> **Why this lecture:** you can already explain why code at DISPATCH_LEVEL can't wait. This lecture makes the whole chain concrete: what each stage is allowed to do, how data passes between stages, how a KMDF driver writes it, and the precise rule about paging. It also separates two ideas that are easy to merge, privilege and priority.

---

## Core ideas (the answer key)

1. **Privilege and priority are two different axes.** *Privilege* (user mode vs kernel mode) decides what memory and instructions code may use. *Priority* (IRQL) decides what may interrupt it. All user code runs at PASSIVE_LEVEL; kernel code can be at any IRQL.
2. **IRQL is a per-processor threshold held in a CPU register** (CR8 on x64). It's raised automatically when the processor takes an interrupt, raised explicitly by code (taking a spin lock, `KeRaiseIrql`), and lowered when that code finishes. It's not a value in RAM, and it's not a wire.
3. **Interrupt delivery is event-driven.** At boot, routes are *set up* (ACPI, the interrupt controller's routing table, the IDT, interrupt objects). At runtime the hardware *fires* and the processor jumps to the handler. Nothing in the OS watches the lines.
4. **Each stage of the chain does the minimum its level allows:**
   - **ISR** (DIRQL): confirm it's ours, silence or mask the source, capture what's volatile, queue a DPC.
   - **DPC** (DISPATCH_LEVEL): finish short, non-waiting work, complete requests, queue a work item if waiting is needed.
   - **Work item** (PASSIVE_LEVEL, on an existing system worker thread): anything slow or blocking.
5. **No thread is created per interrupt.** DPCs go into a per-processor DPC queue that the processor drains when its IRQL drops below DISPATCH_LEVEL. Work items go into a queue served by worker threads that already exist.
6. **Stages share data through the device context, protected by the right lock.** Data shared with an ISR needs the **interrupt spin lock** (raises to DIRQL). Data shared among DPCs needs a regular spin lock (raises to DISPATCH_LEVEL). Holding either one puts you at elevated IRQL, with all its rules.
7. **Paging is forbidden above APC_LEVEL because resolving a page fault requires waiting for disk I/O, and waiting requires the scheduler, which runs at DISPATCH_LEVEL.** So code at DISPATCH_LEVEL or above must touch only **nonpaged** memory and run only **nonpaged** code. Breaking this is 0xD1/0xA, made deterministic by Verifier's Force IRQL Checking.
8. **For devices behind a bus (I2C/SPI), the ISR can't silence the device**, because that requires a bus transfer. KMDF's passive-level interrupt solves it: the pin is masked at the GPIO controller, the ISR runs on a kernel thread at PASSIVE_LEVEL and reads the device, then the pin is **unmasked after** the ISR returns.

---

## Table of Contents

- [1. Two axes: privilege and priority](#1-two-axes-privilege-and-priority)
- [2. IRQL precisely](#2-irql-precisely)
- [3. Setup time vs run time](#3-setup-time-vs-run-time)
- [4. The chain, stage by stage](#4-the-chain-stage-by-stage)
- [5. The chain in KMDF code](#5-the-chain-in-kmdf-code)
- [6. Sharing data between stages: locks and IRQL](#6-sharing-data-between-stages-locks-and-irql)
- [7. The bus-device case: passive-level interrupts](#7-the-bus-device-case-passive-level-interrupts)
- [8. Why paging is forbidden at DISPATCH_LEVEL](#8-why-paging-is-forbidden-at-dispatch_level)
- [9. How violations show up](#9-how-violations-show-up)
- [10. Misconceptions](#10-misconceptions)
- [11. Saying it precisely](#11-saying-it-precisely)
- [12. Self-check](#12-self-check)
- [Sources](#sources)

---

## 1. Two axes: privilege and priority 🟢

These two ideas are easy to merge into "levels of permission". They're separate:

| Axis | Values | What it controls | Who changes it |
|---|---|---|---|
| **Privilege** | User mode / kernel mode (on x64: ring 3 / ring 0; on Arm: EL0 / EL1) | Which memory pages are reachable (kernel pages are marked supervisor-only), and which instructions are allowed | Changes only at defined entry points: system calls, interrupts, exceptions |
| **Priority (IRQL)** | 0 … 15 on x64 (PASSIVE, APC, DISPATCH, device levels, CLOCK, IPI, HIGH) | Which interrupts may preempt the running code on this processor, and so what the code may do (wait, page fault) | Raised by taking an interrupt or a spin lock; lowered on release |

The four combinations, with examples:

| | PASSIVE_LEVEL | DISPATCH_LEVEL or above |
|---|---|---|
| **User mode** | Every application thread | *Never happens*: user code always runs at PASSIVE_LEVEL |
| **Kernel mode** | A driver's `DriverEntry`, most dispatch routines, work items, the passive-level ISR | DPCs, code holding a spin lock, ISRs (at DIRQL) |

So "the ISR runs at the highest level of permissions" mixes the axes. An ISR runs in **kernel mode** (privilege) at **its device's DIRQL** (priority). That level isn't the highest one: CLOCK, IPI and HIGH sit above every device level.

---

## 2. IRQL precisely 🟢

**Definition.** Each processor has a current IRQL. *A processor at IRQL n accepts only interrupts whose IRQL is greater than n.*

What each symbol stands for:
- **The processor's IRQL**: on x64, kept in the CPU register **CR8**, which programs the local APIC's task-priority threshold. Raising IRQL means writing a larger value there. On Arm, Windows maintains the equivalent with the GIC's priority mechanism. Either way it's processor state, not a variable in RAM that the OS looks up.
- **An interrupt's IRQL** (its DIRQL): assigned when the interrupt is connected. On x64 it comes from the interrupt's vector number (the vector's priority class).

**How it changes, step by step:**
1. The processor is running a thread at PASSIVE_LEVEL (0).
2. A device interrupt arrives whose IRQL is, say, 5. 5 > 0, so it's accepted. The processor saves state and jumps through the IDT. The kernel's dispatch code raises the processor's IRQL to 5 and calls the driver's ISR.
3. While at 5, interrupts at 5 or below wait. Higher ones (clock, IPI) can still preempt.
4. The ISR returns. The kernel lowers the IRQL back to what it was.
5. If DPCs were queued, the processor drains them at DISPATCH_LEVEL (2) before returning to the thread at 0.

**What runs where** (Microsoft's list of driver routines per IRQL):

| IRQL | Interrupts masked | Driver routines that run here |
|---|---|---|
| PASSIVE_LEVEL (0) | none | `DriverEntry`, `AddDevice`, Unload, most dispatch routines, driver-created threads, worker-thread callbacks |
| APC_LEVEL (1) | APC | some dispatch routines; same as PASSIVE except APCs are blocked; still a thread context, and still allowed to page |
| DISPATCH_LEVEL (2) | DISPATCH and APC | DPCs (`DpcForIsr`, custom DPCs, timer DPCs), StartIo, code holding a spin lock |
| DIRQL (3 … ~12) | everything at or below this interrupt's level | ISR, routines synchronized with the ISR (`SynchCritSection`) |
| HIGH_LEVEL (15) | everything | bugcheck code, a few very special paths |

---

## 3. Setup time vs run time 🟢

A common mistake is to picture the OS consulting a table, or watching a line, when an interrupt happens. It doesn't. Everything is prepared in advance, and at runtime the hardware does the routing.

| | **Setup time** (boot / device start) | **Run time** (each interrupt) |
|---|---|---|
| Firmware | ACPI says: touch device, GPIO pin 35, level, active-low | — |
| PnP manager | Turns the ACPI entry into the device's interrupt resource | — |
| Driver | Declares its ISR (and DPC) to KMDF (`WdfInterruptCreate`) | ISR and DPC run |
| Kernel / HAL | Connects an interrupt object to the vector; programs the interrupt controller's routing; the IDT already points vectors at the kernel's dispatch code | Raises IRQL, calls the ISR via the interrupt object |
| Hardware | — | The device asserts the line → the controller detects it → the CPU is interrupted with a vector → jump through the IDT |

The interrupt path is **wired up once, then fires on its own**. That's why a wrong ACPI description (say, edge instead of level) produces a wrongly wired path that silently misbehaves at runtime. Nothing re-reads the table.

The path also isn't always "one GPIO pin per device". Depending on the hardware:
- an interrupt may arrive on a dedicated interrupt-controller input,
- it may share a level-triggered line with other devices (each ISR answers TRUE "mine" or FALSE "not mine"),
- it may arrive as a message (MSI, typical for PCIe), or
- it may come through a GPIO controller acting as a second-tier controller.

---

## 4. The chain, stage by stage 🟢

Use a memory-mapped device as the example (registers directly accessible, unlike I2C): say a sensor block inside the SoC that raises an interrupt when a sample is ready.

### Stage 1: ISR (at DIRQL)

**Job:** the minimum that can't wait.
1. **Is it ours?** Read the device's interrupt-status register. If our bit isn't set, return FALSE: the line may be shared.
2. **Silence the source:** write the device's acknowledge register, so a level-triggered line drops and doesn't storm.
3. **Capture volatile data:** anything the device will overwrite (here, the sample register) into the device context.
4. **Queue the DPC** and return TRUE.

**Not allowed:** waiting, page faults, calling most kernel APIs, taking ordinary locks, running long.

### Stage 2: DPC (at DISPATCH_LEVEL)

**What a DPC is:** a small kernel object (`KDPC`) holding a function pointer and a context. Queueing it puts it on **the current processor's DPC queue**. When that processor's IRQL drops below DISPATCH_LEVEL, i.e. after the ISR returns, it **drains the queue**: it raises to DISPATCH_LEVEL and calls each DPC.

**Job:** finish what's short and non-blocking.
- Process the captured sample.
- Complete a pending I/O request (say, a read that was waiting for this data).
- Queue a **work item** if something must wait (talking to another driver synchronously, writing a file, a bus transfer).

**Not allowed:** waiting, page faults, running long (the DPC watchdog, 0x133).

### Stage 3: Work item (at PASSIVE_LEVEL)

**What a work item is:** a request that "a system worker thread call this function". The kernel keeps a **pool of worker threads that already exist**. Queueing a work item puts it on their queue; a worker thread picks it up and calls the function at PASSIVE_LEVEL, in a normal thread context.

**Job:** anything slow or blocking: waits, synchronous I/O, pageable memory, calls that must be made at PASSIVE_LEVEL.

### The flow, as one numbered trace

1. The device asserts its line. The controller interrupts CPU 2 with a vector.
2. CPU 2's IRQL is raised to the device's DIRQL. The ISR runs: it checks status, acks, captures the sample, and queues a DPC on CPU 2's queue. It returns TRUE.
3. CPU 2's IRQL drops toward DISPATCH_LEVEL. The DPC queue is non-empty, so the DPC runs at DISPATCH_LEVEL: it processes the sample, completes a read request, and queues a work item.
4. CPU 2's IRQL drops to PASSIVE_LEVEL and the interrupted thread continues.
5. Later, a system worker thread is scheduled (on any CPU), and the work-item function runs at PASSIVE_LEVEL.

**Pause and predict:** where does each stage run, in terms of *thread*? (Careful.)

<details><summary>Answer</summary>The ISR and the DPC run on whatever thread happened to be interrupted on that processor. They borrow it, and they have no thread of their own (that's why <code>PROCESS_NAME</code> in a dump can be misleading). The work item runs on a real, existing system worker thread. No thread is created for any stage.</details>

---

## 5. The chain in KMDF code 🔵

KMDF wraps the raw kernel objects. Here is a sketch of a driver's interrupt path (not compiled here: it needs the WDK):

```c
// Per-device state shared by the ISR, DPC and work item.
typedef struct _DEVICE_CONTEXT {
    PULONG  Regs;          // mapped device registers (MMIO), nonpaged
    ULONG   LastSample;    // captured by the ISR
    WDFWORKITEM WorkItem;  // for PASSIVE_LEVEL follow-up
} DEVICE_CONTEXT, *PDEVICE_CONTEXT;
WDF_DECLARE_CONTEXT_TYPE_WITH_NAME(DEVICE_CONTEXT, GetContext)

#define REG_STATUS 0   // which word of the register block (illustrative)
#define REG_SAMPLE 1
#define REG_ACK    2
#define STATUS_READY 0x1

// Stage 1: ISR, at DIRQL. Return TRUE only if our device interrupted.
BOOLEAN EvtInterruptIsr(WDFINTERRUPT Interrupt, ULONG MessageID)
{
    UNREFERENCED_PARAMETER(MessageID);
    PDEVICE_CONTEXT ctx = GetContext(WdfInterruptGetDevice(Interrupt));

    ULONG status = READ_REGISTER_ULONG(&ctx->Regs[REG_STATUS]);
    if ((status & STATUS_READY) == 0) {
        return FALSE;                                          // not ours (shared line)
    }
    ctx->LastSample = READ_REGISTER_ULONG(&ctx->Regs[REG_SAMPLE]); // capture volatile data
    WRITE_REGISTER_ULONG(&ctx->Regs[REG_ACK], STATUS_READY);       // silence the source
    WdfInterruptQueueDpcForIsr(Interrupt);                         // stage 2
    return TRUE;
}

// Stage 2: DPC, at DISPATCH_LEVEL. Short, non-waiting work.
VOID EvtInterruptDpc(WDFINTERRUPT Interrupt, WDFOBJECT AssociatedObject)
{
    UNREFERENCED_PARAMETER(AssociatedObject);
    PDEVICE_CONTEXT ctx = GetContext(WdfInterruptGetDevice(Interrupt));
    ULONG sample;

    WdfInterruptAcquireLock(Interrupt);      // raises to DIRQL: the ISR can't run mid-copy
    sample = ctx->LastSample;
    WdfInterruptReleaseLock(Interrupt);

    // ... complete a pending read request with 'sample' (allowed at DISPATCH_LEVEL) ...
    WdfWorkItemEnqueue(ctx->WorkItem);       // stage 3, for anything that must wait
}

// Stage 3: work item, at PASSIVE_LEVEL, on an existing system worker thread.
VOID EvtWorkItem(WDFWORKITEM WorkItem)
{
    PDEVICE_CONTEXT ctx = GetContext(WdfWorkItemGetParentObject(WorkItem));
    UNREFERENCED_PARAMETER(ctx);
    // ... slow things: synchronous calls, waits, pageable memory ...
}

// Setup time (in EvtDriverDeviceAdd): declare the ISR and DPC to the framework.
//   WDF_INTERRUPT_CONFIG cfg;
//   WDF_INTERRUPT_CONFIG_INIT(&cfg, EvtInterruptIsr, EvtInterruptDpc);
//   WdfInterruptCreate(device, &cfg, WDF_NO_OBJECT_ATTRIBUTES, &interrupt);
//   ... and create ctx->WorkItem with WDF_WORKITEM_CONFIG_INIT + WdfWorkItemCreate.
```

What each name stands for:
- `READ_REGISTER_ULONG` / `WRITE_REGISTER_ULONG`: volatile 32-bit accesses to mapped device registers (lecture 006 / 003's MMIO answer: the registers' physical addresses come as a resource and are mapped into kernel virtual space at start).
- `WdfInterruptQueueDpcForIsr`: queues the interrupt object's DPC on the current processor's queue.
- `WdfInterruptAcquireLock`: takes the **interrupt spin lock**, raising to the interrupt's DIRQL (§6).
- `WdfWorkItemEnqueue`: puts the work item on the system worker queue.

KMDF also offers `WdfInterruptQueueWorkItemForIsr`, which goes straight from the ISR to a work item when there's nothing worth doing at DISPATCH_LEVEL.

---

## 6. Sharing data between stages: locks and IRQL 🟢

The ISR, DPC and work item touch the same device context, possibly on different processors at the same moment. The rule for choosing a lock: **the lock must raise IRQL to at least the highest level of any code that touches the data.**

| Data shared between | Lock | IRQL while held |
|---|---|---|
| ISR and anything else | **Interrupt spin lock** (`WdfInterruptAcquireLock`, or `WdfInterruptSynchronize` with a callback) | The interrupt's DIRQL |
| DPCs and other code (not the ISR) | **Spin lock** (`WdfSpinLockAcquire`, `KeAcquireSpinLock`) | DISPATCH_LEVEL |
| Only PASSIVE_LEVEL code | **Mutex / wait lock** (`WdfWaitLockAcquire`, fast mutex) | Stays at PASSIVE (or APC) |

Why the interrupt spin lock *must* raise to DIRQL: if the DPC held an ordinary spin lock (at DISPATCH_LEVEL) and the ISR fired on the same processor, the ISR would preempt the DPC and spin on a lock that the DPC can't release until the ISR returns. That's a deadlock on one CPU. Raising to DIRQL blocks the ISR on that processor while the lock is held.

**The trap:** holding a spin lock puts you at DISPATCH_LEVEL even in code you think of as "normal". A function marked pageable, called while holding a spin lock, is a 0xD1 waiting for memory pressure. Microsoft lists exactly this: "The function was marked as pageable and was running at an elevated IRQL (which includes obtaining a lock)."

---

## 7. The bus-device case: passive-level interrupts 🟢

For the touch controller, stage 1 breaks: "silence the source" requires an I2C read, which waits. Here are the two options and their costs:

| Option | How | Cost |
|---|---|---|
| Classic chain | ISR masks the GPIO pin (allowed: the GPIO controller is memory-mapped), queues a DPC → work item, the work item does the I2C read and then **unmasks** the pin | Three hops and more code; easy to forget the unmask |
| **Passive-level interrupt** (KMDF/UMDF, Windows 8+, GPIO-based interrupts) | `cfg.PassiveHandling = TRUE;` the system masks the pin, runs the ISR on a kernel thread at PASSIVE_LEVEL, and **unmasks after the ISR returns** | The pin stays masked while the ISR runs, so the ISR should do only the initial servicing and defer the rest to a work item |

The full passive-level sequence for a level-triggered pin (Microsoft's documented behavior):
1. The pin asserts. The GPIO framework's primary handler identifies the pin, and the kernel **masks** it at the GPIO controller.
2. The kernel schedules the driver's ISR on a **passive-level kernel thread** that already exists.
3. The ISR runs at PASSIVE_LEVEL and reads the report over I2C. The device releases the line.
4. The ISR returns. The thread **unmasks** the pin.

If step 3's read fails (a bus error or timeout) and the driver returns anyway, the line is still asserted, so the pin fires again immediately after the unmask. A retry loop with no backoff can produce exactly the cumulative 0x133 from lecture 002.

---

## 8. Why paging is forbidden at DISPATCH_LEVEL 🟢

### The derivation, one step at a time

1. **Pageable memory** may be on disk at any moment: the memory manager moved its contents to the page file to free RAM (lecture 008).
2. Touching a page that's on disk makes the CPU raise a **page fault** (an exception through the IDT).
3. The kernel's page-fault handler must **read the page back from disk**, which means starting an I/O and **waiting** for it.
4. Waiting means "block this thread and let the scheduler run something else" (from 003).
5. The scheduler runs at **DISPATCH_LEVEL**. A processor at DISPATCH_LEVEL or above can't run it.
6. So at DISPATCH_LEVEL or above the wait can never be satisfied. The page-fault handler checks the IRQL first and, finding it above APC_LEVEL, **bugchecks** (0xA, or 0xD1 for driver addresses) instead of deadlocking.

Microsoft states the rule exactly: "Any routine that is running at greater than IRQL APC_LEVEL can not allocate memory from paged pool or access memory in paged pool safely. If a routine running at IRQL greater than APC_LEVEL causes a page fault, it's a fatal error."

The boundary is **"greater than APC_LEVEL"**, so APC_LEVEL itself is still allowed to page: it's a thread context, and the scheduler can still run.

### What a driver does about it

| Need | Use | Not |
|---|---|---|
| Memory touched by the ISR, DPCs, or under spin locks | **Nonpaged pool**: `ExAllocatePool2(POOL_FLAG_NON_PAGED, size, tag)`; WDF objects and contexts default to nonpaged | `POOL_FLAG_PAGED` |
| Code that runs at DISPATCH_LEVEL or above | Default (nonpaged) code sections | `#pragma alloc_text(PAGE, Fn)` |
| Code that only ever runs at PASSIVE_LEVEL and is rarely used | Mark it pageable to save RAM, **and** put `PAGED_CODE();` at its top; in checked/Verifier builds that asserts the IRQL is ≤ APC_LEVEL | Pageable code with no assertion |

`PAGED_CODE()` is the habit to copy: it turns an assumption ("this only runs at PASSIVE_LEVEL") into a checked statement.

---

## 9. How violations show up 🟢

| Violation | What you see | Where to look |
|---|---|---|
| Pageable memory or code at ≥ DISPATCH_LEVEL | 0xD1 / 0xA, rare until memory pressure; deterministic under Verifier Force IRQL Checking | 002 §1; 004 A2 |
| Waiting at ≥ DISPATCH_LEVEL (calling a blocking API) | 0xC4 or 0xD1 depending on the API; under Verifier a direct "called at too high an IRQL" | 004 A4 |
| ISR or DPC too long | 0x133 P1 = 0 | 002 §2 |
| Level-triggered source never silenced | Interrupt storm → 0x133 P1 = 1, or a frozen system | 002 §2; 004 recipe 1 |
| Forgotten unmask (classic-chain bus device) | Device works once, then never interrupts again: a "dead device" with an idle-looking driver | 003 §7 |
| Wrong lock level (ordinary spin lock shared with the ISR) | Single-CPU deadlock → hang, or 0x133 | 003 §6 |

---

## 10. Misconceptions

| You might think | Reality | Why it matters |
|---|---|---|
| IRQL is a value stored in RAM | It's per-processor state in a CPU register (CR8 on x64) | "IRQL" always means "on this processor, right now" |
| The ISR runs at the highest permission level | Kernel mode (privilege) at its device's DIRQL (priority); CLOCK/IPI/HIGH are above it | Keep privilege and priority as separate axes |
| The OS watches the interrupt lines | Hardware detects and delivers; the OS only set up the route in advance | Debug setup (ACPI, routing) separately from runtime behavior |
| A thread is created to handle each interrupt | ISRs and DPCs borrow the interrupted thread; work items run on existing worker threads | Explains `PROCESS_NAME` in dumps, and why no new threads appear |
| APC_LEVEL can't page | It can; the rule is "greater than APC_LEVEL" | Exact boundaries matter in reviews |
| Taking a spin lock in normal code is harmless | It raises to DISPATCH_LEVEL, with all its rules | Pageable code under a lock = latent 0xD1 |
| Masking the pin is the end of the story | The pin must be unmasked after the device is serviced | A forgotten unmask produces a dead device |

---

## 11. Saying it precisely

- "Privilege and IRQL are different axes: an ISR is kernel-mode code running at its device's DIRQL, and user code is always at PASSIVE."
- "IRQL is a per-processor threshold in a CPU register. Taking an interrupt raises it to the device's DIRQL, and taking a spin lock raises it to DISPATCH."
- "The ISR silences the source and queues a DPC on that processor's queue; the DPC does short work at DISPATCH and queues a work item; the work item runs at PASSIVE on an existing system worker thread. No thread is created per interrupt."
- "Paging is fatal above APC_LEVEL because resolving a fault means waiting on disk I/O, and waiting needs the scheduler, which runs at DISPATCH. So anything touched at DISPATCH or above must be nonpaged, and pageable functions carry `PAGED_CODE()`."
- "For an I2C device, the ISR can't silence the device, so KMDF's passive-level interrupt masks the GPIO pin, runs the ISR on a kernel thread at PASSIVE to do the read, and unmasks afterward."

---

## 12. Self-check

1. Fill in the 2×2 of privilege × IRQL with an example per cell (or "never").
<details><summary>Answer</summary>User/PASSIVE: an app thread. User/≥DISPATCH: never. Kernel/PASSIVE: DriverEntry, a work item, a passive-level ISR. Kernel/≥DISPATCH: a DPC, code holding a spin lock, an ISR (at DIRQL).</details>

2. Where is a processor's IRQL kept on x64, and what three things change it?
<details><summary>Answer</summary>In CR8 (the local APIC task priority). Taking an interrupt raises it (to DIRQL); code raises it (a spin lock, KeRaiseIrql); finishing or releasing lowers it.</details>

3. Split the touch interrupt's life into setup-time and run-time steps.
<details><summary>Answer</summary>Setup: ACPI describes the pin; PnP assigns the resource; the driver declares its ISR to KMDF; the kernel connects an interrupt object and programs the routing. Run time: the device asserts → the controller → the CPU is interrupted with a vector → IDT → IRQL raised → ISR.</details>

4. List the ISR's four jobs, in order.
<details><summary>Answer</summary>Check whether it's ours (return FALSE if not); silence or acknowledge the source; capture volatile data; queue the DPC and return TRUE.</details>

5. When exactly does a queued DPC run, and on which thread?
<details><summary>Answer</summary>When that processor's IRQL drops below DISPATCH_LEVEL (typically right after the ISR returns). It drains the queue at DISPATCH_LEVEL on whatever thread was interrupted. It has no thread of its own.</details>

6. Where does a work item run, and is a thread created for it?
<details><summary>Answer</summary>At PASSIVE_LEVEL on an existing system worker thread that picks it from a queue. No thread is created.</details>

7. Data shared between the ISR and the DPC: which lock, and why that one?
<details><summary>Answer</summary>The interrupt spin lock (WdfInterruptAcquireLock), which raises to DIRQL. An ordinary DISPATCH_LEVEL spin lock would let the ISR preempt the holder on the same CPU and spin forever.</details>

8. Derive why page faults are fatal above APC_LEVEL.
<details><summary>Answer</summary>Pageable memory may be on disk → a fault needs a disk read → that's a wait → waiting needs the scheduler → the scheduler runs at DISPATCH_LEVEL → at ≥ DISPATCH it can't run → the wait would never finish → the handler bugchecks instead.</details>

9. What does `PAGED_CODE()` do, and why use it?
<details><summary>Answer</summary>It asserts (in checked or verified builds) that the current IRQL is ≤ APC_LEVEL. It turns "this pageable function only runs at PASSIVE" into a checked claim.</details>

10. A touch driver uses the classic chain: the ISR masks the pin and the work item reads over I2C. After the first touch, it never interrupts again. What's the likely bug?
<details><summary>Answer</summary>The work item never unmasks the pin after the read (or only unmasks on the success path).</details>

11. Why can a failed I2C read in a passive-level ISR lead to 0x133?
<details><summary>Answer</summary>The device keeps the level line asserted, so after the unmask the interrupt fires again immediately. Repeated endlessly, the time at elevated IRQL accumulates past the watchdog limit (P1 = 1).</details>

---

## Sources

Checked 2026-10-21.

- Microsoft Learn: Managing hardware priorities (which routines run at each IRQL; "any routine that is running at greater than IRQL APC_LEVEL can not … access memory in paged pool safely… it's a fatal error"; APC_LEVEL still allows paging). https://learn.microsoft.com/windows-hardware/drivers/kernel/managing-hardware-priorities
- Microsoft Learn: Passive-level ISRs (GPIO): mask → passive thread → ISR → unmask. https://learn.microsoft.com/windows-hardware/drivers/gpio/passive-level-isrs
- Microsoft Learn: Supporting passive-level interrupts (WDF). https://learn.microsoft.com/windows-hardware/drivers/wdf/supporting-passive-level-interrupts
- Microsoft Learn: WDF interrupt, DPC and work-item reference (`WDF_INTERRUPT_CONFIG`, `WdfInterruptQueueDpcForIsr`, `WdfInterruptAcquireLock`, `WdfWorkItemEnqueue`, `WdfInterruptQueueWorkItemForIsr`).
- Microsoft Learn: Bug Check 0xD1 (causes, including pageable functions "running at an elevated IRQL (which includes obtaining a lock)").
- *Windows Internals, 7th ed., Part 1*: IRQL on x64 (CR8), DPC queues, system worker threads.

The KMDF code is a sketch and wasn't compiled here; the WDK isn't available in this environment. Register indices are illustrative.
