# Windows Internals, Part 1: WinDbg Essentials (audio lecture)

This is part one of an eight-part series on Windows internals. Parts one through four cover debugging: the WinDbg debugger, the common blue-screen codes, crash dumps and how to handle different kinds of failure, and the tools Driver Verifier and event tracing. Parts five through eight cover the kernel mechanics underneath: interrupt handling, device stacks, power management, and processes, threads and memory.

## Why this episode exists

Timothy is an electrical engineer who's getting deep into how Windows works at the kernel level: how drivers talk to hardware, why systems crash, and how engineers figure out what went wrong. The main tool for that is a debugger called WinDbg, said "win-debug". Almost every investigation of a crash or a hang starts with the same handful of WinDbg commands. By the end of this episode, Timothy should know what each of those commands asks, and how to read what comes back.

## The core ideas

Here are today's core ideas, stated plainly. They're the answer key for the walk questions at the end.

One. WinDbg can look at three kinds of target: a dump file, which is a saved snapshot; a live machine connected over a debug cable or the network; or the local machine, read-only. The commands are the same for all three.

Two. Symbols turn addresses into names. Without the right symbol files, every stack is a list of meaningless numbers. So the first step of every session is fixing symbols.

Three. The command bang-analyze dash-v is triage, not a verdict. It reads the stop code and its parameters, finds the thread that matters, and names a likely driver. It can blame the wrong driver.

Four. The command k shows the call stack. Read it from the top to see where the code stopped. Read it from the bottom to see how it got there, and that tells you what context the code was running in.

Five. The command l-m lists loaded modules and their versions. Bang-thread shows what a thread is doing or waiting for. Bang-I-R-Q-L shows a processor's priority level when it stopped.

Six. Bang-dev-node and bang-dev-stack show the device tree and the stack of drivers layered on one device. Together they answer "which drivers own this device, and is it running?"

## Section one: three targets

A word on pronunciation first. Commands that begin with an exclamation mark are called "bang" commands; they're extensions. Commands that begin with a dot, like dot-reload, are built-in debugger commands.

WinDbg can attach to three kinds of target. The first is a dump file: a snapshot of memory written when a machine crashed, or on request. You can read everything that was captured, but you can't run, step through code, or set breakpoints. Most crash investigations work this way, including every crash someone sends you from another machine.

The second is a live kernel on another machine. The target boots with debugging turned on, connected over the network (called K-D-NET) or a serial cable, and WinDbg runs on a second computer. You can stop the machine, inspect anything, set breakpoints, step and continue. Hardware bring-up labs work this way.

The third is local kernel debugging: WinDbg on the same machine, with debug mode turned on, looking at the running kernel read-only. You can't stop anything, but it's a wonderful way to practice the inspection commands without crashing anything. One catch: turning on debug mode is blocked while Secure Boot is on, so it's for lab machines.

## Section two: symbols

When a driver is compiled, the compiler produces two files: the driver itself, and a program database, a P-D-B file. The P-D-B maps addresses to names: function names, global variables, and the layouts of structures. The driver records exactly which P-D-B belongs to it, and WinDbg only loads an exact match, because a P-D-B from a different build would put the names on the wrong code.

Microsoft publishes symbols for Windows itself on a public symbol server. The command dot-sym-fix, followed by a local folder such as C colon backslash symbols, tells WinDbg to download from that server and cache the files locally. For your own driver, you add its build folder with dot-sym-path-plus. Then dot-reload re-resolves everything.

Here's the habit worth keeping. If a stack shows things like "the driver name plus hex one A two C" instead of "the driver name, exclamation mark, a function name", symbols are missing for that module. Don't reason about a stack until symbols are fixed. The command bang-sym-noisy, followed by a forced reload of that module, prints every place WinDbg looked, which usually reveals the problem.

## Section three: bang-analyze dash-v

Bang-analyze dash-v runs Microsoft's automated triage. It reads the stop code and its four parameters, finds the thread and the saved processor state that matter, walks the stack, skips the frames that belong to Windows' own crash machinery, and names the first interesting function and driver. It ends with a failure bucket: a short signature that groups identical crashes from many machines.

The fields to read every time are these. The bugcheck code and its four parameters, whose meanings depend on the code, which is the subject of part two. The stack text. The module name and image name it blames. And the failure bucket.

Now the warning. Bang-analyze names the driver where the fault happened, and that isn't always the driver that caused it. If driver A frees a buffer and driver B later uses a stale pointer to it, the crash lands in B. If driver A corrupts memory and Windows' own memory code trips over it later, Windows gets the blame. That's why bang-analyze is step one, and reading the stack yourself is step two.

## Section four: the call stack

The command k walks the current thread's stack and prints one line per function call, newest at the top. Each line shows a module, an exclamation mark, a function name, and an offset into that function. The k-n variant adds frame numbers.

There are two ways to read a stack, and both matter.

Read it from the top to find where it stopped. The top few frames in a crash are Windows' own machinery: K-E-bug-check-E-X is the "stop the machine" function, and K-I-page-fault means a page fault was being handled. The first frame below those that belongs to a driver is where the fault happened.

