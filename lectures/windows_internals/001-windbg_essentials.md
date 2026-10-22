2026_10_21_21_40-(WinDbg-Essentials)

# Lecture 001 — WinDbg Essentials: Symbols and the Eight Commands That Do Most of the Work

> **For:** Timothy · **Date:** 2026-10-21
> **Prerequisites:** `lectures/firmware/003-from_bare_metal_to_an_os.md` (components, IRQL, drivers aren't processes). Helpful later: lectures 005 (IRQL in depth) and 006 (device stacks).
> **Why this lecture:** WinDbg is the main tool for Windows kernel debugging. Almost every crash or hang investigation starts with the same handful of commands. This lecture teaches those commands one at a time: what each one asks, what it prints, and how to read the output. It starts with symbols, because without them every command prints useless numbers.

---

## Core ideas (the answer key)

1. **WinDbg looks at one of three targets:** a dump file (a snapshot), a live machine through a debug connection (KDNET or serial), or the local machine read-only (local kernel debugging). The commands are the same; what you can do differs.
2. **Symbols turn addresses into names.** A `.pdb` file maps a module's addresses to function and type names. Without matching symbols, stacks are raw addresses and `!analyze` guesses. Fix symbols first: `.symfix`, `.reload`, and `!sym noisy` when something won't load.
3. **`!analyze -v` is triage, not a verdict.** It reads the bugcheck code and parameters, finds the faulting thread, and names a likely module. Its output fields (code, parameters, stack, module, failure bucket) are your starting evidence. It's sometimes wrong, especially when the module it names is the victim.
4. **`k` shows the call stack of the current thread, newest call on top.** Read it bottom-up to see how the thread got there. Read it top-down to see where it stopped. `kn` adds frame numbers, and `.frame N` + `dv` inspect one frame.
5. **`lm` lists loaded modules.** `lmv m name` gives one driver's version, timestamp, path and symbol status. "Which version of the driver was running?" is answered here.
6. **`!thread` shows one thread's state, wait reason, IRPs and stack; `!process` shows a process and its threads.** Hangs are diagnosed by finding the thread that's waiting, and then what it's waiting for.
7. **`!irql` shows the IRQL a processor was at when it stopped.** It's the first check for any "touched pageable memory at high IRQL" crash.
8. **`!devnode` walks the PnP device tree; `!devstack` shows one device's stack of drivers (PDO at the bottom, FDO, filters).** Together they answer "which drivers sit on this device, and what state is it in?"
9. **Every command answers one question.** Pick the command from the question, not the other way round: *what crashed* → `!analyze -v`; *how did we get here* → `k`; *which driver and version* → `lm`; *who is waiting on what* → `!thread`; *at what priority* → `!irql`; *which drivers own this device* → `!devstack`.

---

## Table of Contents

- [0. Direct answers](#0-direct-answers)
- [1. The three targets](#1-the-three-targets)
- [2. Symbols](#2-symbols)
- [3. `!analyze -v`](#3-analyze--v)
- [4. `k` and friends: the call stack](#4-k-and-friends-the-call-stack)
- [5. `lm`: loaded modules](#5-lm-loaded-modules)
- [6. `!thread` and `!process`](#6-thread-and-process)
- [7. `!irql`](#7-irql)
- [8. `!devnode` and `!devstack`](#8-devnode-and-devstack)
- [9. The next ring of commands](#9-the-next-ring-of-commands)
- [10. A first session, start to finish](#10-a-first-session-start-to-finish)
- [11. Lab](#11-lab)
- [12. Misconceptions](#12-misconceptions)
- [13. Saying it precisely](#13-saying-it-precisely)
- [14. Self-check](#14-self-check)
- [Sources](#sources)

Depth tags: 🟢 OWN IT · 🔵 CONTRACT (know what it does) · ⚫ BLACK BOX (know it exists).

---

## 0. Direct answers

| You want to know | Command | Section |
|---|---|---|
| Why did it crash? | `!analyze -v` | §3 |
| How did this thread get here? | `k`, `kn`, `kb` | §4 |
| Which driver, which version? | `lm`, `lmv m <name>` | §5 |
| What is this thread doing or waiting for? | `!thread <addr>` (and `!process 0 0`) | §6 |
| What priority was the CPU running at? | `!irql` | §7 |
| What devices exist, and in what state? | `!devnode 0 1` | §8 |
| Which drivers are layered on this device? | `!devstack <devobj>` | §8 |
| Why are the names missing? | `.symfix`, `.reload`, `!sym noisy`, `lm` | §2 |

---

## 1. The three targets 🟢

WinDbg ("win-debug") is one program that can attach to three kinds of target:

| Target | How you get it | What you can do | Typical use |
|---|---|---|---|
| **Dump file** | Open a `.dmp` (File → Open dump file) | Read memory that was captured; no running, no stepping | Most crash investigations; anything a partner sends you |
| **Live kernel (remote)** | Target machine boots with debugging on (KDNET over the network, or serial); WinDbg runs on a second host machine | Break in, read *and* change state, set breakpoints, step, resume | Bring-up labs; hangs you can reproduce; driver development |
| **Local kernel** | `bcdedit /debug on` on the same machine, reboot, then File → Attach to kernel → Local | **Read-only** view of the running kernel; no breakpoints, can't stop the machine | Learning and inspecting (great for practicing `!devnode`, `!devstack`, `lm`, `!process`) |

Two practical notes:
- Turning on kernel debugging with `bcdedit` is blocked while **Secure Boot** is on. In a lab VM you turn Secure Boot off; on a production machine you usually work from dumps instead.
- The command language is identical across all three targets. Everything below works on a dump unless it says otherwise.

---

## 2. Symbols 🟢

### 2.1 What a symbol file is

When a driver is compiled, the compiler writes two files:
- the binary (`hidi2c.sys`), which contains machine code and addresses, and
- a **PDB** (program database, `hidi2c.pdb`), which maps those addresses to **names**: functions, global variables, and type layouts (structure fields and offsets).

The binary records which PDB it matches, using a GUID and an "age". WinDbg only loads a PDB whose identity matches the binary exactly. A PDB from a different build is refused, because its addresses would point at the wrong code.

**Public vs private symbols:**
- Microsoft publishes **public symbols** for Windows on its symbol server. These include function names and most types the debugger needs (`nt!_KPRCB`, `nt!_TRIAGE_9F_POWER`), but not local variable names or source lines.
- Your own driver has **private symbols** (everything), because you built it.

### 2.2 Setting the symbol path

```
.symfix C:\symbols             ← use the Microsoft symbol server, cache downloads in C:\symbols
.sympath+ C:\mydriver\build    ← ADD your own driver's PDB folder (the + appends)
.reload                        ← re-resolve symbols for all loaded modules
```

The full form `.symfix` writes for you is:

```
srv*C:\symbols*https://msdl.microsoft.com/download/symbols
```

Read it as: "**s**e**rv**er store; **cache** to `C:\symbols`; **fetch** from Microsoft." You can also set it before WinDbg starts, with the environment variable `_NT_SYMBOL_PATH`, so every debugger session uses it.

### 2.3 When symbols won't load

| Symptom | Meaning | Fix |
|---|---|---|
| Stack shows `hidi2c+0x1a2c` instead of `hidi2c!SomeFunction+0x4c` | That module has no symbols loaded (exports only, or nothing) | `.reload /f hidi2c.sys`, then `lmv m hidi2c` to see status |
| `*** WARNING: Unable to verify checksum` | Harmless on its own | Ignore |
| `*** ERROR: Symbol file could not be found` | No matching PDB found on the path | `!sym noisy` then `.reload /f <module>`. The noisy log shows every place it looked |
| `!analyze` says "Probably caused by: ntkrnlmp.exe" for everything | Often a symbol problem upstream | Fix symbols, then re-run `!analyze -v` |

`lm` prints a symbol status per module: `(pdb symbols)` means good, `(deferred)` means not loaded yet (normal; it loads when needed), and `(export symbols)` or `(no symbols)` means you only have partial names.

**Rule:** if a stack looks wrong, check symbols *before* drawing any conclusion. Wrong symbols make a correct stack look like nonsense.

---

## 3. `!analyze -v` 🟢

### 3.1 What it does

`!analyze -v` (the `!` marks an *extension* command; `-v` means verbose) runs Microsoft's automated triage:
1. It reads the bugcheck code and its four parameters.
2. It finds the thread and the trap/exception context that matter for this code.
3. It walks the stack, skips frames that belong to Windows' own crash machinery, and picks the first "interesting" module.
4. It prints a structured report and a **failure bucket**, a signature that groups identical crashes from many machines.

### 3.2 How to read the report

The fields you'll read every time (names as they appear in the output):

| Field | What it tells you |
|---|---|
| `BUGCHECK_CODE` and `BUGCHECK_P1` … `P4` | The stop code and its four parameters. **Always look up what each parameter means for this code** (lecture 002). |
| A plain-English description at the top | Windows' own explanation of the code, e.g. "An attempt was made to access a pageable (or completely invalid) address at an interrupt request level (IRQL) that is too high." |
| `PROCESS_NAME` | Which process's context the CPU was in. For kernel crashes this is often incidental: an ISR runs in whatever thread it interrupted. |
| `TRAP_FRAME` / `CONTEXT` / `EXCEPTION_RECORD` | Pointers to the saved CPU state at the fault. `!analyze` usually switches to it for you, or tells you which command to run (`.trap`, `.cxr`, `.exr`). |
| `STACK_TEXT` | The call stack at the fault, top = most recent. |
| `SYMBOL_NAME`, `MODULE_NAME`, `IMAGE_NAME` | The function and driver `!analyze` blames. |
| `FAILURE_BUCKET_ID` | A short signature such as `AV_hidi2c!SomeFunction`. Same bucket = probably the same bug. |

### 3.3 How it goes wrong

`!analyze` names the module **where the fault happened**. That isn't always the module that **caused** it:
- Driver A frees a buffer; driver B later uses a stale pointer to it → the crash lands in B, but A's lifetime bug is the cause.
- Driver A corrupts pool memory; Windows' own pool code trips over the damage later → `!analyze` blames `nt`.

That's why `!analyze -v` is step one, not the answer. Steps two and three are reading the stack (`k`) and the parameters yourself. When memory corruption is suspected, Driver Verifier (lecture 004) moves the crash to the moment of the corruption.

---

## 4. `k` and friends: the call stack 🟢

### 4.1 What a stack trace is

Each thread has a stack. Each function call pushes a frame: the return address, saved registers, and local variables. `k` walks those frames from the current one back toward the thread's start. One line is printed per frame:

```
 # Child-SP          RetAddr               Call Site
00 ffff8a0c`1e7ff6b8 fffff801`2c4b1a29     nt!KeBugCheckEx
01 ffff8a0c`1e7ff6c0 fffff801`2c4ad4a8     nt!KiBugCheckDispatch+0x69
02 ffff8a0c`1e7ff800 fffff801`5a2a1234     nt!KiPageFault+0x468
03 ffff8a0c`1e7ff998 fffff801`5a2a0f10     MyDriver!MyEvtInterruptDpc+0x44
04 ffff8a0c`1e7ff9a0 fffff801`2c2d6b9e     Wdf01000!FxInterrupt::_InterruptDpcThunk+0x9d
05 ffff8a0c`1e7ffa00 fffff801`2c2d5d84     nt!KiExecuteAllDpcs+0x30e
06 ffff8a0c`1e7ffb40 fffff801`2c4a1f1e     nt!KiRetireDpcList+0x1f4
07 ffff8a0c`1e7ffde0 00000000`00000000     nt!KiIdleLoop+0x9e
```

*(This stack is illustrative, written to show the shape. It's not from a real dump.)*

What each column stands for:
- `#`: frame number (shown by `kn`). Frame 00 is the newest.
- `Child-SP`: the stack pointer value for that frame.
- `RetAddr`: where execution returns when this frame's function finishes.
- `Call Site`: `module!function+offset`. The offset is the number of bytes into the function, which is how you find the exact instruction.

### 4.2 Reading it

**Top-down: where did it stop?** Frames 00–02 are Windows' crash machinery: `KeBugCheckEx` is the "stop the machine" function, and `KiPageFault` means a page fault was being handled. The first frame that isn't crash machinery, frame 03, is where the fault happened: `MyDriver!MyEvtInterruptDpc+0x44`.

**Bottom-up: how did it get there?** The processor was idle (`KiIdleLoop`), retired its DPC queue (`KiRetireDpcList` → `KiExecuteAllDpcs`), KMDF's DPC thunk ran, and it called the driver's DPC callback. So this code was running **as a DPC, at DISPATCH_LEVEL**. A page fault inside it means the code touched pageable or invalid memory at DISPATCH_LEVEL: the textbook 0xD1. The stack alone told you the IRQL context, before you ran `!irql`.

That bottom-up habit is the most valuable one in this lecture: **the shape of the stack tells you what context the code ran in.** Frames like `KiInterruptDispatch` mean an ISR, `KiExecuteAllDpcs` means a DPC, `ExpWorkerThread` means a system work item at PASSIVE_LEVEL, and `KiSystemServiceCopyEnd` means a system call coming up from user mode.

### 4.3 Variants

| Command | Adds |
|---|---|
| `k` | Basic stack |
| `kn` | Frame numbers |
| `kb` | First parameters passed to each function (x64 calling conventions make these unreliable; treat them as hints) |
| `kv` | Frame-pointer-omission info and trap frames |
| `kp` | Full parameter lists, if private symbols exist |
| `.frame N`, then `dv` | Switch to frame N and display its local variables (private symbols needed) |
| `!stacks 2` | A summary of **all** threads' kernel stacks: the hang investigator's command (lecture 003) |

---

## 5. `lm`: loaded modules 🟢

`lm` ("list modules") prints every module loaded in the target: the kernel (`nt`), the HAL, every driver, and (in a process context) user-mode DLLs.

```
lm                       ← all modules: start/end address, name, symbol status
lm t n                   ← names with timestamps
lmv m hidi2c             ← one module, verbose
```

`lmv m hidi2c` gives you (field names as WinDbg prints them):
- `Image path`: where the binary was loaded from (inbox `System32\drivers` or a driver store folder),
- `Timestamp`: when it was built,
- `File version` / `Product version`: the version resource,
- symbol status, and the PDB it loaded.

Why this matters for platform work: a large share of real bugs are **version mismatches**. A driver was older than the firmware expected, or a user-mode tool was newer than the kernel driver. Your Nvidia qualification-script story was exactly this. In a dump, `lmv m` is how you prove which versions were actually running, not which ones were supposed to be installed.

`lm` also shows **unloaded modules** at the end of the list. A crash in an address range belonging to an *unloaded* driver means something still called into a driver after it was unloaded, which is a lifetime bug.

---

## 6. `!thread` and `!process` 🟢

### 6.1 Quick vocabulary (lecture 008 has the full version)

- A **process** is a container: an address space, a handle table, and a security identity.
- A **thread** is the thing that runs. It has CPU registers, a stack, a state, and a priority.
- In kernel memory, the kernel's record of a process is an `EPROCESS` structure, and its record of a thread is an `ETHREAD`. The addresses WinDbg prints for processes and threads are the addresses of those structures.

### 6.2 `!process`

```
!process 0 0                 ← every process, one summary line each (address, PID, image name)
!process 0 0 explorer.exe    ← only processes with that image name
!process <addr> 7            ← one process, with all its threads and their stacks (flags 7 = full detail)
```

### 6.3 `!thread`

```
!thread                      ← the current thread
!thread <ETHREAD address>    ← a specific thread
```

What it prints, and what each part answers:

| Part | Question it answers |
|---|---|
| `THREAD ffff…` and `Cid pid.tid` | Which thread, in which process |
| State: `RUNNING on processor 2`, `READY`, or `WAIT: (Executive) KernelMode Non-Alertable` | Is it running, waiting for a CPU, or waiting for something? |
| The objects it's waiting on (events, mutexes, …) | **What** is it waiting for? |
| `IRP List:` | Which I/O requests this thread issued that haven't completed |
| `Wait Start TickCount`, `Ticks` | **How long** it has waited |
| The stack | Where in code it's waiting |

Hangs are diagnosed with `!thread`. The typical chain is:
1. Thread T is waiting on event E.
2. Event E is set by a completion routine that runs when IRP X completes.
3. `!irp X` shows that IRP X is sitting in driver D and was never completed.
4. So driver D is the bug.

You follow waits until you reach something that will never happen.

---

## 7. `!irql` 🟢

```
!irql        ← the IRQL of the current processor, at the moment it stopped (in a dump: when it crashed)
!irql 2      ← processor 2
```

Remember from 003, refined here: IRQL is a **per-processor** value, held in a CPU register (`CR8` on x64), **not** a location in RAM. "Current IRQL" only means something for a particular processor at a particular moment. In a crash dump, `!irql` shows the value that was saved when the crash happened. That's why it's useful: "Was this code at DISPATCH_LEVEL when it touched that address?"

Two cautions:
- A bugcheck raises the IRQL to HIGH_LEVEL on its way down, so the *current* IRQL in a dump can look like 15. `!irql` reports the IRQL saved *before* the debugger or bugcheck took over. The 0xD1 parameter 2 also records it directly.
- Microsoft's own 0xD1 guidance warns that "in the majority of cases of this type of bug check, the issue is not the IRQL level, but rather the memory that is being accessed." Check both: the IRQL, **and** whether the address was pageable, freed, or garbage (`!pte`, `!pool`, `!address`; §9).

---

## 8. `!devnode` and `!devstack` 🟢

These two commands connect the debugger to lecture 006's device stacks. Here's just enough to read them.

**Just enough device-stack theory:** every device Windows knows about has a **device node** (devnode) in the PnP device tree. Each devnode has a **device stack**, a vertical list of device objects, one per driver layered on that device:
- **PDO** (physical device object), at the bottom, created by the *bus driver* that found the device (for the touchscreen, the ACPI driver).
- **FDO** (functional device object), created by the main *function driver* (for the touchscreen, `hidclass` with `hidi2c` as its HID-over-I2C minidriver).
- Optional **filter** device objects above or below the FDO.

### 8.1 `!devnode`

```
!devnode 0 1                 ← walk the whole device tree from the root (0 = root, flag 1 = include children)
!devnode 0 1 hidi2c          ← only devnodes whose service (driver) is hidi2c
!devnode <address>           ← one devnode in detail
```

A devnode entry shows:
- the **instance path** (e.g. `ACPI\PNP0C50\...`), which is the device's identity,
- the **PDO** address,
- the **state**: for example `DeviceNodeStarted` (running) or `DeviceNodeRemoved`, and a **problem code** if it failed. Problem codes are the same numbers Device Manager shows ("Code 10", "Code 43").

For a "dead device" investigation, this answers the first question: *does Windows still think the device is started, or did it fail or get removed?*

### 8.2 `!devstack`

```
!devstack <device object address>   ← the PDO from !devnode, or a device object from an IRP
```

Output shape (illustrative):

```
  !DevObj           !DrvObj            !DevExt           ObjectName
  ffffd30a1b2c4e30  \Driver\VendorFilt ffffd30a1b2c4f80               ← upper filter (if any)
> ffffd30a1b2c3a10  \Driver\hidi2c     ffffd30a1b2c3b60               ← FDO (function driver)
  ffffd30a1a9f1c00  \Driver\ACPI       ffffd30a1a9f1d50  0000003a     ← PDO (bus driver)
!DevNode ffffd30a1a9f2a40 :
  DeviceInst is "ACPI\PNP0C50\1"
  ServiceName is "hidi2c"
```

How to read it:
- The list runs **top to bottom = top of the stack to the bottom**. The PDO is last.
- The `>` marks the device object you asked about.
- Each `!DrvObj` names the driver that owns that layer. **This is the "whose bug is it?" map:** an IRP stuck at the hidi2c layer belongs to hidi2c's owner; one stuck in the ACPI layer points at platform firmware/ACPI.
- `!DevExt` is that driver's private per-device data. With the driver's symbols, `dt` on it shows its internal state.

The typical chain in a 0x9F investigation (lecture 002):
1. `!irp <blocked irp>` shows which device object holds the IRP.
2. `!devstack <that device object>` shows every driver on that device.
3. `!devnode` shows the device's PnP state.

---

## 9. The next ring of commands 🔵

You'll meet these inside the recipes in lectures 002–004. Know what question each one answers:

| Command | Question it answers |
|---|---|
| `.trap <addr>` / `.cxr <addr>` / `.exr <addr>` | Switch to the CPU state saved at a fault (trap frame or context record), or show an exception record. After `.trap` or `.cxr`, `k` shows the stack **at the fault** |
| `r` | CPU registers in the current context |
| `u <addr>`, `ub <addr>` | Disassemble forward / backward: the exact instruction that faulted |
| `ln <addr>` | Nearest symbol: "what function is this address in?" |
| `dt <type> <addr>` | Lay a structure type over memory, e.g. `dt nt!_TRIAGE_9F_POWER <addr>` |
| `dx <expression>` | The modern data-model inspector; e.g. `dx KiBugCheckDriver` shows which driver Windows blamed |
| `!irp <addr>` | One I/O request: its stack locations, which driver currently holds it (marked `>`) |
| `!drvobj <name> 2` | A driver object and its dispatch routines |
| `!pte <addr>` | How an address maps: is the page present, writable, kernel or user? (lecture 008) |
| `!pool <addr>` | Is this address in a pool allocation, which tag, freed or in use? |
| `!address <addr>` | What kind of memory region an address belongs to |
| `!stacks 2` | All threads' kernel stacks, summarized (hangs) |
| `!locks` | Who owns which executive resources (lock-based hangs) |
| `!running` | What each processor is running right now (live hangs) |
| `!dpcs` | Queued DPCs per processor (DPC watchdog investigations) |
| `!poaction` | Power operations in progress and power IRPs (sleep/resume bugs) |
| `!wdfkd.wdflogdump <driver>` | A KMDF driver's in-flight recorder log: the framework's own record of recent events for that driver |
| `.hh <command>` | Open help for any command |

---

## 10. A first session, start to finish

A scenario: a test machine blue-screens overnight, and you have its `MEMORY.DMP`.

1. **Open** the dump in WinDbg.
2. **Symbols:** `.symfix C:\symbols`, `.sympath+ <your driver's PDB folder>`, `.reload`.
3. **Triage:** `!analyze -v`. Note the code (say 0xD1) and its four parameters, and write them down.
4. **Interpret the parameters** (lecture 002): P1 = the address touched, P2 = the IRQL (2 = DISPATCH_LEVEL), P3 = read or write, P4 = the instruction address.
5. **Confirm the context:** `k`. Is it a DPC stack? An ISR stack? That should agree with P2.
6. **Find the instruction:** `ln <P4>` and `u <P4>`: which function, and which instruction.
7. **Classify the address:**
   - `!pte <P1>`: is the page not present?
   - `!pool <P1>`: is it in paged pool, and freed or in use?
   - `!address <P1>`: what kind of region it is.
8. **Which version:** `lmv m <driver>`.
9. **Conclusion** in one sentence, layer named: "`MyDriver!MyEvtInterruptDpc` read a paged-pool buffer at DISPATCH_LEVEL. The allocation used the paged-pool flag; it must be nonpaged. Driver version 1.2.0.4."

That last sentence is the deliverable. Every step above exists to make it precise.

---

## 11. Lab

On a Windows VM:

1. Install WinDbg (`winget install Microsoft.WinDbg`) and Sysinternals NotMyFault.
2. Set dumps to **Kernel memory dump** (System Properties → Advanced → Startup and Recovery). Lecture 003 explains why.
3. Run NotMyFault as administrator and choose **High IRQL fault (Kernel-mode)**. The VM will blue-screen. Reboot.
4. Open `C:\Windows\MEMORY.DMP`. Then:
   - Run §10 steps 2–9.
   - **Predict before running `k`:** what context do you expect the faulting code to be in? Then check.
   - Run `lmv m myfault` (NotMyFault's driver is `myfault.sys`).
5. **Local kernel debugging** (optional; Secure Boot off in the VM): `bcdedit /debug on`, reboot, then attach to the local kernel and run:
   - `!devnode 0 1`, then find one device and run `!devstack` on its PDO,
   - `!process 0 0`,
   - `!thread` on any thread of `explorer.exe`.

Record in your notes: the failure bucket, the stack's context frame (which `Ki…` routine), and the IRQL.

---

## 12. Misconceptions

| You might think | Reality | Why it matters |
|---|---|---|
| `!analyze -v` tells you the root cause | It names the module **where** the fault occurred, with a guessed cause | Victim drivers get blamed for corruption caused by others |
| A stack full of `+0x` offsets means the code is broken | It means **symbols** are missing | Fix symbols before reasoning |
| `PROCESS_NAME` tells you who caused a kernel crash | ISRs and DPCs run in whatever thread they interrupted; the process is often incidental | Don't chase the wrong process |
| IRQL is a value stored in RAM that WinDbg reads | It's a per-processor CPU register value; dumps save what it was at the crash | Ask "IRQL **on which processor, when**?" |
| `!devstack` and `!devnode` show the same thing | `!devnode` = the device's identity and PnP state in the tree; `!devstack` = the drivers layered on it | You need both for a dead-device investigation |
| A driver is a process you can list with `!process` | Kernel drivers are modules (`lm`), not processes; their code runs on whatever thread calls them | Look for drivers with `lm`, `!drvobj`, `!devstack` |

---

## 13. Saying it precisely

- "First I fix symbols, then run `!analyze -v` for the code and parameters, then confirm with `k` what context the faulting code ran in: ISR, DPC, worker thread, or system call."
- "`!analyze` names where it faulted, not necessarily who caused it. For corruption, I'd move the crash earlier with Driver Verifier."
- "For a dead device, `!devnode` gives me the PnP state and problem code, and `!devstack` gives me every driver layered on it, from the PDO up."
- "For a hang, I follow waits with `!thread` and `!irp` until I find an IRP or lock that will never be released."

---

## 14. Self-check

1. Name WinDbg's three target types and one thing you can't do with each.
<details><summary>Answer</summary>Dump: can't run, step, or set breakpoints. Live remote kernel: can't use it without a debug-enabled target and a second host. Local kernel: can't break or set breakpoints (read-only), and needs debug mode (Secure Boot off).</details>

2. What does a PDB contain, and why will WinDbg refuse a PDB from a different build?
<details><summary>Answer</summary>Address → name mappings for functions, globals and types. The binary records the PDB's GUID and age; a different build's addresses would point at the wrong code, so only an exact match loads.</details>

3. Your stack shows `hidi2c+0x1a2c`. What's wrong, and which three commands fix or diagnose it?
<details><summary>Answer</summary>No symbols for hidi2c. Use <code>.symfix</code> (or fix the path), <code>.reload /f hidi2c.sys</code>, and <code>!sym noisy</code> to see where it looked. Confirm with <code>lmv m hidi2c</code>.</details>

4. List four fields from `!analyze -v` and what each tells you.
<details><summary>Answer</summary>BUGCHECK_CODE/P1–P4 (the stop code and its parameters), STACK_TEXT (the call stack at the fault), MODULE_NAME/IMAGE_NAME (the blamed driver), FAILURE_BUCKET_ID (a signature that groups identical crashes). Also PROCESS_NAME (the context, often incidental).</details>

5. A stack contains `nt!KiExecuteAllDpcs` below the faulting frame. What IRQL was the faulting code at?
<details><summary>Answer</summary>DISPATCH_LEVEL: it ran as a DPC.</details>

6. Why can `!analyze` blame the wrong driver?
<details><summary>Answer</summary>It names the module where the fault occurred. A different driver may have caused it earlier, by corrupting memory or freeing a buffer still in use.</details>

7. Which command proves which version of a driver was running when the crash happened?
<details><summary>Answer</summary><code>lmv m &lt;driver&gt;</code>: image path, timestamp, file version.</details>

8. What does `!thread` show that you need for a hang?
<details><summary>Answer</summary>State (running / ready / waiting), the objects it's waiting on, how long it has waited, its outstanding IRPs, and its stack.</details>

9. Why is `!irql`'s answer tied to a processor and a moment?
<details><summary>Answer</summary>IRQL is a per-processor CPU register value that changes constantly. A dump records each processor's value at the crash.</details>

10. In `!devstack` output, which line is the PDO, who created it, and what does the `>` mean?
<details><summary>Answer</summary>The bottom line is the PDO, created by the bus driver (e.g. ACPI). <code>&gt;</code> marks the device object you passed in.</details>

11. What does `!devnode 0 1 hidi2c` show?
<details><summary>Answer</summary>All device nodes in the tree whose service (driver) is hidi2c, with their instance paths, PDOs, states and any problem codes.</details>

12. You see a crash address inside a module listed under "Unloaded modules". What kind of bug is that?
<details><summary>Answer</summary>A lifetime bug: something called into, or used memory of, a driver after it was unloaded (a stale callback or function pointer).</details>

---

## Sources

Checked 2026-10-21.

- Microsoft Learn: Symbol path for Windows debuggers (`.symfix`, `.sympath`, `srv*cache*server`, `_NT_SYMBOL_PATH`, `!sym noisy`, `.reload /f`). https://learn.microsoft.com/windows-hardware/drivers/debugger/symbol-path
- Microsoft Learn: Bug check 0xD1 page (debugging steps: `dx KiBugCheckDriver`, `k`, `!irql`, `ln`, `!pool`, `!address`, `lm t n`; the note that the issue is usually the memory, not the IRQL). https://learn.microsoft.com/windows-hardware/drivers/debugger/bug-check-0xd1--driver-irql-not-less-or-equal
- Microsoft Learn: Debugger reference pages for `!analyze`, `k`, `lm`, `!thread`, `!process`, `!irql`, `!devnode`, `!devstack`, `!irp`, `!poaction`.
- *Windows Internals, 7th ed., Part 1*: processes, threads, IRQL, the I/O system.

Stack and `!devstack` outputs in this lecture are illustrative shapes, not captured from a real dump. Run the lab to see real output.
