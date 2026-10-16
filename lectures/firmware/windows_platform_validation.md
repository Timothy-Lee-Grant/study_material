# Windows Platform Validation: The Concepts Behind Your Microsoft Interview

*Lecture written 2026-10-16 from your debrief of the Windows validation / reliability interview.*

---

## Core ideas

1. **The job is platform bring-up and reliability.** Microsoft's client-Windows reliability team helps OEMs and IHVs get Windows running stably on new hardware, then makes sure shipped hardware meets Microsoft's bar. The core skill is root-causing crashes and hangs across the hardware / firmware / driver / OS boundary.
2. **A hardware event reaches software through a stack of layers.** For a touchscreen on a Windows laptop: touch controller → interrupt line → GPIO controller → I2C (SPB) controller driver → HID-over-I2C driver → HID class driver → input stack → app. Good debugging answers name these layers and say what evidence each layer leaves behind.
3. **Windows runs code at different IRQLs, and the IRQL decides what code may do.** ISRs run at DIRQL and must be short and non-blocking; deferred work runs as a DPC at DISPATCH_LEVEL; anything that waits (including a slow I2C transfer) must run at PASSIVE_LEVEL.
4. **An I2C read cannot happen inside a classic ISR.** The transfer is slow and needs the bus controller's own interrupts to finish. The pattern is: acknowledge, defer, read at passive level. Windows supports *passive-level interrupt handling* for exactly this case.
5. **Level- vs edge-triggered interrupts matter for "dead until reset" bugs.** A device that holds its interrupt line asserted until serviced will deadlock with a host that only reacts to edges. If the host misses the one edge, nothing ever happens again.
6. **"Fails after time, stays failed until hard reset" points at stuck state, not a transient.** Strong hypotheses: a missed interrupt, a hung I2C bus, a failed power transition (idle → low power that never comes back), a counter wrap, or resource exhaustion. Each has a distinct signature you can check.
7. **Processes share memory by mapping the same physical pages.** The kernel owns the shared region; the processes agree on it through a *name* (Windows: named section object; Linux/POSIX: `shm_open` name) or an inherited handle. Each process may see it at a different virtual address, so store offsets, not pointers.
8. **Processes can use locks.** Named mutexes, semaphores and events (Windows), process-shared pthread mutexes and named semaphores (POSIX) all work across processes. Your two-mailbox design is a valid lock-free alternative only with atomic flags and memory ordering.
9. **On Windows, a crash is a bugcheck with a code and a dump.** The tools are WinDbg (`!analyze -v`), Driver Verifier, ETW traces, and the kernel debugger. Your Linux instincts (`dmesg`, logs) were right in spirit; translate them to the Windows equivalents.
10. **Your differentiator is the hardware-to-OS boundary.** An EE who has debugged a vendor qualification suite and written user-mode code that talks to I2C through an OS is exactly this profile. Interviews for these roles test mechanism-level understanding, not LeetCode. Prepare by depth in OS internals and a bank of debugging stories told layer by layer.

---

## Part 1 — What this job actually is (decoding your notes)

Your notes, translated:

