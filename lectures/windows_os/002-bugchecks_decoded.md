2026_10_21_22_00-(Bugchecks-Decoded)

# Lecture 002 — Bugchecks Decoded: 0xD1, 0x133, 0x9F, 0x50, 0x7E

> **For:** Timothy · **Date:** 2026-10-21
> **Prerequisites:** 001 (WinDbg commands). Mechanisms behind these codes: 005 (IRQL, DPCs, paging), 006 (device stacks), 007 (power).
> **Why this lecture:** five stop codes cover a large share of the driver-caused crashes you'll see on new hardware. Each code is a sentence the kernel writes about *which rule was broken*, and its four parameters are the evidence. This lecture teaches you to read that sentence and follow it to the layer at fault.

---

## Core ideas (the answer key)

1. **A bugcheck is the kernel stopping itself on purpose** because a rule it depends on was broken in kernel mode, where nothing can be isolated. The code names the rule; the four parameters are evidence; the meaning of each parameter depends on the code.
2. **0xD1 (DRIVER_IRQL_NOT_LESS_OR_EQUAL):** a driver touched pageable or invalid memory at DISPATCH_LEVEL or above. P1 = address touched, P2 = IRQL, P3 = read/write/execute, P4 = the instruction. Usually the *address* is the bug (freed, garbage, or paged), not the IRQL itself.
3. **0x133 (DPC_WATCHDOG_VIOLATION)** has two forms. P1 = 0: one DPC or ISR ran too long (the stack usually names it). P1 = 1: the processor spent too long *in total* at DISPATCH_LEVEL or above, which is harder; use `!dpcs` and ETW.
4. **0x9F (DRIVER_POWER_STATE_FAILURE):** a power transition didn't finish in time. P1 = 3 means a device object held a power IRP too long (P2 = PDO, P4 = the IRP). P1 = 4 means the transition timed out waiting on PnP (P3 = the thread holding the PnP lock). It's a *timeout*, so the stack of the crash is a watchdog, not the culprit.
5. **0x50 (PAGE_FAULT_IN_NONPAGED_AREA):** invalid system memory was referenced: a bad, freed or non-canonical address. Unlike 0xD1 it's not about IRQL; the address could never be paged in. P1 = address, P2 = read/write/execute, P3 = instruction, P4 = fault subtype.
6. **0x7E (SYSTEM_THREAD_EXCEPTION_NOT_HANDLED):** a kernel thread raised an exception nobody caught. P1 = exception code (0xC0000005 = access violation, 0x80000003 = breakpoint/assert), P2 = where. Use `.exr P3` and `.cxr P4` to see the fault, then `k`.
7. **The method is the same for every code:** read the parameters for *this* code → set the right context (trap, context, or IRP) → read the stack → identify the instruction and the address → name the layer and the rule in one sentence.
8. **Timeout codes (0x133 P1=1, 0x9F) crash in the watchdog, not in the guilty code.** For those, the evidence is in a structure the parameters point to (a triage block, a blocked IRP, a thread), not in the crashing stack.

---

## Table of Contents

