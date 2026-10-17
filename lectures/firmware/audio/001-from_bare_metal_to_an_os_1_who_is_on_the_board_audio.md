# From Bare Metal to an OS, Part 1: Who Is on the Board, and How They Talk (audio lecture)

This is part one of a three-part series. Part one covers the components in a Windows laptop's touchscreen path: what each one is, where it physically sits, where its code runs, who writes it, and how the components talk to each other. Part two follows an interrupt from a wire all the way to a driver's handler, and explains the priority levels Windows calls IRQL. Part three covers memory, pageable memory, why a kernel bug produces a blue screen, and how all of this compares with Linux.

## Why this series exists

Timothy just interviewed with Microsoft for a Windows reliability and validation role. Its daily work is debugging crashes and hangs on new laptops, where hardware, firmware, drivers and Windows meet. Afterwards he read a lecture about the interview and noticed something honest about himself. His experience with interrupts is on bare metal: code on an ATmega microcontroller (said "A-T-mega"), with no operating system. There, an interrupt service routine felt like a callback function. The lecture talked about interrupt request levels, frameworks, device stacks and pageable memory, and a lot of names appeared at once that he couldn't place. He asked a precise question: for each of these pieces, what is it, where does it live, who puts it there, is it a separate process, and how do the pieces actually communicate?

That's the right question to start with, because the interviewer's touchscreen question was really a question about placement. If you can put every piece in the right place, you can reason about which one is stuck. By the end of this episode, Timothy should be able to name every component in the touch path, say where its code runs, and say which of four communication channels connects any two of them.

## The core ideas

Here are today's core ideas, stated plainly. They're the answer key for the walk questions at the end.

One. Code on a laptop runs in three places: inside other chips, on the main processor in kernel mode, and on the main processor in user mode. A fourth kind, the boot firmware, runs before Windows starts.

Two. Kernel mode is one shared room. The Windows kernel and every kernel driver, from every vendor, share the same memory. User mode is many separate rooms, one per process.

Three. A kernel driver is not a process. It's a module of functions loaded into that shared room, with no thread of its own. Its code runs only when something calls it.

Four. The touch controller is a separate small computer. It runs its own firmware on its own processor, and it's an I2C target that pulls a wire low to say "read me."

Five. Components talk through exactly four channels: electrical signals on wires, hardware registers the processor reads and writes, function calls and request objects between software layers, and interrupts.

Six. The firmware's ACPI tables tell Windows what hardware exists and how it's wired. Windows matches each device to a driver, and the driver is handed its wires as resources.

## Section one: three places code runs

Picture the laptop's main board. On it sits the main chip, which contains the processor cores plus a collection of hardware blocks. Around it sit other chips: the touch controller, the keyboard controller, the solid-state drive's controller, and so on.

Here's the first important fact. Many of those other chips are computers in their own right. Each has a small processor and its own firmware, which never runs on the laptop's main processor. That's the first place code runs.

The second and third places are both on the main processor, which runs in two modes. In user mode run processes: the browser, the settings app, background services. Each process gets its own private memory, its own room, and if it misbehaves, Windows can kill that one process and everything else keeps going. In kernel mode run the Windows kernel and all the kernel drivers. Kernel mode is one room, with no walls inside it. The kernel, the file system, the network stack, the graphics driver, the touch driver: all of them share one address space. Keep that picture of one room in mind. In part three it explains why a single driver bug stops the whole computer.

And there's a fourth kind of code, which only runs at boot: the UEFI firmware, stored in a flash chip on the motherboard. Before Windows starts, it initializes the board and leaves Windows a set of description tables, called ACPI tables (said "A-C-P-I"). More on those soon.

Pause here and predict. Where does the code that turns finger positions into coordinates run: on the main processor or somewhere else?

The answer is somewhere else. It runs on the touch controller chip.

## Section two: the components, one at a time

Let's walk the touch path from the glass inward. For each component, ask the same questions: what is it, where is it, where does its code run, who writes it, and who does it talk to.

First, the touch sensor. It's a grid of transparent electrodes on the glass. It has no logic at all.

Second, the touch controller. This is a small chip on the display's cable or a small board beside the panel. It drives the electrode grid, measures the tiny changes in capacitance where a finger is, filters out noise, tracks each finger, and builds a report: finger one at this X and Y, finger two just lifted. All of that runs as firmware on the touch controller's own little processor, from its own flash memory. The chip vendor writes the firmware, and the laptop maker tunes it for its panel. It's programmed at the factory and occasionally updated by a package the laptop maker ships. The touch controller talks to the rest of the laptop through wires only. Two wires, called S-D-A and S-C-L, carry the I2C bus (said "I-squared-C"), where the touch controller plays the target role: the main chip reads reports from it and writes commands to it. A third wire is the interrupt line, which the HID specification calls ATTN, for attention. The touch controller pulls it to its asserted state whenever it has a report waiting, and holds it there until the report is read.

