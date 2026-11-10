# Windows Internals, Part 5: Interrupt Handling, IRQL, and Deferred Work (audio lecture)

This is part five of an eight-part series on Windows internals, and the first of the kernel mechanics episodes. It covers the interrupt request level, the chain of interrupt routine, then deferred procedure call, then work item, how the stages share data safely, and exactly why paging is forbidden at the DISPATCH level.

## Why this episode exists

Timothy can already explain why code at DISPATCH level can't wait. This episode makes the whole picture concrete: what each stage of interrupt handling is allowed to do, how a driver passes work from one stage to the next, which locks it uses, and the precise rule about paging. It also separates two ideas that are easy to blur together: privilege and priority.

## The core ideas

Here are today's core ideas. They're the answer key for the walk questions at the end.

One. Privilege and priority are two different axes. Privilege, user mode or kernel mode, decides what memory and instructions code may use. Priority, the IRQL, decides what can interrupt it. All user code runs at the lowest level, PASSIVE. Kernel code can be at any level.

Two. IRQL is a per-processor threshold held in a processor register. It's raised automatically when the processor takes an interrupt, raised by code that takes a spin lock, and lowered when that code finishes.

Three. Interrupt delivery is set up in advance and then fires on its own. At boot the routes are prepared. At runtime the hardware signals and the processor jumps to the handler. Nothing in the operating system watches the wires.

Four. Each stage does the minimum its level allows. The interrupt routine confirms the interrupt, silences the source, captures data, and queues a D-P-C. The D-P-C does short work that never waits, and queues a work item if waiting is needed. The work item, running on an existing system worker thread at PASSIVE level, does anything slow.

Five. No thread is created per interrupt. Interrupt routines and D-P-Cs borrow whatever thread was interrupted. Work items run on worker threads that already exist.

Six. Paging is forbidden above the level called APC, because fixing a page fault means waiting for the disk, and waiting needs the scheduler, which runs at DISPATCH. So anything touched at DISPATCH or above must be nonpaged.

## Section one: two axes

It's tempting to think of kernel code as running at "a higher level of permission", and of interrupt routines as running at "the highest level". That merges two separate ideas.

The first axis is privilege: user mode or kernel mode. On Intel-style processors those are ring three and ring zero; on Arm, exception levels zero and one. Privilege decides which memory pages are reachable, because kernel pages are marked supervisor-only, and which instructions are allowed. Privilege only changes at defined entry points: system calls, interrupts, and exceptions.

The second axis is priority: the interrupt request level, IRQL, said "I-R-Q-L". It decides which interrupts may preempt the running code on this processor, and therefore what the code may do, like whether it may wait.

Picture the four combinations. User mode at PASSIVE level: every application thread. User mode at DISPATCH or above: never happens, because user code always runs at PASSIVE. Kernel mode at PASSIVE: a driver's entry routine, most request handlers, work items. Kernel mode at DISPATCH or above: D-P-Cs, code holding a spin lock, and interrupt routines.

So an interrupt routine runs in kernel mode, at its own device's interrupt level. And that's not the highest level: the clock, inter-processor interrupts, and a level called HIGH all sit above every device.

## Section two: IRQL precisely

Here's the definition, once, carefully. Each processor has a current IRQL. A processor at IRQL n accepts only interrupts whose level is greater than n.

Now what each symbol means. The processor's IRQL is processor state: on sixty-four-bit Intel and AMD machines it lives in a control register called C-R-eight, which sets the threshold in the processor's local interrupt controller. It's not a variable in RAM that the system looks up. An interrupt's level is assigned when the interrupt is connected, and on those machines it comes from the interrupt's vector number.

Here's how it changes, step by step. A processor is running a thread at PASSIVE, level zero. A device interrupt arrives at level five. Five is greater than zero, so it's accepted. The processor jumps through its interrupt table, the kernel raises the processor's level to five, and calls the driver's interrupt routine. While at five, interrupts at five or below wait, and higher ones can still get in. The routine returns, the kernel lowers the level, and if any D-P-Cs were queued, the processor runs them at DISPATCH, level two, before going back to the thread at zero.

