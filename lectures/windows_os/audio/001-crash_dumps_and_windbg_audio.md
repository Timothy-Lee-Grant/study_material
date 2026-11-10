# Crash Dumps and WinDbg: Turning a Dead Machine into a Diagnosis (audio lecture)

## Why this episode exists

Timothy has spent the last few weeks building his own Windows kernel driver, TgCounter, inside a Windows 11 Arm virtual machine on his Mac. He has built it, signed it, loaded it, called it from a user-mode program, and attached WinDbg to the running kernel in local mode, where the prompt reads "L-K-D". The next labs in his plan crash the machine on purpose and then analyze the result. This episode is the thinking that goes with those labs.

Here is the core problem. When a Windows machine fails at the kernel level, it either stops dead with a blue screen, or it freezes and stops responding. Either way, the person in front of it sees almost nothing. A stop code. A sad face. A spinning circle that never ends. Everything that actually explains the failure — which code was running, on which processor, at what priority, holding which lock, in the middle of which request — lives in memory, and memory disappears the moment the machine resets. A crash dump is how that evidence survives. WinDbg, usually said "win-debug", is how you read it.

The skill this episode builds is specific and measurable. By the end, Timothy should be able to open a kernel dump he has never seen before and, within about ten minutes, say four things out loud. First, the stop code in plain words. Second, the module on top of the stack, and whether it belongs to Microsoft or to a hardware vendor. Third, the IRQL, the interrupt priority level the processor was running at. And fourth, what he would capture next to confirm or rule out his first guess. That last part is what turns "the computer crashed" into a bug someone can own and fix.

This is a long episode, and it's meant to be. It moves through seven parts. One: what a bug check actually is. Two: the kinds of dump files and what each one contains. Three: symbols, and why a stack full of raw numbers usually means a configuration problem rather than a broken tool. Four: the first five minutes with any dump, command by command. Five: the device and power views, for failures involving hardware and sleep. Six: the stop codes you'll meet most often, explained by meaning. Seven: hangs, which are not crashes at all, and how a kernel debugger gets attached to a real device in the first place. Then a worked triage of Timothy's own planned crash, and a recap.

## The core ideas

Here are today's core ideas, stated plainly. They are the answer key for the walk questions at the end.

One. A bug check is the kernel deliberately stopping the machine because it detected a state it cannot safely continue from. It is a decision, not an accident. The stop code says what kind of failure the kernel detected, and the four parameters add details specific to that code.

Two. A dump is a saved copy of memory and processor state at the moment of failure. The types differ in how much they keep: a minidump keeps the crashing thread's story, a kernel dump keeps all kernel memory, a complete dump keeps everything, and a live dump is a snapshot taken while the machine keeps running.

Three. Symbols, stored in P-D-B files, are what turn raw addresses into function names. A stack full of bare addresses almost always means missing or mismatched symbols, not a broken debugger. Wrong symbols are worse than no symbols, because they produce names that look plausible and lie.

Four. The first five minutes follow a fixed path: bang analyze dash v for an automatic first guess, then k for the stack, then l-m for the loaded modules, then bang thread and bang process to see who was running, then bang irql to see at what priority. The automatic analysis is a hypothesis you check, not a verdict you accept.

Five. Learn each stop code by what it means, not by its parameters. The common ones fall into a few families: touching memory you shouldn't at a raised priority, taking too long at a raised priority, failing to finish a power transition, an exception nobody caught, and the hardware itself reporting failure.

Six. A hang is not a crash, and nothing writes a dump for you. You must break in with a kernel debugger or force a dump, and then ask what every processor is doing and who holds what. Never just reboot a hung machine; that throws the evidence away.

Seven. A kernel debugger runs on a separate host machine and talks to the target over a transport. The modern transport is K-D-net, debugging over a network link. Arm devices commonly run K-D-net over a USB cable that pretends to be an Ethernet adapter, and the firmware describes the debug port to Windows using an ACPI table called debug-two.

Keep these seven in mind. The rest of the episode explains each one with its mechanism.

## Part one: what a bug check actually is

Start with a scenario that Timothy is about to create himself. His TgCounter driver has a lab-only control code that raises the processor's interrupt priority to a level called DISPATCH_LEVEL and then writes through a null pointer, address zero. What happens, step by step?

The processor executes the write instruction. The memory management unit looks up the virtual address zero in the page tables and finds no valid mapping. So the processor takes an exception, a page fault, and jumps into the kernel's page fault handler. Now the kernel has to decide what to do with this fault.

In ordinary circumstances, a page fault is normal. Most page faults are the memory manager's way of noticing that a page needs to be brought in from disk, or that a page was trimmed and needs to be restored. The memory manager resolves the fault, often by waiting for a disk read, and then lets the instruction run again. But here is the key detail. Resolving a page fault might require waiting, and waiting requires the scheduler to switch to another thread. The scheduler itself runs at DISPATCH_LEVEL. So code that is already running at DISPATCH_LEVEL or above cannot wait, because the mechanism that would let it wait is blocked by its own priority level. Timothy derived this rule himself several weeks ago, in his own words: the scheduler lives at a lower level than the code that is currently running.

So the page fault handler checks the IRQL at the moment of the fault. It finds DISPATCH_LEVEL. It cannot resolve any fault at this level, whether the address was valid-but-paged-out or completely invalid like address zero. And it cannot just skip the instruction, because the driver's logic would continue in an unknown state. There is no safe option. So the kernel calls a function named KeBugCheckEx, said "K-E bug check E-X", with a stop code that names this situation: 0xD1, DRIVER_IRQL_NOT_LESS_OR_EQUAL. The name reads oddly, but it means: a driver touched memory at an IRQL that was not less than or equal to the level where touching that memory would have been allowed.

That is the first core idea in action. A bug check is a decision. The kernel detected a condition, judged that continuing would risk corrupting data or the disk, and stopped everything on purpose. This framing matters because it tells you where to look. The question is never "why did Windows crash?" The question is "what did the kernel detect, and who put the system into that state?"

What does KeBugCheckEx actually do? It does a few things in a careful order. It raises the processor to the highest IRQL so nothing can interrupt it. It signals the other processors to stop what they are doing and freeze, so the picture of memory stays consistent. It records the stop code and four parameters. It saves the processor context, which is the register state at the moment of the failure. It shows the blue screen. And then it writes the dump.