Timothy will recognize this role. In his pigpio project his Raspberry Pi acted as an I2C target. The touch controller is the same kind of device: an I2C target, running bare-metal-style firmware, with a line that says "read me." The only difference is what sits at the other end of the wire: a whole operating system.

Third, the I2C controller. This is a hardware block inside the main chip that speaks the bus protocol (start, address, read or write, acknowledge, stop), so the processor doesn't have to toggle pins by hand. A laptop has several. The block is hardware. Its driver is software, running on the main processor in kernel mode, written by the chip vendor (Intel, AMD or Qualcomm) on top of a Microsoft framework called S-P-B-C-X, where S-P-B stands for Simple Peripheral Bus. One detail matters for part two: the I2C controller has its own interrupt, which it uses to report that a byte went out or a transfer finished.

Fourth, the GPIO controller (said "G-P-I-O", for general-purpose input and output). This hardware block in the main chip manages a large number of pins, often hundreds, grouped into banks. For each pin it can read the level, drive the level, and detect interrupts, with a per-pin enable bit, mask bit and status bit. The touch controller's interrupt line is wired to one of these pins, say pin thirty-five. Its driver is again written by the chip vendor, on a Microsoft framework called GPIO-C-L-X. The vendor writes only the small functions that touch its own registers, like "mask pin thirty-five" or "read the status register", and Microsoft's framework does the rest. The GPIO controller usually has just one interrupt wire going upward for many pins. Part two explains why that makes it a second-tier interrupt controller.

Fifth, the main interrupt controller. On Intel and AMD machines it's called the APIC (said "A-pick"); on Arm machines, the GIC (said "gick"). It's the hardware funnel between devices and processor cores. Microsoft's Hardware Abstraction Layer, the HAL, programs it.

Sixth, the boot firmware and its ACPI tables. These are written by the laptop maker together with a firmware vendor and the chip vendor. For the touchscreen, the ACPI entry says, in effect: "I am a HID-over-I2C device. I'm at address hex two-C on I2C controller one, at four hundred kilohertz. My interrupt is pin thirty-five on GPIO controller zero, level-triggered, active low. And here is how to power me on and off." Windows can't discover any of that by probing. It believes the table. If the table is wrong, say the wrong pin, or edge instead of level, the device either never works or works for a while and then dies. A wrong table is the laptop maker's bug, not Windows', and finding exactly that is the daily work of the team Timothy interviewed with.

Seventh, the parts of the Windows kernel itself, all written by Microsoft. The scheduler decides which thread runs. The Plug and Play manager builds the list of devices, picks drivers and loads them. The I/O manager carries requests between drivers. The power manager turns devices on and off. The memory manager runs virtual memory. And the ACPI driver reads the firmware's tables and reports the devices it finds.

Eighth, the drivers in the touch device's own path. One is H-I-D-I-2-C, which speaks the HID-over-I2C protocol: when the interrupt fires, it reads the report over I2C. Above it is the HID class driver, which turns raw reports into meaningful fields: X, Y, whether the finger is touching, which contact it is. Microsoft writes both, and both ship inside Windows. Above them, Windows' input system turns contacts into pointer messages that applications receive.

## Section three: is a driver a process?

This was Timothy's sharpest question, and the answer is no. A kernel driver is a file ending in dot-S-Y-S, holding a set of functions. When Windows loads it, it's mapped into the shared kernel room, a bit like loading a library. It has an entry function that runs once, and then it waits to be called. It has no thread of its own and no process. Its code runs in exactly three situations: when the I/O manager or a framework calls it to handle a request, when its interrupt fires, or when it earlier asked Windows to run something for it later.

So when someone says "the GPIO controller driver handles that," picture a set of functions sitting in the kernel room, called by whoever needs them at that moment. Its code might run on any processor, inside whichever thread happened to be interrupted.

There's one exception worth knowing. Windows also has user-mode drivers, built with the User-Mode Driver Framework, U-M-D-F. Those are loaded into a small host process. If one crashes, only the host process dies, which is exactly why Microsoft encourages simple devices to use it.

The word "framework" deserves a sentence of its own, because it puzzled Timothy. A framework here is a Microsoft library loaded into the kernel that implements the hard, repetitive rules every driver must follow, and calls the driver's own functions at the right moments. The main one is the Kernel-Mode Driver Framework, K-M-D-F. The S-P-B and GPIO frameworks from earlier are specialized versions of the same idea. It's the same "the framework calls my code" pattern Timothy already knows from ASP.NET (said "A-S-P dot net"). The driver says, "here are my functions," and the framework decides when to call them.

