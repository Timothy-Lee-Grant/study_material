2026_10_16_19_00-(From-Bare-Metal-To-An-OS)

# Lecture 003 — From Bare Metal to an OS: The Components, the Interrupt Path, and the Rules the OS Adds

> **For:** Timothy
> **Date:** 2026-10-16
> **Prerequisites:** `lectures/firmware/windows_platform_validation.md` (the interview lecture), especially Part 2 (the touch path) and Part 3 (IRQL). Helpful but not required: `lectures/firmware/002-when_root_isnt_enough.md` (your pigpio I2C target project).
> **Why this lecture:** after reading the interview lecture you said three things. First, you have only met interrupts on bare metal (your ATmega), where an ISR felt like "a callback function", and IRQL looked like a different world. Second, there were too many components you couldn't place: what each one is, where it lives, who puts it there, whether it is a separate process, and how they talk. Third, specific phrases didn't land: "touching pageable memory", the bugcheck codes, "the driver registers its interrupt as passive and the framework runs its handler". You also asked how interrupt *lines* are actually wired, how this relates to "interrupts are flags" from school, and how Linux compares. This lecture answers each of those, in that order: components first, then interrupts from the wire up, then the rules an operating system adds.

---

## Core ideas (the answer key)

1. **There are three places code runs on a laptop:** inside other chips (the touch controller runs its own firmware on its own little processor), on the main CPU in **kernel mode** (the Windows kernel and kernel drivers), and on the main CPU in **user mode** (processes such as apps).
2. **A kernel driver is not a process.** It is a module of functions loaded into the kernel's single shared address space. Its code runs when something calls it: the I/O manager, a framework, or the interrupt machinery.
3. **Components talk through four channels:** electrical signals on wires, registers the CPU reads and writes, function calls and request objects between software layers, and interrupts.
4. **At the hardware level an interrupt request really is a flag:** a pending bit, plus an enable bit, plus a global permission. Your ATmega works exactly this way. An operating system keeps that mechanism and adds layers on top.
5. **Edge-triggered means the flag is latched on a transition. Level-triggered means there is no latch: the request is the live state of the wire.** A level line keeps requesting until the device's condition is cleared.
6. **Devices do not each get a wire to the CPU, and they do not all share one.** Lines go into an **interrupt controller** (APIC on x86, GIC on Arm) that turns each input into a **vector number**. Lines can be shared, PCIe devices use messages instead of wires (MSI), and a GPIO controller acts as a second-tier interrupt controller for its pins.
7. **IRQL is not a line. It is a per-processor priority threshold in software.** Code running at an IRQL blocks interrupts at that level and below on that processor. The thread scheduler itself runs at DISPATCH_LEVEL, which is why code at DISPATCH_LEVEL or above can never wait.
8. **A framework (KMDF) is a library that calls your driver's functions.** The driver registers callbacks, including its interrupt handler, by filling in a configuration structure and calling a framework function. The kernel connects the handler to the interrupt using resources the firmware described in ACPI.
9. **Pageable memory is memory the memory manager may move to disk.** Touching it may cause a page fault, and resolving a page fault is a wait. So kernel code at DISPATCH_LEVEL or above must only touch nonpaged memory. If it doesn't, the kernel's page-fault handler checks the IRQL, finds the rule broken, and stops the machine (bugcheck 0xA or 0xD1).
10. **Linux has the same hardware and the same problems under different names.** It has no numeric IRQL; it has "atomic context" vs "process context". Its kernel memory is never paged, so the Linux rule is "never sleep in atomic context". Its threaded interrupt with IRQF_ONESHOT is the equivalent of the Windows passive-level ISR.

---

## Table of Contents