Writing the dump is worth a moment, because it explains several surprises later. At this point the kernel cannot trust the file system or most of the drivers, because one of them may be the cause of the crash. So Windows uses a path prepared in advance at boot: a special crash-mode copy of the storage driver stack, and a region of the disk it already knows about, which is the space reserved for the page file. The kernel writes memory directly into that space through the crash-mode path, bypassing the normal file system. On the next boot, Windows finds the dump data in the page file and copies it out to a real file, usually named MEMORY dot D-M-P in the Windows folder, with small dumps going into a folder called Minidump.

Pause here and predict. If the crash itself was caused by the storage driver, the driver for the disk, what happens to the dump?

The answer is that there may be no dump at all. The dump-writing path depends on storage working. This is exactly why one particular stop code, which we'll reach later, INACCESSIBLE_BOOT_DEVICE, so often leaves nothing behind. When the storage path is the problem, you need a different tool: a debugger attached during boot.

Now, the four parameters. Every stop code has four parameters, and their meanings depend entirely on the code. For 0xD1, the first parameter is the address that was referenced, the second is the IRQL at the time, the third says whether it was a read, a write, or an attempt to execute, and the fourth is the address of the instruction that did it. For a different stop code, the four parameters mean completely different things. That's why the advice is to learn what each code means and look up the parameters when you need them. The documentation for each code lists them, and bang analyze dash v prints them with labels.

A common misconception is that the blue screen means the hardware failed, or that Windows itself is buggy. Sometimes that's true. But most bug checks on a stable Windows release are caused by drivers, because drivers are the code that runs in the kernel's address space with the kernel's privileges but was written by someone else, often for a brand-new piece of hardware. On a new device being brought up for the first time, drivers and firmware are immature, and crashes are frequent. A dump is how each of those crashes becomes something specific: this driver, this function, this condition.

## Part two: the kinds of dump files, and what each one keeps

Windows can write several kinds of dump, and the choice is a tradeoff between size and evidence. The setting lives in the system's startup and recovery options, and it's stored in the registry under a key called CrashControl. Timothy already set it in his lab: the value CrashDumpEnabled set to two, which means a kernel memory dump.

Let's go through the types, smallest to largest.

The minidump, also called the small memory dump, is tiny, a few hundred kilobytes. It contains the stop code and parameters, the processor context of the processor that crashed, the crashing thread's kernel stack, some information about the current process and thread, and the list of loaded modules. That's enough to answer "what was the crashing thread doing?" It is not enough to answer most other questions. You cannot follow a pointer to a device extension, because that memory isn't in the file. You cannot look at the other processors in any depth. You cannot walk the device tree. A minidump is a single photograph of one thread.

The kernel memory dump contains all of the memory the kernel was using: every driver's code and data, every kernel stack, the non-paged pool and whatever paged pool was resident, the page tables, the device tree, the I/O requests in flight. It does not contain user-mode memory, which means the private memory of applications. For driver and device work, the kernel dump is the usual choice. Its size depends on how much the kernel was using, typically a fraction of physical RAM.

There's also a setting called automatic memory dump. It's a kernel dump, with the difference that Windows manages the page file size to make sure there's room to write it. It's the default on most modern systems. And there's an active memory dump, which is like a complete dump but leaves out memory that is unlikely to matter, such as pages belonging to virtual machines when the machine is a host.

The complete memory dump contains all physical memory, kernel and user. You need it when the failure involves user-mode processes too, for example when a critical system process dies and you want to see what it was doing, or when a driver and an application share memory. It's as large as the machine's RAM, and it requires a page file at least that large.

Then there is the live dump, which is different in kind. A live dump is a snapshot of kernel memory taken while the machine keeps running. There is no blue screen and no reboot. The kernel briefly pauses things just long enough to make a consistent copy, then continues. You can ask for one yourself: Task Manager has an option on a process's right-click menu called "Create live kernel memory dump file". And Windows takes some live dumps on its own, when a component detects a serious problem that isn't fatal. The graphics driver timing out and being reset is one example. A power-related watchdog firing while the device is supposed to be asleep is another, and we'll meet that one by name later. Live dumps land in a folder called LiveKernelReports inside the Windows folder, often in a subfolder named after the kind of report, such as WATCHDOG.

Why would anyone want a live dump? Because some failures don't crash the machine but still break it. A single device stops working. The battery drains overnight because the machine never reaches its deepest sleep state. A network adapter hangs and gets reset. Crashing the machine to diagnose these would destroy the very state you want to see, and might not even be possible on a machine someone is using. A live dump lets you look without killing.

A live dump has one important limitation. Because the machine kept running while the snapshot was taken, the snapshot might not be perfectly consistent. A pointer might have been updated halfway through. So live dumps are excellent for "what state was this device in, who was holding this request, what were the threads waiting on", and slightly less trustworthy for very fast-changing data.

Pause and predict. Timothy's TgCounter driver keeps a counter in kernel memory. If he takes a live dump right after his client program increments it three times, can he read the value three from the dump?

Yes. The counter lives in the driver's global data, which is kernel memory, which is in a live kernel dump. That is precisely what his lab 5.2 asks him to do: read the same thing from the live machine and from the live dump, and see that they match. The value of that exercise is seeing that a dump is the same memory you were reading live, just frozen.

Here is the guiding rule for choosing: take the smallest dump that still contains the evidence you need. For a crash that is obviously contained in one thread, a minidump might be enough to start. For anything involving devices, power, locks, or other processors, you need at least a kernel dump. For anything involving user-mode processes, a complete dump. And for a machine that's misbehaving but still running, a live dump first, before anyone tries a recovery that would change the state.

## Part three: symbols, and why raw addresses usually mean a configuration problem

Open a dump without symbols and the call stack looks like a column of entries such as "nt plus some large hexadecimal offset", or worse, bare sixteen-digit addresses with nothing attached. Many people's first reaction is that the dump is corrupt or the tool is broken. Almost always, it's neither. WinDbg simply doesn't have the files that map addresses to names.

Here's the mechanism. When a driver or a kernel component is compiled, the compiler and linker produce two outputs. One is the executable image itself, the dot S-Y-S file for a driver or the kernel image for Windows. The other is a program database file, a P-D-B. The P-D-B holds the mapping from addresses in the image to function names, global variable names, data type layouts, and, in the full version, source file names and line numbers. The executable doesn't contain any of that; it's just machine code and data.