## Section four: how drivers get onto the laptop

How does a touchscreen that has never met this laptop just work? Every device reports identifying names. The ACPI entry for the touchscreen gives a compatible name, P-N-P-zero-C-fifty, which means "HID over I2C." Every driver package comes with a small text file, an I-N-F file, that lists the names it supports. The Plug and Play manager matches device names to I-N-F files and loads the matching driver. Microsoft's HID-over-I2C driver claims P-N-P-zero-C-fifty, so any compliant touchscreen gets it automatically.

Drivers arrive on a laptop in three ways. Some are built into Windows, "inbox" drivers like the HID ones. Some are in the laptop maker's factory image. Some are delivered later through Windows Update. Chip vendors' drivers, like the I2C and GPIO controller drivers, usually come in the factory image and through Windows Update. Kernel drivers must be signed by Microsoft before Windows will load them.

## Section five: the four channels

Now the question of how everything talks. Every interaction in this whole system uses one of four channels.

The first channel is electrical signals on wires, between chips: the touch controller pulling its interrupt line low, and the clock and data wires carrying the I2C transfer.

The second channel is registers. A register is a location the processor reads or writes that's actually a control point inside a hardware block, arranged so it looks like a memory address. When the GPIO driver masks pin thirty-five, it writes a bit in the GPIO controller's mask register. When the I2C driver starts a transfer, it writes the address and length into the I2C controller's registers. This is the channel between a driver and its own hardware.

The third channel is function calls and request objects, between pieces of software. The framework calls the driver's interrupt handler. The touch driver sends a request, "read thirty bytes from the device at hex two-C", which the I/O manager delivers to the I2C controller's driver. The request object has a name you'll hear in interviews: an I-R-P, for I/O request packet.

The fourth channel is interrupts, from hardware to software: the GPIO controller signaling the interrupt controller, which signals a processor core.

Pause and predict. When the touch driver wants to read the report, which channels does that request travel through, in order?

Here's the answer. It starts as a function call and request (channel three), from the touch driver to the I2C controller driver. That driver writes registers (channel two). The I2C controller then wiggles the wires (channel one). And as the transfer progresses, the I2C controller raises its own interrupts (channel four), which tell its driver the transfer is done, and the result travels back up as a completed request (channel three again).

## Section six: a correction worth making

The earlier interview lecture drew the touch path as one tall stack, with the I2C and GPIO controller drivers underneath the touch driver. That was a simplification, and it could mislead you about ownership, so here is the accurate version.

There are three separate device stacks side by side. The touch device's stack has the ACPI driver at the bottom, then the HID class driver and the HID-over-I2C driver. The I2C controller has its own stack. The GPIO controller has its own stack. When Windows starts the touch device, it hands the touch driver two resources from the ACPI entry: an I2C connection number and a GPIO interrupt. The touch driver turns the connection number into a channel to the I2C controller's driver, through a small Windows component called the Resource Hub. The interrupt is routed to it through the GPIO framework and the HAL, which part two covers. So the stacks are joined by requests and by interrupt routing, not by stacking. When you ask "whose bug is it?", these lines tell you where to look.

## Connections

This connects to three things Timothy already knows. His pigpio project was the touch controller's role, from the device side. His understanding of inversion of control from ASP.NET is exactly how driver frameworks work. And the interview's touchscreen question is now a placement exercise: a stuck interrupt line belongs to the wires and the GPIO controller; a hung bus belongs to the I2C controller; a wrong trigger type belongs to the ACPI table; a driver that stopped reading belongs to the touch device's stack.

## Recap

Let's restate the core ideas in slightly different words. Code runs in other chips, in the shared kernel room, in private user-mode rooms, and in boot firmware before Windows starts. A kernel driver is a set of functions in the shared room, called by others, never a process of its own. The exception is user-mode drivers, which live in a host process. The touch controller is its own small computer, an I2C target with a "read me" line. The ACPI tables describe how everything is wired, and Windows trusts them. And every interaction travels on wires, through registers, through calls and requests, or through interrupts.

## Walk questions

Here are three questions to answer out loud on the next walk.

First: walk the touch path from the glass to an application, and for each component say where its code runs and who wrote it.

Second: is the GPIO controller driver a process? If not, what is it, and in what three situations does its code run?

Third: the touch driver needs one report from the touch controller. Name the four channels, and say which ones that single read uses, in order.