- [0. How to read any stop code](#0-how-to-read-any-stop-code)
- [1. 0xD1 DRIVER_IRQL_NOT_LESS_OR_EQUAL](#1-0xd1-driver_irql_not_less_or_equal)
- [2. 0x133 DPC_WATCHDOG_VIOLATION](#2-0x133-dpc_watchdog_violation)
- [3. 0x9F DRIVER_POWER_STATE_FAILURE](#3-0x9f-driver_power_state_failure)
- [4. 0x50 PAGE_FAULT_IN_NONPAGED_AREA](#4-0x50-page_fault_in_nonpaged_area)
- [5. 0x7E SYSTEM_THREAD_EXCEPTION_NOT_HANDLED](#5-0x7e-system_thread_exception_not_handled)
- [6. Telling them apart](#6-telling-them-apart)
- [7. Neighbors worth recognizing](#7-neighbors-worth-recognizing)
- [8. Misconceptions](#8-misconceptions)
- [9. Saying it precisely](#9-saying-it-precisely)
- [10. Self-check](#10-self-check)
- [Sources](#sources)

---

## 0. How to read any stop code 🟢

**Who raises it.** Kernel code calls `KeBugCheckEx(code, p1, p2, p3, p4)`. Sometimes a driver calls it directly. Much more often it's Windows itself: the page-fault handler, the DPC watchdog, the power manager's timer, or the exception dispatcher, catching a broken rule. The *code* tells you which part of Windows caught it. The *parameters* are what that part wanted you to know.

**Why the whole machine stops** (from 003): kernel drivers share one address space with the kernel. There's no wall to put around the damage, so continuing risks writing corrupted data to disk.

**The five-step method:**

| Step | Do | Command |
|---|---|---|
| 1. Code and parameters | Look up what P1–P4 mean **for this code** | `!analyze -v`, then this lecture |
| 2. Context | Switch to the state that matters: trap frame, context record, or the IRP or thread a parameter points to | `.trap`, `.cxr`, `!irp`, `!thread` |
| 3. Stack | What was running, and in what context (ISR / DPC / worker / system call)? | `k`, `kn` |
| 4. Instruction and address | Which instruction, touching which address, and what kind of memory is it? | `ln`, `u`, `!pte`, `!pool`, `!address` |
| 5. One sentence | Name the layer, the rule broken, and the evidence | — |

---

## 1. 0xD1 DRIVER_IRQL_NOT_LESS_OR_EQUAL 🟢

### Meaning

Microsoft's description: "Typically, when this error occurs, a driver has tried to access an address that is pageable (or that is completely invalid) while the interrupt request level (IRQL) was too high."

The name is the rule, written in reverse: *the IRQL should have been less than or equal to* the level at which page faults can be served, APC_LEVEL (lecture 005 derives why). The plain sibling **0xA IRQL_NOT_LESS_OR_EQUAL** is the same rule; Windows uses 0xD1 when the faulting address belongs to a driver.

### Parameters

| Param | Meaning | What to do with it |
|---|---|---|
| P1 | Memory referenced | `!pte P1` (present?), `!pool P1` (freed? paged pool?), `!address P1` (what region?) |
| P2 | IRQL at the time | 2 = DISPATCH_LEVEL (a DPC, or holding a spin lock); higher = an ISR |
| P3 | 0 = read, 1 = write, 8 = execute | An execute means the code *itself* was pageable or the function pointer was bad |
| P4 | Address of the instruction | `ln P4` (which function), `u P4` (which instruction) |

### Typical causes (Microsoft's list)

- Dereferencing a bad pointer (NULL or freed) while at or above DISPATCH_LEVEL.
- Accessing pageable data at or above DISPATCH_LEVEL.
- Executing pageable code at or above DISPATCH_LEVEL, for example a function marked pageable that runs while holding a spin lock.
- Calling into a driver that has been unloaded.
- Calling through an invalid function pointer.

### Recipe

1. `!analyze -v`, then write down P1–P4.
2. `k`: confirm the context. Do you see a DPC frame (`KiExecuteAllDpcs`), an ISR frame (`KiInterruptDispatch`), or a spin-lock acquire? It should agree with P2.
3. `ln P4`, `u P4`: which function and which instruction.
4. Classify P1:
   - A small number like `0x10` or `0x28` → NULL plus a structure offset. A missing pointer check.
   - `!pool P1` says *Free* → use-after-free.
   - `!pool P1` says *Paged pool* → wrong pool type for code that runs at DISPATCH_LEVEL.
   - P3 = 8 and P1 is inside the driver's own code → a function in a pageable code section ran at high IRQL.
5. `lmv m <driver>`: record the version.

Microsoft's own warning, worth remembering: "In the majority of cases of this type of bug check, the issue is not the IRQL level, but rather the memory that is being accessed." The IRQL explains why the crash happened *now*. The address explains the bug.

**Pause and predict:** P1 = `0000000000000028`, P2 = 2, P3 = 0, and `k` shows a DPC. What happened?

<details><summary>Answer</summary>A DPC read a field at offset 0x28 of a structure through a NULL pointer, for example <code>context->Something</code> where <code>context</code> was NULL. The IRQL just turned the NULL read into this particular code. The fix is the missing pointer or lifetime check, not changing the IRQL.</details>

---

## 2. 0x133 DPC_WATCHDOG_VIOLATION 🟢

### Meaning

Windows sets time limits on running at DISPATCH_LEVEL and above, because while a processor is there, its scheduler can't run (005). The **DPC watchdog** measures that time in clock ticks and stops the machine when a limit is exceeded. Two different limits produce two different forms.

### Form 1: P1 = 0, a single DPC or ISR overran

| Param | Meaning |
|---|---|
| P1 | 0: "A single DPC or ISR exceeded its time allotment." |
| P2 | The DPC time count (ticks) |
| P3 | The DPC time allotment (ticks) |
| P4 | Address of `nt!DPC_WATCHDOG_GLOBAL_TRIAGE_BLOCK` (more detail) |

**Recipe:** the offending code is usually *on the stack*, because the watchdog fired while it was still running. Run `!analyze -v` (check `IMAGE_NAME`), then `k` and `u`. For more detail: `!pcr` (find the processor's PRCB), `dt nt!_KPRCB <prcb> Dpc*`, and `dt nt!DPC_WATCHDOG_GLOBAL_TRIAGE_BLOCK <P4>`.

**Typical cause:** a DPC that polls hardware in a loop ("wait until the status bit clears") and the bit never clears. Device stuck, wrong register, wrong bit, or the device was powered down. On new hardware, think *the hardware didn't respond the way the driver assumed*.

### Form 2: P1 = 1, too much time in total at DISPATCH_LEVEL or above

| Param | Meaning |
|---|---|
| P1 | 1: "The system cumulatively spent an extended period of time at IRQL DISPATCH_LEVEL or above." |
| P2 | The watchdog period |
| P3 | Address of `nt!DPC_WATCHDOG_GLOBAL_TRIAGE_BLOCK` |
| P4 | Reserved |

**Recipe:** the crashing stack may be **innocent**. It's simply whatever was running when the cumulative budget ran out. Steps:
1. `dt nt!DPC_WATCHDOG_GLOBAL_TRIAGE_BLOCK <P3>`.
2. `!dpcs` to see the DPC queues: is one driver's DPC re-queuing itself endlessly?
3. Look for long-held spin locks on the stacks of other processors.
4. Then use ETW (lecture 004): a WPR trace with DPC/ISR events, sorted by duration per module, shows who has been eating the time. Microsoft's own guidance for this form says the code "may not stop in the offending area" and suggests event tracing.

**Typical causes:**
- An interrupt storm. A level-triggered line that's never silenced runs the ISR → DPC chain endlessly.
- A DPC that keeps re-queuing itself.
- Many short DPCs that add up.
- A spin lock held across a long operation.

**Pause and predict:** a touch controller's interrupt is level-triggered, but its driver's ISR returns without masking the pin or making the device release the line. Which form of 0x133 do you expect?

<details><summary>Answer</summary>Usually the cumulative form (P1 = 1). Each ISR invocation is short, but they repeat back to back forever, so the processor never gets below DISPATCH_LEVEL long enough. An ETW trace would show one ISR with an enormous count.</details>

---

## 3. 0x9F DRIVER_POWER_STATE_FAILURE 🟢

### Meaning

A power transition, such as sleep, resume, a device turning off when idle, or shutdown, didn't complete. Windows runs power transitions with **power IRPs** sent down device stacks (007), and it sets a timer. If a driver never completes or passes on the IRP, the timer fires and the machine stops. This is the classic **sleep/resume** stop code, very common in platform bring-up and especially on laptops that rely on Modern Standby.

The crash is raised by a *watchdog timer*, so the crashing thread's stack is the watchdog's. **The evidence is in the parameters.**

### Parameters by P1 (the subtype)

| P1 | Meaning (Microsoft) | P2 | P3 | P4 |
|---|---|---|---|---|
| **0x3** (most common) | "A device object has been blocking an IRP for too long a time." | PDO of the stack | `nt!_TRIAGE_9F_POWER` | **The blocked IRP** |
| **0x4** | "The power state transition timed out waiting to synchronize with the PnP subsystem." | Timeout (seconds) | **Thread holding the PnP lock** | `nt!_TRIAGE_9F_PNP` |
| 0x1 | A device object being freed still has an outstanding power request | Device object | — | — |
| 0x2 / 0x500 | A driver completed the system power IRP but didn't call `PoStartNextPowerIrp` | (device objects) | | |
| 0x5 / 0x6 | Runtime power framework (directed power transitions) didn't complete | PDO / POP_FX_DEVICE | | |

### Recipe for P1 = 3

1. `!analyze -v`, then note P2 (PDO) and P4 (IRP).
2. `!irp P4`. The IRP's stack locations are listed; the one marked `>` is the **current** location, which tells you which driver holds the IRP right now. Note its minor function (for example `IRP_MN_SET_POWER`) and the target power state (for example D3 or D0).
3. `!devstack P2`: the drivers on that device. Which layer is the holder?
4. `dt nt!_TRIAGE_9F_POWER P3`: lists outstanding power IRPs and the power worker threads.
5. `!poaction`: the overall power operation (system going to sleep? resuming?).
6. For a KMDF driver: `!wdfkd.wdflogdump <driver>` shows the framework's recent log for that driver, often including "waiting for the driver to complete request X". `!wdfkd.wdfdevicequeues <WDFDEVICE>` shows the driver's pending requests.
7. Find what the holder is waiting for: `!stacks 2`, then look for that driver's threads, then `!thread` on them. Typical findings: a thread inside the driver waiting on a hardware event that never comes; a lock held by another thread; an I2C transfer to a device that's already powered off.

### Recipe for P1 = 4

1. `!thread P3`: the PnP-lock holder. What is it doing? Often it's stuck in another driver's start, stop or remove routine.
2. `dt nt!_TRIAGE_9F_PNP P4`: the dispatched-but-not-completed PnP IRPs.
3. Then the same `!irp`, `!devstack` and `!wdfkd` steps as P1 = 3.

**Pause and predict:** P1 = 3, and `!irp P4` shows the current stack location in `\Driver\hidi2c` for `IRP_MN_SET_POWER` to **D0** (power on), during resume. Name two plausible root causes, at different layers.

<details><summary>Answer</summary>(a) Driver layer: hidi2c is waiting for the device to answer a command after power-on, and the touch controller never responds. It may be held in reset, its power rail not yet up, or its firmware not ready. (b) Platform layer: the ACPI power method (or a GPIO the device depends on) didn't actually turn the device's power on, so the I2C transfer to it times out or hangs. Check with a logic analyzer on SCL/SDA and the reset line, and review the ACPI power methods.</details>

---

## 4. 0x50 PAGE_FAULT_IN_NONPAGED_AREA 🟢

### Meaning

"Invalid system memory has been referenced. Typically the memory address is wrong or the memory address is pointing at freed memory."

How it differs from 0xD1: 0xD1 is about a memory access that *might* be valid at a lower IRQL (pageable memory, touched too high). 0x50 is about an address that **can't be valid at any IRQL**: freed, never mapped, or garbage. The name says "nonpaged area" because the kernel expected the address to be resident and it wasn't.

### Parameters

| Param | Meaning |
|---|---|
| P1 | Memory address referenced |
| P2 | Operation. x64/x86 after Windows 10 1507: 0 = read, 2 = write, 10 = execute. Arm: 0 = read, 1 = write, 8 = execute. (Older x64: 0 = read, 1 = write.) |
| P3 | Address of the instruction (if known) |
| P4 | Fault subtype: 0x0 = PTE marked free; 0x2 = no valid page table entry; 0x4 = non-canonical (illegal) address; 0xF = kernel accessed a user address where that isn't allowed |

P2's encoding differs by architecture. That matters on Arm laptops, so always check which architecture the dump came from (`vertarget`).

### Recipe

1. `!analyze -v`; `dx KiBugCheckDriver` (the driver Windows blamed, if any).
2. `.trap` (to the trap frame `!analyze` prints), then `kb`: the stack at the fault.
3. `u P3`, `r`: the instruction, and the register holding the bad address.
4. Classify P1:
   - `!pte P1` and `!address P1`: is it unmapped, or a freed page?
   - `!pool P1`: is it inside a freed pool allocation? (use-after-free)
   - P4 = 0x4 (non-canonical): the pointer itself is garbage, often uninitialized or corrupted memory.
   - P4 = 0xF: kernel code dereferenced a **user-mode** pointer directly instead of using the safe access pattern (lecture 008: user addresses must be probed and copied).
5. If you suspect corruption, run Driver Verifier with Special Pool (004) so the crash moves to the moment of the bad access.

Microsoft also lists non-driver causes: faulty RAM and corrupted NTFS volumes. If 0x50s are random across unrelated drivers, suspect hardware (run memory diagnostics) before suspecting code.

---

## 5. 0x7E SYSTEM_THREAD_EXCEPTION_NOT_HANDLED 🟢

### Meaning

A **system thread**, a kernel-mode thread such as a driver's worker thread or a system worker thread, generated an exception that no handler caught.

### Parameters

| Param | Meaning |
|---|---|
| P1 | The exception code |
| P2 | The address where the exception occurred |
| P3 | Address of the exception record |
| P4 | Address of the context record |

Common P1 values:
- **0xC0000005 STATUS_ACCESS_VIOLATION**: a bad memory access, in a context where it became an exception rather than a 0x50 or 0xD1.
- **0x80000003 STATUS_BREAKPOINT**: "a breakpoint or ASSERT was encountered when no kernel debugger was attached." A debug build of a driver hit an assertion. That's useful: the assertion *message* names the broken assumption.

### Recipe

1. `!analyze -v`.
2. `.exr P3`: the exception record (code, address, parameters).
3. `.cxr P4`: switch to the CPU context at the exception. Then `k` shows the stack **at the fault**, not the exception-dispatch machinery.
4. `ln P2`, `u P2`, `r`: the function, the instruction, and the registers.
5. If the stack ends in `nt` and looks generic, use `!thread` and `dps`/`dqs` on the stack memory to find driver return addresses (Microsoft's suggestion when the result is "Probably caused by: ntkrnlmp.exe").

A close neighbor: **0x1E KMODE_EXCEPTION_NOT_HANDLED** is the same idea, but not tied to a system thread. Same recipe.

---

## 6. Telling them apart 🟢

| Question | Answer → code |
|---|---|
| Bad memory access, and the IRQL was ≥ DISPATCH_LEVEL? | **0xD1** (driver) / 0xA |
| Bad memory access to an address that can't be valid at all? | **0x50** |
| An exception thrown and not caught, in a kernel thread? | **0x7E** (0x1E outside system threads) |
| Too long at DISPATCH_LEVEL or above, from one routine or in total? | **0x133** P1 = 0 / P1 = 1 |
| A power IRP or power transition that never finished? | **0x9F** |

And where the evidence lives:

| Code | The guilty code is… | Look at… |
|---|---|---|
| 0xD1, 0x50, 0x7E | **On the crashing stack** (after the right context switch) | `k`, P-address, instruction |
| 0x133 P1 = 0 | Usually **on the stack** | `k`, triage block |
| 0x133 P1 = 1 | **Possibly not on the stack** | `!dpcs`, triage block, ETW |
| 0x9F | **Not on the stack** (a watchdog crashed) | The IRP (P4) or thread (P3) the parameters point to |

---

## 7. Neighbors worth recognizing 🔵

| Code | Name | One line |
|---|---|---|
| 0xC4 | DRIVER_VERIFIER_DETECTED_VIOLATION | Driver Verifier caught a rule break; P1 says which rule (lecture 004) |
| 0xC1 / 0xD6 | SPECIAL_POOL_DETECTED_MEMORY_CORRUPTION / DRIVER_PAGE_FAULT_BEYOND_END_OF_ALLOCATION | Special Pool caught a buffer overrun (004) |
| 0x3B | SYSTEM_SERVICE_EXCEPTION | An exception during a system call (kernel code called from user mode) |
| 0x161 | LIVE_SYSTEM_DUMP | Not a crash: the code stamped on a **live dump** (003) |
| 0xE2 | MANUALLY_INITIATED_CRASH | Someone forced a crash from the keyboard to capture a hang (003) |
| 0x117 | VIDEO_TDR_TIMEOUT_DETECTED | The display driver hung and was recovered; recorded as a live dump, not a blue screen |

---

## 8. Misconceptions

| You might think | Reality | Why it matters |
|---|---|---|
| The stop code tells you which driver is broken | It tells you which **rule** was broken and which part of Windows caught it | The driver comes from the parameters and the stack |
| Parameters mean the same thing for every code | Each code defines its own P1–P4, and some even vary by architecture (0x50's P2) | Always look them up |
| 0xD1 means "fix the IRQL" | Usually the address is the bug (NULL, freed, wrong pool type) | Fix the pointer or lifetime, not the level |
| The crashing stack always contains the culprit | Not for watchdog codes (0x133 cumulative, 0x9F) | Follow the IRP, thread or triage block |
| 0x9F is a "power bug in Windows" | It's usually a driver that didn't complete or pass on a power IRP, or hardware that didn't respond after a power change | Find the holder with `!irp` and `!devstack` |
| A blue screen is random hardware flakiness | Repeated identical buckets = a deterministic software bug; scattered unrelated buckets = suspect RAM or storage | Compare buckets across crashes |

---

## 9. Saying it precisely

- "0xD1 is a driver touching pageable or invalid memory at DISPATCH_LEVEL or above. P1 is the address, P2 the IRQL, P4 the instruction. Usually the address is the real bug."
- "0x133 has two forms: one overlong DPC or ISR, which is usually on the stack, or too much cumulative time at DISPATCH, where I'd use `!dpcs` and an ETW DPC/ISR trace because the stack may be innocent."
- "0x9F with P1 = 3 means a device held a power IRP too long. The crash is in the watchdog, so I go to the IRP in P4, find the holding driver with `!irp` and `!devstack`, then check whether it's waiting on hardware that didn't come back after power-on."
- "0x50 is an address that can't be valid at any IRQL: freed, unmapped or garbage. 0x7E is an uncaught exception in a system thread, where `.exr` and `.cxr` get me to the faulting context."

---

## 10. Self-check

1. Who calls `KeBugCheckEx` in a typical 0xD1, and why?
<details><summary>Answer</summary>Windows' page-fault handler. It was asked to resolve a fault at an IRQL where it can't wait (or for an invalid address), so it stops the machine.</details>

2. 0xD1: what are P1–P4?
<details><summary>Answer</summary>P1 address referenced, P2 IRQL, P3 read/write/execute (0/1/8), P4 the instruction's address.</details>

3. P1 = 0x28, P2 = 2, and the stack shows a DPC. Your diagnosis?
<details><summary>Answer</summary>A NULL pointer plus offset 0x28, dereferenced in a DPC. The bug is the missing pointer or lifetime check.</details>

4. Distinguish the two forms of 0x133 and where the evidence is for each.
<details><summary>Answer</summary>P1 = 0: a single DPC or ISR overran; usually on the stack. P1 = 1: cumulative time at ≥ DISPATCH; the stack may be innocent, so use the triage block, <code>!dpcs</code>, and ETW DPC/ISR durations.</details>

5. Why is an interrupt storm more likely to cause 0x133 P1 = 1 than P1 = 0?
<details><summary>Answer</summary>Each ISR run is short, but they repeat endlessly, so the total time at elevated IRQL accumulates past the cumulative limit.</details>

6. 0x9F with P1 = 3: what are P2 and P4, and what's your first command?
<details><summary>Answer</summary>P2 = the PDO of the stack, P4 = the blocked IRP. Run <code>!irp P4</code> to see which driver holds it (the <code>&gt;</code> line), then <code>!devstack P2</code>.</details>

7. Why isn't the 0x9F crashing stack the culprit?
<details><summary>Answer</summary>The crash is raised by a watchdog timer when the deadline passes. The guilty driver is wherever the IRP is stuck.</details>

8. How does 0x50 differ from 0xD1?
<details><summary>Answer</summary>0x50 is an address that's invalid at any IRQL (freed, unmapped, non-canonical). 0xD1 is pageable or invalid memory touched at an IRQL where paging is impossible.</details>

9. 0x50 with P4 = 0xF. What did the driver do wrong?
<details><summary>Answer</summary>Kernel code accessed a user-mode virtual address where that isn't allowed. It should have probed and copied the user buffer safely, or used a system buffer.</details>

10. 0x7E with P1 = 0x80000003. What happened, and what's useful about it?
<details><summary>Answer</summary>A breakpoint or assertion was hit with no debugger attached, typically an ASSERT in a debug build. The assertion names the broken assumption.</details>

11. Which two commands take you from a 0x7E's parameters to the faulting stack?
<details><summary>Answer</summary><code>.exr P3</code> (the exception record) and <code>.cxr P4</code> (switch to the context), then <code>k</code>.</details>

12. Ten crashes from ten different machines show ten unrelated buckets in unrelated drivers. What do you suspect?
<details><summary>Answer</summary>Hardware (RAM) or system-wide corruption, rather than one driver's logic bug. Run memory diagnostics, and consider Driver Verifier to catch a corrupter.</details>

---

## Sources

Checked 2026-10-21. Parameter tables and quoted descriptions come from Microsoft's bug check reference pages:

- Bug Check 0xD1: https://learn.microsoft.com/windows-hardware/drivers/debugger/bug-check-0xd1--driver-irql-not-less-or-equal
- Bug Check 0x133: https://learn.microsoft.com/windows-hardware/drivers/debugger/bug-check-0x133-dpc-watchdog-violation
- Bug Check 0x9F: https://learn.microsoft.com/windows-hardware/drivers/debugger/bug-check-0x9f--driver-power-state-failure
- Bug Check 0x50: https://learn.microsoft.com/windows-hardware/drivers/debugger/bug-check-0x50--page-fault-in-nonpaged-area
- Bug Check 0x7E: https://learn.microsoft.com/windows-hardware/drivers/debugger/bug-check-0x7e--system-thread-exception-not-handled
- Task Manager live dump page (0x161 LIVE_SYSTEM_DUMP): https://learn.microsoft.com/windows-hardware/drivers/debugger/task-manager-live-dump

The 0xD1 page's P3 table is garbled in its source. The values used here (0 read, 1 write, 8 execute) match its own example output and the debugger's conventions.