So when WinDbg sees an address on a stack, it does two lookups. First, which loaded module contains this address? It knows this from the loaded module list, which records each module's name, start address, and size. Second, within that module, which function contains this offset? For that it needs the module's P-D-B. With the P-D-B, the address becomes something like "TgCounter, exclamation mark, TgDeviceControl, plus 0x2c", which reads as: inside the TgCounter module, in the function TgDeviceControl, forty-four bytes past the start of that function. Without the P-D-B, WinDbg can only say "TgCounter plus some offset from the start of the module", which tells you whose code it is but not which function.

The P-D-B has to be the exact one built alongside the exact binary that was running. Every image carries an identifier, a unique ID plus an age counter, and the P-D-B carries the same identifier. WinDbg checks that they match. If you rebuild your driver, the old P-D-B no longer matches the new binary, even if the source code barely changed, because function addresses shift.

Where do the P-D-B files come from? There are three situations.

For Microsoft's own components, such as the kernel, the HAL, and Microsoft's inbox drivers, Microsoft publishes public symbols on a symbol server on the internet. WinDbg is configured with a symbol path, which tells it where to look. The usual setup says, in words: use the Microsoft symbol server, and cache whatever you download in a local folder. The command dot symfix sets that up automatically, and dot reload tells WinDbg to reload symbols for the loaded modules. Timothy's lab session already showed this working: the default symbol path was "srv star", meaning the symbol server, and kernel functions like KiSwapContext appeared by name.

Public symbols are deliberately partial. They contain function names and the names of global variables, and some type information, but not local variables and not source line numbers. So you can see that the crash happened inside a particular kernel function, but you can't step through its source.

For your own driver, you have the full private P-D-B, because you built it. That's why Timothy's lab guide tells him to add his driver's build output folder to the symbol path with dot sympath plus. With his private P-D-B, WinDbg can show not just the function in TgCounter but the exact source line that faulted.

For a vendor's driver, a driver from a chip maker or a hardware partner, there are often no symbols available at all outside that vendor. You'll see the module name and an offset. That is still a lot of information. It tells you whose code was running, which tells you who needs to look at the problem. In many triage situations, "the top of the stack is in the vendor's touch controller driver, at this offset, here's the dump" is exactly the right handoff.

Now the misconception, and it's an important one. A stack full of raw addresses usually means missing symbols. A stack full of strange, implausible function names usually means wrong symbols. The second is much more dangerous. If WinDbg loads a P-D-B that doesn't match, or if the symbol path forces a mismatched file to be accepted, it will happily turn addresses into names using the wrong map, and you get a stack that looks fine but describes code that wasn't running. Signs of this include warnings in the output about symbols not matching, functions on the stack that make no sense together, and very large offsets like "plus 0x1a3f0" into a function that is obviously small. When you see those, stop and fix symbols before analyzing anything. The command bang sym noisy makes WinDbg narrate where it looks for each symbol file, which tells you exactly what went wrong. And l-m with a v and a module name, written lmvm followed by the name, shows the details of one module, including whether its symbols loaded and from where.

Pause and predict. Timothy rebuilds TgCounter with a one-line change, re-signs it, copies it into the virtual machine, crashes it, and analyzes the dump, but he forgot to point WinDbg at the new build output. What will the stack look like?

The kernel frames will have proper names, because those symbols come from Microsoft's server and the kernel didn't change. The TgCounter frames will either show only "TgCounter plus offset", if WinDbg found no P-D-B, or show names with a warning about mismatched symbols, if it found the old one. The fix is to point the symbol path at the folder that holds the P-D-B produced by the same build as the binary that crashed.

## Part four: the first five minutes with any dump

There is a fixed opening sequence that works for almost every kernel dump. The value of a fixed sequence is that it stops you from tunneling on the first interesting thing you see. Every dump gets the same five questions, in the same order.

### Step one: bang analyze dash v

The command is written with an exclamation mark, "!analyze -v". The exclamation mark means it's an extension command, a plug-in rather than a built-in, and the dash v means verbose. This command does an automatic triage. It reads the stop code and parameters, explains them in words, finds the faulting thread, examines the stack, applies a large set of rules about which modules to blame and which to skip, and produces a guess.

The output has several parts worth knowing by name. At the top, the stop code's name and a short description, followed by the four arguments, labeled. Then a section of keyed facts, things like BUGCHECK_CODE, PROCESS_NAME, and the IRQL. Then STACK_TEXT, the call stack of the faulting thread. Then a line called SYMBOL_NAME, which names the specific function it blames, MODULE_NAME and IMAGE_NAME, which name the module, and a FAILURE_BUCKET_ID, which is a compact label combining the stop code and the blamed function. Microsoft uses failure buckets to group thousands of crash reports from the field into the same underlying bug. There's also a familiar older line, "Probably caused by", followed by a module name.

Here's how to treat the output. It's an excellent first hypothesis, and a hypothesis is all it is. The analyzer's rules are good but they're rules. It sometimes blames the kernel itself, because the kernel's code was on top of the stack, when the real culprit is a driver that passed the kernel a bad pointer two frames down. It sometimes blames a module that was merely the victim of memory corruption caused by someone else. So the habit is: read its conclusion, then check it against the raw evidence with the next four commands.

### Step two: k, the stack

The command k prints the call stack of the current thread. Variants add detail: k-b shows the first few arguments to each function, k-n numbers the frames, and k-v adds more. Read the stack from top to bottom as "most recent first". The top frame is the innermost function, the one that was running at the moment of the bug check. In a crash dump, the top few frames are usually the bug check machinery itself, KeBugCheckEx and some helpers. Just below that, you'll often see a trap handler, the code that ran when the processor took the exception. Below that is the frame that actually caused the problem. And further down is the history of how we got there.

Learning to read the shape of a stack is one of the most useful skills in this whole area. A stack that bottoms out in a system call entry function tells you that this thread started in user mode and called into the kernel, so it was probably running at PASSIVE_LEVEL until something raised it. A stack that bottoms out in an interrupt or DPC dispatch routine tells you this code was running in an interrupt context or as a deferred procedure call, which means a raised IRQL and no ability to wait. A stack that bottoms out in a system thread start routine tells you it's a kernel worker thread. That one fact, what kind of context the code was running in, often explains the crash on its own.