- [0. Direct answers to your questions](#0-direct-answers-to-your-questions)
- [1. The map: where code runs](#1-the-map-where-code-runs)
- [2. The components, one at a time](#2-the-components-one-at-a-time)
- [3. How the components talk](#3-how-the-components-talk)
- [4. Interrupts from the wire up](#4-interrupts-from-the-wire-up)
- [5. What an operating system adds, and IRQL](#5-what-an-operating-system-adds-and-irql)
- [6. How a driver registers its interrupt (the framework question)](#6-how-a-driver-registers-its-interrupt-the-framework-question)
- [7. Pageable memory, page faults, and bugchecks](#7-pageable-memory-page-faults-and-bugchecks)
- [8. Linux: same problems, different names](#8-linux-same-problems-different-names)
- [9. Misconceptions: you thought X, reality Y](#9-misconceptions-you-thought-x-reality-y)
- [10. Interview relevance](#10-interview-relevance)
- [11. Self-check questions](#11-self-check-questions)
- [Sources](#sources)

Depth tags: 🟢 **OWN IT** (know it cold) · 🔵 **CONTRACT** (know what it does and who calls it) · ⚫ **BLACK BOX** (know it exists; stop digging for now).

---

## 0. Direct answers to your questions

1. **"I thought of an ISR as a callback function."** That's correct, and it's worth keeping. The detail that matters is *who calls it*: the hardware does, between two instructions of whatever was running. On your ATmega nothing else competes, so "callback" is the whole story. An OS adds three things that turn it into a rule system: threads with a scheduler, many drivers from different authors sharing one CPU, and virtual memory. IRQL is how Windows enforces those rules. §4–5.
2. **"Interrupts were flags in school."** Also correct, at the hardware level. An interrupt request is a pending bit plus an enable bit plus a global permission bit. Edge-triggered requests latch that flag; level-triggered requests don't latch anything, so the wire *is* the request. §4.1–4.2.
3. **"Does every device get its own line, share one line, or does each level have a line?"** None of the three. Lines go into an interrupt controller that maps each input to a vector number. Some lines are shared, PCIe devices send messages instead of using wires, and GPIO pins are funneled through a GPIO controller. Levels (IRQL) are a priority class derived from the vector number, not wires. §4.3–4.5.
4. **"Who is the touch controller, the GPIO controller driver, where do they live, are they processes?"** The touch controller is a separate chip running its own firmware. The GPIO controller is a hardware block inside the main chip; its driver is a kernel module, **not** a process. There's a card per component in §2, and the communication channels are in §3.
5. **"What is touching pageable memory, and is the kernel verifying a separate process?"** Pageable memory is memory that may currently be on disk. The check is not done on a separate process. It's the kernel's own page-fault handler, finding that kernel code (a driver) broke the IRQL rule, and stopping the whole system on purpose. §7.
6. **"Who is 'the framework', and how does a driver register its interrupt? Was it the table?"** The framework is KMDF, a Microsoft library loaded into the kernel. The driver fills in a configuration structure naming its handler and calls `WdfInterruptCreate`. The "table" you remember is probably one of three different tables, and §4.5 separates them: ACPI tables (describe the hardware), the interrupt controller's routing table, and the CPU's interrupt descriptor table. Registration is covered in §6.
7. **"Linux?"** Same hardware mechanisms, same problems, different vocabulary and one big difference: Linux never pages kernel memory. There's a translation table in §8.

---

## 1. The map: where code runs

Before the components, the one picture everything hangs on. **Code runs in three places**, plus one more at boot:

```
 ┌──────────────────────────── the laptop ─────────────────────────────┐
 │                                                                      │
 │  OTHER CHIPS (each has its own processor + firmware)                 │
 │    touch controller IC · keyboard controller · SSD controller · ...  │
 │        │  wires: I2C (SDA, SCL), interrupt line (ATTN), reset        │
 │        ▼                                                             │
 │  MAIN CHIP (SoC / CPU + chipset)                                     │
 │    hardware blocks: I2C controller · GPIO controller ·               │
 │                     interrupt controller (APIC / GIC) · CPU cores    │
 │                                                                      │
 │    CPU cores run software in two modes:                              │
 │    ┌───────────────── USER MODE ──────────────────┐                  │
 │    │ processes: apps, services, UMDF driver hosts │  each has its    │
 │    └──────────────────────────────────────────────┘  own memory      │
 │    ┌──────────────── KERNEL MODE ─────────────────┐                  │
 │    │ ONE shared address space:                    │                  │
 │    │ kernel + HAL + managers + ALL kernel drivers │                  │
 │    └──────────────────────────────────────────────┘                  │
 │                                                                      │
 │  BOOT ONLY: UEFI firmware (from the board's SPI flash), which also   │
 │  hands Windows the ACPI tables that describe the hardware            │
 └──────────────────────────────────────────────────────────────────────┘
```

Three facts to own from this picture 🟢:

- **Kernel mode is one room.** Every kernel driver, from every vendor, shares the same memory with the kernel. There are no walls between them. This one fact explains why a driver bug crashes the whole machine (§7.5).
- **User mode is many rooms.** Each process has its own private memory. A bug kills only that process.
- **The touch controller is not in either room.** It is a separate computer on the same board, and it talks to the main chip only through wires.

---

## 2. The components, one at a time

Every card uses the same fields, so you can compare them:
**What it is · Where it physically is · Where its code runs · Who writes it · How it gets onto the device · Who it talks to, and how.**

### 2.1 Touch sensor and touch controller (with its firmware) 🔵

- **What it is.** The *sensor* is a grid of transparent electrodes on the glass. It has no logic. The *touch controller* is a small mixed-signal chip that drives the grid, measures capacitance at each crossing, and turns the measurements into contacts: "finger 1 at X, Y; finger 2 lifted".
- **Where it physically is.** On the display's flex cable or a small board next to the panel, connected to the motherboard by a cable.
- **Where its code runs.** On the touch controller's own processor (typically a small microcontroller core inside the chip), from its own flash. Its firmware scans the sensor in a loop, filters noise, tracks fingers, and keeps a report ready. It never runs on the laptop's CPU.
- **Who writes it.** The touch-controller vendor writes the firmware; the OEM (Dell, HP, Surface, …) supplies tuning for its particular panel.
- **How it gets on the device.** It's programmed at the factory. Updates come from a vendor tool or an update package the OEM ships, sometimes through Windows Update.
- **Who it talks to, and how.**
  - **I2C, as a target (slave).** The host reads reports from it and writes commands to it. This is the same role your Pi played in the pigpio project, from the other side.
  - **An interrupt output line** (HID calls it ATTN) that it pulls to "asserted" while it has a report waiting.
  - **A reset input and power rails** controlled by the host.

The connection you asked about: yes, this chip is a microcontroller running bare-metal-style firmware, like code you have written. It is an I2C target that raises a line to say "read me". The difference from your ATmega is only who is on the other end of the wire: a whole operating system.

### 2.2 The I2C bus and the I2C controller 🔵

- **What it is.** The *bus* is two wires, SDA (data) and SCL (clock), shared by several devices, each with an address. The *I2C controller* is a hardware block that runs the bus protocol (start, address, read/write bits, ACK/NACK, stop) so the CPU doesn't have to wiggle the pins itself.
- **Where it physically is.** Inside the main chip (SoC or chipset). A laptop has several of them.
- **Where its code runs.** The controller is hardware. **Its driver** runs on the CPU in kernel mode.
- **Who writes the driver.** The chip vendor (Intel, AMD, Qualcomm), building on Microsoft's **SpbCx** framework extension (SPB means Simple Peripheral Bus: I2C, SPI and UART).
- **How it gets on the device.** In a driver package (an INF file, the `.sys` file, and a signature catalog), delivered in the OEM's factory image or through Windows Update.
- **Who it talks to, and how.**
  - The CPU reads and writes the controller's **registers**, and the controller raises **its own interrupt** to report progress (a byte sent, the FIFO needing service, the transfer finished).
  - Other drivers send it **I/O requests** ("read 30 bytes from address 0x2C").

### 2.3 The GPIO controller 🔵

- **What it is.** A hardware block managing many general-purpose pins (often hundreds, grouped in banks). For each pin it can set direction, read or drive the level, and **detect interrupts** (edge or level, either polarity) with per-pin enable, mask and status bits.
- **Where it physically is.** Inside the main chip. The touch controller's interrupt line is wired to one of its pins.
- **Where its code runs.** Hardware, plus a kernel-mode driver on the CPU.
- **Who writes the driver.** The chip vendor, on Microsoft's **GpioClx** framework extension. The vendor writes only the "talk to my registers" callbacks (mask pin 35, read the status register). GpioClx (Microsoft's code) does the rest.
- **How it gets on the device.** In a driver package, the same way as the I2C controller driver.
- **Who it talks to, and how.**
  - **Upward to the interrupt controller:** typically one interrupt line for the whole controller or for a bank of pins. That makes it a **second-tier interrupt controller** (§4.4).
  - **To other drivers:** I/O requests to read or write pins.
- **Is it a separate process?** No (§2.8). It is a kernel module whose functions run when they're called: at start-up, when another driver asks for pin I/O, and when the GPIO controller's interrupt fires.

### 2.4 The interrupt controller 🔵

- **What it is.** The hardware funnel between devices and CPU cores. On x86 there's a **Local APIC** in every core plus one or more **I/O APICs** with input pins. On Arm (including Windows on Arm laptops) it's the **GIC**, the Generic Interrupt Controller.
- **Where it physically is.** In the main chip.
- **Where its code runs.** It's hardware, programmed by the kernel's **HAL** (Hardware Abstraction Layer, Microsoft's code that hides interrupt-controller and timer differences).
- **Who it talks to.** Devices raise its inputs (or write messages to it). It signals a specific CPU core with a vector number (§4.3).

### 2.5 The CPU cores 🟢

They run the instruction stream. Between instructions each core checks whether an interrupt is pending and allowed. If one is, it saves where it was and jumps through the **interrupt descriptor table** (§4.5) to a handler. That's the same check your ATmega makes, done per core.

### 2.6 UEFI firmware and the ACPI tables 🔵

- **What it is.** The boot firmware that initializes the board, and the **ACPI tables** it hands to Windows. Those tables describe hardware that can't be discovered by probing. For the touch device the entry says: "I am a HID-over-I2C device (compatible ID `PNP0C50`); I'm at address 0x2C on I2C controller 1 at 400 kHz; my interrupt is GPIO pin 35 on GPIO controller 0, level-triggered, active-low; here is how to power me on and off."
- **Where it is.** Stored in an SPI flash chip on the motherboard. It runs before Windows. The tables stay in memory for Windows to read.
- **Who writes it.** The OEM, with a firmware vendor (AMI, Insyde, Phoenix) and the chip vendor's reference code.
- **Why it matters for your interview role.** A wrong ACPI entry (wrong pin, edge instead of level, wrong polarity) is a classic bring-up bug, and it's the OEM's to fix, not Windows'.

### 2.7 The Windows kernel's managers 🔵

All of these are Microsoft code, in kernel mode:

| Part | Its job, in one line |
|---|---|
| **Kernel (scheduler, interrupt dispatch, DPCs, synchronization)** | Decides which thread runs, dispatches interrupts to handlers, runs deferred work |
| **HAL** | Programs the interrupt controller and timers; hides platform differences |
| **I/O manager** | Delivers I/O requests (IRPs) to drivers and returns results |
| **Plug and Play (PnP) manager** | Builds the device tree, matches drivers to devices, loads them, assigns resources |
| **Power manager** | Moves devices between power states (D0 = on … D3 = off) and the system in and out of sleep |
| **Memory manager** | Virtual memory, page tables, paging to and from disk (§7) |
| **ACPI driver (`acpi.sys`)** | Reads the ACPI tables and reports the devices they describe to PnP |

### 2.8 Drivers and frameworks: what a driver actually is 🟢

This answers "is it a separate process or integrated?"

- A **kernel-mode driver** is a `.sys` file: a module with an entry function (`DriverEntry`) and a set of functions that other kernel code calls. Once loaded it lives in the shared kernel address space. **It has no thread of its own and no process.** Its code runs in three situations:
  - When the I/O manager or a framework calls it to handle a request.
  - When an interrupt arrives (its ISR).
  - When it asks the system to run something later (a DPC or a work item).
- **One exception to know:** **UMDF** drivers (User-Mode Driver Framework) are DLLs loaded into a host process (`WUDFHost.exe`). A crash there kills only the host process, not the machine. That's why simple devices are pushed toward user mode.
- A **framework** is a Microsoft library loaded into the kernel that implements the hard, repetitive rules (PnP, power, request queues, interrupt connection) and **calls the driver's callbacks**. This is the same "the framework calls my code" idea you know from .NET (inversion of control).
  - **KMDF** (Kernel-Mode Driver Framework, file `Wdf01000.sys`) is the general one.
  - **SpbCx** (for bus controllers), **GpioClx** (for GPIO controllers) and **HID class** (`hidclass.sys`) are specialized frameworks layered on that idea.

The drivers in the touch path:

| Driver | Who writes it | What it does |
|---|---|---|
| `hidi2c.sys` (inbox) | Microsoft | Speaks the HID-over-I2C protocol: on interrupt, reads the input report over I2C |
| `hidclass.sys` (inbox) | Microsoft | Parses HID reports into usages (X, Y, tip switch, contact ID) and exposes them upward |
| I2C controller driver | Chip vendor, on SpbCx | Runs I2C transfers on the controller hardware |
| GPIO controller driver | Chip vendor, on GpioClx | Masks, unmasks and clears pins; reads the status registers |
| Input stack (in `win32k` and related components) | Microsoft | Turns contacts into pointer messages for applications |

### 2.9 How each piece gets onto the device: one table

| Component | Lives in | Written by | Installed by |
|---|---|---|---|
| Touch controller firmware | Touch IC's flash | Touch IC vendor (+ OEM tuning) | Factory; vendor update tool or package |
| UEFI + ACPI tables | Motherboard SPI flash | OEM + firmware vendor + chip vendor | Factory; firmware update ("capsule") |
| I2C / GPIO controller drivers | `C:\Windows\System32\drivers` | Chip vendor | OEM image or Windows Update (driver package, signed) |
| `hidi2c.sys`, `hidclass.sys`, KMDF, SpbCx, GpioClx | Same folder | Microsoft | Part of Windows ("inbox") |
| Kernel, HAL, managers | `ntoskrnl.exe` and related | Microsoft | Part of Windows |

How Windows picks a driver 🔵: every device reports IDs (the ACPI entry gives `PNP0C50` for HID-over-I2C). Each driver package's **INF file** lists the IDs it supports. The PnP manager matches IDs to INFs and loads the winner. `hidi2c.inf` claims `ACPI\PNP0C50`, which is how a touchscreen that has never seen this laptop "just works".

---

## 3. How the components talk

Every interaction in the system uses one of four channels 🟢:

| Channel | Between | Example in the touch path |
|---|---|---|
| **1. Electrical signals on wires** | Chip ↔ chip | Touch controller pulls ATTN low; SDA/SCL carry the I2C transfer |
| **2. Registers** (memory-mapped I/O: the CPU reads/writes an address that is really a hardware block) | Driver ↔ its hardware | GPIO driver writes "mask pin 35"; I2C driver loads the transfer length |
| **3. Function calls and request objects** (IRPs, WDF requests, callbacks) | Software ↔ software | `hidi2c` sends "read report" to the I2C controller driver; the framework calls `hidi2c`'s ISR |
| **4. Interrupts** | Hardware → software | GPIO controller signals the interrupt controller, which signals a CPU core |

### 3.1 A correction to the interview lecture's diagram

`windows_platform_validation.md` §2.2 drew one vertical stack with the I2C controller driver and GPIO controller driver *underneath* `hidi2c`. That was simplified in a way that could mislead you about ownership, so here is the accurate version.

- **The touch device has its own device stack:** `acpi.sys` at the bottom (the bus driver that reported it), and `hidclass.sys` plus `hidi2c.sys` above it.
- **The I2C controller and the GPIO controller are separate devices with their own stacks.** They are not below `hidi2c`.
- **`hidi2c` uses them as resources.** When it starts, the PnP manager hands it two resources from the ACPI entry: an **I2C connection ID** and a **GPIO interrupt**.
  - `hidi2c` opens the connection ID through a small Windows component called the **Resource Hub**, and gets back a target it can send read and write requests to. Those requests go to the I2C controller driver's stack.
  - The interrupt resource reaches `hidi2c` as an ordinary interrupt (§6). GpioClx and the HAL route the pin to it.

So the honest picture is three stacks side by side, joined by requests and by interrupt routing. Ownership questions ("whose bug is it?") follow these lines.

---

## 4. Interrupts from the wire up

### 4.1 An interrupt request is a flag: start from your ATmega 🟢

Your school memory is right. Here is the mechanism on the ATmega328P, because it's small enough to see whole. Three bits decide whether an interrupt happens:

1. **The flag.** The peripheral sets a bit when its event occurs. For external interrupt 0 that's `INTF0` in the register `EIFR`.
2. **The enable.** You set a bit to say "I care about this event" (`INT0` in `EIMSK`).
3. **The global permission.** One bit in the status register (`I` in `SREG`) allows or blocks all interrupts.

Between instructions, the CPU checks: *is there a flag whose enable is set, while the global permission is set?* If yes, this sequence runs, in hardware:

1. It finishes the current instruction.
2. It pushes the return address on the stack.
3. It **clears the global permission bit**, so no other interrupt can nest by default.
4. It jumps to the address stored in that interrupt's slot of the **vector table**, a fixed list of handler addresses at the start of flash.
5. For many sources, it clears the flag as it enters the handler.

Your ISR runs. Its last instruction, `RETI`, returns and sets the global permission bit again. If two flags are pending at once, the one with the lower vector address wins. That fixed order is the AVR's entire priority system.

So **"callback"** is right: it's a function the hardware calls. **"Flag"** is also right: the request is a stored bit.

### 4.2 Edge vs level, stated in terms of flags 🟢

On the ATmega you choose INT0's sense with two bits in `EICRA` (`ISC01:ISC00`):

| ISC01:ISC00 | Meaning |
|---|---|
| 00 | **Low level** requests an interrupt |
| 01 | Any change |
| 10 | Falling edge |
| 11 | Rising edge |

- **Edge-triggered:** a detector watches the pin, and **on a transition it sets the flag**. The flag is a memory: it stays set even if the pin goes back, until it's cleared. One transition → one request.
- **Level-triggered:** **there is no latch.** The datasheet says the INT0 flag is always cleared when INT0 is set to level mode. The request *is* the live pin. While the pin is low, the CPU sees a request, so after `RETI` the ISR runs again, and again, for as long as the pin stays low.

Name the two quantities and the difference becomes one sentence (pattern T16):

- `request(edge)` = "a transition happened since the flag was last cleared".
- `request(level)` = "the line is asserted right now".

**Pause and predict:** on your ATmega, set INT0 to low-level and wire a button that holds the pin low. You press and hold for one second. How many times does the ISR run?

<details><summary>Answer</summary>
Continuously, back to back, for the whole second. The main loop barely advances, because between each `RETI` and the next entry it gets one instruction at most. This is an <b>interrupt storm</b>, the same failure the interview lecture described for a level-triggered touch line whose ISR returns without clearing the device's condition. The fix is the same in both worlds: the handler must make the source stop asserting, or mask the request.
</details>

Why level exists at all: it's **impossible to miss**. If the host was busy, the request is still there when it looks. Why edge exists: it never storms, and it suits signals that are naturally "something happened". The interview lecture's "dead until hard reset" bug is the mismatch of the two: a device that holds its line (level behavior) described to the host as edge. One missed transition leaves the line low forever, and the host waits for a transition that can't come.

### 4.3 How lines reach the CPU: the interrupt controller 🔵

Your question: does each device get its own wire, does everyone share one, or is there a wire per level? On a PC it's none of those. There is a funnel:

```
 device lines ──► I/O APIC input pins ──► (routing table entry per pin) ──► message to a core's Local APIC ──► CPU core
                                         vector number, target core,
                                         edge/level, polarity, mask
```

- An **I/O APIC** has a set of input pins (24 is typical). Each pin has an entry in a **redirection (routing) table**, which the kernel's HAL programs. The entry says:
  - which **vector number** (0–255) to deliver,
  - to which core,
  - whether the pin is edge or level, and which polarity,
  - whether the pin is masked.
- The core's **Local APIC** receives the vector, decides whether it's allowed right now (§5.2), and if so interrupts the core.

On Arm, the GIC does the same job with its own names: shared peripheral interrupts go to any core, private ones belong to one core.

### 4.4 Sharing, messages, and second-tier controllers 🔵

So, are lines shared? Sometimes. There are three variations to know:

1. **Shared lines.** Several devices can be wired to one input. Sharing only works with **level** triggering, because then each device holds the line until it's serviced, and nothing is lost.
   - When the interrupt fires, the kernel calls each ISR registered on that line in turn.
   - Each ISR reads *its own device's* status register and returns **TRUE** ("that was mine, I handled it") or **FALSE** ("not mine").
   - That's why ISRs on Windows (and on Linux, as `IRQ_HANDLED` / `IRQ_NONE`) return a value. Your ATmega's ISRs return nothing, because each vector belongs to exactly one source.
2. **No wire at all: MSI (Message-Signaled Interrupts).** PCIe devices (GPUs, SSDs, network cards) interrupt by **writing a small value to a special memory address**. The interrupt controller treats that write as a request for a particular vector. Each device can get its own vector (or many: MSI-X allows up to 2048 per device), so there's no sharing and no wire to get stuck.
3. **Second-tier controllers: the GPIO controller.** A GPIO controller has many pins but usually one line up to the main interrupt controller. Microsoft calls this two-stage handling:
   - **Primary interrupt.** A touch controller asserts pin 35 → the GPIO controller raises its single line → the **primary** ISR runs. This is GpioClx's ISR, which uses the vendor driver's callbacks to read the status registers and find which pin fired.
   - **Secondary interrupt.** GpioClx maps the pin to a system-wide interrupt number (a GSI, Global System Interrupt) and passes it to the HAL. The HAL then raises a **secondary** interrupt that runs the ISR of the driver that owns pin 35, here `hidi2c`.

So the full answer: some devices have dedicated inputs, some share an input, some send messages instead, and many small devices hang off GPIO pins behind a second-tier controller.

### 4.5 The three tables (this is probably the "table" you remember) 🔵

Three different tables appear in this story. They're easy to blur, so here they are side by side:

| Table | Where it lives | Who fills it | What it maps |
|---|---|---|---|
| **ACPI tables** | Firmware → memory | OEM firmware | Describe the hardware: "touch device, I2C address 0x2C, GPIO pin 35, level, active-low" |
| **I/O APIC redirection table** (GIC configuration on Arm) | Interrupt controller registers | HAL (kernel) | Input pin → vector number, target core, trigger mode, polarity, mask |
| **IDT (Interrupt Descriptor Table)** | Memory, one per core; the CPU's IDTR register points to it | Kernel | Vector number → handler address. It's the ATmega vector table's equivalent, but in RAM and filled at boot |

A detail that connects later sections: IDT entries 0–31 are reserved for **CPU exceptions**, events the CPU itself raises. Vector 14 is the **page fault** (§7). Hardware interrupts and CPU exceptions use the same table. Whenever the CPU is diverted, it looks up its new destination here.

A driver never writes these tables directly. It asks the kernel to connect its handler (§6), and the kernel links the vector the interrupt controller delivers to a kernel **interrupt object** that records the driver's ISR.

---

## 5. What an operating system adds, and IRQL

### 5.1 Three things your ATmega doesn't have 🟢

| Added by the OS | Why it creates a rule |
|---|---|
| **Threads and a scheduler** | Code can *wait*: "pause me until the I2C transfer completes, and run someone else meanwhile." Waiting needs the scheduler to be able to run. |
| **Many drivers from many vendors on one CPU** | One driver's handler must not stall everyone else's. Priorities must be enforced, not agreed on. |
| **Virtual memory with paging** | Some memory may be on disk right now. Reaching it means waiting for the disk (§7). |

On the ATmega there's one global permission bit and a single programmer. Windows replaces the bit with a **number**.

### 5.2 IRQL: a per-processor threshold 🟢

Every processor, at every moment, has a current **IRQL** (Interrupt Request Level). Its meaning, stated once:

> **A processor at IRQL `n` does not accept interrupts whose level is `n` or lower. It accepts only interrupts above `n`.**

What each symbol stands for:

- `n`: the processor's current IRQL, a small integer.
- *An interrupt's level*: on x64 it comes straight from its vector number. The upper four bits of the vector (`vector ÷ 16`, rounded down) are its priority class, and Windows uses that class as the interrupt's IRQL.
- *Where `n` is stored*: on x64, in the CPU's `CR8` register, which programs the Local APIC's task-priority threshold. Raising IRQL means writing a bigger number there.

So IRQL is **not a wire**. It's a threshold the kernel sets in each processor, and the hardware enforces it against each interrupt's priority class. Your ATmega's `I` bit is the special case with only two values: "everything blocked" or "nothing blocked".

The levels you'll meet (x64):

| IRQL | Name | What runs here |
|---|---|---|
| 0 | **PASSIVE_LEVEL** | Normal threads: all user code, and most driver code |
| 1 | **APC_LEVEL** | Asynchronous procedure calls (⚫ for now: small routines that must run in a specific thread, e.g. finishing an I/O into that thread's buffer) |
| 2 | **DISPATCH_LEVEL** | **The scheduler ("dispatcher")** and DPCs (deferred procedure calls); also any code holding a spin lock |
| 3 – ~12 | **DIRQL** (device IRQL) | Device ISRs, each at its own interrupt's level |
| top few (13–15) | CLOCK, IPI, HIGH | Clock tick, inter-processor interrupts, "block everything" |

### 5.3 Why code at DISPATCH_LEVEL or above can never wait: a derivation 🟢

Each step is one move:

1. To **wait** means: "mark my thread as blocked, and let the scheduler run another thread until my event happens."
2. The scheduler is code. It runs at **DISPATCH_LEVEL**. That's where the level's name comes from.
3. A processor at IRQL `n` does not run anything at level `n` or lower (§5.2).
4. So a processor sitting at DISPATCH_LEVEL or above **cannot run the scheduler**.
5. So a wait there can never hand the processor to anyone. Nothing that would end the wait can run on that processor.
6. So waiting at DISPATCH_LEVEL or above is a guaranteed deadlock. Windows treats it as a fatal bug instead of hanging forever.

You've already seen step 5 on bare metal. The Arduino `Wire` library on an ATmega runs I2C transfers **using the TWI peripheral's own interrupt**: a read sets up the transfer, then loops until the TWI ISR marks it done. Call `Wire` from inside another ISR, where the global permission bit is cleared, and the TWI ISR can never run, so the loop never ends. It's the same deadlock as step 5 with two levels instead of sixteen, and it's the core of the interview question "an ISR does an I2C read; what happens?"

### 5.4 The pattern: do the minimum high, do the rest low 🟢

| Stage | Runs at | Must do | May not |
|---|---|---|---|
| **ISR** | DIRQL | Confirm it's ours; make the device stop asserting (or mask it); note what happened; queue a DPC | Wait, touch pageable memory, take long |
| **DPC** | DISPATCH_LEVEL | Short follow-up that doesn't wait; queue a work item if waiting is needed | Wait, touch pageable memory |
| **Work item / thread** | PASSIVE_LEVEL | Anything slow: I2C transfers, file I/O, allocation from pageable memory | — |

### 5.5 Passive-level ISRs: why a touch driver needs one 🔵

There's a problem the table can't solve on its own. For a memory-mapped device, the ISR can stop the device from asserting by writing one of its registers directly. The touch controller's registers are **across an I2C bus**. Silencing it *requires an I2C read*, which waits, which the ISR can't do. Meanwhile the line is level-triggered, so returning without silencing it causes a storm.

Since Windows 8, KMDF and UMDF drivers whose interrupt comes through a GPIO pin can ask for a **passive-level ISR**. Microsoft's documented sequence for a **level-triggered** pin:

1. The interrupt fires. The kernel's trap handler, working through GpioClx, **masks pin 35 at the GPIO controller** (a register write, which is fine at high IRQL).
2. It schedules the driver's ISR to run in a **passive-level kernel thread**.
3. The driver's ISR runs at PASSIVE_LEVEL, so it can do the I2C read. Reading the report makes the touch controller deassert the line.
4. When the ISR returns, the kernel thread **unmasks pin 35**.

For an **edge-triggered** pin, step 1 *clears* the latched request instead of masking, because the flag already holds the event. Because the pin stays masked until the ISR returns, Microsoft advises the ISR to do only the initial servicing and push the rest to a lower-priority worker.

Name the quantity and the rule falls out (T16). Call the thing that must be true before unmasking `line_deasserted`. Unmasking is only safe when `line_deasserted` is true. Only the I2C read makes it true. So the read must finish before the unmask, and the read must run at passive level. That's the whole design.

---

## 6. How a driver registers its interrupt (the framework question)

You asked who "the framework" is and how the driver registers. Here's the whole sequence from boot. Every step is someone calling someone 🔵:

1. **Firmware → Windows.** UEFI hands over the ACPI tables. `acpi.sys` reads the touch entry and reports a device with ID `ACPI\PNP0C50` to the PnP manager.
2. **PnP manager → driver package.** It matches the ID against INF files, finds `hidi2c.inf`, and loads `hidi2c.sys` into the kernel. (Loading is like loading a DLL: map the file, fix up addresses, link it to KMDF.)
3. **Kernel → `DriverEntry`.** The driver's entry function runs once. A KMDF driver calls `WdfDriverCreate` here and hands the framework a configuration naming its **`EvtDriverDeviceAdd`** callback.
4. **Framework → `EvtDriverDeviceAdd`.** Called once for each matching device. Here the driver creates its device object and **declares its interrupt**:

```c
WDF_INTERRUPT_CONFIG cfg;
WDF_INTERRUPT_CONFIG_INIT(&cfg, MyEvtInterruptIsr, NULL);  // which function is my ISR
cfg.PassiveHandling = TRUE;                                 // run it at PASSIVE_LEVEL (§5.5)
WdfInterruptCreate(device, &cfg, WDF_NO_OBJECT_ATTRIBUTES, &interrupt);
```

   What each name stands for:
   - `WDF_INTERRUPT_CONFIG`: a structure that describes the interrupt to the framework.
   - `MyEvtInterruptIsr`: **the driver's own function**, which the framework will call.
   - `PassiveHandling`: the request for passive-level handling.
   - `WdfInterruptCreate`: the framework function that records all of this.

   **Nothing is connected yet.** The driver has only said what it wants.
5. **PnP manager → resources.** When it starts the device, it turns the ACPI entry into **resources** for this device: "your interrupt is GPIO pin 35, level, active-low" and "your I2C connection ID is …". The framework passes them to the driver's `EvtDevicePrepareHardware` callback.
6. **Framework → kernel: connect.** As the device powers up, the framework asks the kernel to **connect** the interrupt. The kernel creates an **interrupt object** that ties the interrupt (here a GPIO secondary interrupt) to the driver's ISR, its IRQL and its options. This is the step that makes the IDT path from §4.5 lead to the driver's code.
7. **At interrupt time, in reverse:**
   1. Pin 35 asserts.
   2. The GPIO controller raises its line.
   3. GpioClx's primary ISR finds the pin and hands its number to the HAL.
   4. Because this interrupt is passive, the pin is masked and a kernel thread calls `MyEvtInterruptIsr` at PASSIVE_LEVEL.
   5. The driver reads the report over I2C.
   6. The pin is unmasked.
   7. The report is handed up to `hidclass`.

Who calls whom, in one line: **firmware describes → PnP matches and loads → the driver declares its handler to the framework → the framework connects it through the kernel → the hardware triggers it.** The driver never touches an interrupt table. It fills in a form and calls a function.

---

## 7. Pageable memory, page faults, and bugchecks

### 7.1 Virtual memory in four sentences 🟢

1. Code uses **virtual addresses**. The CPU translates each one to a **physical address** using **page tables**, in units of **pages** (4 KB on x64).
2. Each process has its own page tables. Kernel mode has one shared set: the room from §1.
3. A page-table entry can say **"not present"**: the page isn't in RAM right now. Its contents were written to the **page file** on disk to free RAM for something else.
4. Touching a not-present page makes the **CPU** raise a **page fault**: exception vector 14, delivered through the same IDT as interrupts (§4.5).

### 7.2 What the page-fault handler does 🔵

The kernel's memory manager handles the fault:

1. It finds where the page's contents are (in the page file).
2. It allocates a physical page, starts a disk read into it, **waits for the read**, updates the page table, and resumes the faulting instruction as if nothing happened.

Step 2 contains a **wait**, and §5.3 says a wait is only possible below DISPATCH_LEVEL.

### 7.3 "Pageable" vs "nonpaged" 🟢

- **Pageable memory:** the memory manager *is allowed to* move it to disk. Examples: the paged pool (driver allocations marked paged), driver code placed in a pageable section, and all user-mode memory.
- **Nonpaged memory:** guaranteed to stay in RAM. Examples: the nonpaged pool, and most driver code by default.

A driver chooses at allocation time (pool flags such as `POOL_FLAG_PAGED` vs `POOL_FLAG_NON_PAGED`). Drivers mark pageable functions so they don't hold RAM when idle. Microsoft's `PAGED_CODE()` macro, placed at the top of such a function, asserts in debug builds that it's being called below DISPATCH_LEVEL.

### 7.4 "Touching pageable memory at high IRQL", derived 🟢

1. Driver code runs at DISPATCH_LEVEL or above (an ISR, a DPC, or while holding a spin lock).
2. It reads a variable in pageable memory. Usually the page is in RAM and nothing happens.
3. Sometimes, under memory pressure, the page is on disk. The CPU raises a page fault.
4. The page-fault handler would have to wait for the disk, which is impossible at this IRQL (§5.3).
5. The handler **checks the current IRQL**, sees it's too high, and calls `KeBugCheckEx`, the kernel's deliberate "stop the system" function, with code **0xA `IRQL_NOT_LESS_OR_EQUAL`**. Or, when the faulting code is in a driver, **0xD1 `DRIVER_IRQL_NOT_LESS_OR_EQUAL`**.
   - The name reads as the rule that was broken: the IRQL should have been *less than or equal to* the highest level at which paging is allowed (APC_LEVEL).
   - The four parameters on the blue screen are: the address touched, the IRQL at the time, whether it was a read, write or execute, and the address of the instruction that did it.

Your guess, that "the kernel verifies something to see if it's allowed", was half right. It is the kernel checking a rule. **But no separate process is involved:** the code that broke the rule is kernel code (a driver), running inside the kernel's own room, and the kernel catches it in the act through its own page-fault handler. The same two codes also appear when a driver uses a garbage pointer at high IRQL, because a garbage address faults the same way.

### 7.5 Why the whole machine stops 🟢

When a **user process** touches invalid memory, the kernel kills that process ("access violation") and everything else carries on. That's possible because the process lives in its own room.

When **kernel code** breaks a rule, there is no wall to put between the bug and the rest. That driver shares memory with the file system, the network stack and every other driver. Continuing might write corrupted data to disk. So the kernel stops everything on purpose and writes a **crash dump**, a snapshot of memory for WinDbg. A **bugcheck** (the blue screen) is the kernel's self-check firing, not "the computer crashing" at random.

### 7.6 Why this bug hides, and how Driver Verifier finds it 🔵

In step 3 the page is usually in RAM, so the bug passes every test on a developer's machine with plenty of memory, then crashes customers' machines under memory pressure. **Driver Verifier** (built into Windows) makes it deterministic. With *Force IRQL checking* on, whenever the driver raises IRQL to DISPATCH_LEVEL or above, or takes a spin lock, Verifier pages out its pageable code and data first. The first illegal touch then faults every time. In your interview role this is a standard tool: turn a "1-in-1,000-units" crash into a reproducible one.

---

## 8. Linux: same problems, different names

The hardware underneath is identical: the same APIC or GIC, the same GPIO controllers, the same HID-over-I2C touch chips. Both kernels face the same three problems from §5.1. They solve them with different vocabulary, and with one real difference.

### 8.1 Translation table 🔵

| Concept | Windows | Linux |
|---|---|---|
| Hardware description | ACPI tables | ACPI on x86 laptops; **device tree** on most Arm boards (your Raspberry Pi) |
| Driver module | `.sys`, loaded by PnP via INF match | `.ko` kernel module, matched by `compatible` string or ACPI ID |
| Not a process | Kernel drivers share the kernel address space | Same |
| Priority model | **IRQL**: a number per CPU | **Contexts:** hard-IRQ, softirq, process context. Interrupts and preemption are disabled or enabled instead of using a numeric level |
| "Can't wait here" | IRQL ≥ DISPATCH_LEVEL | **Atomic context**: interrupt handlers, softirqs, code holding a spinlock, preemption disabled |
| Register an ISR | `WdfInterruptCreate` (KMDF) / `IoConnectInterruptEx` (WDM) | `request_irq(irq, handler, flags, name, dev)` |
| Shared-line return value | ISR returns TRUE / FALSE | Handler returns `IRQ_HANDLED` / `IRQ_NONE` |
| Deferred work | DPC → work item | "Bottom halves": softirq / tasklet → **workqueue** (process context, may sleep) |
| Passive-level ISR | `PassiveHandling = TRUE` on a GPIO interrupt | **Threaded IRQ**: `request_threaded_irq(...)` with `IRQF_ONESHOT`, which keeps the line masked until the thread handler finishes. The `i2c-hid` driver uses exactly this |
| GPIO as second-tier controller | GpioClx primary → HAL secondary | gpiolib **irqchip** (chained or nested handlers) |
| Bus framework | SpbCx | The I2C core (`i2c_adapter` / `i2c_client`) |
| HID over I2C | `hidi2c.sys` + `hidclass.sys` | `i2c-hid` + the HID core (`hid-multitouch` for touchscreens) |
| Fatal kernel error | Bugcheck (stop code) + crash dump | Oops (may continue, "tainted") or panic + kdump |
| Interrupt counts | ETW traces, WinDbg `!idt` | `/proc/interrupts`: counts per IRQ per CPU, readable in one command |

### 8.2 The real difference: Linux never pages kernel memory 🔵

On Linux, kernel memory (`kmalloc`, `vmalloc`, module code) is **never swapped to disk**. So "touching pageable memory at high IRQL" doesn't exist as a category. The rule collapses into one: **never sleep in atomic context.**

What breaks it:
- taking a mutex,
- `kmalloc(..., GFP_KERNEL)`, which may sleep (atomic context must use `GFP_ATOMIC`),
- `copy_from_user`, because *user* memory can be swapped out, so touching it can fault and sleep. That's the one place the Windows rule reappears.

With `CONFIG_DEBUG_ATOMIC_SLEEP` enabled, Linux prints **"BUG: sleeping function called from invalid context"**. The scheduler reports **"BUG: scheduling while atomic"** when sleeping actually happens. Those two messages are Linux's 0xD1.

Both kernels solve one problem: waiting requires the scheduler, and the scheduler can't run from inside high-priority code. Windows writes the rule as a number (IRQL). Linux writes it as a context (atomic vs process).

### 8.3 Which to study first

For the Microsoft role, Windows vocabulary first: IRQL, DPC, work item, KMDF, bugcheck, Driver Verifier, WinDbg. For hands-on practice, Linux on your Pi is cheaper and more visible: you can watch `/proc/interrupts` climb, write a 50-line module with `request_threaded_irq`, and put a logic analyzer on the line. The concepts transfer one-to-one through the table above. That makes it a good lab even for a Windows role, as long as you say the Windows names in the interview.

---

## 9. Misconceptions: you thought X, reality Y

| You thought | Reality | Why it matters |
|---|---|---|
| An ISR is a callback | It is, called by the hardware between instructions, under rules the OS adds (IRQL) | Interviewers probe the rules, not the callback |
| Interrupts are flags | At the hardware level, yes for edge (a latched bit); for level, the live wire is the request | Explains storms and "dead until reset" |
| Each device has its own line, or all share one, or there's one line per level | Interrupt controllers map inputs to vectors; lines can be shared (level only); PCIe uses messages; GPIO pins go through a second-tier controller; levels are not wires | Lets you reason about where an interrupt can get lost |
| IRQL is something about the interrupt line | It's a per-CPU threshold in software (in CR8 on x64) compared against each interrupt's priority class | The "can't wait" rule follows from it |
| Drivers might be separate processes | Kernel drivers are modules in one shared kernel address space with no threads of their own; only UMDF drivers live in a host process | Explains why one driver bug stops the whole machine |
| The GPIO and I2C drivers sit under `hidi2c` in one stack | They're separate device stacks; `hidi2c` uses them as resources through requests and interrupt routing | Ownership: whose bug is it? |
| A bugcheck is the kernel checking a separate process | It's the kernel's own handler catching kernel-mode code breaking a rule, then stopping on purpose | Knowing who checks tells you what the dump will show |
| Linux works the same way, with IRQL | Same problems and hardware, but contexts instead of IRQL, and no pageable kernel memory | Translate vocabulary in interviews |

---

## 10. Interview relevance

Sentences you can say, each at mechanism depth:

- "An interrupt request is a pending bit. Level-triggered lines don't latch, so they keep requesting until the device is serviced. That's why a level device described as edge in ACPI can go dead until reset."
- "IRQL is a per-processor threshold. The scheduler runs at DISPATCH_LEVEL, so anything at DISPATCH or above can't wait. That's why the I2C read moves to passive level."
- "For a GPIO interrupt from an I2C device, KMDF's passive-level ISR masks the pin, runs the ISR in a kernel thread at PASSIVE_LEVEL so it can read the device over I2C, and unmasks after it returns."
- "0xD1 means kernel-mode code touched pageable or invalid memory at DISPATCH_LEVEL or above. The page-fault handler can't wait for the disk there, so the kernel bugchecks. I'd turn on Driver Verifier's IRQL checking to make it reproducible."
- "The touch path is three device stacks: the HID touch stack, the I2C controller and the GPIO controller. `hidi2c` reaches the bus through an SPB connection ID and gets its interrupt routed by GpioClx and the HAL."
- Linux translation, if asked: "On Linux that's a threaded IRQ with IRQF_ONESHOT, and the rule is 'don't sleep in atomic context'."

---

## 11. Self-check questions

1. Name the three places code runs on a laptop, and put the touch controller firmware, `hidi2c.sys`, and a web browser in the right place.
<details><summary>Answer</summary>Other chips (touch firmware), the CPU in kernel mode (<code>hidi2c.sys</code>), the CPU in user mode (the browser, a process). UEFI also runs at boot.</details>

2. Is the GPIO controller driver a process? When does its code run?
<details><summary>Answer</summary>No. It's a kernel module in the shared kernel address space with no thread of its own. Its code runs when it's called: at start-up, when another driver requests pin I/O, and when GpioClx's primary ISR calls its callbacks to read, mask or clear pins.</details>

3. On your ATmega, what three bits must line up for INT0 to fire, and what does the hardware do on entry?
<details><summary>Answer</summary>The flag (<code>INTF0</code>, or the live pin in level mode), the enable (<code>INT0</code> in <code>EIMSK</code>), and the global <code>I</code> bit. On entry the hardware finishes the instruction, pushes the return address, clears <code>I</code>, jumps through the vector table, and clears the flag. <code>RETI</code> sets <code>I</code> again.</details>

4. Define edge- and level-triggered in terms of a flag.
<details><summary>Answer</summary>Edge: a transition sets a latched flag that stays set until cleared. Level: no latch; the request is the live state of the line.</details>

5. Why can only level-triggered lines be shared safely?
<details><summary>Answer</summary>Each device holds the line until it is serviced, so if two devices assert at once, the line stays asserted until both have been handled. With edges, the second device's transition can be lost while the line is already active.</details>

6. What is MSI, and why does it remove the sharing problem?
<details><summary>Answer</summary>Message-Signaled Interrupts: a PCIe device interrupts by writing a value to a special address. Each device (or each queue of a device) gets its own vector, so no wire is shared and none can get stuck.</details>

7. Name the three tables and what each maps.
<details><summary>Answer</summary>ACPI tables: a hardware description (address, pin, trigger). I/O APIC redirection table: input pin → vector, core, trigger, polarity, mask. IDT: vector → handler address.</details>

8. Derive, in steps, why code at DISPATCH_LEVEL can't wait.
<details><summary>Answer</summary>Waiting = let the scheduler run another thread. The scheduler runs at DISPATCH_LEVEL. A CPU at IRQL n doesn't run code at level ≤ n. So at ≥ DISPATCH the scheduler can't run, the wait can never be satisfied, and it's a deadlock. Windows treats it as fatal.</details>

9. Walk through a passive-level ISR for a level-triggered GPIO interrupt.
<details><summary>Answer</summary>The interrupt fires → the pin is masked at the GPIO controller → the driver's ISR is scheduled in a kernel thread at PASSIVE_LEVEL → the ISR reads the device over I2C, which makes it deassert → the ISR returns → the pin is unmasked.</details>

10. How does a KMDF driver register its interrupt, and when does it actually get connected?
<details><summary>Answer</summary>In <code>EvtDriverDeviceAdd</code> it fills <code>WDF_INTERRUPT_CONFIG</code> (its ISR function, <code>PassiveHandling</code>) and calls <code>WdfInterruptCreate</code>. The PnP manager later assigns the resources from ACPI, and the framework has the kernel connect an interrupt object when the device starts.</details>

11. What is "pageable memory", and who raises a page fault?
<details><summary>Answer</summary>Memory the memory manager may move to the page file on disk. The CPU raises the page fault (vector 14) when a not-present page is touched. The kernel's memory manager handles it.</details>

12. Explain bugcheck 0xD1 from cause to blue screen.
<details><summary>Answer</summary>A driver at DISPATCH_LEVEL or above touches pageable memory that's on disk (or an invalid address) → page fault → the handler can't wait at that IRQL → it checks the IRQL and calls <code>KeBugCheckEx(0xD1, address, IRQL, read/write, instruction)</code> → the system stops and writes a dump.</details>

13. Why does a kernel driver bug stop the whole machine, when a user-mode bug doesn't?
<details><summary>Answer</summary>Kernel drivers share one address space with the kernel and every other driver. There's no wall to isolate the damage, so the kernel stops everything to avoid corrupting data. A user process has its own address space and can be killed alone.</details>

14. What's the Linux name for the Windows "can't wait at ≥ DISPATCH_LEVEL" rule, and what's the equivalent of a passive-level ISR?
<details><summary>Answer</summary>"Never sleep in atomic context". The equivalent is a threaded IRQ registered with <code>request_threaded_irq</code> and <code>IRQF_ONESHOT</code>.</details>

15. Why doesn't Linux have a "touched pageable memory at high IRQL" bug class for kernel data?
<details><summary>Answer</summary>Linux never pages kernel memory out. The leftover case is user memory (<code>copy_from_user</code>), which can fault and sleep, so it's forbidden in atomic context.</details>

---

## Sources

Checked 2026-10-16.

- Microsoft Learn: *Passive-level ISRs* (GPIO), the documented mask → passive thread → unmask sequence for level- and edge-triggered pins. https://learn.microsoft.com/windows-hardware/drivers/gpio/passive-level-isrs
- Microsoft Learn: *GPIO interrupts*, primary/secondary interrupts, GpioClx ISR → GSI → HAL; passive-level ISR registration since Windows 8; shared GPIO lines are typically level-triggered. https://learn.microsoft.com/windows-hardware/drivers/gpio/gpio-interrupts
- Microsoft Learn: *Supporting passive-level interrupts* (WDF). https://learn.microsoft.com/windows-hardware/drivers/wdf/supporting-passive-level-interrupts
- Microsoft Learn: *WDF_INTERRUPT_CONFIG structure*. https://learn.microsoft.com/windows-hardware/drivers/ddi/wdfinterrupt/ns-wdfinterrupt-_wdf_interrupt_config
- Microsoft Learn: *Interrupts from SPB-connected peripheral devices*. https://learn.microsoft.com/windows-hardware/drivers/spb/interrupts-from-spb-connected-peripheral-devices
- Microsoft Learn: *Touchscreen device bus connectivity*: HID I2C devices should use level-triggered interrupts; the line goes to an on-SoC GPIO controller or an IOAPIC. https://learn.microsoft.com/windows-hardware/design/component-guidelines/touchscreen-device-bus-connectivity
- Microsoft Learn: Bug check 0xA / 0xD1 reference pages, and Driver Verifier *Force IRQL checking*.
- Microchip ATmega328P datasheet: External Interrupts (EICRA ISC bits; INTF0 is always cleared in level mode), Reset and Interrupt Handling (I bit, vector priority, RETI).
- *Windows Internals, 7th ed., Part 1*: IRQL on x64 (CR8, vector priority classes), interrupt dispatching, memory management.
- Linux kernel documentation: `request_threaded_irq` / `IRQF_ONESHOT`, the `i2c-hid` driver, `might_sleep()` / CONFIG_DEBUG_ATOMIC_SLEEP.

Not verified here: the internal implementation of `hidi2c.sys` (whether it uses `PassiveHandling` itself or an equivalent path). The documented GPIO passive-level mechanism above is what Microsoft describes for SPB-connected peripherals in general.
