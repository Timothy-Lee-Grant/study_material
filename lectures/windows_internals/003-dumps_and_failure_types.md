2026_10_21_22_20-(Dumps-And-Failure-Types)

# Lecture 003 — Dumps and Failure Types: Crash, Hang, or Dead Device, and What to Collect for Each

> **For:** Timothy · **Date:** 2026-10-21
> **Prerequisites:** 001 (WinDbg), 002 (bugchecks).
> **Why this lecture:** the most expensive mistake in platform debugging is collecting the wrong evidence. You reboot a hung machine and lose the state, or you get a minidump when the bug needed the whole kernel. This lecture covers the dump types, live dumps for systems that haven't crashed, and a decision procedure: **first classify the failure, then collect the evidence that type needs.**

---

## Core ideas (the answer key)

1. **A dump is a snapshot of memory plus processor state, written for later analysis.** The types differ in *how much memory* they include: small (minidump) < kernel < active < complete. Automatic is a kernel dump with flexible page-file sizing.
2. **Choose the smallest dump that contains the evidence.** A minidump has the stop code, the crashing thread's stack and the module list. It can't show other threads, IRPs, pool or devnodes. Driver and platform work usually needs at least a kernel dump.
3. **A crash dump is written through the page file at bugcheck time, and copied out on the next boot.** No suitable page file (or dedicated dump file) means no full dump.
4. **A live dump captures kernel state while the machine keeps running.** Use it for a device that's dead or a subsystem that's hung while the system still works. Make one from Task Manager (right-click **System** → *Create live kernel memory dump file*); it's stamped 0x161 LIVE_SYSTEM_DUMP. Windows also takes some live dumps itself (under `LiveKernelReports`).
5. **Three failure types need three different kits.** **Crash**: the machine bugchecked, so analyze the dump. **Hang**: the machine stopped responding without a bugcheck, so break in with a debugger or *force* a crash dump, and trace. **Dead device**: the machine is fine but one device stopped, so take a live dump, check PnP state and logs, trace the device, and probe the hardware.
6. **For a hang, never just reboot.** A reboot destroys the only evidence. Force a dump instead (keyboard CrashOnCtrlScroll → 0xE2, NMI → 0x80), or break in with an attached kernel debugger.
7. **Evidence for a hang is *who is waiting on what*:** all thread stacks (`!stacks`), locks (`!locks`), what each CPU runs (`!running`), DPC queues (`!dpcs`). A system hang is often one processor stuck at high IRQL, or a chain of waits ending at something that will never happen.

---

## Table of Contents