The question to ask of the stack is: which frame is the first one that isn't Microsoft's? Or, if they're all Microsoft's, which frame is the first one where something looks wrong? That frame, and its owner, is your lead.

### Step three: l-m, the loaded modules

The command l-m lists every loaded module, its start and end address, and its symbol status. Its job here is to answer "whose driver is this?" Given a module name from the stack, l-m-v-m with that name gives the details: the full path of the file, the timestamp, the version information, and the company name if the file has one. This is how you decide whether the module on top of the stack is Microsoft's or a vendor's, and which version it is. A crash from a driver dated three years ago on a device that was released last month tells you something.

The module list also tells you what else was loaded. Sometimes the interesting fact is a filter driver, an antivirus driver, or a debugging tool's driver that you didn't expect to be there.

### Step four: bang thread and bang process, who was running

The command bang thread, with no arguments, describes the current thread: its address, its owning process, its state, how long it has been running, what it's waiting on if it's waiting, the IRPs, which are I/O request packets, said "urps", associated with it, and its stack. The command bang process zero zero lists every process on the system in brief: its name, its address, and its ID. The variant bang process with a process address and a detail level shows one process deeply, including all its threads.

Why does this matter? Because it answers whose request this was. If the crashing thread belongs to Timothy's tgclient program, then a user-mode call into his driver led to the crash, and that tells him which request path to examine. If it belongs to the System process, it's a kernel worker or system thread. If it belongs to a service, that service triggered the code path.

### Step five: bang irql, at what level

The command bang irql shows the IRQL of the current processor. In a crash dump there's a subtlety worth knowing. KeBugCheckEx raises the processor to the highest IRQL as it starts, so the live IRQL in the dump would always be "high". To be useful, the debugger reports the IRQL that was saved just before the bug check started, and it says so in its output: "debugger saved IRQL for processor zero". That saved value is the one that matters.

This is a good place to fix a detail precisely, because it's easy to blur. IRQL is not a single number in some shared location in RAM. It's a per-processor priority threshold. Every processor has its own current IRQL. On x64 machines, it lives in a processor register named C-R-8. On Arm64, the kernel tracks it per processor and programs the interrupt controller's priority mask to match. Either way, the important property is that it's per processor. In a dump of a four-processor machine, one processor can be at DISPATCH_LEVEL inside a driver's DPC while the other three sit at PASSIVE_LEVEL running ordinary threads. That's why the command is per processor, and why, for hangs, you'll want to check every processor.

And keep two axes separate in your head. Privilege is whether the processor is in kernel mode or user mode. Priority is the IRQL. Kernel code can run at PASSIVE_LEVEL, the lowest priority, and often does. Privilege says what code may touch; IRQL says what may interrupt it and whether it may wait.

At the end of these five steps, you should be able to say: the stop code means this; the code at the top of the stack belongs to this module, owned by this company, at this version; the thread was running on behalf of this process, in this kind of context; and the IRQL was this. That's the triage note. The only thing left is what to capture next, and that depends on the stop code, which is Part six.

## Part five: the device and power views

Many failures on new hardware involve devices and power transitions, and for those you need to see how Windows views the device tree. Here are the commands, explained by what question each answers.

Bang devnode zero one shows the whole device tree as Windows sees it. Every device Windows knows about is a node in a tree, from the root at the top, through buses like PCI or the system-on-chip's internal buses, down to individual devices. Each node, called a devnode, records which driver serves it and what state it's in: started, stopped, failed, or removed with a problem code. When a device "isn't working", the first question is whether Windows even believes it started. This command answers that.

Bang devstack, given a device object, shows the stack of drivers attached to one device. Remember from Timothy's earlier work on device stacks that each device is served by a stack of drivers: a bus driver at the bottom that discovered the device and created the physical device object, the function driver in the middle that knows how to operate the device, and possibly filter drivers above or below it. A request travels down this stack. When something is stuck, bang devstack shows who is in the path.

Bang drvobj, given a driver name or driver object, shows one driver: its dispatch table, meaning which of its functions handles which kind of request, and the list of device objects it created. Timothy's first lab exercise used exactly this to find TgCounter's dispatch routines and device object inside the live kernel.

Bang irp, given the address of an I/O request packet, shows one in-flight request. An IRP has a stack of its own, with one location per driver it will pass through, and bang irp shows which location is current, meaning which driver is holding it right now, and whether it has been marked pending. This is the core question for anything stuck: who has the request, and why hasn't it come back?

Bang poaction shows the power manager's view of any power transition in progress. If the system was going to sleep, waking up, or shutting down, this command tells you which transition, and which devices still have outstanding power requests. It's the first command for any failure that happens around sleep and resume.

Bang running dash t-i shows what every processor was doing. For each processor it shows the current thread and, with the t, its stack, and with the i, it includes processors that were idle. This is the command for "the whole machine": it immediately shows if one processor is stuck in a loop inside a driver while the others are idle.

And bang dpcs lists the deferred procedure calls queued on each processor, which helps when the failure is about deferred work piling up or one DPC running forever.

These commands work in kernel dumps and in live kernel debugging sessions. Most of them need more than a minidump, because a minidump doesn't contain the device tree or other processors' state. That's another reason driver work defaults to kernel dumps.

## Part six: the stop codes you'll meet most, by meaning

There are hundreds of stop codes, but a small group accounts for most failures during device bring-up. The goal here is to know what each one means, what question it immediately raises, and what to capture next. Notice as we go that they cluster into families. Some are about touching memory you shouldn't. Some are about taking too long at a raised priority. Some are about power transitions. Some are exceptions nobody caught. And some are the hardware reporting its own failure.

### The memory-access family: 0xD1, 0xA, and 0x50

0xD1, DRIVER_IRQL_NOT_LESS_OR_EQUAL, means a driver touched memory at a raised IRQL, where that memory was either invalid or pageable. The address it touched could be completely bogus, such as a null pointer or a freed pointer, or it could be a perfectly valid address of memory that happens to be pageable and was paged out at that moment. Either way, at DISPATCH_LEVEL or above, the fault can't be handled. 0xA, IRQL_NOT_LESS_OR_EQUAL, means the same thing, but the faulting address was in the kernel itself rather than in a driver. In practice, 0xA often still turns out to be a driver's fault: a driver handed the kernel a bad pointer, and the kernel's code tripped over it.

