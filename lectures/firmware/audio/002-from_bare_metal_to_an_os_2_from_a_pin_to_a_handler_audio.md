# From Bare Metal to an OS, Part 2: From a Pin to a Handler, and What IRQL Really Is (audio lecture)

This is part two of a three-part series. Part one placed every component in a Windows laptop's touchscreen path. Part two follows a single interrupt from the touch controller's wire all the way to the driver's handler. On the way it explains what an interrupt request physically is, how edge and level triggering differ, how wires actually reach the processor, what the priority levels called IRQL are, why some code may never wait, and how a driver registers its handler with the framework.

## Why this matters to Timothy

In his Microsoft interview, Timothy was asked what happens when an interrupt service routine tries to read an I2C device (said "I-squared-C"). His instinct was right: get out of the routine quickly and set a flag. The interviewer was pushing for the mechanism underneath. Afterwards Timothy said that his experience with interrupts is on an ATmega microcontroller, where a routine felt like a callback, and that in school interrupts were described as flags. He wondered how that relates to a full operating system. He also asked whether every device has its own interrupt wire, whether they all share one, or whether there's a wire for each priority level. By the end of this episode he should be able to answer all of that from his ATmega upward, in one connected story.

## The core ideas

Here are today's core ideas. They're the answer key for the walk questions at the end.

One. At the hardware level an interrupt request really is a flag. Three things must line up: a pending bit, an enable bit, and a global permission. Your ATmega works exactly this way.

Two. Edge-triggered means a transition sets a latched flag that stays set until it's cleared. Level-triggered means there's no latch at all: the request is the live state of the wire, so it keeps requesting until the device is serviced.

Three. Devices don't each get a wire to the processor, and they don't all share one. Wires go into an interrupt controller that turns each input into a vector number. Level-triggered wires can be shared, PCIe devices send messages instead of using wires, and a GPIO controller acts as a second-tier interrupt controller for its pins.

Four. IRQL is not a wire. It's a priority threshold that each processor holds in software, and the processor accepts only interrupts above it.

Five. The scheduler itself runs at the level called DISPATCH. So code at DISPATCH or above can never wait, because waiting needs the scheduler.

Six. A driver registers its handler by filling in a configuration form and calling a framework function. The connection to the actual interrupt is made later, by the kernel, using the wiring the firmware described.

## Section one: the flag, on your ATmega

Let's start where Timothy has stood. On the ATmega three-twenty-eight-P, an external interrupt involves three bits.

The first bit is the flag. When the event happens, the hardware sets a bit in a register called E-I-F-R. For external interrupt zero, that bit is called INT-F-zero.

The second bit is the enable. Timothy sets a bit to say "I care about this event."

The third bit is the global permission, the "I" bit in the status register, which allows or blocks all interrupts at once.

Between every two instructions, the processor checks whether any flag is set whose enable is set, while the global permission is on. If so, the hardware does a fixed sequence. It finishes the current instruction. It pushes the return address on the stack. It clears the global permission bit, so nothing else interrupts the handler. It jumps to the address stored in that interrupt's slot of the vector table, a fixed list of handler addresses at the start of flash. And for many sources it clears the flag on the way in. The handler's last instruction, R-E-T-I, return from interrupt, comes back and sets the global permission bit again. If two flags are waiting at once, the one with the lower slot in the vector table goes first. That's the ATmega's whole priority system.

So Timothy's two memories are both right. It's a callback, a function the hardware calls between instructions. And it's a flag, a stored bit. An operating system doesn't replace this. It builds on top of it.

## Section two: edge versus level, as flags

On the ATmega you choose how external interrupt zero is sensed, with two bits. One setting is "low level", one is "any change", one is "falling edge", and one is "rising edge."

In edge mode, a detector watches the pin, and on a transition it sets the flag. The flag is a memory. It stays set even if the pin goes back, until it's cleared. One transition, one request.

