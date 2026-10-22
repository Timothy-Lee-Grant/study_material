# Windows Internals, Part 3: Dumps, and Crash versus Hang versus Dead Device (audio lecture)

This is part three of an eight-part series on Windows internals. Part one covered WinDbg and part two covered blue-screen codes. This part covers crash dumps of every kind, live dumps for systems that haven't crashed, and how to collect the right evidence for three different kinds of failure.

## Why this episode exists

The most expensive mistake in debugging isn't misreading evidence. It's not having the evidence at all: rebooting a frozen machine and losing everything in memory, or getting a tiny dump when the bug needed the whole kernel. Timothy wants a dependable procedure: first classify the failure, then collect what that kind of failure needs. By the end of this episode he should be able to do that for a crash, a hang, and a single dead device.

## The core ideas

Here are today's core ideas. They're the answer key for the walk questions at the end.

One. A dump is a snapshot of memory plus processor state, for later analysis. The types differ in how much memory they include: small, then kernel, then active, then complete. Automatic is a kernel dump where Windows manages the page file's size.

Two. Choose the smallest dump that still contains the evidence. A minidump shows only the crashing thread. Driver work usually needs at least a kernel dump.

Three. A crash dump is written into the page file's space while the machine is going down, and copied out to a file on the next boot.

Four. A live dump captures kernel memory while the machine keeps running. You can make one from Task Manager, and Windows also takes some by itself.

Five. Crash, hang and dead device need three different kits. For a hang, never just reboot: force a dump or break in with a debugger. For a dead device, capture a live dump before trying any recovery.

## Section one: how a crash dump gets written

When the kernel calls its stop function, the machine is in an unknown and possibly corrupt state. Windows can't trust the file system, and it can't trust most drivers. So it uses a small, pre-prepared path: a special crash mode of the storage drivers, set up at boot. Through that path, it writes the chosen memory directly into the space occupied by the page file on the boot drive, because that space was reserved and mapped in advance. On the next boot, Windows notices the dump data in the page file and copies it out to a file called MEMORY dot D-M-P in the Windows folder, and small dumps into a Minidump folder.

Two consequences follow. If the page file is missing, too small, or on the wrong drive, the dump may be incomplete or absent, and automatic mode exists to manage that. And if the crash is in the storage drivers themselves, writing the dump can fail. So a machine that reboots after a blue screen and leaves no dump is giving you a clue.

## Section two: the dump types

The small dump, or minidump, contains the stop code and its parameters, the crashing thread's stack and processor state, and the list of loaded modules. That's enough to count and group crashes across many machines. It's not enough to root-cause most driver bugs: it doesn't contain other threads, pending input-output requests, memory pools, or the device tree.

The kernel dump contains all memory used by the kernel and drivers, but no user-mode memory. That answers nearly every driver question: every thread's kernel stack, every pending request, every device node, the power state. Automatic mode produces the same contents as a kernel dump, while letting Windows size the page file appropriately.

The active dump is like a complete dump, but it leaves out pages unlikely to be useful, like free memory and memory belonging to guest virtual machines. The complete dump is all of physical memory, as large as the machine's RAM. Use active or complete when the bug spans a user-mode program and a driver, and you need to see both sides.

The practical rule for test machines: default to kernel or automatic dumps. And never try to debug a hang from a minidump, because the threads you need simply aren't in it.

## Section three: live dumps

A live dump captures kernel memory while the machine keeps running. You want one when nothing has crashed but something is wrong right now: a device that's stopped responding while everything else works, a subsystem that's stuck while the desktop still responds, or any state you need before trying a recovery that would destroy it.

To make one, run Task Manager as an administrator, right-click the process called System, and choose "Create live kernel memory dump file". You get two choices. A full live kernel dump includes active kernel memory, and optionally hypervisor and user memory. A kernel stacks dump is smaller and holds the processor states and every kernel thread's stack. The file goes into a LiveKernelDumps folder under your local application data, and the dump carries the code hex one-six-one, live system dump. That's a label, not a crash.

Windows also takes live dumps on its own for certain recoverable failures, and stores them in a folder called LiveKernelReports in the Windows directory. The best-known example is when the display driver hangs and Windows resets it, which records hex one-one-seven. If a machine glitched and recovered, look there.

One limit: capturing a live dump temporarily needs enough free memory to copy kernel memory. By default it gives up under memory pressure, and it can succeed with an incomplete result.

Pause and predict. The touchscreen is dead, everything else works, and someone is about to disable and re-enable the device in Device Manager. What should you capture first, and why?

A live kernel dump, before the disable and re-enable. Re-enabling tears down and rebuilds the device's driver stack, which destroys the stuck state: the pending requests, the driver's internal state, and whatever its threads were waiting on.

## Section four: classify first