The parameters are especially useful here. Parameter one is the address touched. If it's zero or a small number, you're looking at a null pointer, possibly plus an offset into a structure. Parameter two is the IRQL. Parameter three says read, write, or execute. Parameter four is the instruction that did it.

The interesting split within this family is between a bad pointer and a good pointer to pageable memory. The second is a latent bug. Imagine a driver that reads some pageable data while holding a spin lock. Holding a spin lock raises the processor to DISPATCH_LEVEL. As long as the data happens to be resident in memory, the read works, and the driver passes every test. Then one day, under memory pressure, the page gets trimmed, and the next read at DISPATCH_LEVEL crashes. Timothy's driver contains exactly this bug, deliberately: a lab control code that takes a spin lock and reads a value from paged pool. In his lab, it will probably work fine almost every time. That's the point. The tool that turns this latent bug into a crash every time is Driver Verifier, which, with its IRQL checking option, deliberately pages out pageable memory whenever a driver raises its IRQL. Under Verifier, the "works on my machine" bug becomes a deterministic stop.

0x50, PAGE_FAULT_IN_NONPAGED_AREA, means something touched a kernel address that is simply invalid: not pageable, not paged out, just nothing there. The classic causes are use-after-free, where a driver frees memory and then keeps using a pointer to it, and wild pointers from corrupted structures. The parameters give the address, whether it was a read or a write, and the instruction. If the address looks like it was once a valid pool allocation, think use-after-free. The next capture is usually to turn on Driver Verifier's special pool for the suspect driver. Special pool places each allocation right against an inaccessible page and keeps freed memory inaccessible, so the bad access crashes immediately, at the exact instruction, instead of later, somewhere else.

### The "too long at raised priority" family: 0x133 and 0x101

0x133, DPC_WATCHDOG_VIOLATION, means the system spent too long at DISPATCH_LEVEL or above. Windows has a watchdog that counts how long each processor stays at that level. Parameter one distinguishes the two cases. A value of zero means a single DPC or interrupt service routine ran past its time allowance. In that case, the offending code is usually right there on the stack, because it was still running when the watchdog fired. A value of one means the processor cumulatively spent too long at DISPATCH_LEVEL or above, perhaps through many DPCs in a row, or through code that raised the IRQL, for example by holding a spin lock, and then did a long operation. In the cumulative case, the stack may show whoever happened to be running at the moment the limit was crossed, which isn't necessarily the guilty party. Microsoft's own guidance for that case is to use event tracing to measure how long each driver's DPCs actually run.

This stop code connects directly to a point Timothy has been sharpening. Deferred work at DISPATCH_LEVEL can't block. It can't wait for a device, it can't sleep, and it can't wait on a lock that a lower-priority thread holds. A DPC that tries to "wait" by spinning, polling a hardware register in a loop until a bit changes, doesn't technically block, but it holds the processor at DISPATCH_LEVEL for as long as the hardware takes. If the hardware is slow or never responds, the DPC watchdog eventually fires and you get 0x133. So the fix for a 0x133 almost always has the same shape: move the slow or waiting part out of the DPC into a context that may wait, such as a work item running at PASSIVE_LEVEL, and keep the DPC short.

Why does this watchdog exist at all? Partly because on tablets and other devices without keyboards, a processor stuck forever at a raised IRQL would otherwise produce a silent freeze that nobody could break into. The watchdog converts an endless hang into a crash with a dump.

0x101, CLOCK_WATCHDOG_TIMEOUT, is a different thing, and the distinction is important. Each processor regularly receives a clock interrupt. If one processor stops responding to clock interrupts for too long, another processor notices and issues the bug check. So 0x101 means a processor went completely silent. Not just busy at DISPATCH_LEVEL, but not even taking the clock interrupt. That points toward something running with interrupts fully masked, a processor stuck in firmware or in a hypervisor, or a hardware problem with the processor or its interrupt controller.

Here is a trap that catches a lot of people. In a 0x101 dump, the current processor, the one whose stack you see first, is usually the one that noticed, not the one that hung. Parameter four tells you the index of the processor that stopped responding. You have to switch to that processor's context to see what it was doing, which you do with a tilde, then the processor number, then s. And for that to work, the dump must contain the other processors' state, which a minidump typically doesn't. So for 0x101, a kernel dump or larger is essential, and if the hung processor's context is empty or unreadable, that itself is evidence that it was stuck somewhere Windows couldn't see, such as in firmware.

### The power family: 0x9F and 0x15F

0x9F, DRIVER_POWER_STATE_FAILURE, means a driver didn't finish a power transition in time. When Windows puts the system to sleep, wakes it, or changes a device's power state, it sends power requests, power IRPs, down each device's stack, and each driver must complete them. A watchdog times each one. If a driver holds a power IRP too long, for example because it's waiting for hardware that never answers, or because it forgot to pass the request down to the driver below it, the watchdog fires.

Two values of parameter one cover most cases. When it's three, a device object blocked a power IRP for too long. Parameter two is the physical device object of the stuck device, and parameter four is the blocked IRP itself. So the recipe is direct: run bang irp on parameter four to see which driver currently holds the request, then bang devstack on parameter two to see the whole stack for that device, then bang poaction to see the overall transition. Very often you'll find the IRP sitting at a vendor's function driver, marked pending, with no sign that it was ever passed down. When parameter one is four, the timeout happened while the power manager was synchronizing with Plug and Play, the system that starts and stops devices, and the stuck thread is usually the one to look at.

0x15F, CONNECTED_STANDBY_WATCHDOG_TIMEOUT_LIVEDUMP, isn't a crash at all. It's a live dump identifier: the machine kept running, and the code can never appear on an actual blue screen. It belongs to Modern Standby, the phone-like sleep mode in which the screen is off but the system stays connected. In that mode, the goal is to reach the deepest idle state of the whole platform, called DRIPS, said "drips", short for deepest runtime idle platform state. If the system sits in the screen-off standby phase for too long without reaching DRIPS, the watchdog takes a live dump so someone can see why. The first parameter gives a sub-code describing which kind of blocker: a device that wouldn't go idle, the platform's power engine vetoing deep sleep, or simply too much activity. The practical cause is anything that keeps the system from going quiet: a device left in an insufficient low-power state, a timer firing too often, a driver holding something active. The symptom a user sees is a battery that drains overnight.