Read it from the bottom to find out how it got there, and therefore what context the code ran in. This is the most valuable habit in this episode. If the bottom of the stack shows the processor's idle loop, then a routine called K-I-retire-D-P-C-list, then K-I-execute-all-D-P-Cs, then the driver's function, the driver was running as a deferred procedure call, a D-P-C, at the DISPATCH priority level. If you see K-I-interrupt-dispatch, it was an interrupt service routine. If you see E-X-P-worker-thread, it was a system work item at the lowest priority level, PASSIVE. If you see K-I-system-service, a user application called into the kernel.

Pause here and predict. A driver crashed with a page fault, and below its function you see K-I-execute-all-D-P-Cs. What priority level was it running at, and why does that matter?

The answer: DISPATCH level, because it was running as a D-P-C. At that level, a page fault on memory that's out on disk can't be served, which is exactly the blue screen called D-one. The stack's shape told you the context before you ran any other command.

## Section five: modules, threads, and priority

The command l-m lists every loaded module: the kernel, the hardware abstraction layer, and every driver. L-M-V followed by M and a driver name gives one driver's details: where it was loaded from, when it was built, its version, and whether its symbols loaded. A large share of real bugs are version mismatches, a driver older or newer than something else expects. L-M-V is how you prove which version was actually running when it crashed. L-m also lists unloaded modules at the end. A crash at an address belonging to an unloaded driver means something called into a driver after it was gone, which is a lifetime bug.

Next, processes and threads. A process is a container: an address space, its open handles, its security identity. A thread is what actually runs: registers, a stack, a state. Bang-process zero zero lists every process. Bang-thread followed by an address shows one thread: whether it's running, ready, or waiting; what it's waiting on; how long it has waited; which input-output requests it has outstanding; and its stack. Hangs are diagnosed with bang-thread, following each wait until you find something that will never happen.

Then bang-I-R-Q-L. IRQL is the processor's interrupt request level, its current priority. It isn't a value in memory; it's a per-processor value held in a processor register. So "the IRQL" only means something for one processor at one moment. In a dump, bang-I-R-Q-L shows the value saved when the crash happened. Microsoft adds a useful caution for the D-one blue screen: in most cases, the issue isn't the level, it's the memory being accessed. Check both.

## Section six: devices

Every device Windows knows about has a device node, a dev-node, in a tree that records which devices exist and how they're connected. Each dev-node has a device stack: a vertical list of the drivers layered on that device. At the bottom is the physical device object, the P-D-O, created by the bus driver that discovered the device. For a laptop touchscreen, that's the A-C-P-I driver. Above it is the functional device object, the F-D-O, created by the main driver that knows how to run the device. Filters may sit above or below.

Bang-dev-node zero one walks the whole tree. Adding a driver's name filters it to the devices that driver runs. Each entry shows the device's identity, its state (started, failed or removed), and any problem code, the same numbers Device Manager shows. For a device that has stopped working, this answers the first question: does Windows still think it's running?

Bang-dev-stack followed by a device object address shows the stack, top to bottom, with the driver that owns each layer. That's the "whose bug is it" map. If an input-output request is stuck at one layer, the driver that owns that layer owns the problem.

## Section seven: one session, start to finish

Here's a whole first session, as a sequence. Open the dump. Fix symbols: sym-fix, add your driver's symbol folder, reload. Run bang-analyze dash-v and write down the code and its four parameters. Look up what those parameters mean for that code. Run k, and confirm what context the code was in: does it agree with the level in the parameters? Find the instruction with l-n and u on the instruction's address. Classify the memory address with bang-P-T-E, bang-pool and bang-address. Record the driver's version with L-M-V. Then write one sentence that names the function, the layer, the rule that was broken, and the version. That sentence is the deliverable.

## Connections

This connects to the touchscreen example from the earlier platform lectures. Bang-dev-node would show the HID-over-I2C touch device and its state. Bang-dev-stack would show the A-C-P-I physical device object at the bottom and the HID class driver with its I2C mini-driver above it. And the stack-shape habit connects to part five, where the interrupt routine, the D-P-C and the work item each leave their own signature on a stack.

## Recap

The core ideas again, in different words. WinDbg reads dumps, live remote kernels, or the local kernel read-only, with one command language. Symbols come first, always. Bang-analyze dash-v is the first look, and it can blame a victim. The stack read from the bottom tells you whether the code was an interrupt routine, a D-P-C, a worker, or a system call. L-m proves versions, bang-thread follows waits, and bang-I-R-Q-L shows a processor's priority at the crash. Bang-dev-node and bang-dev-stack map devices and the drivers on them.

## Walk questions

Three questions to answer out loud on the next walk.

First: why must symbols be fixed before you trust a stack, and how would you notice they're missing?

Second: name the four kernel routines whose presence at the bottom of a stack tells you the code was an interrupt routine, a D-P-C, a worker thread, or a system call.

Third: for a device that's stopped working, what do bang-dev-node and bang-dev-stack each tell you, and how do they differ?
