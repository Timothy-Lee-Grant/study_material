2026_11_07_12_00-(Phase-5-Concepts-What-The-Analyses-Are-Doing)

# 018 — Phase 5, Conceptually: What We're Doing, How the Pieces Interact, and What Each Analysis Looks For

> **For:** Timothy · **Date:** 2026-11-07
> **Pairs with:** `../labs/013-phase5_guide_inspect_crash_analyze.md` (the *steps*). This lecture is the *why*: it explains the ideas behind every Phase 5 lab, so the commands stop being recipes. It's self-contained; you don't need to reread 001–004 first, though it points to them.
> **Why this lecture:** you've got the driver loaded and WinDbg attached to the live kernel on ARM64 (`lkd>`, `lm m TgCounter` showed your driver at `fffff800`66080000`). Next come `!drvobj`, a live dump, a deliberate crash, Driver Verifier and a WPR trace. You asked for the conceptual picture: what is actually going on, how everything interacts, how these analyses work, and what we're looking for. The short answer: **the kernel is a program whose state lives in memory; every Phase 5 lab is a different way of getting at that state (now, frozen, at the moment of death, under stress, or as a timeline) and reading it with a map (symbols).** The rest of the lecture unpacks that sentence.
> **Format notes:** no new commands to learn; the commands are in 013. Where something you saw in your own session illustrates a concept (the `PEB is paged out` message, threads waiting in `KiSwapContext`, a kernel base that changes every boot), it's used as the example. No firmware analogies.

---

## Core ideas (the answer key)

1. **The kernel is software, and its whole state is bytes in memory:** the list of loaded drivers, your driver object, your device object, your counter, every thread's stack. Debugging the kernel means **reading those bytes** and interpreting them.
2. **Symbols (PDB files) are the map** from raw addresses and bytes to names and types. Without symbols, memory is anonymous numbers; with them, `0xfffff800...` becomes `TgCounter!g_PagedValue`, and a block of bytes becomes a `_TG_EXTENSION` with a field `Counter`.
3. **Most of what you look for is found by following pointers from a known name:** `\Driver\TgCounter` (a name in the object manager) → the driver object → its device object → its device extension → `Counter`. Every `!` command is a pre-written pointer walk.
4. **Phase 5 has three ways to get the state:** *live* (local kernel debugging: read the running kernel, read-only), *frozen while running* (a live dump: a copy, the machine keeps going), and *frozen at death* (a crash dump: the kernel copies memory out as it stops itself). Same data, different moments.
5. **A bugcheck is the kernel deliberately stopping** because it detected that a rule was broken and continuing could corrupt data. The **stop code names the rule**; the **parameters are the evidence**; the **stack is the story of how execution got there**.
6. **The rule that fires isn't always the bug.** In 5.3 the bug is a NULL write; the rule that catches it is "no page faults at DISPATCH_LEVEL or above", so the stop code is 0xD1. Analysis means going from *rule* to *evidence* to *location* to *cause*.
7. **Some bugs are latent:** wrong, but they only fail when an unlikely condition happens (a page that's usually in RAM isn't). **Driver Verifier makes the unlikely condition happen every time**, turning a probabilistic bug into a deterministic one.
8. **Dumps and the debugger show one instant; tracing shows a timeline.** ETW providers write timestamped events into buffers; WPR chooses which providers to record; WPA draws them. Use snapshots for "what is the state?" and traces for "what happened, in what order, and how long did it take?"
9. **Every analysis follows the same loop:** a question → a prediction → collect evidence → compare → a one-sentence conclusion that names the rule, the location, the cause and the proof.

---

## Table of Contents