This is a good example of why live dumps exist. Nothing crashed. But something is wrong, and the snapshot shows which device or component was keeping the system awake. It connects to Timothy's earlier reading on power management and battery life.

### The uncaught exception family: 0x7E and 0x3B

0x7E, SYSTEM_THREAD_EXCEPTION_NOT_HANDLED, means code running in a system thread raised an exception that nobody caught. An exception here means things like an access violation, a divide by zero, or an illegal instruction, which the processor reports and the kernel then looks for a handler for. In a system thread, if there's no handler, the result is a bug check.

0x3B, SYSTEM_SERVICE_EXCEPTION, is similar, except that the exception happened while the kernel was executing a system call on behalf of a user-mode program.

The extra step these codes require is important. The stack you see first with k is the stack of the bug check machinery, after the exception happened. To see the code that actually raised the exception, you have to switch to the context that was saved at the moment of the exception. For 0x7E, parameters three and four are the addresses of the exception record and the context record. The command dot e-x-r on the exception record shows what kind of exception it was and where. The command dot c-x-r on the context record switches the debugger's view to the register state at the moment of the exception, and then k shows the real stack, the one where the fault happened. For 0x3B, parameter four is the context record, so it's dot c-x-r on that. Forgetting this step is one of the most common mistakes in reading these dumps, because the default stack looks like it's all exception-handling code in the kernel.

### The boot and system integrity family: 0x7B and 0xEF

0x7B, INACCESSIBLE_BOOT_DEVICE, means Windows started loading, the boot loader handed control to the kernel, but the kernel couldn't reach the disk it booted from. So the very next thing it needed, reading the rest of itself and its registry from disk, failed. Causes include a missing or failing storage driver, the wrong storage controller mode set in firmware, a disk or partition layout that doesn't match what the boot configuration expects, or a corrupted image. On new hardware, it's often that the storage controller's driver isn't included in the image, or the firmware's description of the storage controller doesn't match what the driver expects.

As we predicted earlier, 0x7B often leaves no dump, because the dump-writing path needs the same storage that just failed. So the tool for 0x7B is usually a kernel debugger attached from boot, or the boot logs, rather than a dump.

0xEF, CRITICAL_PROCESS_DIED, means a process Windows can't live without has exited. A few user-mode processes are marked critical, including the session manager, the Windows subsystem process, and the process that starts services. If any of them terminates, for any reason, the kernel stops the system rather than continue without it. The first parameter is the process object, and bang process on it shows which one. The interesting thing is that the cause is often in user mode, for example a crash inside that process, or something deliberately killing it. So 0xEF is a case where a complete dump, including user-mode memory, can be worth the size.

### The hardware family: 0x124

0x124, WHEA_UNCORRECTABLE_ERROR, said "wee-uh", means the hardware itself reported a fatal error. WHEA stands for Windows Hardware Error Architecture, the framework through which processors, memory controllers, buses like PCI Express, and the platform firmware report errors. Correctable errors, such as a single flipped bit that error-correcting memory repairs, are logged and the system continues. An uncorrectable error means the hardware told Windows that data may be corrupt, so Windows stops.

The parameters point to a hardware error record, and the command bang errrec on that address decodes it: which component reported the error, what kind, and where. The analysis here is different from a driver bug. You're not looking for a function to blame. You're looking for which piece of hardware complained, and whether that's consistent across crashes. A pattern of errors from the same memory region or the same bus link points to hardware or to the firmware that configures it. On a new platform, that might mean incorrect voltage or timing settings, or a defective board, and the evidence goes to the hardware and firmware teams.

## Part seven: hangs are not crashes

Now consider a different failure. The screen freezes. The mouse doesn't move. Nothing responds. There's no blue screen. After a few minutes, someone holds the power button and the machine reboots.

That is the worst possible outcome, because all the evidence was in memory and it's gone. Unlike a crash, a hang writes no dump by itself, because the kernel never detected anything and never called KeBugCheckEx. The core rule for hangs is: never just reboot a hung machine. First, get the evidence out.

There are three ways to do that.

The first is a kernel debugger that's already attached. If a host machine is connected as a kernel debugger, you can break in at any time. Breaking in freezes the target, and then you can inspect everything live: every processor, every thread, every lock. You can also write a dump from inside the debugger with the dot dump command before letting the machine go.

The second is forcing a crash. Windows can be configured, in advance, to bug check on demand. The classic method is a keyboard sequence: with a registry setting named CrashOnCtrlScroll enabled, holding the right Control key and pressing Scroll Lock twice produces bug check 0xE2, MANUALLY_INITIATED_CRASH. That gives you a normal crash dump of the hung state. Servers and some machines can also send a non-maskable interrupt, an NMI, from a management controller or a button, which produces bug check 0x80. And on devices that have a hardware power button routed through firmware to Windows, there's a feature that fits tablets and laptops well. With a registry value enabled, holding the power button for about seven seconds, and releasing it before the firmware's hard reset at around ten, triggers bug check 0x1C8, MANUALLY_INITIATED_POWER_BUTTON_HOLD, and writes a dump. There's even a live dump variant that captures the state without rebooting. For a device with no keyboard, this is how a hang becomes a dump.

The third is the watchdogs. As we discussed, some hangs eventually convert themselves into crashes: 0x133 if a processor is stuck at DISPATCH_LEVEL or above, 0x101 if a processor stops taking clock interrupts, 0x9F if the hang is a stuck power transition. But many hangs never trip a watchdog. A deadlock between ordinary threads at PASSIVE_LEVEL can last forever without any watchdog noticing.

Once you have the evidence, the question changes. For a crash, the question is "which instruction did the kernel object to?" For a hang, there is no faulting instruction. The question is "what is every processor doing, and who holds what?"

It helps to classify a hang into one of two shapes.

The first is a busy hang. One or more processors are spinning at a raised IRQL, perhaps stuck in a DPC that's polling hardware, or spinning on a spin lock that another processor holds and will never release. Bang running dash t-i shows this immediately: one processor's stack is inside a driver at DISPATCH_LEVEL, and its run time is huge. If two processors are each spinning, waiting for a lock the other one holds, that's a spin lock deadlock.

