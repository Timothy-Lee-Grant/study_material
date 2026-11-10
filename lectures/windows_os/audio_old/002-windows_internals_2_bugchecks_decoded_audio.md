# Windows Internals, Part 2: Blue Screens Decoded (audio lecture)

This is part two of an eight-part series on Windows internals. Part one covered the WinDbg debugger. This part covers five blue-screen codes that account for a large share of driver-caused crashes, what each one means, and how to follow its evidence to the driver at fault.

## Why this episode exists

A blue screen looks like a failure, but it's really a message. The kernel stops the machine on purpose because a rule it depends on was broken, and it writes down which rule and four pieces of evidence. Timothy wants to be able to read those messages fluently. By the end of this episode, he should be able to hear a stop code and its parameters and say which rule broke, where to look next, and whether the crashing code is even the guilty code.

## The core ideas

Here are today's core ideas. They're the answer key for the walk questions at the end.

One. A blue screen, which Windows calls a bug check, is the kernel stopping itself deliberately because a rule was broken in kernel mode, where nothing can be isolated. The code names the rule. The four parameters are evidence, and their meaning depends on the code.

Two. Hex D-one means a driver touched pageable or invalid memory while the processor was at the DISPATCH level or above. Usually the real bug is the address, not the level.

Three. Hex one-three-three, the D-P-C watchdog violation, has two forms. Parameter one equal to zero means a single routine ran too long. Parameter one equal to one means too much total time was spent at DISPATCH or above, and the crashing code may be innocent.

Four. Hex nine-F, driver power state failure, means a power transition didn't finish in time. The crash happens in a watchdog timer. The guilty driver is wherever the stuck power request is, which a parameter points to.

Five. Hex fifty means an address that can never be valid was used. Hex seven-E means a kernel thread threw an exception that nobody caught.

Six. The method is the same for every code: read the parameters for this code, switch to the right saved context, read the stack, identify the instruction and the address, and say in one sentence which layer broke which rule.

## Section one: why the machine stops

Why stop the whole machine instead of just the broken driver? Because kernel drivers share one address space with the kernel and every other driver. There's no wall to put around the damage. A driver that has corrupted memory might be about to write that corruption to disk. So the kernel calls its stop function, K-E-bug-check-E-X, with a code and four parameters, writes a dump, and halts.

Who calls that function? Sometimes a driver, but usually part of Windows that caught a broken rule: the page-fault handler, the D-P-C watchdog, the power manager's timer, or the exception dispatcher. The code tells you which part of Windows caught the problem.

## Section two: hex D-one

The full name is driver IRQL not less or equal. Read the name as the rule written backwards: the processor's priority level should have been less than or equal to the highest level at which page faults can be served, and it wasn't. Its sibling, hex A, is the same rule when the address isn't attributed to a driver.

The four parameters are: the memory address that was touched; the priority level at the time; whether it was a read, a write, or an execute; and the address of the instruction that did it.

Microsoft lists the usual causes: dereferencing a bad pointer, null or already freed, at DISPATCH or above; touching pageable data at that level; running pageable code at that level, for instance a function marked pageable that runs while holding a lock; calling into a driver that's been unloaded; or calling through an invalid function pointer.

And Microsoft adds a sentence worth remembering: in most cases of this bug check, the issue isn't the level, but the memory being accessed. The level explains why it crashed now. The address explains the bug.

Pause and predict. Parameter one is hex twenty-eight, parameter two is two, and the stack shows a D-P-C. What happened?

Here's the reasoning. Two is DISPATCH level, consistent with the D-P-C. Hex twenty-eight is a tiny address, which is what you get when code reads a field forty bytes into a structure through a null pointer. So a D-P-C used a pointer that was null. The fix is the missing pointer check or the object's lifetime, not anything about the level.

## Section three: hex one-three-three

While a processor is at DISPATCH level or above, its scheduler can't run, so Windows limits how long that may last. A component called the D-P-C watchdog measures the time and stops the machine when a limit is exceeded. There are two limits, and so two forms.

In the first form, parameter one is zero: a single D-P-C or interrupt routine exceeded its time allotment. The offending routine is usually still on the stack when the watchdog fires, so bang-analyze and k usually name it. A typical cause on new hardware is a D-P-C polling a status bit that never clears: the device didn't behave the way the driver assumed.

In the second form, parameter one is one: the processor cumulatively spent too long at DISPATCH or above. Here the crashing stack may be innocent; it's just whatever was running when the total ran out. The evidence is in a triage structure that parameter three points to, in the queue of pending D-P-Cs (bang-D-P-Cs), and in event tracing, which part four covers. Microsoft itself says that for this form, the code may not stop in the offending area, and suggests tracing.

Pause and predict. A level-triggered interrupt is never silenced: the routine returns without making the device let go of the line. Which form do you expect?

The cumulative form. Each run of the routine is short, but it runs again immediately, forever, so the total time at high priority grows past the limit. A trace would show that one routine with an enormous count.