Microsoft lists what runs where. At PASSIVE: driver entry, adding devices, most request handling, driver-created threads, and worker-thread callbacks. At APC, level one: some request handling; it's like PASSIVE except a certain kind of callback is blocked, and it can still page. At DISPATCH, level two: D-P-Cs, timer D-P-Cs, and code holding spin locks. At device levels: interrupt routines.

## Section three: setup time versus run time

A common mental model has the operating system watching interrupt lines, or looking up a table to see which device signaled. It doesn't work that way. Everything is prepared in advance, and at runtime the hardware does the routing.

At setup time, during boot and device start: the firmware's A-C-P-I description says which pin the device uses and how it's triggered. The Plug and Play manager turns that into the device's interrupt resource. The driver declares its interrupt routine and D-P-C to its framework. The kernel connects an interrupt object, programs the interrupt controller's routing, and the processor's interrupt table points the vector at the kernel's dispatch code.

At run time, for each interrupt: the device asserts its line, the controller detects it, the processor is interrupted with a vector, it jumps through its interrupt table, the kernel raises the level and calls the driver's routine through the interrupt object.

That's why a wrong hardware description, edge instead of level, for example, produces a path that's wired wrong and misbehaves silently at runtime. Nothing re-reads the description. And the path isn't always one pin per device. An interrupt may come on a dedicated controller input, on a shared level-triggered line where each routine answers "mine" or "not mine", as a message for P-C-I Express devices, or through a G-P-I-O controller acting as a second-tier controller.

## Section four: the chain, stage by stage

Take a device whose registers are directly mapped into memory: say, a sensor block inside the main chip that interrupts when a sample is ready.

Stage one is the interrupt routine, the I-S-R, at the device's level. It has four jobs, in order. First, check whether the interrupt is its own, by reading the device's status register; if not, return false, because the line may be shared. Second, silence the source, by writing the device's acknowledge register, so a level-triggered line drops and doesn't storm. Third, capture anything volatile, like the sample register, into the device's context memory. Fourth, queue a D-P-C, and return true. It may not wait, page-fault, or run long.

Stage two is the D-P-C, the deferred procedure call, at DISPATCH level. A D-P-C is a small kernel object holding a function and a context. Queueing it puts it on the current processor's D-P-C queue. When that processor's level drops below DISPATCH, right after the interrupt routine returns, it drains the queue, running each D-P-C at DISPATCH. Its job is short, non-waiting work: process the sample, complete a pending read request, and queue a work item if something needs to wait.

Stage three is the work item, at PASSIVE level. The kernel keeps a pool of system worker threads that already exist. Queueing a work item puts it on their queue, and a worker thread picks it up and calls the function in an ordinary thread context, where it can wait, do synchronous input-output, and touch pageable memory.

Pause and predict. In terms of threads, where does each stage run? Careful.

The interrupt routine and the D-P-C run on whatever thread happened to be interrupted on that processor. They borrow it, and have no thread of their own. That's why the process name in a crash dump can be misleading. The work item runs on a real, already-existing system worker thread. No thread is created for any stage.

In the Kernel-Mode Driver Framework, K-M-D-F, these stages are functions the driver registers. The interrupt routine calls a framework function to queue its D-P-C, the D-P-C calls another to queue a work item, and the framework takes care of the kernel objects underneath.

## Section five: sharing data, and which lock

The interrupt routine, the D-P-C and the work item all touch the same device context, possibly on different processors at the same moment. The rule for choosing a lock: the lock must raise the priority to at least the highest level of any code that touches the data.

Data shared with the interrupt routine needs the interrupt spin lock, which raises to the device's interrupt level. Data shared among D-P-Cs and other kernel code, but not the interrupt routine, needs an ordinary spin lock, which raises to DISPATCH. Data touched only at PASSIVE can use a mutex or wait lock, which keeps you at PASSIVE.