The second is an idle hang, or a deadlock. Every processor is idle or running unrelated work, but the threads the user cares about are all waiting for something that never arrives. Thread A holds lock one and waits for lock two; thread B holds lock two and waits for lock one. Or a thread waits for an I/O request that a driver marked pending and then never completed. Here, bang running shows nothing interesting, and that is the clue. You turn instead to commands that show waiting threads. Bang stacks summarizes the stacks of all threads, so you can search for threads waiting in a particular driver. Bang locks shows kernel resource locks, who owns them, and who is waiting. And bang irp on any stuck request shows which driver is holding it.

Pause and predict. A device's touch input stops working, but the rest of the system runs fine. Is that a crash, a hang, or something else? And what do you capture?

It's neither a system crash nor a system hang. It's a dead device. The system is healthy except for one device, and the evidence is the state of that one device's stack and its requests. The right first move is a live dump, taken before anyone tries a recovery such as disabling and re-enabling the device, because recovery resets the very state you want to see. Then bang devnode to see whether Windows thinks the device is started, bang devstack for its driver stack, and bang irp on any requests pending inside it.

## Part eight: attaching a kernel debugger to a real device

So far we've assumed you can get into the machine with a debugger. On Timothy's virtual machine, he uses local kernel debugging: WinDbg running inside the same Windows it's examining, with the "L-K-D" prompt. Local kernel debugging is useful for reading memory, which is exactly what his first labs need. But it has hard limits. You can't break in, because the debugger would freeze the machine it's running on. You can't set breakpoints. And you can't debug a crash or a hang, because the debugger itself would be frozen too. For real kernel debugging, the debugger has to live on a different machine.

The arrangement always has two parts. The host is the machine running WinDbg, usually a developer's PC. The target is the machine being debugged, the device. They connect over a transport, and the target's boot configuration is set up to enable kernel debugging over that transport. The target's kernel includes a small, self-contained debug engine that can talk to the host even when the rest of Windows is frozen. That's what makes breaking in possible: the debug transport doesn't use Windows' normal drivers, it uses a minimal private path to the hardware, much like the crash dump path uses a private path to storage.

Historically, the transport was a serial cable, then FireWire, then special USB debug cables. The modern, recommended transport is K-D-net, kernel debugging over a network. The target's boot configuration names the host's IP address, a port number, and a key that both sides share. Windows includes a utility, kdnet dot exe, that checks whether a network adapter supports debugging and sets the configuration. On the target, the kernel's debug engine uses its own small driver for the network hardware. That's why K-D-net only works on network adapters that Microsoft or the vendor has written a debug transport module for.

Arm devices, such as laptops and tablets built on Arm processors, add a twist. Many don't have a supported wired network adapter at all. The common solution is K-D-net over USB in Ethernet emulation mode, often written as K-D-net E-E-M U-S-B. The device's USB port, using a USB controller that supports this, presents itself to the host as a network adapter over a USB cable. On the host, a network adapter named for K-D-net USB E-E-M appears, and K-D-net runs over it exactly as if there were an Ethernet cable. On a Surface Pro X, for example, the documentation names the specific USB-C port to use.

But how does Windows on the target know which USB controller to use for debugging, and where its registers are, before any normal drivers have loaded? On PCs with a standard PCI layout, the configuration can name the device by its PCI bus location. On Arm systems, devices often aren't on PCI at all; they're blocks inside the system-on-chip at fixed addresses. So the firmware describes the debug ports to Windows with an ACPI table called DBG2, said "debug two", the Microsoft Debug Port Table version two. ACPI is the set of tables the firmware hands to the operating system to describe the hardware. The DBG2 table is a list of entries, each describing one debug-capable device: its type, such as serial or network, its subtype, which identifies the specific hardware, and the addresses of its registers. The debugging configuration's bus parameters then just pick an entry from this list by number. Entry zero is usually reserved for a serial port, so on Arm devices the USB debug entry is commonly entry one.

Why does this matter beyond setup? Because on a brand-new device, the debug connection itself can be the first thing that doesn't work. If the firmware's DBG2 table is missing an entry, or describes the controller with the wrong registers, the debugger can't connect, and then every other problem gets harder. Knowing that the debug port is described by firmware through DBG2 tells you where to look: is the table present, is the entry correct, and does the USB controller match the transport module Windows expects?

## Putting it together: a worked triage of Timothy's own crash

Let's walk through the dump Timothy is about to produce in lab 5.3, using the first five minutes exactly as described. Treat each step as a prediction to check against what the lab actually shows.

He runs his client with the crash argument. The client opens the device and sends the lab-only control code. The I/O manager builds an IRP and calls TgCounter's device control routine at PASSIVE_LEVEL, on the client's thread. The driver raises the IRQL to DISPATCH_LEVEL and writes through a null pointer. The page fault handler finds IRQL at DISPATCH_LEVEL and a driver address involved, and calls KeBugCheckEx. The virtual machine shows a blue screen, writes the kernel dump into the page file space, and reboots. On the next boot, MEMORY dot D-M-P appears in the Windows folder.

He opens it in WinDbg with the symbol path pointing at both the Microsoft symbol server and his driver's build folder.

Step one, bang analyze dash v. Predict the stop code: 0xD1, DRIVER_IRQL_NOT_LESS_OR_EQUAL. Predict the parameters: parameter one, the address referenced, is zero. Parameter two, the IRQL, is two, which is DISPATCH_LEVEL. Parameter three is one, meaning a write. Parameter four is an address inside TgCounter. The analyzer should name TgCounter as the module, and with his private symbols, name the function and even the source line.

Step two, k. From the top: the bug check functions, then the kernel's trap handling for the fault, then TgCounter's device control function, then the I/O manager's functions that dispatch a request to a driver, then the system call entry for the device control call, and at the bottom, the transition from user mode. Reading the bottom, he sees this thread came from user mode through a system call. Reading the middle, he sees his driver's function. Nothing else in the chain looks suspicious.

Step three, l-m-v-m TgCounter. It shows his file path, today's timestamp, and that symbols loaded from his build folder. It's not Microsoft's; it's his.

Step four, bang thread. The thread belongs to the tgclient process. This crash was triggered by a user-mode request, which tells him the exact entry point: the control code dispatch.