In level mode there's no latch. The datasheet says the flag is always cleared while the pin is in level mode. The request simply is the pin. While the pin is low, the processor sees a request. So when the handler returns, if the pin is still low, the handler runs again immediately.

Pause and predict. You set the ATmega to low-level mode and hold a button that keeps the pin low for one full second. How many times does the handler run?

The answer is continuously, back to back, for the whole second. The main loop barely moves. That's called an interrupt storm. It's exactly the failure the interview lecture described: a level-triggered touch line whose handler returns without making the device let go of the line.

Why have level triggering at all, then? Because it's impossible to miss. If the processor was busy, the request is still there when it looks. Edge triggering never storms, but it can be missed, and a missed edge is gone forever. That's the shape of the "touchscreen dead until hard reset" bug: a device that holds its line low until it's read, described to Windows as edge-triggered. One missed transition leaves the line low forever, and Windows waits for a transition that can never come, because the line is already low.

## Section three: how wires actually reach the processor

Timothy's question: does each device have its own wire to the processor, do they share one, or is there a wire per level? On a laptop it's none of those. There's a funnel.

On Intel and AMD machines the funnel is called the APIC (said "A-pick"). Its input side, the I/O APIC, has a set of input pins, often twenty-four. For each pin there's an entry in a routing table, which the kernel programs at boot. The entry says which vector number to deliver for this pin, a number from zero to two hundred fifty-five, which processor core to send it to, whether the pin is edge- or level-triggered, which polarity counts as asserted, and whether the pin is masked. Each core has its own local APIC that receives the vector and decides whether to interrupt the core right now. On Arm machines the same job is done by the GIC (said "gick").

There are three variations. First, shared wires. Several devices can be wired to one input, and this only works safely with level triggering, because each device holds the line until it's serviced, so nothing gets lost. When a shared interrupt fires, the kernel calls each driver's handler registered on that line, one after another. Each handler reads its own device's status register and answers "yes, that was mine" or "no, not mine." That's why interrupt handlers on Windows and Linux return a value, while Timothy's ATmega handlers return nothing: on the ATmega, each slot belongs to one source.

Second, no wire at all. Modern PCI Express devices, like graphics cards and solid-state drives, interrupt by writing a small value to a special memory address. This is called a message-signaled interrupt, M-S-I. The interrupt controller treats the write as a request for a particular vector. Each device can have its own vectors, so there's no sharing and no wire to get stuck.

Third, the second-tier controller. This is the touchscreen's case. The touch controller's line goes to pin thirty-five of a GPIO controller (said "G-P-I-O"). The GPIO controller has hundreds of pins but usually one wire up to the main interrupt controller. Microsoft calls the handling two-stage. When pin thirty-five asserts, the GPIO controller raises its single wire, and the primary handler runs. That's code in Microsoft's GPIO framework, using the vendor's functions to read the status register and find out which pin fired. It then maps that pin to a system-wide interrupt number and passes it to the Hardware Abstraction Layer, the HAL, which raises a secondary interrupt. That secondary interrupt runs the handler of the driver that owns pin thirty-five, the touch driver.

One more piece, because Timothy remembered something about a table. There are three different tables in this story, and they're easy to blur. The ACPI tables, from the firmware, describe the hardware: this device, this address, this pin, level-triggered, active low. The interrupt controller's routing table maps an input pin to a vector number, a core and a trigger type. And the processor's interrupt descriptor table, the I-D-T, maps a vector number to the address of the code to run. The I-D-T is the full-size version of the ATmega's vector table, except it lives in memory and the kernel fills it at boot. Its first thirty-two slots are reserved for events the processor raises itself. Slot fourteen is the page fault, which will matter in part three.

## Section four: what an operating system adds

Timothy's ATmega has one programmer, no threads, and no virtual memory. A Windows laptop adds three things, and each one creates a rule.

First, threads and a scheduler. Code can now wait: "pause me until the I2C transfer finishes, and run someone else meanwhile." Waiting only works if the scheduler can run.