- [1. What a dump is, and how it gets written](#1-what-a-dump-is-and-how-it-gets-written)
- [2. The dump types](#2-the-dump-types)
- [3. Live dumps](#3-live-dumps)
- [4. Classify first: crash, hang, or dead device](#4-classify-first-crash-hang-or-dead-device)
- [5. Kit 1: crash](#5-kit-1-crash)
- [6. Kit 2: hang](#6-kit-2-hang)
- [7. Kit 3: dead device](#7-kit-3-dead-device)
- [8. Lab](#8-lab)
- [9. Misconceptions](#9-misconceptions)
- [10. Saying it precisely](#10-saying-it-precisely)
- [11. Self-check](#11-self-check)
- [Sources](#sources)

---

## 1. What a dump is, and how it gets written 🟢

A **dump** is a file containing:
- a header: the stop code and parameters, the Windows version, and the processor count;
- each processor's saved **context** (its registers, including its IRQL);
- some range of **physical memory pages**, together with enough page-table information that the debugger can translate virtual addresses back into those pages.

**How a crash dump gets written, step by step:**
1. `KeBugCheckEx` runs. The machine is in an unknown, possibly corrupt, state, so Windows can't trust the file system or most drivers.
2. Windows uses a small, pre-prepared **dump path**: the storage driver stack's special "crash dump" mode, set up in advance at boot.
3. It writes the selected memory directly into the space occupied by the **page file** on the boot volume (or a dedicated dump file), because that space was reserved and mapped beforehand.
4. On the next boot, Windows notices the dump data in the page file and copies it into `%SystemRoot%\MEMORY.DMP` (and for small dumps, `%SystemRoot%\Minidump\`).

Two consequences that matter in practice:
- If the page file is too small or not on the boot volume, the dump may be truncated or missing. *Automatic* dump mode exists to manage this for you.
- If the crash is **in the storage stack itself** (the disk or controller driver that the dump path needs), writing the dump can fail. A machine that reboots after a blue screen with no dump is a clue in itself.

---

## 2. The dump types 🟢

| Type | Contains | Can answer | Can't answer | Size |
|---|---|---|---|---|
| **Small (minidump)** | Stop code and parameters, the crashing thread's stack and context, the loaded module list, a little more | "What crashed, where, which driver version?" | Other threads, IRPs, pool contents, devnodes, the kernel's global state | Tiny (shown as 256 KB in current Settings) |
| **Kernel** | All memory in use by the kernel and drivers; no user-mode memory, no free pages | Nearly every driver question: all threads' kernel stacks, IRPs, pool, devnodes, power state | User-mode memory (e.g. what a user app had in its buffers) | Proportional to kernel memory use |
| **Automatic** | Same contents as Kernel | Same as Kernel | Same as Kernel | Same as Kernel; Windows manages page-file size to make room |
| **Active** | Like Complete, but leaves out pages unlikely to be useful (for example, free pages and memory that belongs to guest virtual machines) | Kernel and user-mode questions | Excluded pages | Smaller than Complete |
| **Complete** | All of physical memory | Everything, including user-mode memory of every process | Nothing that was in RAM | ≈ RAM size |

Configure the type in System Properties → Advanced → Startup and Recovery (stored in the registry under `HKLM\SYSTEM\CurrentControlSet\Control\CrashControl`).

**Choosing:**
- **Platform and driver work:** Kernel or Automatic as the default. Minidumps are fine for counting and bucketing crashes across a fleet, but too thin to root-cause a driver bug.
- **The bug involves a user-mode service talking to a driver:** Active or Complete, so you can see both sides.
- **Never** debug a hang from a minidump: the threads you need aren't in it.

One more note from Microsoft's documentation: "no kernel-mode dump file can provide as much information as debugging the crash directly with a kernel debugger." A dump is a single photo, while a live debugger can watch the next frame.

---

## 3. Live dumps 🟢

### 3.1 What and why

A **live dump** is a snapshot of kernel memory taken **while the system keeps running**. Use it when nothing has crashed, but something is wrong right now:
- a device has stopped responding while everything else works,
- a subsystem is hung (one driver's threads are stuck) but the desktop still responds,
- you need the state *before* you try a recovery step that would destroy it.

### 3.2 How to take one

**Task Manager** (run as administrator):
1. Go to the **Details** or **Processes** tab.
2. Right-click the **System** process and choose *Create live kernel memory dump file*.
3. Choose **Full live kernel memory dump** (active kernel memory, optionally with hypervisor and user pages) or **Kernel stacks memory dump** (smaller: processor states and all kernel thread stacks).
4. The file is saved under `%LocalAppData%\Microsoft\Windows\TaskManager\LiveKernelDumps`, and a dialog offers *Open file location*.

The dump carries stop code **0x161 LIVE_SYSTEM_DUMP**. That's a label, not a crash.

**Other ways (know they exist):**
- **Windows takes some itself.** For certain recoverable failures, Windows writes a live dump automatically to `%SystemRoot%\LiveKernelReports\`. The well-known example is the display driver timing out and being reset (0x117 VIDEO_TDR_TIMEOUT_DETECTED). If a machine "glitched but recovered", look in that folder.
- **Sysinternals LiveKD** can write a dump of the live kernel (⚫ for now).

### 3.3 Limits 🔵

- **Consistency:** Microsoft describes it as "a consistent snapshot of kernel memory". Windows briefly pauses the system to copy memory, then writes the copy.
- **It needs free memory:** the capture "temporarily requires enough available free physical memory to hold a copy". By default it aborts under memory pressure, and it can succeed but be incomplete.
- **Kernel stacks only** is often enough for hangs, and much smaller.

**Pause and predict:** the touchscreen is dead, everything else works, and the user is about to disable and re-enable the device in Device Manager. What should you capture *first*, and why?

<details><summary>Answer</summary>A live kernel dump (Full), before the disable/enable. Re-enabling tears down and rebuilds the device stack, destroying the stuck state: the pending IRPs, the driver's internal state, and the thread waits. Also note the device's status in Device Manager, start a WPR trace, and only then try the recovery.</details>

---

## 4. Classify first: crash, hang, or dead device 🟢

| Type | What the user sees | System state | Is there a bugcheck? |
|---|---|---|---|
| **Crash** | Blue screen, reboot | Stopped on purpose | Yes: the stop code is your first clue |
| **System hang** | Frozen screen; keyboard and mouse dead; maybe the clock stops; no blue screen | One or more processors stuck (often at high IRQL), or everything waiting on something that never comes | No, unless you force one |
| **Partial hang** | Some apps freeze; others work; operations involving one subsystem never finish | Some threads stuck waiting | No |
| **Dead device** | One device stops (touch, Wi-Fi, camera); the rest is fine | The device's stack is stuck, failed, or removed, or the hardware itself is wedged | No |

Two questions sort most cases:
1. **Does anything still respond?** Moving mouse, network ping, a clock updating.
   - Nothing → system hang.
   - Something → partial hang or dead device.
2. **Does disabling and re-enabling the device (soft reset) bring it back, or only a power cycle?** (Ask after capturing evidence; see §3.)
   - Soft reset helps → the stuck state lives in the driver stack.
   - Only a power cycle helps → it lives in the hardware, the bus, or the power rails.

---

## 5. Kit 1: crash 🟢

| Collect | Why |
|---|---|
| `MEMORY.DMP` (kernel or automatic dump, or larger) | The full kernel state at the crash |
| Any minidumps from earlier crashes (`%SystemRoot%\Minidump\`) | Compare buckets: same bug, or different? |
| Event Viewer → System log around the crash time | Warnings that came before the crash (timeouts, PnP errors) |
| Driver and firmware versions (`lmv m` in the dump; `pnputil /enum-drivers`) | Version mismatches are common root causes |
| Reproduction notes: what was happening (resume? idle? heavy use?) | Ties the stop code to a scenario |

**Analysis:** lectures 001 and 002, i.e. the five-step method.

**If it reproduces:** enable Driver Verifier on the suspect driver (004) and reproduce again, so the crash moves to the moment of the real violation.

---

## 6. Kit 2: hang 🟢

### 6.1 The first rule

**Don't reboot.** A hang's evidence exists only in memory. Get it out first, by one of three routes:

| Route | Needs | How |
|---|---|---|
| **A. Attached kernel debugger** | The machine was booted with kernel debugging and WinDbg is connected | Break in (Ctrl+Break in WinDbg) → full live access |
| **B. Forced crash dump from the keyboard** | Registry value `CrashOnCtrlScroll = 1` set **before** the hang, under the keyboard driver's `Parameters` key (`kbdhid` for USB/HID keyboards, `i8042prt` for PS/2) | Hold **right Ctrl**, press **Scroll Lock** twice → bugcheck **0xE2 MANUALLY_INITIATED_CRASH** → dump. (Laptops without Scroll Lock: the trigger keys can be remapped in the same registry key.) |
| **C. Forced crash dump by NMI** | Hardware or hypervisor that can send a non-maskable interrupt, plus crash-on-NMI enabled | An NMI is delivered even when a processor is stuck at high IRQL → bugcheck **0x80** → dump. Lab VMs can usually inject one |

Why route B can fail and C still works: the keyboard path needs the keyboard's interrupt and driver to run. If a processor is stuck at very high IRQL, or the keyboard's interrupts are blocked, the key combination never gets processed. An NMI can't be masked by IRQL.

Plan this **before** the test run: set `CrashOnCtrlScroll` and a Kernel or Automatic dump type on every test machine as standard practice.

### 6.2 What to look at in a hang dump

| Command | Question |
|---|---|
| `!running` (live) or `!pcr` / `k` per processor (`~0s`, `~1s`, …) | What was each processor executing? Is one stuck in a loop at DISPATCH_LEVEL or above? |
| `!irql <n>` per processor | Which processors were at elevated IRQL? |
| `!dpcs` | Are DPC queues backed up? |
| `!stacks 2` | Every thread's kernel stack, summarized: find the many threads waiting in the same place |
| `!locks` | Which executive resources are held, and who is waiting for them? |
| `!thread <addr>` → its wait objects → `!irp` | Follow the wait chain to the thing that will never happen |
| `!poaction` | Is a power transition in progress (hang during sleep or resume)? |

### 6.3 The two shapes of a system hang

1. **Spinning:** a processor is stuck at DISPATCH_LEVEL or above, looping. That usually means a spin lock that's never released or a hardware-polling loop. With several processors, others pile up behind the same lock. Usually the DPC watchdog turns this into 0x133 eventually. If it doesn't (very high IRQL, or watchdogs disabled), you see a silent freeze. Evidence: `!running`, per-processor stacks, `!irql`.
2. **Waiting (deadlock):** every processor is idle or doing little, but the threads that matter are all waiting. A waits on a lock B holds; B waits on an IRP that driver C never completes. Evidence: `!stacks`, `!locks`, `!thread` chains, `!irp`.

### 6.4 If it's only partially hung

The machine responds, so use the dead-device kit (§7) for the stuck subsystem. Add a **user-mode dump** of any frozen application (Task Manager → right-click process → *Create dump file*): its stack shows which call into the system it's stuck in, often a `DeviceIoControl` or `ReadFile` that a driver never completes.

### 6.5 Tracing a hang that you can reproduce

Start a WPR trace (004) before reproducing; memory (circular) mode keeps only the last minutes. When the hang starts, stop and save the trace, if the machine still lets you. The CPU, DPC/ISR and Generic Events graphs show what led up to it.

---

## 7. Kit 3: dead device 🟢

The system is healthy, but one device has stopped. This is the touchscreen-dies-until-reset scenario. Collect in this order, **least destructive first**:

| Step | Collect | Tool | Question it answers |
|---|---|---|---|
| 1 | Device status and problem code | Device Manager (device → Properties → General / Events tab), `pnputil /enum-devices /problem` | Does Windows think the device failed (a Code 10, Code 43…), or that it's fine? |
| 2 | Live kernel dump (Full) | Task Manager, §3 | The stuck state: pending IRPs, the driver's internal state, waits |
| 3 | The driver's own log | In the dump: `!wdfkd.wdflogdump <driver>` (KMDF in-flight recorder) | What the framework saw the driver do last |
| 4 | System event log | Event Viewer → System; Applications and Services → Microsoft → Windows → Kernel-PnP | PnP and driver errors, timeouts, resets |
| 5 | A trace of an attempt to use the device | WPR with a profile that includes the driver's and the bus's providers (004) | Do interrupts still arrive? Do I2C transfers complete or time out? |
| 6 | Hardware truth | Logic analyzer / oscilloscope on the interrupt line and the bus (SCL/SDA), the reset line, and the power rail | Is the line stuck asserted? Is the bus held low? Is the device powered at all? |
| 7 | Only now: recovery experiments | Disable/enable in Device Manager → if that fails, sleep/resume → if that fails, a cold power cycle | Which recovery works tells you which layer holds the stuck state |

### 7.1 Reading the dump for a dead device

1. `!devnode 0 1 <service>`: is the device node *started*, or failed / removed, and with which problem code?
2. `!devstack <PDO>`: which drivers are on it?
3. `!wdfkd.wdfdevicequeues <WDFDEVICE>`: requests stuck in the driver's queues?
4. `!irp` on any pending request: which layer holds it?
5. `!stacks 2`, then find the driver's threads: waiting on what?
6. For an interrupt-driven device: is the interrupt still connected? (KMDF extensions can display interrupt objects; ⚫ for now.) Combine this with ETW interrupt counts and the logic analyzer.

### 7.2 Mapping evidence to layers

| Evidence | Points to |
|---|---|
| Device shows a problem code | PnP / driver start failed → driver or firmware (ACPI) issue |
| Device "working properly", no pending requests, no interrupts arriving, line idle | The device stopped asserting → touch controller firmware / power |
| Device "working properly", line **stuck asserted**, no interrupts counted | A missed edge, or an edge/level mismatch → ACPI description or GPIO configuration |
| SDA held low, all transfers time out | Hung I2C bus |
| Requests pending in the driver, the driver's thread waiting forever | Driver state machine bug |
| Only after resume, or after idle | Power transition (lecture 007) |

---

## 8. Lab

On a Windows VM:

1. **Dump settings:** set *Kernel memory dump*. Check the page file is on `C:`.
2. **Crash:** NotMyFault → *High IRQL fault (Kernel-mode)*. Open `MEMORY.DMP` and note the code and bucket. Then find the matching minidump in `C:\Windows\Minidump\` and compare: run `!stacks 2` in each. What's missing from the minidump?
3. **Live dump:** Task Manager → right-click **System** → *Create live kernel memory dump file* → *Kernel stacks memory dump*. Open it: confirm the code is 0x161, then run `!stacks 2` and `!devnode 0 1`. Nothing crashed, yet you can see all the state.
4. **Forced crash:** set `CrashOnCtrlScroll` (DWORD, value 1) under `HKLM\SYSTEM\CurrentControlSet\Services\kbdhid\Parameters` and reboot. Hold right Ctrl, press Scroll Lock twice. Confirm stop code 0xE2.
5. **Hang (spinning):** NotMyFault's *Hang* options include a DPC-based hang. Predict what happens on your VM (silent freeze, or a 0x133?), then run it and check. If it freezes silently, use step 4's keys to capture it, then find the stuck processor's stack.

---

## 9. Misconceptions

| You might think | Reality | Why it matters |
|---|---|---|
| A minidump is enough for driver bugs | It has only the crashing thread; hangs, IRPs and devnodes are invisible | Default to kernel or automatic dumps on test machines |
| A hang leaves no evidence, so just reboot | All the evidence is in memory; a reboot destroys it | Force a dump or break in first |
| A live dump crashes the machine | It's a snapshot; the system keeps running (0x161 is a label) | Safe to use on a dead-device report |
| "Dead device" = broken hardware | Often the driver stack is stuck while the hardware is fine, or the reverse; the recovery that works tells you which | Capture first, then test recoveries in order |
| Ctrl+Scroll Lock always works | It needs the registry setting beforehand, and a functioning keyboard interrupt path | Have NMI as a backup |
| Windows writes the dump to `MEMORY.DMP` during the crash | It writes into the page-file space, then copies to `MEMORY.DMP` on the next boot | Page-file configuration determines whether you get a dump |

---

## 10. Saying it precisely

- "First I classify: crash, system hang, partial hang, or dead device. Each needs different evidence."
- "For crashes I want a kernel or automatic dump; minidumps only show the crashing thread."
- "For a hang I never reboot. I break in with an attached debugger, or force a dump with Ctrl+Scroll Lock or an NMI, then look at what each processor runs and follow the thread wait chains."
- "For a dead device I capture a live kernel dump *before* disabling and re-enabling it, check the devnode's state and the driver's in-flight log, trace an attempt to use it, and put a logic analyzer on the lines. Then I try recoveries in order, from soft reset to power cycle, because which one works tells me which layer holds the stuck state."

---

## 11. Self-check

1. Order the dump types by size, and say what a kernel dump has that a minidump lacks.
<details><summary>Answer</summary>Small &lt; kernel (= automatic) &lt; active &lt; complete. A kernel dump has all kernel memory: every thread's kernel stack, IRPs, pool, devnodes, power state.</details>

2. Where is a crash dump physically written at bugcheck time, and why there?
<details><summary>Answer</summary>Into the page file's space on the boot volume (or a dedicated dump file), through a pre-prepared dump path, because the file system can't be trusted mid-crash. It's copied to MEMORY.DMP on the next boot.</details>

3. Why is "machine rebooted after a blue screen, but there's no dump" itself a clue?
<details><summary>Answer</summary>The dump path may have failed: the crash may be in the storage stack itself, or the page file was missing or too small.</details>

4. How do you make a live kernel dump with Task Manager, and what stop code does it carry?
<details><summary>Answer</summary>Run Task Manager as admin, right-click the System process, choose <i>Create live kernel memory dump file</i>, then Full or Kernel stacks. It carries 0x161 LIVE_SYSTEM_DUMP.</details>

5. Where does Windows put the live dumps it takes on its own, and give one event that produces one.
<details><summary>Answer</summary><code>%SystemRoot%\LiveKernelReports</code>. For example, a display driver timeout with recovery (0x117 VIDEO_TDR_TIMEOUT_DETECTED).</details>

6. Name the three routes to evidence from a system hang, and why an NMI can work when the keyboard route doesn't.
<details><summary>Answer</summary>An attached kernel debugger (break in), a keyboard-forced crash (CrashOnCtrlScroll → 0xE2), or an NMI → 0x80. An NMI can't be masked by IRQL; the keyboard route needs the keyboard's interrupt and driver to run.</details>

7. Describe the two shapes of a system hang and the evidence for each.
<details><summary>Answer</summary>Spinning: a processor stuck at elevated IRQL (<code>!running</code>, per-CPU stacks, <code>!irql</code>). Waiting/deadlock: threads waiting in a chain on something that never completes (<code>!stacks</code>, <code>!locks</code>, <code>!thread</code> → <code>!irp</code>).</details>

8. For a dead touchscreen, why take the live dump before disabling and re-enabling the device?
<details><summary>Answer</summary>Disable/enable rebuilds the device stack and destroys the stuck state (pending IRPs, driver state, waits).</details>

9. The device shows "working properly", the interrupt line is stuck asserted, and ETW shows no new interrupts. Which layer do you suspect?
<details><summary>Answer</summary>Interrupt configuration: a missed edge or an edge/level mismatch in the ACPI GpioInt description or the GPIO setup. The device is waiting to be read and the host isn't seeing a request.</details>

10. What does it tell you if disable/enable doesn't fix the device but a cold power cycle does?
<details><summary>Answer</summary>The stuck state is in hardware, the bus, or power (the device controller, a held bus, a power rail), not only in the driver stack.</details>

---

## Sources

Checked 2026-10-21.

- Microsoft Learn: Varieties of kernel-mode dump files (complete, active, kernel, small, automatic; "no kernel-mode dump file can provide as much information as debugging the crash directly"). https://learn.microsoft.com/windows-hardware/drivers/debugger/varieties-of-kernel-mode-dump-files
- Microsoft Learn: Task Manager live dump (steps, Full vs Kernel stacks, save location, memory-pressure behavior, 0x161). https://learn.microsoft.com/windows-hardware/drivers/debugger/task-manager-live-dump
- Microsoft Learn: Kernel live dump code reference. https://learn.microsoft.com/windows-hardware/drivers/debugger/kernel-live-dump-code-reference
- Microsoft Learn: Forcing a system crash from the keyboard (CrashOnCtrlScroll, 0xE2) and Bug Check 0x80 (NMI). Reference pages in the debugger documentation.
- Microsoft Learn: Bug Check 0x133 (event tracing when "the code may not stop in the offending area").

To verify on your Windows build: the exact Settings label for the small dump (it has varied between 64 KB and 256 KB across versions), and the registry path for your keyboard type before relying on CrashOnCtrlScroll.