Why must the interrupt's lock raise all the way to the device level? Imagine a D-P-C holding an ordinary spin lock at DISPATCH, and the device's interrupt arrives on the same processor. The interrupt routine preempts the D-P-C and spins on the lock, but the D-P-C can't release it until the interrupt routine returns. That's a deadlock on a single processor. Raising to the device level blocks that interrupt on that processor while the lock is held.

And here's a trap: taking any spin lock puts you at DISPATCH, even in code you think of as normal. A function marked pageable, called while holding a spin lock, is a D-one waiting for memory pressure.

## Section six: the bus-device case

For a touch controller on an I2C bus, stage one breaks. Silencing the device requires an I2C read, and an I2C read waits. Meanwhile the line is level-triggered, so returning without silencing it causes a storm.

There are two solutions. In the classic chain, the interrupt routine masks the G-P-I-O pin, which is allowed because the G-P-I-O controller's registers are directly mapped. It queues a D-P-C, which queues a work item, and the work item does the I2C read and then unmasks the pin. The cost is three hops, and an unmask that's easy to forget.

The simpler solution is the framework's passive-level interrupt. The driver sets one option when declaring its interrupt. Then the system masks the pin when it fires, runs the driver's routine on an existing kernel thread at PASSIVE, and unmasks the pin after the routine returns. Because the pin stays masked while the routine runs, it should do only the initial servicing and pass the rest to a work item.

Pause and predict. In a passive-level interrupt routine, the I2C read fails, and the routine returns anyway. What happens next?

The device still has the line asserted, so as soon as the pin is unmasked, the interrupt fires again. If it keeps failing and retrying with no backoff, the time at elevated priority piles up, which leads to the cumulative form of blue screen one-three-three.

## Section seven: why paging is forbidden at DISPATCH

Here's the derivation, one step at a time.

Step one. Pageable memory may be on disk at any moment, because the memory manager moved its contents to the page file to free RAM.

Step two. Touching a page that's on disk makes the processor raise a page fault.

Step three. The kernel's page-fault handler must read the page back from disk, which means starting an input-output operation and waiting for it.

Step four. Waiting means blocking this thread and letting the scheduler run something else.

Step five. The scheduler runs at DISPATCH. A processor at DISPATCH or above can't run it.

Step six. So at DISPATCH or above, the wait could never finish. The page-fault handler checks the level first, and when it's above APC, it stops the machine, with hex A or hex D-one, instead of deadlocking.

Microsoft states it exactly: any routine running above APC level cannot safely allocate or access paged memory, and a page fault there is a fatal error. Note the exact boundary: above APC. APC level itself may still page.

What a driver does about it: memory touched at DISPATCH or above comes from the nonpaged pool. Code that runs at DISPATCH or above stays in normal, nonpaged code sections. Code marked pageable starts with a macro called PAGED-underscore-CODE, which asserts in debug and verified builds that the level is APC or below, turning an assumption into a checked statement.

## Connections

This connects to part two: D-one is this paging rule broken, and one-three-three is the time limit on these stages. It connects to part four: Force IRQL Checking exists because of section seven. And it connects to the touch example: the passive-level interrupt is exactly how a touch controller behind an I2C bus gets serviced.

## Recap

The core ideas again, in different words. Privilege and IRQL are separate: an interrupt routine is kernel-mode code at its device's level, and user code is always at PASSIVE. IRQL is a per-processor register value raised by interrupts and spin locks. Interrupt paths are set up at boot and fire on their own at runtime. The interrupt routine silences and queues; the D-P-C does short work on the processor's queue; the work item runs on an existing worker thread at PASSIVE. Locks must raise to the highest level of any code touching the data. And paging is fatal above APC because a page fault needs a wait, and waiting needs the scheduler, which lives at DISPATCH.

## Walk questions

Three questions for the next walk.

First: describe the four combinations of privilege and IRQL, with an example of each, or "never".

Second: list the interrupt routine's four jobs in order, and say on which thread the interrupt routine, the D-P-C and the work item each run.

Third: derive, step by step, why a page fault above APC level is fatal.