Step five, bang irql. The debugger's saved IRQL for that processor reads two, DISPATCH_LEVEL. That matches parameter two.

His triage note, in four lines, would read: Stop 0xD1, a driver wrote to address zero at DISPATCH_LEVEL. The top non-kernel frame is TgCounter's device control routine, which is my driver, not Microsoft's. The IRQL was DISPATCH_LEVEL, raised by the driver itself. Next capture: none needed for this one, since the source line is known; for a real bug of this shape I'd check where the pointer came from and run Driver Verifier on the driver to catch related mistakes.

Now compare this to a realistic version with a vendor driver and no private symbols. The note would read: Stop 0xD1, a driver read address 0x28 at DISPATCH_LEVEL, which looks like a null structure pointer plus an offset. The top non-Microsoft frame is in the vendor's touch driver, at an offset with no symbols, file dated a particular day. IRQL was DISPATCH_LEVEL, and the stack bottoms out in a DPC, so this ran in deferred interrupt processing. Next capture: a kernel dump with Driver Verifier enabled on that driver, the driver version and its symbols from the vendor, and a reproduction rate. That note is a complete, owned bug. It names a module, an owner, a context, and an action.

## Common misconceptions, gathered in one place

Several misconceptions came up along the way. Here they are together.

First, "the blue screen means Windows is broken." Usually it means the kernel detected someone breaking a rule, and most often that someone is a driver.

Second, "bang analyze dash v gave me the answer." It gave you a hypothesis. Check it against the stack, the modules, the thread, and the IRQL. Be especially suspicious when it blames the kernel itself, or when memory corruption is possible.

Third, "the stack is all garbage, the dump is corrupt." Almost always, symbols are missing or mismatched. Fix symbols first.

Fourth, "a minidump is enough." It's enough for the crashing thread's story. It's not enough for devices, power, other processors, or following pointers.

Fifth, "the top frame is the culprit." The top frames are usually the bug check machinery. For exceptions, you need to switch context with dot c-x-r before the stack means anything. For 0x101, the processor you see first is the one that noticed, not the one that hung.

Sixth, "if it hangs, reboot and try again." Rebooting destroys the evidence. Break in, force a dump, or take a live dump first.

Seventh, "IRQL is a global setting." It's per processor. Check every processor in a hang.

Eighth, "the code passed every test, so a 0xD1 must be from elsewhere." Touching pageable memory at a raised IRQL is a latent bug that passes tests until the page is trimmed. Driver Verifier exists to make those bugs crash every time.

## Connections to what Timothy already knows

This episode sits on top of things Timothy has built and studied. His IRQL derivation, the scheduler living below the running code, is exactly why 0xD1 and 0xA exist. His work separating privilege from priority is what makes bang irql meaningful. His earlier insight that blocking work can't go in a DPC is the whole story behind 0x133. His reading on device stacks is what makes bang devstack and bang irp readable: an IRP stuck at one location in a stack is stuck at one driver. His reading on power management and Modern Standby is the background for 0x9F and 0x15F. And his lab is the place to make all of it concrete: in lab 5.1 he reads his driver's data from the live kernel; in 5.2 he reads the same data from a live dump; in 5.3 he crashes and triages exactly as in the worked example; and in 5.4 Driver Verifier turns his deliberate paged-memory bug into a reliable crash.

The target he set for himself is five written triage notes. Each note is four lines: the stop code in plain words, the module on top and its owner, the IRQL, and the next capture. The first can come from his own 0xD1. Others can come from Microsoft's NotMyFault tool, which crashes a machine on purpose in several different ways, or from his own Verifier lab.

## Recap

Let's restate the core ideas in slightly different words.

A bug check is a deliberate stop. The kernel found a state it couldn't safely continue from. The stop code names the category; the four parameters are details you look up for that code.

Dumps trade size for evidence. A minidump tells the crashing thread's story. A kernel dump holds all kernel memory and is the usual choice for driver work. A complete dump adds user-mode memory. A live dump captures the kernel while the machine keeps running, for failures that don't crash. Pick the smallest that contains your evidence.

Symbols turn addresses into names. Microsoft's public symbols come from its symbol server. Your own driver's private P-D-B gives you source lines. Vendor drivers often have no symbols outside the vendor, but the module name still tells you whose code it is. Raw addresses mean missing symbols; implausible names mean wrong ones.

The first five minutes are always the same: bang analyze dash v for a guess, k for the stack, l-m for whose module, bang thread and bang process for who was running, bang irql for the priority. Then write the four-line note.

Stop codes come in families. Touching bad or pageable memory at raised IRQL: 0xD1, 0xA, 0x50. Too long at raised priority, or a processor gone silent: 0x133, 0x101. Power transitions not finishing, or standby not reaching deep idle: 0x9F, and the live dump 0x15F. Uncaught exceptions: 0x7E and 0x3B, where you must switch to the saved context. Boot and system integrity: 0x7B and 0xEF. Hardware reporting failure: 0x124.

Hangs write nothing by themselves. Break in, force a dump with the keyboard, an NMI, or a long power-button hold, or let a watchdog catch it. Then ask what every processor is doing and who holds what.

A kernel debugger needs a separate host. K-D-net over a network is the modern transport, and on Arm devices it commonly runs over USB in Ethernet emulation mode, with the debug port described by the firmware's DBG2 ACPI table.

## Walk questions

Here are three questions to answer out loud on the next walk.

One. Walk through what happens, step by step, from the moment a driver reads a pageable address while holding a spin lock to the moment a dump file exists on disk. Include why the page fault can't be handled, which stop code results, what the second parameter will show, and why this bug might pass every test without Driver Verifier.

Two. You open a dump and the stop code is 0x101. Explain what it means, why the stack you see first is probably not the one you want, which parameter tells you where to look, and why a minidump might not be enough.

Three. A tablet freezes completely, with no blue screen. Explain why rebooting is the wrong first move, name two ways to get a dump from it, and describe how you'd tell a busy hang from a deadlock once you have the evidence.

Sources, not meant to be read aloud: Microsoft Learn's bug check reference pages for 0x133, 0x15F, and 0x1C8; the Kernel Live Dump Code Reference; Forcing a System Crash with the Power Button; and Setting Up Kernel-Mode Debugging over USB EEM on an Arm Device using KDNET, which describes the DBG2 bus parameters.