## Section four: hex nine-F

Driver power state failure. Power transitions, like sleeping, resuming, or a device turning off when idle, are carried out by power requests sent down device stacks, and the power manager sets a timer on them. If a driver neither finishes nor passes on a power request, the timer fires and the machine stops. This is the classic sleep and resume crash, very common during hardware bring-up.

Since a timer raised it, the crashing stack belongs to the timer. The evidence is in the parameters, and parameter one says which subtype it is.

When parameter one is three, a device object has been blocking a power request too long. Parameter two is the physical device object at the bottom of that device's stack, and parameter four is the blocked request itself. The recipe: run bang-I-R-P on parameter four. The request lists one slot per driver layer, and the one marked with a "greater than" arrow is the layer that holds it now. Then run bang-dev-stack on parameter two to see every driver on that device. Bang-P-O-action shows the overall power operation. For drivers built on the Kernel-Mode Driver Framework, the framework's own log for that driver often says it's waiting for the driver to complete a request. Then find the driver's thread and see what it's waiting for.

When parameter one is four, the power transition timed out waiting to synchronize with Plug and Play, and parameter three is the thread holding the Plug and Play lock. Run bang-thread on it to see what it's stuck in. Often it's another driver's start or remove routine.

Pause and predict. Parameter one is three, and the blocked request is a "set power to fully on" request, held by the touchscreen's HID-over-I2C driver, during resume. Name two possible root causes at different layers.

First, at the driver layer: the driver sent the touch controller a command after power-on and is waiting for an answer that never comes, maybe because it didn't wait for the controller to be ready, or didn't handle a reset. Second, at the platform layer: the firmware's power method never actually restored power to the controller, so the I2C transfers can't complete. A logic analyzer on the bus and the reset line would tell them apart.

## Section five: hex fifty and hex seven-E

Hex fifty is page fault in nonpaged area. Microsoft's description: invalid system memory was referenced, typically a wrong address or one pointing at freed memory. Here's how it differs from D-one. D-one is about memory that might be valid at a lower priority level. Hex fifty is about an address that can't be valid at any level: freed, never mapped, or garbage. Parameter one is the address. Parameter two is the operation, and its encoding differs between Intel-style and Arm processors, so check which architecture the dump came from. Parameter three is the instruction. Parameter four is a subtype: for example, four means the address isn't even well-formed for the processor, which points to a garbage pointer, and hex F means kernel code touched a user-mode address it wasn't allowed to touch directly. If hex-fifty crashes show up randomly across unrelated drivers, suspect hardware, like faulty memory, before suspecting code.

Hex seven-E is system thread exception not handled. A kernel-mode system thread raised an exception that nothing caught. Parameter one is the exception code: hex C-zero-zero-zero-zero-zero-zero-five is an access violation, and hex eight-zero-zero-zero-zero-zero-zero-three is a breakpoint or assertion hit with no debugger attached, which is actually helpful, because the assertion names the broken assumption. Parameter two is where it happened. Parameters three and four point to the exception record and the saved processor context. Use dot-E-X-R on parameter three to see the exception, then dot-C-X-R on parameter four to switch to the processor state at the moment of the fault. Then k shows the stack at the fault instead of the exception machinery.

## Section six: telling them apart

Here are the questions that sort them. A bad memory access while at DISPATCH or above is D-one. A bad access to an address that can't be valid at all is fifty. An uncaught exception in a kernel thread is seven-E. Too long at high priority is one-three-three, with parameter one telling you single or cumulative. A power request that never finished is nine-F.

And here's where the evidence lives. For D-one, fifty, and seven-E, the guilty code is on the crashing stack, once you've switched to the right context. For one-three-three with parameter one equal to zero, usually on the stack too. For one-three-three cumulative and for nine-F, the guilty code is somewhere else, and the parameters tell you where: a triage structure, a blocked request, a thread.

## Connections

This connects to part one: every recipe uses bang-analyze, k, bang-I-R-P and bang-dev-stack. It connects forward to part five, which explains exactly why paging is forbidden at DISPATCH, and to part seven, which explains the power requests behind nine-F.

## Recap

The core ideas once more. A blue screen is the kernel's deliberate stop, naming the broken rule with four pieces of evidence. D-one is pageable or invalid memory touched at DISPATCH or above, and the address is usually the bug. One-three-three is too long at high priority, either one routine or the total. Nine-F is a power request that never finished, so follow the request, not the stack. Fifty is an address that can't be valid at all, and seven-E is an uncaught kernel exception reached through dot-E-X-R and dot-C-X-R. One method fits all of them: parameters, context, stack, instruction and address, one sentence.

## Walk questions

Three questions for the next walk.

First: explain the two forms of one-three-three, and for each, say whether you trust the crashing stack.

Second: walk through investigating a nine-F with parameter one equal to three, naming each parameter and each command in order.

Third: what's the difference between D-one and fifty, in terms of whether the address could ever have been valid?