| Your note | What it means |
|---|---|
| "Reliability team for Windows" | A team whose metric is crash/hang rate on client Windows devices. |
| "Any vendor which will run Windows" | Partners: **OEMs** (Dell, HP, Lenovo, Microsoft's own Surface — companies that sell the finished device) and **IHVs** (Independent Hardware Vendors: Intel, AMD, Qualcomm, Realtek, touch-controller makers — companies that make components and ship drivers for them). ODMs build devices for OEMs. |
| "Debug problems getting Windows onto new devices" | **Platform bring-up.** A new SoC or laptop design boots Windows for the first time and things break: bugchecks, hangs, devices that don't enumerate, sleep/resume failures. |
| "Once hardware stabilizes… meets the standard bar" | **Compatibility and certification.** The formal program is the Windows Hardware Compatibility Program (WHCP); the test suite is the **Windows Hardware Lab Kit (HLK)**. Shipping hardware has to pass it. |
| "DRTM" | **Dynamic Root of Trust for Measurement.** A CPU-supported way (Intel TXT, AMD SKINIT, Arm equivalents) to restart into a measured, trusted state *after* the firmware has run, so Windows doesn't have to trust all of firmware. It underpins System Guard Secure Launch, a Secured-core PC requirement. Bring-up teams see it because it is fragile: firmware tables, TPM and CPU all have to cooperate, and failures look like boot hangs or security features silently turning off. |
| "Driver pieces of Windows" | Windows ships inbox drivers (HID, USB, storage, ACPI, I2C/SPB frameworks); vendors ship the rest. The team debugs across both. |
| "Only client Windows" | Windows 11 on laptops/desktops/tablets, not Windows Server. |
| "Ensure there are no system crashes" | Crash = **bugcheck** (blue screen). Hang = system or device stops responding without a bugcheck. Both are in scope. |
| "Hardware validation infrastructure… end to end for pre-production devices" | A lab system where prototype devices are plugged in and run automated test passes (install builds, run stress, collect dumps and traces). Built during quieter periods between bring-up emergencies. |

So the daily work alternates between two modes:

- **Firefighting:** a partner's new device crashes; get the dump or a live kernel debugger, find which layer is wrong (hardware, firmware/ACPI tables, vendor driver, Windows itself), and get the right party to fix it.
- **Infrastructure:** build test automation so the next platform's problems are caught earlier.

That is why the interviewer asked about drivers, I2C, ISRs, a failing touchscreen and shared memory. Each question probes whether you can reason about where a hardware event goes once it enters the operating system.

---

## Part 2 — How a touch reaches an application on Windows

This is the architecture the interviewer was steering you toward. Your second answer ("the vendor's driver raises an interrupt into the kernel, which handles the XY event") was the right direction; the full picture has more layers, and each layer is a place a bug can live.

### 2.1 How Windows learns the device exists

On a laptop, the touch controller is not discovered by probing. **Firmware describes it in ACPI tables.** The ACPI entry for an I2C touchscreen says, roughly:

- "I am a HID-over-I2C device" (compatible ID `PNP0C50`).
- "I am on I2C controller X at address 0x..., speed 400 kHz" (an `I2cSerialBusV2` resource).
- "My interrupt is GPIO pin N on GPIO controller Y, level-triggered, active-low" (a `GpioInt` resource).
- Power methods for turning the device on and off.

The Plug and Play manager reads this, builds a **device node**, and loads drivers for it. If the ACPI description is wrong — wrong address, wrong pin, edge instead of level, wrong polarity — the device either never works or works and then dies. Wrong ACPI tables are one of the most common bring-up bugs, and they are owned by the OEM's firmware, not by Windows.

### 2.2 The driver stack

Windows drivers are arranged in **device stacks**: a request (an **IRP**, I/O Request Packet) enters at the top and is passed down; completion travels back up. For an I2C touchscreen:

```
Application (receives WM_POINTER / touch input)
   ↑
Windows input stack (win32k, pointer/touch processing)
   ↑
HID class driver (hidclass.sys) — parses HID reports into usages: X, Y, tip switch, contact ID
   ↑
HID-over-I2C miniport (hidi2c.sys, inbox) — speaks the HID-over-I2C protocol
   ↑  issues I2C reads/writes through the SPB framework
I2C controller driver (SoC vendor's driver, built on SpbCx)
   ↑
GPIO controller driver (built on GpioClx) — turns the touch controller's interrupt pin into an interrupt
   ↑
Touch controller hardware (has its own firmware)
```

Vocabulary to know:

- **KMDF / UMDF** — Kernel-Mode and User-Mode Driver Frameworks (together, WDF). Most modern drivers are written on these rather than raw WDM.
- **SPB** — Simple Peripheral Bus: Windows' abstraction for I2C, SPI and UART. **SpbCx** is the framework extension controller drivers use. Peripheral drivers don't hard-code bus details; they receive a *connection ID* resource and open the bus through it.
- **HID** — Human Interface Device. Originally a USB class, now transport-independent. A HID device describes its own data format with a *report descriptor*; the host reads *input reports*.

### 2.3 What happens on a touch

1. A finger lands. The touch controller's own firmware computes contacts and prepares an input report.
2. The controller **asserts its interrupt line** (pulls it low) and keeps it asserted while it has unread data. HID-over-I2C defines this interrupt as level-triggered.
3. The GPIO controller sees the pin and signals an interrupt to the CPU.
4. Windows dispatches the interrupt to the HID-over-I2C driver's interrupt handler (Part 3 explains at what IRQL and why that matters).
5. The driver issues an **I2C read** of the input report through SpbCx. The I2C controller driver runs the bus transaction, itself driven by the I2C controller's interrupts.
6. Reading the report causes the touch controller to **deassert** the interrupt line (or keep it asserted if more reports are queued).
7. The report goes up to hidclass, which parses it and hands contacts to the input stack, which delivers pointer messages to the app.

The key point for debugging: step 6 is a **handshake**. The device's line stays asserted until the host reads. If the host stops reading, the line stays asserted forever.

---

## Part 3 — Interrupts, IRQL, and why an ISR can't do an I2C read

### The problem statement (as asked)

> An interrupt service routine is invoked to do a read operation on an I2C device. What might occur?

Your answer — exit the ISR fast, set a flag, so other interrupts aren't starved — is the right instinct. The stronger answer explains the *mechanism* that makes a read inside the ISR impossible or dangerous, and names what Windows provides instead.

### 3.1 IRQL: the priority level code runs at

Every processor in Windows runs at an **Interrupt Request Level (IRQL)** at all times. Code running at an IRQL masks interrupts at that level and below on that processor.

| IRQL | Value | What runs here | What code may do |
|---|---|---|---|
| PASSIVE_LEVEL | 0 | Threads: user code, most driver code, work items | Anything: wait, sleep, touch pageable memory, issue blocking I/O |
| APC_LEVEL | 1 | Asynchronous procedure calls | Mostly like passive, some restrictions |
| DISPATCH_LEVEL | 2 | The thread scheduler, **DPCs** (Deferred Procedure Calls), code holding spin locks | **May not wait or block.** May not touch pageable memory. Must be short. |
| DIRQL | >2 | **ISRs** for hardware devices | Even stricter: acknowledge the device, capture minimal state, queue a DPC, return. |

The rule that follows: **at DISPATCH_LEVEL or above, the scheduler can't run on that processor, so a wait can never be satisfied.** Waiting there is a bug, and Windows bugchecks rather than hang silently.

### 3.2 Why an I2C read can't finish inside a classic ISR

An I2C read at 400 kHz takes on the order of tens to hundreds of microseconds for a touch report — far longer than an ISR should run. Worse, it is not something the ISR can just "do":

- The transfer is carried out by the I2C controller, and **its progress is signaled by the I2C controller's own interrupts.** If your ISR is sitting at DIRQL waiting for that transfer, and the I2C controller's interrupt is at the same or lower IRQL on that processor, the completion can't be delivered. That is a deadlock.
- The SPB request path involves IRPs and waits, which require PASSIVE_LEVEL.

What actually goes wrong if a driver tries:

- **Bugcheck 0xD1 `DRIVER_IRQL_NOT_LESS_OR_EQUAL`** or **0xA `IRQL_NOT_LESS_OR_EQUAL`** — touched pageable memory or called a passive-only routine at elevated IRQL.
- **Bugcheck 0x133 `DPC_WATCHDOG_VIOLATION`** — an ISR or DPC ran too long, or the system spent too long at DISPATCH_LEVEL or above.
- **Interrupt storm** — with a level-triggered line, if the ISR returns without making the device deassert (it can't, because deasserting requires the I2C read), the interrupt fires again immediately, forever. The CPU spends all its time re-entering the ISR.

### 3.3 The correct pattern

The classic three-stage pattern:

1. **ISR (DIRQL):** confirm the interrupt is ours, silence it at the source if possible, record that it happened, queue a DPC. Return.
2. **DPC (DISPATCH_LEVEL):** do non-blocking follow-up work; if blocking work is needed, queue a work item.
3. **Work item / thread (PASSIVE_LEVEL):** do the slow, blocking work — such as the I2C read.

For devices on serial buses specifically, **KMDF supports passive-level interrupt handling**: the driver registers its interrupt as passive, and the framework runs its handler at PASSIVE_LEVEL in a thread context. Behind the scenes the GPIO controller masks the pin when it fires, the handler does the I2C read (which makes the device deassert), and then the framework unmasks the pin. That is how a level-triggered GPIO interrupt avoids a storm while the slow read happens. This is how drivers like hidi2c handle their interrupt.

**Model answer, in your words:**

> An I2C read can't be done inside the ISR itself. The ISR runs at an elevated IRQL where blocking is forbidden, and the I2C transfer needs the bus controller's own interrupts to complete, so waiting for it there would deadlock or trip the DPC watchdog. Also, if the device's interrupt is level-triggered, it stays asserted until I read it, so returning without silencing it would cause an interrupt storm. So the ISR masks or acknowledges the interrupt, queues deferred work, and the read happens at passive level — on Windows, KMDF has passive-level interrupts for exactly this — and then the interrupt is unmasked once the device has deasserted.

### 3.4 Level- vs edge-triggered, precisely

- **Level-triggered:** "interrupt is pending *while* the line is asserted." The host keeps getting interrupted until the condition is cleared. Robust against missed signals; risky if never cleared (storm).
- **Edge-triggered:** "interrupt happens *when* the line changes." The host reacts once per transition. If the host misses the transition (masked at the wrong moment, configuration error), there is no second chance.

**The dangerous combination:** a device that holds its line low until serviced, described to the host as *edge*-triggered. The first touch causes a falling edge, the host services it, all is well — until one edge is missed (a race during masking, a power transition, a burst of reports). Now the line is low, the device waits for a read, and the host waits for an edge that can't come because the line is already low. **Touch is dead until something resets the device.** Keep that pattern in mind for Part 4.

---

## Part 4 — Case study: the touchscreen that dies until hard reset

### The problem statement (as asked)

> A computer has a touchscreen. After a certain amount of time, the touchscreen fails. It does not recover on its own; it stays broken until the user does a hard reset. How would you troubleshoot it?

Your clarifying question — does it recover after more time? — was excellent, and the answer ("no, it needs a hard reset") is the single most informative fact in the problem. It rules out transient overload and points to **stuck state**: something in the chain entered a state it never leaves. A hard reset clears it because it power-cycles the controller and reinitializes the drivers.

Your instinct to collect data first (logs, `dmesg`) was right. What lifted your answer was moving to architecture. The strongest structure combines both: **characterize the failure, lay out the stack, form one hypothesis per layer with the evidence that would confirm or kill it, then go get that evidence.**

### 4.1 Characterize before hypothesizing

Questions to ask (or say you'd find out):

- **What does "a certain amount of time" track?** Wall-clock uptime (always ~N hours after boot)? Idle time (fails after the screen is left alone)? Sleep/resume cycles (fails after the lid is closed)? Usage (after heavy multi-touch)? Each points to a different layer.
- **Does the rest of the system work?** Keyboard, trackpad, display all fine → the fault is local to the touch path.
- **What does Windows think?** Does the device still show in Device Manager? With an error code? Does disabling and re-enabling it (a *soft* reset of the driver stack) recover touch? If yes, the hardware is fine and the state lives in software or in a device that a re-init revives. If only a power cycle recovers it, suspect the controller or the bus.
- **One unit or every unit?** One unit → hardware defect. Every unit of this platform → design, firmware or driver bug.
- **Which build / firmware / driver versions?** Did it start after an update? (Your Nvidia story is exactly this.)

### 4.2 Hypotheses by layer, with signatures

| Layer | Hypothesis | What you'd see | How to check |
|---|---|---|---|
| Interrupt line | **Missed interrupt / edge-vs-level mismatch** (Part 3.4) | Interrupt line stuck asserted (low); no further interrupts counted; device still enumerated, no error | Measure the line with a scope or logic analyzer; ETW trace shows interrupt count stops; check ACPI `GpioInt` says level, active-low |
| I2C bus | **Bus hung** — a peripheral is holding SDA low mid-transaction (e.g., host reset partway through a read) | Every I2C transaction to any device on that bus fails or times out; other devices on the same bus also break | Logic analyzer on SDA/SCL; SPB driver errors in traces. Recovery technique: clock SCL 9 times to let the device finish its byte |
| Power management | **Device enters a low-power state on idle and fails to come back** | Fails after idle, not after use; fails after sleep/resume; may coincide with `DRIVER_POWER_STATE_FAILURE` (0x9F) bugchecks on some units | Correlate failure with idle timeout or Modern Standby entries; trace D-state transitions (D0 ↔ D3); disable runtime idle for the device and see if the bug disappears |
| Touch controller firmware | **Controller firmware hangs or its watchdog resets it into an unconfigured state** | Line idle (not asserted), no reports; host's next read gets garbage or NAK | Read the controller's status/reset registers over I2C; check whether the HID driver sees a device reset it never re-handled |
| Driver | **Driver state machine stuck** — e.g., an error path that never re-arms the interrupt or never re-issues a read | Interrupt asserted but driver not reading; driver's pending request queue empty | Kernel debugger: inspect the driver's state and pending IRPs (`!irp`, `!devstack`, `!wdfkd` extensions); ETW logs from the driver |
| Time | **Counter wraparound** — e.g., a 32-bit millisecond counter wraps after ~49.7 days; a timeout computed across the wrap never expires or expires instantly | Fails at a fixed uptime that matches a power of two | Compute 2³² ms ≈ 49.7 days, 2³¹ ms ≈ 24.8 days; check if failure uptime matches |
| Resources | **Leak** — memory, handles or request objects leak per touch until allocation fails | Fails after usage, not time; pool usage grows | Pool usage tracking (poolmon), Driver Verifier pool tracking |

Your "overflow because it's time-based" instinct was legitimate — it is the counter-wrap row. The improvement is presenting it as **one hypothesis among several, each with a test,** rather than as the guess.

### 4.3 Tools you'd name on Windows

- **Device Manager / `pnputil`** — is the device present, error code, driver version.
- **Event Viewer** — PnP and driver errors (the Windows counterpart to scanning logs).
- **ETW (Event Tracing for Windows) with WPR/WPA** — record kernel and driver traces (interrupts, DPCs, power transitions, I/O) and analyze them on a timeline. This is the deep counterpart of `dmesg` plus `perf`.
- **Kernel debugger (WinDbg over KDNET or serial)** — attach to the stuck machine live and inspect driver state without rebooting.
- **Live kernel dump** — capture system state without crashing it.
- **Logic analyzer / oscilloscope on the I2C lines and the interrupt pin** — the hardware truth. As an EE, this is the tool you'd reach for that many software candidates wouldn't.

### 4.4 A model answer you could give in about two minutes

> "Stays broken until a hard reset tells me something is stuck, so I want to find which layer holds the stuck state. First I'd characterize: does the time track uptime, idle or sleep cycles? Does disable/re-enable of the device in Device Manager recover it, or only a power cycle? Every unit or one?
>
> Then I'd lay out the path: the touch controller asserts a level-triggered GPIO interrupt, the HID-over-I2C driver handles it at passive level and reads the report over I2C, which deasserts the line, and hidclass passes it to the input stack.
>
> Then hypotheses per layer. If the interrupt line is stuck low and Windows has stopped servicing it, that's a missed interrupt — I'd check ACPI declares it level-triggered, because an edge declaration with a level device dies exactly like this. If SDA is stuck low, the bus is hung. If it correlates with idle, it's a power transition the device doesn't come back from. If it's a fixed uptime like 49.7 days, it's a counter wrap. I'd confirm with a logic analyzer on the lines, ETW traces of interrupts and power transitions, and a live kernel debugger on a failed unit to see the driver's state."

That answer shows mechanism, layers, evidence and tools — what the interviewer was pulling for.

---

## Part 5 — How two processes share memory

### The problem statement (as asked)

> How would two processes share memory? (Follow-ups: each process has its own address space, so how do they both get access to the same memory, and how do they agree on which memory it is?)

You correctly landed on "the kernel has to allocate it" and "some kind of handle/descriptor." Here is the full mechanism, plus one correction.

### 5.1 Why processes can't just share an address

Each process has its own **virtual address space**. The CPU's MMU translates virtual addresses to physical addresses through **page tables**, and each process has its own page tables. Address `0x7FF6_1234_0000` in process A and the same number in process B refer to unrelated physical memory. That isolation is the point of processes.

So "sharing memory" means: **the kernel maps the same physical pages into both processes' page tables.**

### 5.2 How they get the same pages — and how they agree

The kernel needs an object that represents "this region of shareable memory," and both processes need a way to refer to that same object. The coordination answer the interviewer was hunting for is: **a name in a kernel namespace, or an inherited/duplicated handle.**

**Windows:**

```c
// Process A: create a named, page-file-backed section object and map it
HANDLE h = CreateFileMappingW(INVALID_HANDLE_VALUE, NULL, PAGE_READWRITE,
                              0, 4096, L"Local\\TouchShared");
void* p = MapViewOfFile(h, FILE_MAP_ALL_ACCESS, 0, 0, 4096);

// Process B: open the same object by name and map it
HANDLE h2 = OpenFileMappingW(FILE_MAP_ALL_ACCESS, FALSE, L"Local\\TouchShared");
void* q = MapViewOfFile(h2, FILE_MAP_ALL_ACCESS, 0, 0, 4096);
```

- The kernel object is a **section object**; it lives in the kernel's **object manager namespace** under the name `Local\TouchShared`. The name is the agreement.
- Alternatives to a name: create the handle as inheritable and spawn the child with it, or use `DuplicateHandle` to hand a handle to another process.

**Linux / POSIX:**

```c
// Process A
int fd = shm_open("/touch_shared", O_CREAT | O_RDWR, 0600);
ftruncate(fd, 4096);
void* p = mmap(NULL, 4096, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);

// Process B
int fd2 = shm_open("/touch_shared", O_RDWR, 0);
void* q = mmap(NULL, 4096, PROT_READ | PROT_WRITE, MAP_SHARED, fd2, 0);
```

- Your "file descriptor" instinct was right: `shm_open` returns an fd, and the name `/touch_shared` is the agreement.
- Other routes: `mmap(MAP_SHARED | MAP_ANONYMOUS)` before `fork()` (child inherits the mapping), System V `shmget` with an agreed key, or passing an fd over a Unix domain socket.

### 5.3 The same memory, different addresses

`p` in process A and `q` in process B may be **different virtual addresses** for the same physical pages. Consequence: **never store raw pointers inside shared memory**; store offsets from the start of the region.

### 5.4 Correction: processes *can* use locks

You said that because these are processes and not threads, you can't use locks. That is not right, and it's worth fixing because it's a commonly probed point.

- **Windows:** named kernel synchronization objects work across processes: `CreateMutexW(NULL, FALSE, L"Local\\TouchLock")`, named semaphores, named events. Same naming mechanism as the section object.
- **POSIX:** named semaphores (`sem_open`), and **pthread mutexes placed inside the shared memory** with the `PTHREAD_PROCESS_SHARED` attribute. Under the hood these use futexes, which work on shared pages.
- **Atomics:** atomic operations on a location in shared memory work across processes, because atomicity is a property of the physical memory operation, not of the thread.

What *is* different from threads: you can't use an ordinary in-process lock object (like a `std::mutex` living on process A's heap), because process B can't see it. The lock must live in shared memory or be a named kernel object.

### 5.5 Your two-mailbox design, made correct

Your design — one region A writes and B reads, a second region B writes and A reads — is a real, good pattern: two **single-producer, single-consumer (SPSC)** channels. It can be lock-free, but only if:

- Each region has a **flag or sequence number** written *after* the data, with **release** semantics, and read *before* the data, with **acquire** semantics. Without memory ordering, the CPU or compiler may make the flag visible before the data.
- Flags and counters are **atomic** types.
- For more than one message in flight, use a **ring buffer** with a head index (written only by the producer) and a tail index (written only by the consumer).
- For waiting without spinning, pair it with a named event / semaphore so the consumer can sleep until signaled.

**Model answer:**

> "Each process has its own virtual address space, so the kernel has to map the same physical pages into both. On Windows, one process creates a named section object with `CreateFileMapping` and maps a view; the other opens it by the same name with `OpenFileMapping` and maps its own view. The name in the object manager namespace is how they agree. On Linux it's `shm_open` with a name plus `mmap MAP_SHARED`. The views may be at different virtual addresses, so I'd store offsets, not pointers. For synchronization, I'd use a named mutex or event, or a process-shared mutex inside the region — or, for one producer and one consumer, a lock-free ring buffer with atomic indices and acquire/release ordering."

---

## Part 6 — The Windows crash-debugging toolkit

Your answers drew on Linux (`dmesg`). The concepts carry over; for this team, speak Windows.

### 6.1 Bugchecks

When Windows detects a condition it can't safely continue from in kernel mode, it **bugchecks**: stops, shows a stop code, and writes a **crash dump**. Codes worth recognizing:

| Code | Name | Usual meaning |
|---|---|---|
| 0x0A / 0xD1 | IRQL_NOT_LESS_OR_EQUAL / DRIVER_IRQL_NOT_LESS_OR_EQUAL | Touched pageable or invalid memory at elevated IRQL |
| 0x133 | DPC_WATCHDOG_VIOLATION | ISR/DPC ran too long or system stuck at high IRQL |
| 0x9F | DRIVER_POWER_STATE_FAILURE | A driver didn't complete a power transition in time (sleep/resume bugs) |
| 0x50 | PAGE_FAULT_IN_NONPAGED_AREA | Bad pointer in kernel mode |
| 0x3B / 0x7E | SYSTEM_SERVICE_EXCEPTION / SYSTEM_THREAD_EXCEPTION_NOT_HANDLED | Exception in kernel code |
| 0xC4 | DRIVER_VERIFIER_DETECTED_VIOLATION | Driver Verifier caught a rule break |

### 6.2 Tools

- **WinDbg** — opens dumps or attaches live. Commands to know: `!analyze -v` (automated triage), `k` (stack), `lm` (loaded modules and versions), `!irql`, `!devnode`, `!devstack`, `!irp`, `!poaction` (power state).
- **Kernel debugging over the network (KDNET)** — attach WinDbg from a host machine to a target device. Standard in bring-up labs.
- **Driver Verifier** — makes the kernel strictly check a driver (IRQL rules, pool corruption, deadlocks), turning latent bugs into immediate, diagnosable bugchecks.
- **ETW + WPR/WPA** — traces with timelines for interrupts, DPCs, power, disk, CPU.
- **HLK** — the certification test suite; failures from HLK are a common source of bugs to root-cause.

### 6.3 Linux ↔ Windows translation table

| Linux | Windows |
|---|---|
| kernel panic / oops | bugcheck (stop code) |
| `dmesg`, `journalctl` | Event Viewer, ETW traces |
| kdump / vmcore | crash dump (`MEMORY.DMP`, minidump) |
| `crash`, gdb + kgdb | WinDbg, KDNET |
| device tree / ACPI | ACPI (on x64 and Windows-on-Arm laptops) |
| `/proc/interrupts` | ETW interrupt/DPC traces, `!idt` |
| KASAN, lockdep | Driver Verifier |
| `lsmod`, `modinfo` | `lm` in WinDbg, Device Manager, `driverquery` |

---

## Part 7 — Your story bank: telling your experience at mechanism depth

The interviewer cared about *how you reason*. The same experiences you already described become much stronger when told layer by layer, with root cause and prevention.

### Story 1: The Nvidia qualification script crash

What you said: a vendor-provided qualification script crashed; you ran the executable it called directly; it crashed because the driver wasn't the latest version.

Stronger version (fill in true specifics):

1. **Symptom:** Nvidia's qualification script failed on our platform. The script's output didn't say why.
2. **Isolation:** I separated the layers — the script was only an orchestrator, so I ran the underlying executable directly with the same arguments to remove the script from the picture. That reproduced the crash with a more specific error.
3. **Root cause:** the executable expected a newer driver interface than the installed driver provided — a version mismatch between user-mode tool and kernel driver.
4. **Verification:** updating the driver made the executable and then the full script pass. *(Say how you confirmed versions — which command or log.)*
5. **Prevention:** what you did or would do so it doesn't recur — a pre-flight check that verifies driver version before running the suite; pinning versions in the test environment.

Why it matters for this role: this is literally qualification-suite triage — reducing an orchestrated failure to a minimal reproduction and finding a version mismatch across the user/kernel boundary. Say that explicitly.

### Story 2: P/Invoke to pigpio for an I2C target event

What you have: user-mode managed code (C#/.NET) calling into a native library (pigpio) through P/Invoke to receive I2C target-mode events through the OS.

Tell it with the boundaries named:

- The **managed/native boundary** (P/Invoke marshaling: struct layout, calling convention, pointer lifetime, callbacks from native threads into managed code).
- The **user/kernel boundary** (how pigpio gets to hardware — its daemon, direct register access or kernel interfaces; be accurate about which).
- The **hardware**: the Pi acting as an I2C *target* (slave) — event delivery when the controller addresses it.
- Any bug you hit and how you found it (callback timing, missed events, marshaling bugs).

This shows you have operated across exactly the layers the role debugs.

### Story 3 (worth building): USB gadget mode on the Raspberry Pi

If you finish getting the Pi working as a USB gadget to your MacBook, that's a story about device-side USB drivers, configuration and enumeration — the same territory as "device doesn't enumerate on a new platform." Keep notes on what broke and how you found it.

### The telling template

For any debugging story: **symptom → how I narrowed the layer → evidence → root cause → fix → prevention.** Two minutes. Name the tools.

---

## Part 8 — What this interview tells you, and how to use your position

### 8.1 Reading the signals

- **"Your résumé is impressive."** Your résumé is getting you into the room for hardware-adjacent systems roles. The bottleneck is not getting interviews for these roles; it's converting them. That's good news: conversion is trainable.
- **No LeetCode, all scenario probing.** Platform, validation, driver and bring-up teams interview by depth-probing: they keep asking "and then what happens?" until you reach the limit of your understanding. You can't cram for that with problem lists; you prepare by knowing mechanisms.
- **The interviewer was happier when you went architectural.** Your general answers (collect logs, check for overflow) were reasonable but generic. Your specific answer (vendor driver, interrupt into the kernel, XY event) landed better. The lesson: **in systems interviews, specificity of mechanism is the signal.** Default to naming layers, objects and transitions.
- **Where you hit your edge:** Windows-specific internals (IRQL, driver stacks, named kernel objects), interprocess synchronization (the "no locks between processes" claim), and how the agreement on a shared region is established. These are well-bounded topics — exactly what this lecture covers.

### 8.2 Your unique position

You are an electrical engineer with years of engineering work, who has:

- Debugged a vendor qualification suite (validation work).
- Written user-mode software on an OS that talks to I2C hardware (the hardware/OS boundary).
- Reasoned instinctively about ISRs and interrupt priority.

Most software candidates for these roles are weak at the hardware end — signals, buses, timing, reading a schematic, using a logic analyzer. Many hardware candidates are weak at the OS end. **The boundary is where your value is.** The role families that pay for that boundary:

- **Windows platform reliability / validation / bring-up** (Microsoft, including the Surface devices org)
- **Driver test and validation engineering** at IHVs: Intel, AMD, Qualcomm (Windows on Arm laptops), Nvidia, Realtek, touch/sensor vendors
- **OEM platform engineering**: Dell, HP, Lenovo — BIOS/UEFI validation, platform debug, system integration
- **Embedded Linux / BSP engineering** and **silicon validation** roles, where the same skills apply on Linux

A positioning sentence for your applications and introductions:

> "Electrical engineer working at the hardware/software boundary — I debug why systems fail where hardware, drivers and the OS meet, from logic-analyzer traces up to the user-mode tools."

### 8.3 Prioritized study plan

Ordered by how directly each closes a gap shown in this interview:

1. **Windows kernel and driver fundamentals.** IRQL, ISRs/DPCs/work items, device stacks and IRPs, PnP and power (D-states, S-states, Modern Standby), KMDF basics. Reading: *Windows Internals, 7th ed., Part 1* (chapters on system architecture, processes, memory, I/O system); Microsoft's driver documentation on KMDF, SPB and HID-over-I2C.
2. **Operating systems core: virtual memory, IPC, synchronization.** Page tables, mapping, shared memory, process-shared synchronization, memory ordering. If you want one book: *Operating Systems: Three Easy Pieces* (free online) for memory and concurrency.
3. **Crash analysis hands-on.** Install WinDbg; in a Windows VM, use Sysinternals NotMyFault to cause deliberate bugchecks (IRQL violation, pool corruption, hang), then analyze the dumps with `!analyze -v`. Enable Driver Verifier on a sample driver and observe what it catches. This turns vocabulary into experience you can describe.
4. **A small driver project.** Write a KMDF sample driver (Microsoft's samples repo) and debug it with a kernel debugger attached. Or, on the Pi, write a Linux kernel driver for an I2C sensor with an interrupt line, and reproduce the edge-vs-level and bus-hang failure modes on purpose with a logic analyzer watching. Either produces a résumé line *and* interview stories at exactly the right depth.
5. **Story bank rehearsal.** Write out Stories 1 and 2 using the template in Part 7, out loud, in two minutes each.

### 8.4 How to answer scenario questions: a template

When asked "how would you debug X":

1. **Clarify the symptom** (time-based? recoverable? one unit or all?).
2. **Draw the path** the event takes, layer by layer.
3. **Hypothesize per layer**, each with its signature.
4. **Name the evidence and tools** that confirm or kill each hypothesis.
5. **Prioritize** — cheapest, most discriminating check first.
6. **Prevention** — what test or check would catch this class of bug next time (this team builds validation infrastructure; they love this step).

### 8.5 Where LeetCode fits now

Keep it, but rebalance by target. A previous Microsoft loop asked you to design a rate limiter; this one asked none. For platform/validation/driver roles, depth in systems is the larger lever. For general software roles, LeetCode remains the gate. A reasonable split while you pursue both: systems depth as the main thread, LeetCode as maintenance.

### 8.6 Immediate follow-ups

- Send a short thank-you note to the interviewer/recruiter mentioning one thing you learned about the team (the hardware validation infrastructure is a good hook).
- Ask the recruiter for feedback whatever the outcome; validation teams often have multiple openings, and a near miss can turn into a referral to a sibling team.
- While the interview is fresh, write down any question you haven't captured here.

---

## Self-check (retrieval practice)

Answer these without looking:

1. A device holds its interrupt line low until the host reads it. What goes wrong if the host is configured for edge-triggered interrupts, and what does the user see?
2. Why can't an ISR perform an I2C read? Give two separate reasons.
3. Walk a touch from the finger to the application on a Windows laptop, naming each layer.
4. Two processes need to share a 4 KB buffer on Windows. Which kernel object, which calls, and how do they agree on which buffer?
5. Name two ways two processes can synchronize access to shared memory.
6. A touchscreen dies after exactly 49.7 days of uptime. What's your top hypothesis and why that number?
7. Give the Windows counterparts of `dmesg`, a kernel panic, and kgdb.