Second, many drivers from many companies on one processor. One driver's handler must not stall everyone else's, so priorities have to be enforced by the system, not agreed between authors.

Third, virtual memory with paging. Some memory might be on disk at this moment, and reaching it means waiting for the disk. That's part three.

Windows enforces all of this with one idea. The ATmega's single global permission bit becomes a number.

## Section five: IRQL, precisely

Every processor, at every moment, has a current IRQL, which stands for interrupt request level. Here's the definition, stated once and carefully. A processor at IRQL n does not accept interrupts whose level is n or lower. It accepts only interrupts above n.

Each symbol needs a meaning. "n" is the processor's current IRQL, a small integer from zero to fifteen on sixty-four-bit Intel and AMD machines. An interrupt's level comes from its vector number: the top four bits of the vector, meaning the vector divided by sixteen and rounded down, are its priority class, and Windows uses that class as its IRQL. And on those machines, the processor's current IRQL is literally stored in a processor register called C-R-eight, which sets the threshold in the local APIC. Raising IRQL means writing a bigger number there.

So IRQL is not a wire. It's a threshold that the kernel sets in each processor, and the hardware compares it against each arriving interrupt's priority class. The ATmega's "I" bit is the special case with only two settings: everything blocked, or nothing blocked.

The levels with names worth knowing are these. Level zero is PASSIVE: ordinary threads, all application code, and most driver code. Level one is APC (said "A-P-C"), for small routines that must run inside one particular thread; that one can stay a black box for now. Level two is DISPATCH, where the scheduler runs, along with deferred procedure calls, and any code holding a spin lock. Above that are the device levels, where hardware interrupt handlers run, and at the very top are the clock, the processor-to-processor interrupts, and "block everything."

## Section six: why code at DISPATCH or above can never wait

Here's the derivation, one step at a time.

Step one. To wait means: mark my thread as blocked, and let the scheduler run another thread until my event happens.

Step two. The scheduler is code, and it runs at the DISPATCH level. That's where the level gets its name.

Step three. A processor at IRQL n doesn't run anything at level n or lower.

Step four. So a processor sitting at DISPATCH or above cannot run the scheduler.

Step five. So a wait there can never hand the processor to anyone. Nothing that would end the wait can run on that processor.

Step six. So it's a guaranteed deadlock, and Windows treats it as a fatal bug rather than hanging forever.

Timothy has seen step five on his own hardware without knowing it. The Arduino Wire library on an ATmega does I2C transfers using the I2C peripheral's own interrupt: a read sets up the transfer, then loops until that interrupt's handler marks it done. If you call Wire from inside another interrupt handler, where the global permission bit is off, the I2C handler can never run, and the loop never ends. It's the same deadlock, with two levels instead of sixteen. And it's the heart of the interview question: an I2C read inside an interrupt handler waits on the I2C controller's own interrupt, which can't get in.

## Section seven: do the minimum high, do the rest low

The standard pattern has three stages. The interrupt handler runs at the device level. It confirms the interrupt is its own, makes the device stop asserting or masks it, notes what happened, and queues a deferred procedure call, a D-P-C. The D-P-C runs at DISPATCH and does short follow-up work that never waits; if waiting is needed, it queues a work item. The work item runs in a thread at PASSIVE, where anything is allowed, including slow I2C transfers.

But the touchscreen has a twist. For most devices, the handler silences the device by writing one of its registers. The touch controller's registers are on the other side of an I2C bus, so silencing it requires an I2C read, which waits. Meanwhile its line is level-triggered, so returning without silencing it causes a storm. That's a trap.