- [0. The whole picture on one page](#0-the-whole-picture-on-one-page)
- [1. What's running, and how the pieces connect](#1-whats-running-and-how-the-pieces-connect)
- [2. Memory, addresses, symbols: how the debugger "sees" anything](#2-memory-addresses-symbols-how-the-debugger-sees-anything)
- [3. Following pointers: what the 5.1 exercises are looking for](#3-following-pointers-what-the-51-exercises-are-looking-for)
- [4. Three moments: live, live dump, crash dump](#4-three-moments-live-live-dump-crash-dump)
- [5. What a bugcheck is, and how to read one](#5-what-a-bugcheck-is-and-how-to-read-one)
- [6. Latent bugs and Driver Verifier](#6-latent-bugs-and-driver-verifier)
- [7. Snapshots vs timelines: what tracing adds](#7-snapshots-vs-timelines-what-tracing-adds)
- [8. The analysis loop, and what counts as proof](#8-the-analysis-loop-and-what-counts-as-proof)
- [9. Why this is the real job](#9-why-this-is-the-real-job)
- [Misconceptions](#misconceptions)
- [Self-check questions](#self-check-questions)
- [Sources](#sources)

---

## 0. The whole picture on one page

```
                         ┌───────────────────────── your Mac ─────────────────────────┐
                         │  VMware Fusion: a virtual machine (CPU, RAM, disk, devices)  │
                         │ ┌───────────────────── Windows 11 Arm VM ──────────────────┐ │
                         │ │ user mode                                                │ │
                         │ │   tgclient.exe ── DeviceIoControl ──┐     WinDbg (lkd>)   │ │
                         │ │                                     │       │  reads      │ │
                         │ │ ─────────────── system call ────────┼───────┼──────────── │ │
                         │ │ kernel mode                         ▼       ▼             │ │
                         │ │   I/O manager ── IRP ──► TgCounter.sys   kernel memory:    │ │
                         │ │   object manager (names)   │             driver object,    │ │
                         │ │   memory manager (pages)   └─ Counter ──► device object,   │ │
                         │ │   scheduler, ETW, Verifier               device ext, pool │ │
                         │ │                                                          │ │
                         │ │   at a crash:  kernel ──► page file ──► MEMORY.DMP        │ │
                         │ │   at a trace:  ETW buffers ──► WPR ──► .etl ──► WPA       │ │
                         │ └──────────────────────────────────────────────────────────┘ │
                         └──────────────────────────────────────────────────────────────┘
```

| Lab | The question | How you get the state | What you're looking for |
|---|---|---|---|
| 5.1 | What does my driver look like *inside* the kernel? | read live kernel memory | the chain from `\Driver\TgCounter` to `Counter` |
| 5.2 | Can I capture that without stopping anything? | a live dump (copy) | the same chain, frozen; stop code 0x161 = "this is a label, not a crash" |
| 5.3 | Why did the machine die? | a crash dump | rule (0xD1) → evidence (P1–P4) → location (stack) → cause (NULL store) |
| 5.4 | Why did code that "worked" die under Verifier? | crash dump with Verifier on | the paged-pool address, and proof the page wasn't in RAM (`!pte`) |
| 5.5 | What happened over time when the client ran? | an ETW trace | the client's short life; which drivers do interrupt work |

---

## 1. What's running, and how the pieces connect

**The VM.** Fusion gives Windows a virtual computer: CPUs, RAM, a disk file, virtual devices. Windows can't tell it's virtual, which is why everything below works exactly as on a laptop. (Snapshots are Fusion copying that virtual disk, so a crashed VM can always go back.)

**The kernel is not one blob.** `ntoskrnl.exe` contains several managers, and Phase 5 touches most of them:

| Component | Its job | Where Phase 5 meets it |
|---|---|---|
| **Object manager** | names and tracks kernel objects (`\Driver\TgCounter`, `\Device\TgCounter`, `\GLOBAL??\TgCounter`) | `!object`, the first link in every pointer chain |
| **I/O manager** | turns `DeviceIoControl` into an IRP and calls the driver's dispatch function | `!drvobj` (the dispatch table), the stack in 5.3 |
| **Memory manager** | page tables, paged vs nonpaged pool, page faults | `!pool`, `!pte`, the whole of 5.4 |
| **Scheduler** | which thread runs; IRQL rules | threads waiting in `KiSwapContext`; 0xD1 |
| **Bugcheck / crash dump code** | stops the system safely, writes the dump | 5.3, 5.4 |
| **ETW** | the kernel's event-logging system | 5.5 |
| **Driver Verifier** | a checking layer around a chosen driver's calls into the kernel | 5.4 |

**Your driver is a guest in the kernel's address space.** `TgCounter.sys` was loaded into kernel memory (`lm` showed 32 KB at `fffff800`66080000`). It isn't a process: it has no threads of its own. Its code runs only when the kernel calls it (`DriverEntry` at load, the dispatch routine when an IRP arrives) on whatever thread made the call; here, `tgclient.exe`'s thread, which entered kernel mode through a system call.

**One `tgclient.exe` increment, end to end:**
1. `tgclient` opens `\\.\TgCounter` → the object manager follows the symbolic link `\GLOBAL??\TgCounter` → `\Device\TgCounter`.
2. `DeviceIoControl(INCREMENT)` → system call → the I/O manager builds an **IRP** describing the request.
3. The I/O manager looks in the driver object's **dispatch table** at `IRP_MJ_DEVICE_CONTROL` and calls `TgCounter!TgDispatchDeviceControl`.
4. The dispatch function takes its spin lock, increments `Counter` in the **device extension**, completes the IRP.
5. The system call returns; `tgclient` prints the value.

Every Phase 5 lab is a way of observing some part of that path: its data structures (5.1, 5.2), its failure (5.3, 5.4), or its timing (5.5).

---

## 2. Memory, addresses, symbols: how the debugger "sees" anything

**Everything is bytes at addresses.** A driver object is a structure in kernel memory; your counter is 4 bytes inside another structure. The debugger's basic operation is "read N bytes at address A". Every fancier command is built on that.

**Those addresses are virtual.** Paging is on for the whole time Windows runs, so every address the CPU (and the debugger) uses is translated by the page tables into a physical location. Kernel addresses on 64-bit Windows are the very high ones (`fffff800...`); user addresses are low (`00000008...`). To read memory, the debugger does the same translation the CPU does. That's why a debugger can see a page only if it's **present in RAM**:

> In your session, `.reload` printed **`PEB is paged out (Peb.Ldr = 00000008`41970018)`**. The PEB (process environment block) is a user-mode structure of whatever process the debugger considered current. Its page wasn't in RAM at that moment (it had been written to the page file), so the debugger couldn't read it. Harmless for you, and a perfect preview of 5.4: **"paged out" means the translation says "not present", and anything that touches it takes a page fault.** For a debugger that's an unreadable address; for kernel code at DISPATCH_LEVEL it's a bugcheck.

**Addresses change every boot.** Your kernel base was `fffff800`67600000` that boot; next boot it will be different. That's **KASLR** (kernel address space layout randomization), which makes attacks harder. It's why you never hard-code a kernel address in notes: you use **names**, and symbols turn names into this boot's addresses.

**Symbols are the map.** A **PDB file** (program database) is produced when code is compiled. It records:
- **names → offsets**: `TgDispatchDeviceControl` is at offset X in `TgCounter.sys`;
- **types**: `_TG_EXTENSION` is a structure with field `Counter` at offset Y, size 4;
- **source lines**: instruction at offset Z came from `tgcounter.c` line N.

The debugger combines "where is the module loaded this boot" (`lm`) with "where is the name inside the module" (the PDB) to get a real address. That's what `.reload` sets up and what `(private pdb symbols)` in your `lm` output confirmed: WinDbg found **your** PDB, with your types and local variables. Microsoft's own components come from the **symbol server** (`.symfix` points at it); those are **public** symbols: function names, but not every type and local.

**Types turn bytes into meaning.** `dd addr` shows raw 32-bit values. `dt TgCounter!_TG_EXTENSION addr` shows the same bytes **interpreted** as your structure, field by field. Same memory, different lens. Most of kernel debugging is choosing the right lens for an address.

---

## 3. Following pointers: what the 5.1 exercises are looking for

The 5.1 exercises are one walk through memory, from a name everyone knows to the 4 bytes you care about:

```
"\Driver\TgCounter"  (a name)
      │  object manager lookup                        !drvobj \Driver\TgCounter 2
      ▼
DRIVER_OBJECT ──── MajorFunction[28] (dispatch table) ──► TgCounter!TgDispatchDeviceControl, nt!IopInvalidDeviceRequest...
      │  DeviceObject field
      ▼
DEVICE_OBJECT  (\Device\TgCounter)                     !devobj \Device\TgCounter
      │  DeviceExtension field  ("DevExt")
      ▼
_TG_EXTENSION { Counter = 3 }                          dt TgCounter!_TG_EXTENSION <DevExt>
```

And separately:
```
TgCounter!g_PagedValue (a global, found by symbol)  →  a pointer  →  paged pool block { 42 }
                                                     dd poi(TgCounter!g_PagedValue)   !pool ...
```

**What each step proves:**
- **The dispatch table** is "the I/O manager calls the driver", made physical. It's an array of function pointers that `DriverEntry` filled in. The entries you didn't fill point to `nt!IopInvalidDeviceRequest` (the kernel's "not supported" function). So when you ask "how does Windows know which function handles my IOCTL?", the answer is a pointer in this array, and you can read it.
- **The device object** is what user mode actually opens. The driver object is the code's identity; the device object is the thing requests are sent to. One driver can have many device objects.
- **The device extension** is per-device memory the driver asked for when it created the device: the place a driver keeps its state. `Counter` lives here.
- **Watching the counter change** (run `tgclient` again and repeat `dt`) shows the full loop: a user program changed kernel memory through the I/O path, and you read the effect from outside.
- **`!pool`** asks the memory manager's bookkeeping: which pool (paged or nonpaged) this block came from, its size, and its **tag** (`TgTg`, your 4-character label from `ExAllocatePool2`). That's the setup for 5.4: you're confirming the value lives in **paged** pool.

**What the `!` commands are.** Commands starting with `!` are **debugger extensions**: small programs that know the layout of kernel structures and do the pointer walk for you. `!drvobj` reads a `DRIVER_OBJECT` and follows its fields; `!pool` reads the pool allocator's headers. When you understand the chain above, you could do every one of them by hand with `dt` and addresses. That's the test of whether you understand what they show.

**What `lkd>` can't do.** Local kernel debugging reads the kernel of the **same machine the debugger runs on**. It can't stop the kernel (the debugger itself needs that kernel to run), so no breakpoints, no stepping, and the data can change while you read it. It works through a helper driver that WinDbg loads to read kernel memory, which is why Windows requires `bcdedit /debug on` first. The full version, **remote kernel debugging**, uses a second machine: the target is frozen, the host runs WinDbg, and you can set breakpoints in kernel code. Lecture 001 and 010's optional section cover it.

**The threads you saw** in the Threads pane, waiting in `nt!KiSwapContext+0x20`, are threads that called into the scheduler to wait and were switched out. `KiSwapContext` is the context-switch routine; a waiting thread's saved stack ends there because that's exactly where it stopped running. Almost every thread on the system looks like that at any moment.

---

## 4. Three moments: live, live dump, crash dump

All three give you the same kind of thing (kernel memory + symbols) at different moments, with different trade-offs.

| | Live (`lkd>`, 5.1) | Live dump (5.2) | Crash dump (5.3, 5.4) |
|---|---|---|---|
| When | now, continuously changing | one instant, while running | the instant the kernel stopped itself |
| Machine keeps running? | yes | yes | no (bugcheck, reboot) |
| Consistent? | no: values can change between reads | yes, close to one instant | yes |
| Includes CPU registers of the failure? | no | no failure | **yes**: the context of the crashing CPU |
| Stop code | none | **0x161 LIVE_SYSTEM_DUMP** (a label) | the rule that fired (0xD1, 0xC4...) |
| Use it for | exploring | hangs, stuck devices, "capture it without rebooting a server" | crashes |

**What's inside a dump file.** A dump is: a header (stop code, parameters, OS version), the **CPU context** (registers) of each processor at the moment, the **loaded module list** (which drivers were where), and **pages of memory**. A *kernel* dump has kernel-mode pages only; a *complete* dump has all RAM; a *minidump* has just the essentials (stack, modules, a little memory). WinDbg opens a dump and pretends it's a stopped machine: the same commands work.

**How a crash dump gets written, conceptually.** When the kernel bugchecks, it can't trust anything: the file system or the storage driver might be the thing that's broken. So it doesn't "save a file". It uses a separate, minimal **crash-dump path** to the disk, prepared in advance at boot, and writes memory into the **page file** (a disk area it already knows the location of). On the next boot, Windows notices the dump in the page file and copies it out to `C:\Windows\MEMORY.DMP`. That's why the guide says to wait a minute after rebooting, and why a page file that's too small means no dump.

**Why a live dump says 0x161.** A dump file format always carries a stop code. A live dump isn't a crash, so it carries a code that means "this was taken on purpose while running". Seeing 0x161 tells you how to read everything else in the file: nothing is broken; it's a photograph.

---

## 5. What a bugcheck is, and how to read one

**Why the kernel stops itself.** The kernel constantly relies on rules (invariants): "code at DISPATCH_LEVEL never takes a page fault", "a pool block is never freed twice", "a spin lock is released at the IRQL it was acquired at". When the kernel **detects** a broken rule, it can't know how much else is damaged. Continuing might write garbage to your disk. So it stops everything, on purpose, and records the evidence. A blue screen is a **safety mechanism**, not a random failure.

**The parts of a bugcheck, and what each is for:**

| Part | Meaning | 5.3's expected values |
|---|---|---|
| **Stop code** | which rule was broken | `0xD1` DRIVER_IRQL_NOT_LESS_OR_EQUAL: "a driver touched memory it couldn't, at an IRQL where page faults aren't allowed" |
| **P1–P4** | evidence; each stop code defines its own four | P1 = the address touched (`0`), P2 = the IRQL (`2`, DISPATCH), P3 = read or write, P4 = the instruction address that did it |
| **Stack** | the chain of calls on the crashing thread, newest first | `TgCounter!TgDispatchDeviceControl` ← `nt!IofCallDriver` ← I/O manager ← `NtDeviceIoControlFile` ← system call from `tgclient` |
| **Registers** | the CPU state at the crash | the register holding the store's address = 0 |
| **Module info** | which build of which file was loaded | `C:\drivers\TgCounter.sys`, its timestamp |

**How a NULL write becomes 0xD1, step by step** (this is the "rule vs bug" idea):
1. Your code raises IRQL to DISPATCH_LEVEL, then stores to address 0.
2. Address 0 isn't mapped. The CPU raises a **page fault**: "this address has no valid translation".
3. The kernel's page-fault handler runs. Normally it would try to bring the page in from disk, which can mean **waiting**. But the faulting code was at DISPATCH_LEVEL, where waiting is impossible (the scheduler runs at that level).
4. The handler can't do its normal job, so it bugchecks with the code for exactly this situation: 0xD1 (0xA if it can't attribute the access to a driver).

So: the **bug** is a NULL pointer. The **rule** that caught it is about IRQL. If the same NULL write had happened at PASSIVE_LEVEL, you'd get a different stop code: a kernel-mode exception such as 0x3B SYSTEM_SERVICE_EXCEPTION (the crash happened inside a system call) or 0x7E. Reading a bugcheck well means not stopping at the stop code's name.

**Reading the stack.** A stack is the story of how execution reached the crash, read from the bottom up: a user program made a system call, the I/O manager dispatched an IRP, your function ran, it crashed at instruction P4. Each frame is a function that called the one above it. The first frame that belongs to a non-Microsoft module is usually where to look, and `!analyze` uses exactly that heuristic to pick `MODULE_NAME` and `SYMBOL_NAME`.

**The analysis order** (it's the same for every crash):
1. **Rule:** what does this stop code mean? What do *its* P1–P4 mean?
2. **Evidence:** what are P1–P4 here? Do they make sense together (address, IRQL, read/write, instruction)?
3. **Location:** which function and instruction (P4, the stack, `u`/`ub` around it, `ln`)?
4. **Cause:** why did that instruction do that (the register holding 0, the local variables with `dv`)?
5. **Proof of identity:** which build crashed (`lmv`: path and timestamp), so the conclusion is about the code you think it is.

---

## 6. Latent bugs and Driver Verifier

**A latent bug is code that's wrong but usually works.** 5.4's bug: the driver holds a spin lock (which raises IRQL to DISPATCH_LEVEL) and reads a value stored in **paged pool**. Paged pool is memory the memory manager is allowed to write out to the page file when RAM is needed. The rule says: **at DISPATCH_LEVEL, only touch memory that can never be paged out** (nonpaged pool), because a page fault there can't be handled (§5).

Why it "works": right after allocation and use, the page holding `42` is almost always still in RAM. The read succeeds; no page fault; no crash. The bug is real but only bites when the page happens to have been paged out at the moment of the read: under memory pressure, after hours, on a customer's machine with less RAM, once a month. That's the worst kind of bug: rare, unreproducible, and pointing at the wrong time.

**What Verifier does, conceptually:** it inserts checks around the verified driver's calls into the kernel, and it can **change the conditions** so rare situations happen every time. The option at work in 5.4 is **Force IRQL checking**: whenever the verified driver raises IRQL (here, by acquiring a spin lock), Verifier forces pageable memory out of RAM first. Now the page holding `42` is **guaranteed** not to be present, the read **always** faults at DISPATCH_LEVEL, and the bug crashes **every time**, at the exact line.

| | Without Verifier | With Verifier (Force IRQL checking) |
|---|---|---|
| Is the code wrong? | yes | yes |
| Is the paged value in RAM at the read? | almost always | **never** (Verifier removed it) |
| Result | `PAGED -> 42`, works | page fault at DISPATCH → bugcheck, every time |
| Evidence in the dump | — | P1 = the paged-pool address; `!pool` = paged, tag `TgTg`; `!pte` = **not present** |

**Why the lab uses a spin lock instead of `KeRaiseIrql`.** Verifier works by intercepting the driver's **calls into the kernel**. `KeRaiseIrql` is compiled inline (it becomes a couple of instructions in your driver, not a call), so Verifier never sees the raise. `KeAcquireSpinLock` is a real call into the kernel, which Verifier intercepts, so it gets the chance to page things out. This is a good illustration of "Verifier checks the boundary between your driver and the kernel".

**What `!pte` proves.** `!pte` shows the page-table entry for an address: the translation the CPU would use. "Not present" means the page wasn't in RAM. That's the evidence connecting cause and effect: the address in P1 is your paged-pool block (`!pool`), and it wasn't in memory (`!pte`), at an IRQL where that's fatal (P2). Three commands, one sentence of proof.

**The general idea beyond this lab:** Verifier has many such options (special pool, which places each allocation next to an unmapped page so buffer overruns crash at the exact write; pool tracking, which catches leaks at unload; low-resources simulation, which makes allocations fail randomly). Each one turns a class of rare failure into a reliable one. In validation work, that's often the most valuable move: **make the failure reproducible**, then analyze it.

---

## 7. Snapshots vs timelines: what tracing adds

A dump answers "what is the state?". It can't answer "what happened before?", "in what order?", or "how long did each part take?". For those you need a **timeline**.

**How ETW works:**
- Many components are **providers**: the kernel (context switches, interrupts, DPCs, disk I/O, process start/stop), drivers, services, apps. Each can emit small **events**: a timestamp, an ID, some fields.
- A provider costs almost nothing when nobody is listening.
- A **session** turns chosen providers on and collects their events into memory buffers, then a file (`.etl`).
- **WPR** is a tool that starts a session with a ready-made set of providers (a *profile*, like `GeneralProfile` or `CPU`) and stops it into a file.
- **WPA** reads the file and turns events into tables and graphs: CPU usage per process, every context switch, every DPC and ISR with its duration.

**What 5.5 is looking for:**
- **`tgclient.exe`'s life on a timeline:** process start, a few milliseconds, mostly inside the system call, process end. That's the user side of the path from §1, seen in time instead of as structures.
- **DPC/ISR work by module:** which drivers in your VM do interrupt-time work (VMware's virtual devices, storage, network). This is the kind of view used to find a driver whose DPCs take too long (lecture 004, and the 0x133 watchdog in 002).
- **Why TgCounter isn't there:** it's not a provider. It emits no events and handles no interrupts, so a trace can only see it indirectly (time spent in the system call). Adding TraceLogging to the driver would make it a provider, and its own events would show up next to the kernel's.

**When to reach for which:** crash or hang → dump. "It's slow", "it stutters", "battery drains", "sometimes it takes 2 seconds" → trace. A crash that needs the *history* leading up to it → both (a trace running, then a dump).

---

## 8. The analysis loop, and what counts as proof

Every lab in 013 asks you to **predict before you run**. That's not a teaching gimmick; it's the method used on real failures:

```
question  →  hypothesis + prediction  →  collect evidence  →  compare  →  conclusion (or a new hypothesis)
```

- **Question:** specific. "Why did the VM bugcheck when `tgclient crash` ran?", not "what happened?".
- **Prediction:** concrete values you can check. "0xD1, P1 = 0, P2 = 2, P4 in TgDispatchDeviceControl". A prediction that can't be wrong teaches nothing.
- **Evidence:** from the artifact, not from memory or assumption. Dumps, `!pte`, timestamps, the trace.
- **Compare:** where the prediction and evidence disagree is where your model of the system is wrong. That's the most valuable moment in any lab (for example, getting 0xA instead of 0xD1, or the dump missing because the page file was too small).
- **Conclusion:** one sentence with four parts.

**The one-sentence conclusion, as a template:**

> **[Rule]** fired because **[location]** did **[action]** at **[condition]**; the cause is **[root cause]**; proven by **[evidence]**.

For 5.4: *"0xD1 fired because `TgCounter!TgDispatchDeviceControl` read paged-pool memory (P1, tag `TgTg`) while holding a spin lock at DISPATCH_LEVEL (P2 = 2); the cause is storing a value accessed under a spin lock in paged pool; proven by `!pool` (paged, TgTg) and `!pte` (not present), on build timestamp X, with Verifier's Force IRQL checking making the page absent."*

**What counts as proof:**

| Claim | Proof |
|---|---|
| "It was my driver" | the stack frame and `MODULE_NAME`, and `lmv` showing the path and timestamp of the build you tested |
| "It was a NULL pointer" | P1 = 0 and the faulting instruction's address register = 0 (`r`) |
| "It was at DISPATCH_LEVEL" | P2 = 2, `!irql` agrees |
| "The memory was paged out" | `!pte` says not present |
| "It's my allocation" | `!pool` shows your tag |

Anything not on that kind of list is a hypothesis, not a conclusion.

---

## 9. Why this is the real job

Strip away the lab and this is what platform and validation engineers do with Windows every day:
- A test machine or a customer's PC bugchecks → the dump arrives → **rule, evidence, location, cause, proof** → a bug filed against the right component with a one-sentence conclusion. At scale, Windows Error Reporting groups crashes by a **bucket** (the `FAILURE_BUCKET_ID` you'll see in `!analyze -v`), so thousands of crashes with the same root cause count as one problem.
- A device stops responding but nothing crashed → a **live dump** captures the stuck state without rebooting.
- A driver passes all functional tests → run it **under Verifier** to flush out latent bugs before customers find them.
- Something is slow or drains battery → a **trace**.

Phase 5 is that whole toolkit, on a driver you wrote, where you already know the answer. That's what makes it a safe place to learn how the evidence looks.

---

## Misconceptions

| You might think | Reality |
|---|---|
| The debugger has special access to "the OS" | It reads memory and registers, and interprets them with symbols. Everything it shows is a pointer walk you could do by hand |
| A driver is a running program | It's code and data in kernel memory, run on other threads' behalf when the kernel calls it |
| `!analyze -v` finds the bug | It finds the **rule** and the most likely **location**. The cause and the proof are your job |
| The stop code is the bug | It's the rule that caught it. 0xD1 here catches a NULL write in 5.3 and a paging bug in 5.4 |
| A dump is a log of what happened | It's a photograph of memory at one instant. For history, use a trace |
| Code that works 10 times is correct | Latent bugs depend on conditions (is the page in RAM?). Verifier changes the conditions |
| Kernel addresses in my notes will work next boot | KASLR moves them every boot; use names and symbols |
| Local kernel debugging is the full kernel debugger | It's read-only and can't stop the machine; breakpoints need a second machine (remote KD) |
| A blue screen means Windows failed | It means Windows **detected** a broken rule and stopped to protect your data |

---

## Self-check questions

1. In one sentence, what are all five Phase 5 labs doing at the most general level?
<details><summary>Answer</summary>Getting at the kernel's state, which lives in memory, at different moments or under different conditions (live, frozen while running, frozen at a crash, under Verifier's stress, or as a timeline of events), and reading it with symbols.</details>

2. What do symbols add, and what's the difference between your private PDB and Microsoft's public symbols?
<details><summary>Answer</summary>They map addresses to names (functions, globals), bytes to types (structures and fields), and instructions to source lines. Your private PDB has everything including local variables and your structure types; Microsoft's public symbols from the symbol server have function and global names but not all types and locals.</details>

3. Describe the pointer chain from `\Driver\TgCounter` to `Counter`, naming the structure at each step.
<details><summary>Answer</summary>The object manager resolves the name to the DRIVER_OBJECT; its DeviceObject field points to the DEVICE_OBJECT (\Device\TgCounter); its DeviceExtension field points to the driver's _TG_EXTENSION, which contains Counter.</details>

4. Your session printed `PEB is paged out`. What does that mean, and how does it relate to 5.4?
<details><summary>Answer</summary>The page holding that user-mode structure wasn't in RAM (its page-table entry was "not present"), so the debugger couldn't read it. In 5.4 the same condition, a not-present page, is what makes the driver's read fault; at DISPATCH_LEVEL that fault can't be handled, so it bugchecks.</details>

5. Why does the kernel bugcheck instead of trying to continue?
<details><summary>Answer</summary>It detected that a rule it relies on was broken and can't know what else is corrupted. Continuing could write bad data to disk or spread the damage, so it stops everything and records evidence (stop code, parameters, a dump).</details>

6. Explain why a NULL write at DISPATCH_LEVEL produces 0xD1 rather than a generic access violation.
<details><summary>Answer</summary>The write to address 0 causes a page fault. The page-fault handler would normally resolve faults, possibly by waiting for disk, but the code was at DISPATCH_LEVEL where waiting is impossible. So the handler bugchecks with the rule for that situation, 0xD1 (driver touched memory at IRQL ≥ DISPATCH). The NULL is the bug; the IRQL decides which rule reports it.</details>

7. Why does `tgclient paged` usually work without Verifier and always crash with it?
<details><summary>Answer</summary>The driver reads paged pool while holding a spin lock (DISPATCH_LEVEL). Normally the page is still in RAM, so no fault occurs. Verifier's Force IRQL checking pages out pageable memory whenever the verified driver raises IRQL (here, acquiring the spin lock), so the page is never present, the read always faults at DISPATCH_LEVEL, and it always bugchecks.</details>

8. Which three commands prove the 5.4 conclusion, and what does each show?
<details><summary>Answer</summary>`!analyze -v` (stop code, P1 = the paged-pool address, P2 = 2, the function); `!pool <P1>` (paged pool, tag TgTg: it's your allocation); `!pte <P1>` (not present: the page wasn't in RAM).</details>

9. When would you take a live dump instead of crashing the machine, and what stop code will the dump show?
<details><summary>Answer</summary>When something is stuck or wrong but the system must keep running (a hung device, a server), or you just want a consistent photograph of state. It shows 0x161 LIVE_SYSTEM_DUMP, meaning "taken on purpose", not a failure.</details>

10. Why can't 5.5's trace show TgCounter's own activity, and what kind of question does a trace answer that a dump can't?
<details><summary>Answer</summary>TgCounter isn't an ETW provider (it emits no events) and has no interrupts or DPCs, so it appears only indirectly as time spent in tgclient's system call. A trace answers timeline questions: what happened, in what order, how long each part took; a dump only shows the state at one instant.</details>

11. Write the one-sentence conclusion template and fill it in for 5.3.
<details><summary>Answer</summary>[Rule] fired because [location] did [action] at [condition]; the cause is [root cause]; proven by [evidence]. For 5.3: 0xD1 fired because TgCounter!TgDispatchDeviceControl wrote to address 0 at DISPATCH_LEVEL while handling IOCTL 0x800023FC; the cause is a deliberate NULL pointer store after KeRaiseIrql; proven by P1 = 0, P2 = 2, the store instruction at P4 whose address register is 0, and the build path/timestamp from lmv.</details>

---

## Sources

- Microsoft Learn, [Local kernel-mode debugging](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/performing-local-kernel-debugging) (read-only; requires debug mode on). Checked 2026-11-07.
- Microsoft Learn, [Kernel-mode dump files](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/kernel-mode-dump-files) and [Varieties of kernel-mode dump files](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/varieties-of-kernel-mode-dump-files). Checked 2026-11-07.
- Microsoft Learn, [Bug Check 0xD1: DRIVER_IRQL_NOT_LESS_OR_EQUAL](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/bug-check-0xd1--driver-irql-not-less-or-equal) and [Bug Check 0x161: LIVE_SYSTEM_DUMP](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/bug-check-0x161--live-system-dump). Checked 2026-11-07.
- Microsoft Learn, [Force IRQL Checking](https://learn.microsoft.com/en-us/windows-hardware/drivers/devtest/force-irql-checking) (Verifier pages out pageable memory when a verified driver raises IRQL) and [Driver Verifier](https://learn.microsoft.com/en-us/windows-hardware/drivers/devtest/driver-verifier). Checked 2026-11-07.
- Microsoft Learn, [Symbols for Windows debugging](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/symbols) (public vs private symbols, symbol server). Checked 2026-11-07.
- Microsoft Learn, [Event Tracing for Windows](https://learn.microsoft.com/en-us/windows/win32/etw/about-event-tracing) and [Windows Performance Recorder](https://learn.microsoft.com/en-us/windows-hardware/test/wpt/windows-performance-recorder). Checked 2026-11-07.
- Yosifovich, Ionescu, Russinovich, Solomon, *Windows Internals, Part 1*, 7th ed., ch. 5 (memory management, pools, page faults) and ch. 6 (I/O system: driver/device objects, IRPs); *Part 2*, 7th ed., ch. 10 (ETW, Windows Error Reporting and crash dumps).
- Your own lab record: `../labs/011-session_handoff.md` entries 52–55 (ARM64 local KD, kernel base, `PEB is paged out`, `KiSwapContext`, `lm m TgCounter`).