There are four kinds of failure worth distinguishing. A crash is a blue screen and a reboot, and the stop code is your first clue. A system hang is a frozen screen with dead keyboard and mouse and no blue screen. A partial hang is when some applications freeze while others work. A dead device is when one device stops and everything else is fine.

Two questions sort most cases. First: does anything still respond? A moving mouse, a network ping, a clock that updates. If nothing does, it's a system hang. If something does, it's a partial hang or a dead device. Second, asked only after the evidence is captured: does a soft reset, disabling and re-enabling the device, fix it, or only a cold power cycle? If the soft reset works, the stuck state lived in the driver stack. If only a power cycle works, it lived in the hardware, the bus, or the power supply to the device.

## Section five: the crash kit

For a crash, collect the kernel or automatic dump, any earlier minidumps so you can compare their failure buckets, the system event log around the crash time, the driver and firmware versions, and notes about what was happening: resuming, idle, heavy use. Then analyze with the method from parts one and two. If it reproduces, turn on Driver Verifier for the suspect driver, from part four, so the next crash lands at the moment of the real violation.

## Section six: the hang kit

For a hang, the first rule is: don't reboot. A hang's evidence exists only in memory. There are three ways to get it out.

The first is an attached kernel debugger: if the machine was booted with debugging on and WinDbg is connected, you break in and have full access.

The second is forcing a crash from the keyboard. With a registry value called Crash-On-Control-Scroll set beforehand, holding the right Control key and pressing Scroll Lock twice makes Windows stop with code hex E-two, manually initiated crash, and write a dump. The value lives under the keyboard driver's parameters key in the registry, and laptops without a Scroll Lock key can remap the trigger.

The third is a non-maskable interrupt, an N-M-I, which hardware or a hypervisor can deliver even when a processor is stuck at the highest priority. With crash-on-N-M-I enabled, it produces stop code hex eighty and a dump.

Why might the keyboard method fail when the N-M-I works? Because the keyboard method needs the keyboard's own interrupt and driver to run. If a processor is stuck at very high priority, the key presses are never processed. A non-maskable interrupt can't be blocked by the priority level.

In the dump, a system hang usually has one of two shapes. In the first, a processor is spinning at DISPATCH or above, looping on a lock that's never released or polling hardware that never answers. Bang-running shows what each processor was doing, and per-processor stacks and bang-I-R-Q-L confirm it. In the second, nothing is busy but everything important is waiting: a deadlock. Bang-stacks summarizes every thread's kernel stack, bang-locks shows who holds what, and bang-thread and bang-I-R-P let you follow the chain of waits to the one thing that will never happen.

For a partial hang, also take a user-mode dump of the frozen application from Task Manager. Its stack usually shows which call into the system it's stuck in, often a read or a device control request that a driver never completes.

## Section seven: the dead-device kit

For a dead device, collect evidence in order, least destructive first. One: the device's status and problem code in Device Manager, or with the pnputil command listing devices with problems. Two: a full live kernel dump. Three: the driver's own log, which for framework-based drivers is a small in-flight recorder you can read from the dump. Four: the system event log, including the Plug and Play logs. Five: a trace of an attempt to use the device, which part four explains, to see whether interrupts still arrive. Six: the hardware truth, with a logic analyzer or oscilloscope on the interrupt line, the bus, the reset line and the power rail. Seven, and only now: recovery experiments, in order: disable and re-enable, then sleep and resume, then a cold power cycle.

The evidence maps to layers. A problem code points to a driver or firmware failing at start. A device that Windows says is working, with no interrupts arriving and the line idle, points to the device itself no longer asserting: its firmware or its power. A line stuck asserted with no interrupts counted points to a missed edge or a mismatch between edge and level triggering in the hardware description. A data line held low points to a hung bus. Requests stuck inside the driver point to a driver state-machine bug. Failures only after resume or idle point to power management, which is part seven.

## Connections

This connects back to the stuck touchscreen example: the dead-device kit is the procedure for exactly that problem. It connects forward to part four, where Driver Verifier and tracing provide two of these kits' tools, and to part seven, on power.

## Recap

The core ideas once more. Dumps range from small to complete, and the smallest one that holds the evidence is the right one, which for drivers usually means kernel or automatic. Crash dumps go into the page file at crash time and get copied out at the next boot. Live dumps capture a running machine, from Task Manager or by Windows itself. Classify the failure before collecting. For a hang, don't reboot: break in, or force a dump with the keyboard or an N-M-I. For a dead device, capture a live dump first, then logs, traces and the hardware, and only then try recoveries in order.

## Walk questions

Three questions for the next walk.

First: why is a minidump too thin for driver work, and what does a kernel dump add?

Second: name the three ways to get evidence out of a frozen machine, and explain why the N-M-I can work when the keyboard method can't.

Third: list the dead-device collection steps in order, and explain why the recovery experiments come last.