Since Windows 8, drivers whose interrupt comes through a GPIO pin can ask for a passive-level handler. Microsoft documents the sequence for a level-triggered pin. First, the interrupt fires, and the kernel's trap handler masks pin thirty-five at the GPIO controller; that's just a register write, which is fine at high priority. Second, it schedules the driver's handler to run in a kernel thread at PASSIVE. Third, the handler reads the report over I2C, and reading the report makes the touch controller release the line. Fourth, when the handler returns, the kernel thread unmasks the pin. For an edge-triggered pin, the first step clears the latched request instead of masking, because the flag already holds the event.

Pause and predict. Why must the unmask happen after the handler returns, and not before?

Here's the answer. Name the thing that must be true before unmasking: call it "line released." Only the I2C read makes the line released. If you unmask before the read finishes, the line is still asserted, so the level-triggered pin fires again immediately, and you have the storm you were trying to avoid.

## Section eight: how the driver registers its handler

Timothy asked who "the framework" is and how a driver registers its interrupt. Here's the sequence from boot. Every step is someone calling someone.

First, the firmware hands Windows the ACPI tables, and the ACPI driver reports a device with the compatible name P-N-P-zero-C-fifty, meaning HID over I2C. Second, the Plug and Play manager matches that name to Microsoft's HID-over-I2C driver and loads it into the kernel. Third, the driver's entry function runs once and tells the Kernel-Mode Driver Framework, K-M-D-F, which of its functions to call when a device appears. Fourth, the framework calls that function for the touchscreen, and the driver declares its interrupt. It fills in a small configuration structure naming its own interrupt handler function, sets the passive-handling option to true, and calls a framework function named W-D-F interrupt create. At this point nothing is connected yet. The driver has only filled in a form saying what it wants. Fifth, when the device starts, the Plug and Play manager turns the ACPI entry into resources for this device ("your interrupt is GPIO pin thirty-five, level-triggered, active low"), and the framework hands them to the driver. Sixth, as the device powers on, the framework asks the kernel to connect the interrupt. The kernel creates an interrupt object that ties that interrupt to the driver's handler. That's the moment the path through the tables actually leads to the driver's code.

And at interrupt time it all runs in reverse. Pin thirty-five asserts. The GPIO controller raises its wire. The GPIO framework's primary handler finds the pin and passes it to the HAL. The pin is masked, a kernel thread calls the driver's handler at PASSIVE, the driver reads the report over I2C, the pin is unmasked, and the report goes up to the HID class driver.

The one-sentence version: firmware describes, Plug and Play matches and loads, the driver declares its handler to the framework, the framework connects it through the kernel, and the hardware triggers it. The driver never writes an interrupt table itself.

## Connections

This connects directly to the interview. The ISR question is section six: the I2C read waits on the I2C controller's own interrupt, so it can't run at a high level. The answer is the passive-level handler from section seven. The touchscreen-dies-until-reset question is section two, the edge and level mismatch. It also connects to Timothy's ATmega: the global permission bit, the vector table, the flag, and even the Arduino Wire hang are the same mechanisms in a smaller form.

## Recap

Here are the core ideas again, in different words. An interrupt request is a stored bit, plus an enable bit, plus a global permission. Edge requests are latched transitions, and level requests are the live wire, which is why level lines can storm but can't be missed. Wires go through an interrupt controller that hands out vector numbers; wires can be shared, messages can replace wires, and GPIO controllers sit in between as a second tier. IRQL is a per-processor threshold, not a wire. The scheduler lives at DISPATCH, so nothing at DISPATCH or above may wait. Touch drivers use a passive-level handler: mask the pin, read over I2C in a thread, then unmask. And a driver registers its handler by filling in a form for the framework; the kernel makes the real connection later, from the firmware's description.

## Walk questions

Here are three questions to answer out loud on the next walk.

First: explain edge and level triggering using only the word "flag", and use that to explain both an interrupt storm and the dead-until-reset touchscreen.

Second: derive, in steps, why code running at DISPATCH can never wait, and connect it to the Arduino Wire library hanging inside an interrupt handler.

Third: tell the full story of how the touch driver's handler gets connected, from the ACPI table at boot to the moment pin thirty-five fires.
